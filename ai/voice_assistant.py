"""
ai/voice_assistant.py — Voice recognition + Gemini-powered command execution.

Flow:
  1. Speech → text  (Google STT, free, no key)
  2. Built-in pattern match (instant, no API call needed)
  3. If no match → Gemini reads intent → returns JSON action → executor runs it

Gemini returns structured JSON like:
  {"action": "launch", "app": "spotify"}
  {"action": "hotkey", "keys": ["ctrl", "t"]}
  {"action": "reply", "text": "The capital of France is Paris."}
"""
import os, re, json, threading, logging
logger = logging.getLogger(__name__)

try:
    import speech_recognition as sr
    _SR = True
except ImportError:
    _SR = False
    logger.warning("SpeechRecognition not installed — voice disabled.")

try:
    import google.generativeai as genai
    _GEMINI = True
except ImportError:
    _GEMINI = False
    logger.warning("google-generativeai not installed. Run: pip install google-generativeai")

# ── Built-in launch patterns (instant, no Gemini needed) ─────────────────────
_LAUNCH = {
    r"(open|launch|start|run)\s+(chrome|google chrome|browser)":        "chrome",
    r"(open|launch|start|run)\s+(firefox|mozilla)":                     "firefox",
    r"(open|launch|start|run)\s+(edge|microsoft edge)":                 "edge",
    r"(open|launch|start|run)\s+(vs\s*code|vscode|visual studio code|code editor)": "code",
    r"(open|launch|start|run)\s+spotify":                               "spotify",
    r"(open|launch|start|run)\s+(terminal|cmd|command prompt)":         "terminal",
    r"(open|launch|start|run)\s+notepad":                               "notepad",
    r"(open|launch|start|run)\s+(calc|calculator)":                     "calculator",
    r"(open|launch|start|run)\s+(explorer|file explorer|files)":        "explorer",
    r"(open|launch|start|run)\s+word":                                  "word",
    r"(open|launch|start|run)\s+excel":                                 "excel",
    r"(open|launch|start|run)\s+(powerpoint|presentation)":             "powerpoint",
    r"(open|launch|start|run)\s+(teams|microsoft teams)":               "teams",
    r"(open|launch|start|run)\s+slack":                                 "slack",
    r"(open|launch|start|run)\s+vlc":                                   "vlc",
    r"(open|launch|start|run)\s+steam":                                 "steam",
    r"(open|launch|start|run)\s+discord":                               "discord",
    r"(open|launch|start|run)\s+zoom":                                  "zoom",
    r"(open|launch|start|run)\s+paint":                                 "mspaint",
    r"(open|launch|start|run)\s+outlook":                               "outlook",
}

