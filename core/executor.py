"""core/executor.py — Executes action dicts. Uses Win32 for hotkeys to avoid pyautogui overhead."""
import ctypes, subprocess, logging, time
logger = logging.getLogger(__name__)

import pyautogui
pyautogui.PAUSE    = 0.0
pyautogui.FAILSAFE = False

_APPS = {
    "chrome":"chrome.exe","browser":"chrome.exe","firefox":"firefox.exe",
    "edge":"msedge.exe","spotify":"spotify.exe","code":"code.exe",
    "vscode":"code.exe","terminal":"cmd.exe","notepad":"notepad.exe",
    "calculator":"calc.exe","explorer":"explorer.exe",
    "word":"winword.exe","excel":"excel.exe","powerpoint":"powerpnt.exe",
    "vlc":"vlc.exe","teams":"teams.exe","slack":"slack.exe",
}


class CommandExecutor:
    def __init__(self, cfg):
        self.cfg    = cfg
        self._demo  = cfg.DEMO_MODE
        from core.cursor import CursorController
        self.cursor = CursorController(cfg)

    def execute(self, action):
        if not action or action.get("type") == "none":
            return
        if self._demo:
            logger.debug("[DEMO] %s", action)
            return
        t = action["type"]
        try:
            if   t == "mouse_move":   self.cursor.move(action["norm_x"], action["norm_y"])
            elif t == "click":        self.cursor.click(action.get("button","left"))
            elif t == "double_click": self.cursor.double_click()
            elif t == "right_click":  self.cursor.right_click()
            elif t == "scroll":       self.cursor.scroll(action["direction"])
            elif t == "drag_start":   self.cursor.drag_start()
            elif t == "drag_end":     self.cursor.drag_end()
            elif t == "key":          pyautogui.press(action["key"], _pause=False)
            elif t == "hotkey":       pyautogui.hotkey(*action["keys"], _pause=False)
            elif t == "launch":       self._launch(action["app"])
        except Exception as e:
            logger.warning("Executor [%s]: %s", t, e)

    def _launch(self, name):
        exe = _APPS.get(name.lower(), name)
        try:
            subprocess.Popen(exe, shell=True)
        except Exception as e:
            logger.warning("Launch failed [%s]: %s", exe, e)
