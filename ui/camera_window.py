"""
ui/camera_window.py — Minimal shim.

cv2.imshow is called directly from the pipeline thread in pipeline.py.
This class just holds the visible flag so pipeline knows whether to show.
"""

class CameraWindow:
    def __init__(self, cfg):
        self.cfg     = cfg
        self.visible = True   # show by default

    def push_frame(self, frame, gesture, status):
        pass  # pipeline.py handles imshow directly

    def show(self):    self.visible = True
    def hide(self):    self.visible = False
    def toggle(self):  self.visible = not self.visible
    def close(self):   self.visible = False
    def attach(self, root): pass
    def run(self):     pass