# ── Built-in system shortcuts (instant, no Gemini needed) ────────────────────
_CMDS = {
    r"(take|capture|grab)\s+(a\s+)?screenshot":   {"type":"hotkey","keys":["win","shift","s"]},
    r"\bmute\b":                                   {"type":"key","key":"volumemute"},
    r"volume\s+up":                                {"type":"key","key":"volumeup"},
    r"volume\s+down":                              {"type":"key","key":"volumedown"},
    r"(close|quit|exit)\s+(window|app|this)":      {"type":"hotkey","keys":["alt","f4"]},
    r"\bminimize\b":                               {"type":"hotkey","keys":["win","down"]},
    r"\bmaximize\b":                               {"type":"hotkey","keys":["win","up"]},
    r"show\s+desktop":                             {"type":"hotkey","keys":["win","d"]},
    r"(new|open)\s+tab":                           {"type":"hotkey","keys":["ctrl","t"]},
    r"close\s+tab":                                {"type":"hotkey","keys":["ctrl","w"]},
    r"(next|forward)\s+tab":                       {"type":"hotkey","keys":["ctrl","tab"]},
    r"(prev|previous|back)\s+tab":                 {"type":"hotkey","keys":["ctrl","shift","tab"]},
    r"\b(copy)\b":                                 {"type":"hotkey","keys":["ctrl","c"]},
    r"\b(paste)\b":                                {"type":"hotkey","keys":["ctrl","v"]},
    r"\bundo\b":                                   {"type":"hotkey","keys":["ctrl","z"]},
    r"\bredo\b":                                   {"type":"hotkey","keys":["ctrl","y"]},
    r"\b(save)\b":                                 {"type":"hotkey","keys":["ctrl","s"]},
    r"select\s+all":                               {"type":"hotkey","keys":["ctrl","a"]},
    r"\b(find|search\s+in\s+page)\b":              {"type":"hotkey","keys":["ctrl","f"]},
    r"zoom\s+in":                                  {"type":"hotkey","keys":["ctrl","equal"]},
    r"zoom\s+out":                                 {"type":"hotkey","keys":["ctrl","minus"]},
    r"(task\s*manager)":                           {"type":"hotkey","keys":["ctrl","shift","escape"]},
    r"(lock|lock\s+screen|lock\s+computer)":       {"type":"hotkey","keys":["win","l"]},
    r"(switch\s+window|alt\s+tab)":                {"type":"hotkey","keys":["alt","tab"]},
    r"(refresh|reload)":                           {"type":"hotkey","keys":["ctrl","r"]},
    r"go\s+back":                                  {"type":"hotkey","keys":["alt","left"]},
    r"go\s+forward":                               {"type":"hotkey","keys":["alt","right"]},
    r"(full\s*screen|fullscreen)":                 {"type":"key","key":"f11"},
    r"(play|pause)":                               {"type":"key","key":"space"},
    r"next\s+(track|song)":                        {"type":"hotkey","keys":["ctrl","right"]},
    r"prev(ious)?\s+(track|song)":                 {"type":"hotkey","keys":["ctrl","left"]},
    r"(new\s+window)":                             {"type":"hotkey","keys":["ctrl","n"]},
    r"(print)":                                    {"type":"hotkey","keys":["ctrl","p"]},
}

# ── Gemini system prompt for structured command parsing ───────────────────────
_GEMINI_PROMPT = """You are GestureOS AI — an assistant embedded in a hand-gesture computer control app.

When the user gives a command, respond ONLY with a valid JSON object (no markdown, no explanation).

JSON schema:
  {"action": "launch",  "app": "<app_name>"}           — open an application
  {"action": "hotkey",  "keys": ["ctrl","t"]}           — keyboard shortcut
  {"action": "key",     "key": "<key_name>"}            — single key press
  {"action": "close",   "app": "<app_name_or_window>"}  — close an app
  {"action": "type",    "text": "<text_to_type>"}       — type text
  {"action": "reply",   "text": "<your_answer>"}        — answer a question / chat

Available app names: chrome, firefox, edge, code, spotify, terminal, notepad,
calculator, explorer, word, excel, powerpoint, teams, slack, vlc, steam, discord,
zoom, paint, outlook

Key names follow pyautogui convention: ctrl, alt, shift, win, tab, enter, escape,
space, f1-f12, left, right, up, down, home, end, delete, backspace, volumeup,
volumedown, volumemute, etc.

Examples:
  User: "open youtube"       → {"action": "launch", "app": "chrome"}  (then note: user can navigate manually)
  User: "open spotify"       → {"action": "launch", "app": "spotify"}
  User: "close this"         → {"action": "hotkey", "keys": ["alt", "f4"]}
  User: "press enter"        → {"action": "key", "key": "enter"}
  User: "type hello world"   → {"action": "type", "text": "hello world"}
  User: "what time is it"    → {"action": "reply", "text": "I don't have access to real-time data, but you can check your taskbar clock."}
  User: "what is python"     → {"action": "reply", "text": "Python is a high-level programming language known for its simplicity."}

Always return ONLY the JSON object. No other text.
"""


