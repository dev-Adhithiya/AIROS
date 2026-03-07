"""ai/voice_assistant.py — Background voice recognition + AI chat."""
import os, re, threading, logging
logger = logging.getLogger(__name__)

try:
    import speech_recognition as sr
    _SR = True
except ImportError:
    _SR = False
    logger.warning("SpeechRecognition not installed — voice disabled.")

try:
    from openai import OpenAI as _OAI
    _OPENAI = True
except ImportError:
    _OPENAI = False

_LAUNCH = {
    r"(open|launch|start)\s+(chrome|browser)":  "chrome",
    r"(open|launch|start)\s+firefox":           "firefox",
    r"(open|launch|start)\s+(vs\s*code|vscode|code editor)": "code",
    r"(open|launch|start)\s+spotify":           "spotify",
    r"(open|launch|start)\s+terminal":          "terminal",
    r"(open|launch|start)\s+notepad":           "notepad",
    r"(open|launch|start)\s+calculator":        "calculator",
    r"(open|launch|start)\s+word":              "word",
    r"(open|launch|start)\s+excel":             "excel",
    r"(open|launch|start)\s+powerpoint":        "powerpoint",
    r"(open|launch|start)\s+teams":             "teams",
    r"(open|launch|start)\s+slack":             "slack",
}

_CMDS = {
    r"(take|capture)\s+(a\s+)?screenshot":      {"type":"hotkey","keys":["win","shift","s"]},
    r"mute":                                     {"type":"key","key":"volumemute"},
    r"volume\s+up":                              {"type":"key","key":"volumeup"},
    r"volume\s+down":                            {"type":"key","key":"volumedown"},
    r"(close|quit)\s+(window|app|this)":         {"type":"hotkey","keys":["alt","f4"]},
    r"minimize":                                 {"type":"hotkey","keys":["win","down"]},
    r"maximize":                                 {"type":"hotkey","keys":["win","up"]},
    r"show\s+desktop":                           {"type":"hotkey","keys":["win","d"]},
    r"new\s+tab":                                {"type":"hotkey","keys":["ctrl","t"]},
    r"close\s+tab":                              {"type":"hotkey","keys":["ctrl","w"]},
    r"(copy|ctrl\s+c)":                          {"type":"hotkey","keys":["ctrl","c"]},
    r"(paste|ctrl\s+v)":                         {"type":"hotkey","keys":["ctrl","v"]},
    r"undo":                                     {"type":"hotkey","keys":["ctrl","z"]},
    r"save":                                     {"type":"hotkey","keys":["ctrl","s"]},
    r"select\s+all":                             {"type":"hotkey","keys":["ctrl","a"]},
    r"(find|search\s+in\s+page)":               {"type":"hotkey","keys":["ctrl","f"]},
    r"zoom\s+in":                                {"type":"hotkey","keys":["ctrl","equal"]},
    r"zoom\s+out":                               {"type":"hotkey","keys":["ctrl","minus"]},
    r"(task\s+manager|task manager)":            {"type":"hotkey","keys":["ctrl","shift","escape"]},
    r"(lock|lock\s+screen)":                     {"type":"hotkey","keys":["win","l"]},
    r"(switch\s+window|alt\s+tab)":              {"type":"hotkey","keys":["alt","tab"]},
}


class VoiceAssistant:
    def __init__(self, cfg, executor, on_transcript=None):
        self.cfg           = cfg
        self.executor      = executor
        self.on_transcript = on_transcript
        self._running      = False
        self._ai_client    = None

        key = cfg.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY","")
        if _OPENAI and key:
            self._ai_client = _OAI(api_key=key)

    def listen_loop(self):
        if not _SR:
            return
        self._running = True
        rec = sr.Recognizer()
        rec.energy_threshold        = 300
        rec.dynamic_energy_threshold = True
        rec.pause_threshold         = 0.6
        try:
            with sr.Microphone() as src:
                rec.adjust_for_ambient_noise(src, duration=1)
                logger.info("Voice ready.")
                while self._running:
                    try:
                        audio = rec.listen(src, timeout=5, phrase_time_limit=8)
                        text  = rec.recognize_google(audio, language=self.cfg.VOICE_LANGUAGE).lower().strip()
                        logger.info("Voice: %r", text)
                        self._handle(text)
                    except sr.WaitTimeoutError:
                        pass
                    except sr.UnknownValueError:
                        pass
                    except Exception as e:
                        logger.debug("Voice err: %s", e)
        except Exception as e:
            logger.warning("Microphone unavailable: %s", e)

    def stop(self):
        self._running = False

    def _handle(self, text):
        # launch app?
        for pat, app in _LAUNCH.items():
            if re.search(pat, text):
                self.executor.execute({"type":"launch","app":app})
                self._notify(text, f"Launching {app}…")
                return
        # system command?
        for pat, action in _CMDS.items():
            if re.search(pat, text):
                self.executor.execute(action)
                self._notify(text, f"Done ✓")
                return
        # AI fallback
        reply = self._ask_ai(text)
        self._notify(text, reply)

    def _ask_ai(self, text):
        if not self._ai_client:
            return "(No OpenAI key set — edit OPENAI_API_KEY in config/settings.py)"
        try:
            r = self._ai_client.chat.completions.create(
                model=self.cfg.OPENAI_MODEL,
                messages=[
                    {"role":"system","content":
                     "You are GestureOS AI. Be concise (1–2 sentences). "
                     "If the user wants to do something on their computer, "
                     "say what action you would take."},
                    {"role":"user","content":text},
                ],
                max_tokens=120, temperature=0.4,
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            return f"(AI error: {e})"

    def _notify(self, user, reply):
        if self.on_transcript:
            self.on_transcript(user, reply)
