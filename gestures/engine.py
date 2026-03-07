"""gestures/engine.py — Geometric gesture recogniser.

Tokens:  cursor_move, click, double_click, right_click,
         scroll_up, scroll_down, swipe_left, swipe_right,
         grab, drag_end, open_palm, pinch, peace, idle
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
        self._prev_wrist_x   = None
        self._prev_scroll_y  = None
        self._scroll_smooth  = 0.0
        self._last_swipe_t   = 0.0
        self._last_click_t   = 0.0
        self._last_click_tick= 0.0
        self._click_streak   = 0
        self._was_grabbing   = False
        self._history        = collections.deque(maxlen=6)

    # ── public ────────────────────────────────────────────────────────────────

    def recognize(self, lm):
        now  = time.perf_counter()
        ext  = self._fingers_extended(lm)
        n    = sum(ext)

        # open palm
        if n == 5:
            if self._was_grabbing:
                self._was_grabbing = False
                return self._emit("drag_end")
            return self._emit("open_palm")

        # full grab
        if n == 0:
            self._was_grabbing = True
            self._upd_wrist(lm)
            return self._emit("grab")

        # left click — thumb ↔ index
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
                    return self._emit("double_click")
                return self._emit("click")

        # right click — thumb ↔ middle, index down
        d_tm = lm.dist_px(THUMB_TIP, MID_TIP)
        if d_tm < self.cfg.RCLICK_DIST_PX and not ext[1]:
            if now - self._last_click_t > self.cfg.CLICK_COOLDOWN:
                self._last_click_t = now
                return self._emit("right_click")

        # scroll — index + middle up, ring + pinky down
        if ext[1] and ext[2] and not ext[3] and not ext[4]:
            g = self._detect_scroll(lm)
            return self._emit(g if g else "peace")

        # swipe — 3+ fingers, fast wrist
        if n >= 3:
            sw = self._detect_swipe(lm, now)
            if sw:
                return self._emit(sw)

        # pinch — thumb + index only, close
        if ext[0] and ext[1] and not ext[2] and not ext[3]:
            if d_ti < self.cfg.PINCH_DIST_PX:
                self._upd_wrist(lm)
                return self._emit("pinch")

        # cursor move — index only
        if ext[1] and not ext[2] and not ext[3] and not ext[4]:
            self._upd_wrist(lm)
            return self._emit("cursor_move")

        self._upd_wrist(lm)
        return self._emit("idle")

    # ── internals ─────────────────────────────────────────────────────────────

    def _emit(self, g):
        self._history.append(g)
        return g

    def _fingers_extended(self, lm):
        # Thumb: tip.x < IP.x (mirrored webcam)
        thumb = lm.norm(THUMB_TIP)[0] < lm.norm(THUMB_IP)[0]
        result = [thumb]
        for tip, pip in [(INDEX_TIP,INDEX_PIP),(MID_TIP,MID_PIP),
                          (RING_TIP,RING_PIP),(PINK_TIP,PINK_PIP)]:
            result.append(lm.norm(tip)[1] < lm.norm(pip)[1] - 0.018)
        return result

    def _detect_scroll(self, lm):
        y = lm.norm(INDEX_TIP)[1]
        if self._prev_scroll_y is None:
            self._prev_scroll_y = y; return None
        raw = self._prev_scroll_y - y
        a   = self.cfg.SCROLL_ALPHA
        self._scroll_smooth = a*raw + (1-a)*self._scroll_smooth
        self._prev_scroll_y = y
        if abs(self._scroll_smooth) > self.cfg.SCROLL_DEADZONE:
            return "scroll_up" if self._scroll_smooth > 0 else "scroll_down"
        return None

    def _detect_swipe(self, lm, now):
        wx = lm.norm(WRIST)[0]
        if self._prev_wrist_x is None:
            self._prev_wrist_x = wx; return None
        vel = wx - self._prev_wrist_x
        self._prev_wrist_x = wx
        if abs(vel) > self.cfg.SWIPE_VELOCITY and now - self._last_swipe_t > self.cfg.SWIPE_COOLDOWN:
            self._last_swipe_t = now
            return "swipe_right" if vel > 0 else "swipe_left"
        return None

    def _upd_wrist(self, lm):
        self._prev_wrist_x = lm.norm(WRIST)[0]
