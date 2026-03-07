"""ui/tray.py — System tray icon with Start / Stop / Settings / Quit menu."""
import threading
import logging
import sys

logger = logging.getLogger(__name__)

try:
    import pystray
    from pystray import MenuItem as MItem
    from PIL import Image, ImageDraw
    _TRAY = True
except ImportError:
    _TRAY = False
    logger.warning("pystray/Pillow not installed — tray icon disabled. "
                   "Install with: pip install pystray pillow")


def _make_icon():
    """Generate a simple green-dot icon programmatically (no image file needed)."""
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d    = ImageDraw.Draw(img)
    # Dark background circle
    d.ellipse([2, 2, size-2, size-2], fill=(13, 17, 23, 255))
    # Green dot
    d.ellipse([14, 14, size-14, size-14], fill=(0, 255, 136, 255))
    return img


class TrayIcon:
    def __init__(self, on_start, on_stop, on_toggle_sidebar, on_quit):
        self.on_start           = on_start
        self.on_stop            = on_stop
        self.on_toggle_sidebar  = on_toggle_sidebar
        self.on_quit            = on_quit
        self._icon              = None
        self._running           = False

    def run(self):
        if not _TRAY:
            logger.warning("Tray icon unavailable.")
            return

        def _start(icon, item):
            self._running = True
            self._update_menu()
            self.on_start()

        def _stop(icon, item):
            self._running = False
            self._update_menu()
            self.on_stop()

        def _sidebar(icon, item):
            self.on_toggle_sidebar()

        def _quit(icon, item):
            icon.stop()
            self.on_quit()

        self._icon = pystray.Icon(
            "GestureOS",
            _make_icon(),
            "GestureOS",
            menu=pystray.Menu(
                MItem("▶  Start GestureOS",  _start,  default=True),
                MItem("■  Stop",             _stop),
                pystray.Menu.SEPARATOR,
                MItem("☰  Toggle Sidebar",   _sidebar),
                pystray.Menu.SEPARATOR,
                MItem("✕  Quit",             _quit),
            ),
        )
        self._icon.run()

    def set_status(self, status: str):
        """Update tray tooltip."""
        if self._icon:
            labels = {"active":"● Active", "idle":"◐ Idle", "lost":"○ No hand"}
            self._icon.title = f"GestureOS  {labels.get(status,'')}"

    def _update_menu(self):
        pass   # pystray menus are rebuilt on next open automatically

    def stop(self):
        if self._icon:
            self._icon.stop()
