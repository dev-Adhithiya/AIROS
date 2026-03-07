"""
core/hand_tracker.py
MediaPipe 0.10.x Hand Landmarker (Tasks API).
Works with mediapipe 0.10.30+  —  no mp.solutions needed.
"""
import cv2
import numpy as np
import mediapipe as mp
import urllib.request
import os
import logging

logger = logging.getLogger(__name__)

# ── Landmark index constants ──────────────────────────────────────────────────
WRIST       = 0
THUMB_CMC=1; THUMB_MCP=2;  THUMB_IP=3;   THUMB_TIP=4
INDEX_MCP=5; INDEX_PIP=6;  INDEX_DIP=7;  INDEX_TIP=8
MID_MCP=9;   MID_PIP=10;   MID_DIP=11;   MID_TIP=12
RING_MCP=13; RING_PIP=14;  RING_DIP=15;  RING_TIP=16
PINK_MCP=17; PINK_PIP=18;  PINK_DIP=19;  PINK_TIP=20

_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17),
]

_MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "assets", "hand_landmarker.task"
)


def _ensure_model():
    path = os.path.normpath(_MODEL_PATH)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        logger.info("Downloading hand_landmarker.task (~8 MB) ...")
        urllib.request.urlretrieve(_MODEL_URL, path)
        logger.info("Model saved -> %s", path)
    return path


class HandLandmarks:
    """21-point landmark wrapper with pixel + normalised helpers."""

    def __init__(self, pts, fw, fh):
        self.pts, self.fw, self.fh = pts, fw, fh

    def norm(self, i):
        return self.pts[i][0], self.pts[i][1]

    def px(self, i):
        return int(self.pts[i][0] * self.fw), int(self.pts[i][1] * self.fh)

    def dist_px(self, a, b):
        ax, ay = self.px(a);  bx, by = self.px(b)
        return float(np.hypot(ax - bx, ay - by))

    def dist_norm(self, a, b):
        ax, ay = self.norm(a); bx, by = self.norm(b)
        return float(np.hypot(ax - bx, ay - by))

    def __getitem__(self, i):
        return self.pts[i]


class HandTracker:
    """Wraps MediaPipe 0.10 HandLandmarker (Tasks API)."""

    def __init__(self, cfg):
        self.cfg     = cfg
        model_path   = _ensure_model()

        BaseOptions           = mp.tasks.BaseOptions
        HandLandmarker        = mp.tasks.vision.HandLandmarker
        HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
        RunningMode           = mp.tasks.vision.RunningMode

        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=RunningMode.IMAGE,
            num_hands=cfg.MAX_HANDS,
            min_hand_detection_confidence=cfg.DETECTION_CONFIDENCE,
            min_hand_presence_confidence=cfg.TRACKING_CONFIDENCE,
            min_tracking_confidence=cfg.TRACKING_CONFIDENCE,
        )
        self._detector = HandLandmarker.create_from_options(options)
        logger.info("HandTracker ready (mediapipe %s, Tasks API).", mp.__version__)

    def process(self, frame):
        h, w = frame.shape[:2]
        rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result   = self._detector.detect(mp_image)

        if not result.hand_landmarks:
            return None, False

        raw = result.hand_landmarks[0]
        pts = [(lm.x, lm.y, lm.z) for lm in raw]

        if self.cfg.SHOW_LANDMARKS:
            self._draw(frame, pts, w, h)

        return HandLandmarks(pts, w, h), True

    def _draw(self, frame, pts, w, h):
        px = [(int(x * w), int(y * h)) for x, y, z in pts]
        for a, b in _CONNECTIONS:
            cv2.line(frame, px[a], px[b], (0, 180, 100), 2, cv2.LINE_AA)
        for i, p in enumerate(px):
            r     = 6 if i in (4, 8, 12, 16, 20) else 3
            color = (0, 255, 136) if i in (4, 8, 12, 16, 20) else (100, 220, 160)
            cv2.circle(frame, p, r, color, -1)

    def close(self):
        self._detector.close()
