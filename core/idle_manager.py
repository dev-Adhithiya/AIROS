"""core/idle_manager.py — Tracks hand presence → sleep/wake."""
import time, logging
logger = logging.getLogger(__name__)


class IdleManager:
    def __init__(self, cfg):
        self.cfg        = cfg
        self._last_seen = time.perf_counter()
        self._sleeping  = False

    @property
    def is_sleeping(self):
        return self._sleeping

    def on_hand(self, gesture=None):
        self._last_seen = time.perf_counter()
        if self._sleeping:
            self._sleeping = False
            logger.info("Wake — gesture control resumed.")

    def on_no_hand(self):
        if not self._sleeping and time.perf_counter() - self._last_seen > self.cfg.IDLE_TIMEOUT:
            self._sleeping = True
            logger.info("Sleep — no hand detected.")

    def status(self):
        if self._sleeping:
            return "idle"
        if time.perf_counter() - self._last_seen > 0.5:
            return "lost"
        return "active"