class VoiceAssistant:
    def __init__(self, cfg, executor, on_transcript=None):
        self.cfg            = cfg
        self.executor       = executor
        self.on_transcript  = on_transcript
        self._running       = False
        self._model         = None
        self._chat          = None

        key = cfg.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        if _GEMINI and key:
            try:
                genai.configure(api_key=key)
                self._model = genai.GenerativeModel(
                    model_name=cfg.GEMINI_MODEL,
                    system_instruction=_GEMINI_PROMPT,
                )
                self._chat = self._model.start_chat(history=[])
                logger.info("Gemini AI ready (model: %s).", cfg.GEMINI_MODEL)
            except Exception as e:
                logger.warning("Gemini init failed: %s", e)
        else:
            logger.info("No GEMINI_API_KEY — AI chat disabled (built-in commands still work).")

    # ── voice loop ────────────────────────────────────────────────────────────

    def listen_loop(self):
        if not _SR:
            return
        self._running = True
        rec = sr.Recognizer()
        rec.energy_threshold         = 280
        rec.dynamic_energy_threshold = True
        rec.pause_threshold          = 0.55
        try:
            with sr.Microphone() as src:
                rec.adjust_for_ambient_noise(src, duration=1)
                logger.info("Voice assistant listening...")
                while self._running:
                    try:
                        audio = rec.listen(src, timeout=5, phrase_time_limit=10)
                        text  = rec.recognize_google(
                            audio, language=self.cfg.VOICE_LANGUAGE
                        ).lower().strip()
                        logger.info("Heard: %r", text)
                        self._handle(text)
                    except sr.WaitTimeoutError:
                        pass
                    except sr.UnknownValueError:
                        pass
                    except Exception as e:
                        logger.debug("Voice error: %s", e)
        except Exception as e:
            logger.warning("Microphone unavailable: %s", e)

    def stop(self):
        self._running = False

    # ── command handling ──────────────────────────────────────────────────────

    def _handle(self, text):
        # 1. instant launch match
        for pat, app in _LAUNCH.items():
            if re.search(pat, text):
                self.executor.execute({"type": "launch", "app": app})
                self._notify(text, f"Opening {app}…")
                return

        # 2. instant system shortcut
        for pat, action in _CMDS.items():
            if re.search(pat, text):
                self.executor.execute(action)
                self._notify(text, "Done ✓")
                return

        # 3. Gemini structured execution
        if self._chat:
            self._gemini_execute(text)
        else:
            self._notify(text, "(No Gemini key — set GEMINI_API_KEY to enable AI commands)")

    def _gemini_execute(self, text):
        """Send to Gemini, parse JSON response, execute action."""
        try:
            response = self._chat.send_message(text)
            raw      = response.text.strip()
            logger.debug("Gemini raw: %s", raw)

            # Strip markdown code fences if Gemini wraps in ```json
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"\s*```$",          "", raw, flags=re.MULTILINE)
            raw = raw.strip()

            data   = json.loads(raw)
            action = data.get("action", "reply")

            if action == "launch":
                app = data.get("app", "")
                self.executor.execute({"type": "launch", "app": app})
                self._notify(text, f"Opening {app}…")

            elif action == "hotkey":
                keys = data.get("keys", [])
                self.executor.execute({"type": "hotkey", "keys": keys})
                self._notify(text, f"Pressed {' + '.join(keys)}")

            elif action == "key":
                k = data.get("key", "")
                self.executor.execute({"type": "key", "key": k})
                self._notify(text, f"Pressed {k}")

            elif action == "type":
                import pyautogui
                pyautogui.PAUSE = 0.0
                pyautogui.typewrite(data.get("text", ""), interval=0.04)
                self._notify(text, f"Typed: {data.get('text','')}")

            elif action == "close":
                # Try Alt+F4 as fallback
                self.executor.execute({"type": "hotkey", "keys": ["alt", "f4"]})
                self._notify(text, f"Closed window")

            elif action == "reply":
                reply_text = data.get("text", "")
                self._notify(text, reply_text)

            else:
                self._notify(text, raw)

        except json.JSONDecodeError:
            # Gemini returned plain text — show it as reply
            self._notify(text, raw if raw else "(No response)")
        except Exception as e:
            logger.warning("Gemini execute error: %s", e)
            self._notify(text, f"(Error: {e})")

    def _notify(self, user_text, reply):
        logger.info("Reply: %s", reply)
        if self.on_transcript:
            self.on_transcript(user_text, reply)
