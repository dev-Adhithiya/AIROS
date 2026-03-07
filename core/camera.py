"""core/camera.py — Background-threaded webcam (always latest frame, zero buffer lag)."""
import cv2, threading, time, logging
logger = logging.getLogger(__name__)


class CameraCapture:
    def __init__(self, cfg):
        self.cfg   = cfg
        self._frame = None
        self._lock  = threading.Lock()
        self._stop  = threading.Event()

        # CAP_DSHOW = DirectShow on Windows → lowest possible latency
        self.cap = cv2.VideoCapture(cfg.CAMERA_ID, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {cfg.CAMERA_ID}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  cfg.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS,          cfg.TARGET_FPS)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)   # discard stale frames

        self._t = threading.Thread(target=self._loop, daemon=True, name="Cam")
        self._t.start()
        logger.info("Camera %d ready", cfg.CAMERA_ID)

    def _loop(self):
        while not self._stop.is_set():
            ok, f = self.cap.read()
            if not ok:
                time.sleep(0.005)
                continue
            f = cv2.flip(f, 1)          # mirror — feels natural
            with self._lock:
                self._frame = f

    def read(self):
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def frames(self):
        interval = 1.0 / self.cfg.TARGET_FPS
        while not self._stop.is_set():
            t0 = time.perf_counter()
            f  = self.read()
            if f is not None:
                yield f
            wait = interval - (time.perf_counter() - t0)
            if wait > 0:
                time.sleep(wait)

    def release(self):
        self._stop.set()
        self._t.join(timeout=2)
        self.cap.release()
        logger.info("Camera released.")
