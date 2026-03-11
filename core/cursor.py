"""
core/cursor.py — High-accuracy cursor control using Win32 SendInput.

Improvements over v1:
  - Dual EMA (fast + slow blend): responsive when moving, stable when still
  - Velocity-adaptive smoothing: auto-tightens alpha based on movement speed
  - Micro-jitter deadzone: ignores sub-pixel movements when nearly stationary
  - No pyautogui overhead at all — pure Win32 SendInput
"""
import ctypes
import ctypes.wintypes
import logging

logger = logging.getLogger(__name__)

# ── Win32 structs ─────────────────────────────────────────────────────────────
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

MOUSEEVENTF_MOVE       = 0x0001
MOUSEEVENTF_LEFTDOWN   = 0x0002
MOUSEEVENTF_LEFTUP     = 0x0004
MOUSEEVENTF_RIGHTDOWN  = 0x0008
MOUSEEVENTF_RIGHTUP    = 0x0010
MOUSEEVENTF_WHEEL      = 0x0800
MOUSEEVENTF_ABSOLUTE   = 0x8000
INPUT_MOUSE            = 0


def _send(flags, dx=0, dy=0, data=0):
    extra = ctypes.c_ulong(0)
    mi    = _MouseInput(dx, dy, data, flags, 0, ctypes.pointer(extra))
    inp   = _Input(INPUT_MOUSE, _InputUnion(mi=mi))
    ctypes.windll.user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))


def _screen_size():
    u = ctypes.windll.user32
    u.SetProcessDPIAware()
    return u.GetSystemMetrics(0), u.GetSystemMetrics(1)


class CursorController:
    """
    Converts normalised 0..1 hand position → screen pixels.

    Dual EMA smoothing:
      fast_ema  tracks quickly  (high alpha) — for responsiveness
      slow_ema  tracks slowly   (low alpha)  — for stability
      output = blend(fast, slow) based on current velocity
    """

    def __init__(self, cfg):
        self.cfg        = cfg
        self.sw, self.sh = _screen_size()

        # dual EMA state
        self._fx = self._fy = None   # fast EMA
        self._sx = self._sy = None   # slow EMA
        self._prev_nx = self._prev_ny = None

        self._dragging = False
        logger.info("CursorController ready  screen=%dx%d", self.sw, self.sh)

    def move(self, norm_x, norm_y):
        m  = self.cfg.CURSOR_MARGIN
        # Remap [margin, 1-margin] → [0, 1]
        cx = max(0.0, min(1.0, (norm_x - m) / (1 - 2 * m)))
        cy = max(0.0, min(1.0, (norm_y - m) / (1 - 2 * m)))

        # Sensitivity (pivot at centre)
        cx = max(0.0, min(1.0, 0.5 + (cx - 0.5) * self.cfg.SENSITIVITY))
        cy = max(0.0, min(1.0, 0.5 + (cy - 0.5) * self.cfg.SENSITIVITY))

        # Micro-jitter deadzone — ignore movement smaller than threshold
        if self._prev_nx is not None:
            dx = abs(cx - self._prev_nx)
            dy = abs(cy - self._prev_ny)
            if dx < 0.003 and dy < 0.003:   # ~7px on 1080p — kills micro-tremor
                return
        self._prev_nx, self._prev_ny = cx, cy

        # Velocity-adaptive dual EMA
        if self._fx is None:
            self._fx = self._sx = cx
            self._fy = self._sy = cy
        else:
            # Compute movement velocity (normalised)
            vel = ((cx - self._fx)**2 + (cy - self._fy)**2) ** 0.5

            # Fast alpha: 0.45–0.75 depending on speed
            fast_a = min(0.75, max(0.45, vel * 18))
            # Slow alpha: always gentle
            slow_a = self.cfg.SMOOTHING   # from settings (default 0.28)

            self._fx = fast_a * cx + (1 - fast_a) * self._fx
            self._fy = fast_a * cy + (1 - fast_a) * self._fy
            self._sx = slow_a * cx + (1 - slow_a) * self._sx
            self._sy = slow_a * cy + (1 - slow_a) * self._sy

            # Blend: higher velocity → trust fast EMA more
            blend = min(1.0, vel * 25)
            cx = blend * self._fx + (1 - blend) * self._sx
            cy = blend * self._fy + (1 - blend) * self._sy

        ax = int(cx * 65535)
        ay = int(cy * 65535)

        if self._dragging:
            _send(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, ax, ay)
        else:
            _send(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, ax, ay)

    def click(self, button="left"):
        if button == "left":
            _send(MOUSEEVENTF_LEFTDOWN)
            _send(MOUSEEVENTF_LEFTUP)
        else:
            _send(MOUSEEVENTF_RIGHTDOWN)
            _send(MOUSEEVENTF_RIGHTUP)

    def double_click(self):
        self.click(); self.click()

    def right_click(self):
        _send(MOUSEEVENTF_RIGHTDOWN)
        _send(MOUSEEVENTF_RIGHTUP)

    def scroll(self, direction, amount=None):
        amt   = (amount or self.cfg.SCROLL_SPEED) * 120
        delta = amt if direction == "up" else -amt
        _send(MOUSEEVENTF_WHEEL, data=int(delta))

    def drag_start(self):
        if not self._dragging:
            _send(MOUSEEVENTF_LEFTDOWN)
            self._dragging = True

    def drag_end(self):
        if self._dragging:
            _send(MOUSEEVENTF_LEFTUP)
            self._dragging = False
