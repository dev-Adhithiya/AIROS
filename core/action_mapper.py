"""core/action_mapper.py — Maps (gesture, active_window) → action dict."""
import threading, time, logging
logger = logging.getLogger(__name__)

try:
    import win32gui, win32process, psutil
    _W32 = True
except ImportError:
    _W32 = False
    logger.warning("pywin32/psutil missing — context gestures disabled.")

from core.hand_tracker import INDEX_TIP

# ── Per-app gesture overrides ─────────────────────────────────────────────────
CONTEXT_MAP = {
    "chrome":   {"swipe_left":{"type":"hotkey","keys":["alt","left"]},
                 "swipe_right":{"type":"hotkey","keys":["alt","right"]},
                 "open_palm":{"type":"hotkey","keys":["ctrl","l"]}},
    "firefox":  {"swipe_left":{"type":"hotkey","keys":["alt","left"]},
                 "swipe_right":{"type":"hotkey","keys":["alt","right"]}},
    "msedge":   {"swipe_left":{"type":"hotkey","keys":["alt","left"]},
                 "swipe_right":{"type":"hotkey","keys":["alt","right"]}},
    "powerpnt": {"swipe_right":{"type":"key","key":"right"},
                 "swipe_left":{"type":"key","key":"left"},
                 "open_palm":{"type":"key","key":"f5"},
                 "grab":{"type":"key","key":"escape"}},
    "code":     {"swipe_right":{"type":"hotkey","keys":["ctrl","tab"]},
                 "swipe_left":{"type":"hotkey","keys":["ctrl","shift","tab"]},
                 "open_palm":{"type":"hotkey","keys":["ctrl","shift","p"]}},
    "spotify":  {"open_palm":{"type":"key","key":"space"},
                 "swipe_right":{"type":"hotkey","keys":["ctrl","right"]},
                 "swipe_left":{"type":"hotkey","keys":["ctrl","left"]}},
    "vlc":      {"open_palm":{"type":"key","key":"space"},
                 "swipe_right":{"type":"hotkey","keys":["shift","right"]},
                 "swipe_left":{"type":"hotkey","keys":["shift","left"]}},
    "teams":    {"swipe_right":{"type":"hotkey","keys":["ctrl","shift","right"]},
                 "open_palm":{"type":"hotkey","keys":["ctrl","shift","m"]}},  # mute toggle
}

# ── Default (no specific context) ─────────────────────────────────────────────
DEFAULT_MAP = {
    "cursor_move": {"type":"mouse_move"},
    "click":       {"type":"click","button":"left"},
    "double_click":{"type":"double_click"},
    "right_click": {"type":"right_click"},
    "scroll_up":   {"type":"scroll","direction":"up"},
    "scroll_down": {"type":"scroll","direction":"down"},
    "swipe_right": {"type":"hotkey","keys":["alt","right"]},
    "swipe_left":  {"type":"hotkey","keys":["alt","left"]},
    "grab":        {"type":"drag_start"},
    "drag_end":    {"type":"drag_end"},
    "open_palm":   {"type":"drag_end"},
    "pinch":       {"type":"none"},
    "peace":       {"type":"none"},
    "idle":        {"type":"none"},
}


class ActionMapper:
    def __init__(self, cfg):
        self.cfg  = cfg
        self._ctx = "default"
        self._lock = threading.Lock()
        if _W32:
            threading.Thread(target=self._poll, daemon=True, name="CtxPoll").start()

    def get_context(self):
        with self._lock:
            return self._ctx

    def map(self, gesture, landmarks):
        if gesture is None:
            return None
        ctx     = self.get_context()
        rules   = self._ctx_rules(ctx)
        action  = dict(rules.get(gesture) or DEFAULT_MAP.get(gesture) or {"type":"none"})
        if action["type"] == "mouse_move" and landmarks:
            action["norm_x"] = landmarks.norm(INDEX_TIP)[0]
            action["norm_y"] = landmarks.norm(INDEX_TIP)[1]
        return action

    def _ctx_rules(self, ctx):
        low = ctx.lower()
        for k, v in CONTEXT_MAP.items():
            if k in low:
                return v
        return {}

    def _poll(self):
        while True:
            try:
                hwnd  = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(hwnd)
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                name  = psutil.Process(pid).name().lower().replace(".exe","")
                with self._lock:
                    self._ctx = f"{name} {title}"
            except Exception:
                pass
            time.sleep(self.cfg.CONTEXT_POLL_SEC)
