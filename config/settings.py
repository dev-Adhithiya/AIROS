"""config/settings.py — All tuneable parameters."""
from dataclasses import dataclass, field


@dataclass
class Settings:
    # Camera
    CAMERA_ID:              int   = 0
    FRAME_WIDTH:            int   = 1280
    FRAME_HEIGHT:           int   = 720
    TARGET_FPS:             int   = 30

    # MediaPipe
    MAX_HANDS:              int   = 1
    DETECTION_CONFIDENCE:   float = 0.75
    TRACKING_CONFIDENCE:    float = 0.75

    # Cursor
    SENSITIVITY:            float = 1.2
    SMOOTHING:              float = 0.28    # EMA alpha — lower = smoother, slightly more lag
    CURSOR_MARGIN:          float = 0.08    # crop edges of frame

    # Click
    CLICK_DIST_PX:          int   = 36
    RCLICK_DIST_PX:         int   = 36
    CLICK_COOLDOWN:         float = 0.30
    DBLCLICK_GAP:           float = 0.45

    # Scroll
    SCROLL_SPEED:           int   = 10
    SCROLL_DEADZONE:        float = 0.012
    SCROLL_ALPHA:           float = 0.40

    # Swipe
    SWIPE_VELOCITY:         float = 0.038
    SWIPE_COOLDOWN:         float = 0.55

    # Drag / Pinch
    PINCH_DIST_PX:          int   = 42

    # Idle
    IDLE_TIMEOUT:           float = 2.5
    WAKE_GESTURE:           str   = "open_palm"
    CONTEXT_POLL_SEC:       float = 0.4

    # Voice / AI
    VOICE_ENABLED:          bool  = True
    VOICE_LANGUAGE:         str   = "en-US"
    OPENAI_API_KEY:         str   = ""      # or set env OPENAI_API_KEY
    OPENAI_MODEL:           str   = "gpt-3.5-turbo"

    # HUD / sidebar
    HUD_CORNER:             str   = "bottom-right"   # top-left / top-right / bottom-left / bottom-right
    HUD_OPACITY:            float = 0.88
    SIDEBAR_WIDTH:          int   = 360
    SIDEBAR_SLIDE_MS:       int   = 220

    # Runtime
    DEMO_MODE:              bool  = False
    DEBUG:                  bool  = False
    SHOW_GESTURE:           bool  = True
    SHOW_LANDMARKS:         bool  = True
