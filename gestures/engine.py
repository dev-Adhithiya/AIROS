"""gestures/engine.py — Gesture recogniser, low-res camera robust."""
import time, collections, logging
from core.hand_tracker import (
    WRIST, THUMB_IP, THUMB_TIP,
    INDEX_MCP, INDEX_PIP, INDEX_TIP,
    MID_MCP,   MID_PIP,   MID_TIP,
    RING_MCP,  RING_PIP,  RING_TIP,
    PINK_MCP,  PINK_PIP,  PINK_TIP,
)
logger = logging.getLogger(__name__)


class GestureEngine:
    def __init__(self, cfg):
        self.cfg = cfg
        self._prev_wrist_x   = None
        self._prev_scroll_y  = None
        self._scroll_smooth  = 0.0
        self._last_swipe_t   = 0.0
        self._last_click_t   = 0.0
        self._last_click_tick= 0.0
        self._click_streak   = 0
        self._was_grabbing   = False
        self._confirm_buf    = collections.deque(maxlen=2)
        self._history        = collections.deque(maxlen=6)

    def recognize(self, lm):
        raw = self._raw_recognize(lm)

        self._confirm_buf.append(raw)

        # grab and cursor_move need 2 consistent frames before firing
        # this prevents a single noisy frame from triggering grab
        if len(self._confirm_buf) == 2 and self._confirm_buf[0] == self._confirm_buf[1]:
            confirmed = raw
        else:
            # during transition: only let smooth gestures through unconfirmed
            confirmed = raw if raw in ("cursor_move", "idle",
                                       "scroll_up", "scroll_down") else "idle"

        self._history.append(confirmed)
        return confirmed

    def _raw_recognize(self, lm):
        now = time.perf_counter()
        ext = self._fingers_extended(lm)
        n   = sum(ext)

        # ── GRAB — strict: ALL tips must be below their MCP knuckle ──────────
        # This is the KEY fix: we don't use n==0 (which misfires on low-res)
        # Instead explicitly check every tip is below its MCP base.
        if self._all_closed(lm):
            self._was_grabbing = True
            self._upd_wrist(lm)
            return "grab"

        # ── OPEN PALM ─────────────────────────────────────────────────────────
        if n == 5:
            if self._was_grabbing:
                self._was_grabbing = False
                return "drag_end"
            return "open_palm"

        self._was_grabbing = False

        # ── RIGHT CLICK: pinky only extended ─────────────────────────────────
        if ext[4] and not ext[1] and not ext[2] and not ext[3]:
            if now - self._last_click_t > self.cfg.CLICK_COOLDOWN:
                self._last_click_t = now
                return "right_click"

        # ── LEFT CLICK: thumb tip ↔ index tip close ───────────────────────────
        d_ti = lm.dist_px(THUMB_TIP, INDEX_TIP)
        if d_ti < self.cfg.CLICK_DIST_PX:
            if now - self._last_click_t > self.cfg.CLICK_COOLDOWN:
                self._last_click_t = now
                if now - self._last_click_tick < self.cfg.DBLCLICK_GAP:
                    self._click_streak += 1
                else:
                    self._click_streak = 1
                self._last_click_tick = now
                if self._click_streak >= 2:
                    self._click_streak = 0
                    return "double_click"
                return "click"

        # ── SCROLL: index + middle up, ring + pinky down ──────────────────────
        if ext[1] and ext[2] and not ext[3] and not ext[4]:
            g = self._detect_scroll(lm)
            return g if g else "peace"

        # ── SWIPE: 3+ fingers, fast wrist motion ─────────────────────────────
        if n >= 3:
            sw = self._detect_swipe(lm, now)
            if sw:
                return sw

        # ── CURSOR MOVE: index only up, middle must be clearly down ──────────
        if ext[1] and not ext[2] and not ext[3] and not ext[4]:
            self._upd_wrist(lm)
            return "cursor_move"

        self._upd_wrist(lm)
        return "idle"

    # ── finger state helpers ──────────────────────────────────────────────────

    def _fingers_extended(self, lm):
        """
        Returns [thumb, index, middle, ring, pinky] — True = finger is up.

        Uses a SMALL margin (0.01) so low-res cameras still detect extended fingers.
        Compares tip to PIP joint — tip must be above PIP by at least 1% of frame.
        Thumb uses X-axis (webcam is mirrored so left hand thumb goes right).
        """
        # Thumb: tip x must be past IP joint
        thumb = lm.norm(THUMB_TIP)[0] < lm.norm(THUMB_IP)[0] - 0.02

        result = [thumb]
        for tip, pip in [
            (INDEX_TIP, INDEX_PIP),
            (MID_TIP,   MID_PIP),
            (RING_TIP,  RING_PIP),
            (PINK_TIP,  PINK_PIP),
        ]:
            # Small 0.01 margin — works on low-res cameras
            # (was 0.025 which was too strict and caused n==0 / false grabs)
            result.append(lm.norm(tip)[1] < lm.norm(pip)[1] - 0.01)
        return result

    def _all_closed(self, lm):
        """
        Strict grab check: every fingertip must be BELOW or AT its MCP knuckle.
        MCP is the big knuckle at the base of each finger.
        This is a much higher bar than n==0 and survives low-res noise.
        """
        # Thumb closed: tip x past base (MCP direction)
        thumb_closed = lm.norm(THUMB_TIP)[0] > lm.norm(INDEX_MCP)[0] - 0.02

        # Each finger: tip Y must be at or below MCP Y (tip lower = closed)
        # Allow 0.01 tolerance so nearly-closed counts
        pairs = [
            (INDEX_TIP, INDEX_MCP),
            (MID_TIP,   MID_MCP),
            (RING_TIP,  RING_MCP),
            (PINK_TIP,  PINK_MCP),
        ]
        fingers_closed = all(
            lm.norm(tip)[1] > lm.norm(mcp)[1] - 0.01
            for tip, mcp in pairs
        )
        return thumb_closed and fingers_closed

    def _detect_scroll(self, lm):
        y = lm.norm(INDEX_TIP)[1]
        if self._prev_scroll_y is None:
            self._prev_scroll_y = y
            return None
        raw = self._prev_scroll_y - y
        a   = self.cfg.SCROLL_ALPHA
        self._scroll_smooth = a * raw + (1 - a) * self._scroll_smooth
        self._prev_scroll_y = y
        if abs(self._scroll_smooth) > self.cfg.SCROLL_DEADZONE:
            return "scroll_up" if self._scroll_smooth > 0 else "scroll_down"
        return None

    def _detect_swipe(self, lm, now):
        wx = lm.norm(WRIST)[0]
        if self._prev_wrist_x is None:
            self._prev_wrist_x = wx
            return None
        vel = wx - self._prev_wrist_x
        self._prev_wrist_x = wx
        if (abs(vel) > self.cfg.SWIPE_VELOCITY and
                now - self._last_swipe_t > self.cfg.SWIPE_COOLDOWN):
            self._last_swipe_t = now
            return "swipe_right" if vel > 0 else "swipe_left"
        return None

    def _upd_wrist(self, lm):
        self._prev_wrist_x = lm.norm(WRIST)[0]
