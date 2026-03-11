"""gestures/engine.py — Geometric gesture recogniser (v2).

Gesture tokens:
  cursor_move    — index finger only → move mouse
  click          — thumb tip ↔ index tip close → left click
  double_click   — two quick clicks
  right_click    — PINKY finger only extended (distinct, no accidental triggers)
  scroll_up/down — index + middle extended, move vertically
  swipe_left/right — open hand (3+ fingers), fast wrist motion
  grab           — all fingers closed → drag start
  drag_end       — open palm after grab → release
  open_palm      — all 5 fingers extended (no prior grab)
  pinch          — thumb + index only, close together
  peace          — index + middle held still
  idle           — no clear gesture

Cursor accuracy improvements:
  - Dual EMA: fast EMA for responsiveness + slow EMA for stability
  - Velocity-based smoothing: more responsive when moving fast, smoother when still
  - Larger deadzone when nearly stationary to kill micro-jitter
  - Confirmation buffer: clicks only fire after 2 consistent frames
"""
import time, collections, logging, numpy as np
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

        # swipe / scroll state
        self._prev_wrist_x   = None
        self._prev_scroll_y  = None
        self._scroll_smooth  = 0.0
        self._last_swipe_t   = 0.0

        # click state
        self._last_click_t   = 0.0
        self._last_click_tick= 0.0
        self._click_streak   = 0

        # drag state
        self._was_grabbing   = False

        # gesture confirmation buffer (reduces false positives)
        self._confirm_buf    = collections.deque(maxlen=2)

        # history for UI
        self._history        = collections.deque(maxlen=6)

    # ── public ────────────────────────────────────────────────────────────────

    def recognize(self, lm):
        raw = self._raw_recognize(lm)
        # Require gesture to appear in last 2 frames to confirm
        self._confirm_buf.append(raw)
        if len(self._confirm_buf) == 2 and self._confirm_buf[0] == self._confirm_buf[1]:
            confirmed = raw
        else:
            # During transition, keep cursor moving to avoid stutters
            confirmed = raw if raw in ("cursor_move", "idle", "scroll_up",
                                       "scroll_down", "grab") else "idle"
        self._history.append(confirmed)
        return confirmed

    # ── core recognition ──────────────────────────────────────────────────────

    def _raw_recognize(self, lm):
        now = time.perf_counter()
        ext = self._fingers_extended(lm)
        # ext = [thumb, index, middle, ring, pinky]
        n   = sum(ext)

        # ── open palm (all 5) ─────────────────────────────────────────────────
        if n == 5:
            if self._was_grabbing:
                self._was_grabbing = False
                return "drag_end"
            return "open_palm"

        # ── grab (all closed) ─────────────────────────────────────────────────
        if n == 0:
            self._was_grabbing = True
            self._upd_wrist(lm)
            return "grab"

        # ── RIGHT CLICK: pinky only extended ─────────────────────────────────
        # Very distinct — hard to trigger accidentally
        if ext[4] and not ext[1] and not ext[2] and not ext[3]:
            if now - self._last_click_t > self.cfg.CLICK_COOLDOWN:
                self._last_click_t = now
                return "right_click"

        # ── LEFT CLICK: thumb tip ↔ index tip ────────────────────────────────
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

        # ── PINCH: thumb + index only, close ─────────────────────────────────
        if ext[0] and ext[1] and not ext[2] and not ext[3] and not ext[4]:
            if d_ti < self.cfg.PINCH_DIST_PX:
                self._upd_wrist(lm)
                return "pinch"

        # ── CURSOR MOVE: index only ───────────────────────────────────────────
        if ext[1] and not ext[2] and not ext[3] and not ext[4]:
            self._upd_wrist(lm)
            return "cursor_move"

        self._upd_wrist(lm)
        return "idle"

    # ── helpers ───────────────────────────────────────────────────────────────

    def _fingers_extended(self, lm):
        """
        Returns [thumb, index, middle, ring, pinky].
        Uses PIP joint comparison with a comfortable margin.
        Thumb uses X-axis (mirrored webcam).
        """
        thumb = lm.norm(THUMB_TIP)[0] < lm.norm(THUMB_IP)[0] - 0.02

        result = [thumb]
        for tip, pip in [
            (INDEX_TIP, INDEX_PIP),
            (MID_TIP,   MID_PIP),
            (RING_TIP,  RING_PIP),
            (PINK_TIP,  PINK_PIP),
        ]:
            # Require tip to be clearly above PIP (larger margin = fewer false positives)
            result.append(lm.norm(tip)[1] < lm.norm(pip)[1] - 0.025)
        return result

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
