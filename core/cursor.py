"""core/cursor.py — High-speed cursor control using Win32 SendInput (lower latency than pyautogui)."""
import ctypes, ctypes.wintypes, logging
logger = logging.getLogger(__name__)

# ── Win32 structs for SendInput ────────────────────────────────────────────────
PUL = ctypes.POINTER(ctypes.c_ulong)

class _MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx",          ctypes.c_long),
        ("dy",          ctypes.c_long),
        ("mouseData",   ctypes.c_ulong),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]

class _InputUnion(ctypes.Union):
    _fields_ = [("mi", _MouseInput)]

class _Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", _InputUnion)]

MOUSEEVENTF_MOVE        = 0x0001
MOUSEEVENTF_LEFTDOWN    = 0x0002
MOUSEEVENTF_LEFTUP      = 0x0004
MOUSEEVENTF_RIGHTDOWN   = 0x0008
MOUSEEVENTF_RIGHTUP     = 0x0010
MOUSEEVENTF_MIDDLEDOWN  = 0x0020
MOUSEEVENTF_MIDDLEUP    = 0x0040
MOUSEEVENTF_WHEEL       = 0x0800
MOUSEEVENTF_ABSOLUTE    = 0x8000

INPUT_MOUSE = 0


def _send_mouse(flags, dx=0, dy=0, data=0):
    extra = ctypes.c_ulong(0)
    mi    = _MouseInput(dx, dy, data, flags, 0, ctypes.pointer(extra))
    inp   = _Input(INPUT_MOUSE, _InputUnion(mi=mi))
    ctypes.windll.user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))


def _screen_size():
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


class CursorController:
    """
    Converts normalised (0..1) index-finger position → screen coords.
    Uses Win32 SendInput for the lowest possible latency on Windows.
    EMA smoothing removes jitter while keeping response crisp.
    """

    def __init__(self, cfg):
        self.cfg        = cfg
        self.sw, self.sh = _screen_size()
        self._sx        = None
        self._sy        = None
        self._dragging  = False
        logger.info("CursorController ready  screen=%dx%d", self.sw, self.sh)

    def move(self, norm_x, norm_y):
        m  = self.cfg.CURSOR_MARGIN
        cx = max(0.0, min(1.0, (norm_x - m) / (1 - 2*m)))
        cy = max(0.0, min(1.0, (norm_y - m) / (1 - 2*m)))
        # sensitivity pivot at centre
        cx = max(0.0, min(1.0, 0.5 + (cx - 0.5) * self.cfg.SENSITIVITY))
        cy = max(0.0, min(1.0, 0.5 + (cy - 0.5) * self.cfg.SENSITIVITY))
        # EMA
        a = self.cfg.SMOOTHING
        if self._sx is None:
            self._sx, self._sy = cx, cy
        else:
            self._sx = a*cx + (1-a)*self._sx
            self._sy = a*cy + (1-a)*self._sy
        # SendInput expects 0..65535
        ax = int(self._sx * 65535)
        ay = int(self._sy * 65535)
        _send_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, ax, ay)

    def click(self, button="left"):
        if button == "left":
            _send_mouse(MOUSEEVENTF_LEFTDOWN)
            _send_mouse(MOUSEEVENTF_LEFTUP)
        elif button == "right":
            _send_mouse(MOUSEEVENTF_RIGHTDOWN)
            _send_mouse(MOUSEEVENTF_RIGHTUP)

    def double_click(self):
        self.click("left"); self.click("left")

    def right_click(self):
        self.click("right")

    def scroll(self, direction, amount=None):
        amt   = (amount or self.cfg.SCROLL_SPEED) * 120
        delta = amt if direction == "up" else -amt
        _send_mouse(MOUSEEVENTF_WHEEL, data=delta)

    def drag_start(self):
        if not self._dragging:
            _send_mouse(MOUSEEVENTF_LEFTDOWN)
            self._dragging = True

    def drag_end(self):
        if self._dragging:
            _send_mouse(MOUSEEVENTF_LEFTUP)
            self._dragging = False
