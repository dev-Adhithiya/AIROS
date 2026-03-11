"""ui/tray.py — System tray icon."""
import threading, logging, sys
logger = logging.getLogger(__name__)

try:
    import pystray
    from pystray import MenuItem as MItem
    from PIL import Image, ImageDraw
    _TRAY = True
except ImportError:
    _TRAY = False
    logger.warning("pystray/Pillow not installed — tray icon disabled.")


def _make_icon():
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d    = ImageDraw.Draw(img)
    d.ellipse([2, 2, size-2, size-2], fill=(13, 17, 23, 255))
    d.ellipse([14, 14, size-14, size-14], fill=(0, 255, 136, 255))
    return img


class TrayIcon:
    def __init__(self, on_start, on_stop, on_toggle_sidebar, on_quit,
                 on_toggle_preview=None):
        self.on_start            = on_start
        self.on_stop             = on_stop
        self.on_toggle_sidebar   = on_toggle_sidebar
        self.on_quit             = on_quit
        self.on_toggle_preview   = on_toggle_preview   # NEW
        self._icon               = None
        self._running            = False

    def run(self):
        if not _TRAY:
            logger.warning("Tray icon unavailable.")
            return

        def _start(icon, item):
            self._running = True
            self.on_start()

        def _stop(icon, item):
            self._running = False
            self.on_stop()

        def _preview(icon, item):
            if self.on_toggle_preview:
                self.on_toggle_preview()

        def _sidebar(icon, item):
            self.on_toggle_sidebar()

        def _quit(icon, item):
            icon.stop()
            self.on_quit()

        self._icon = pystray.Icon(
            "AIROS",
            _make_icon(),
            "AIROS — Hand Gesture Control",
            menu=pystray.Menu(
                MItem("▶  Start AIROS",          _start,   default=True),
                MItem("■  Stop",                 _stop),
                pystray.Menu.SEPARATOR,
                MItem("📷  Show/Hide Preview",   _preview),
                MItem("☰  Toggle Sidebar",       _sidebar),
                pystray.Menu.SEPARATOR,
                MItem("✕  Quit",                 _quit),
            ),
        )
        self._icon.run()

    def set_status(self, status: str):
        if self._icon:
            labels = {"active": "● Active", "idle": "◐ Idle", "lost": "○ No hand"}
            self._icon.title = f"AIROS  {labels.get(status, '')}"

    def stop(self):
        if self._icon:
            self._icon.stop()
