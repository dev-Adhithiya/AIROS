"""
ui/camera_window.py — Holds the visible flag for the cv2 preview.
Toggling visible=True causes pipeline.py to call cv2.imshow again,
recreating the window after it was closed.
"""
import logging
logger = logging.getLogger(__name__)


class CameraWindow:
    def __init__(self, cfg):
        self.cfg     = cfg
        self.visible = True   # show by default; False = hidden

    # pipeline.py reads self.visible to decide whether to call imshow
    def push_frame(self, frame, gesture, status): pass

    def show(self):
        logger.info("Camera preview: show")
        self.visible = True

    def hide(self):
        logger.info("Camera preview: hide")
        self.visible = False

    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()

    def close(self):
        self.visible = False

    # kept for API compat
    def attach(self, root): pass
    def run(self):          pass
