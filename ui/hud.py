"""ui/hud.py — Tiny always-on-top corner indicator.

Shows:  ● status dot  |  gesture name  |  click to open sidebar
Transparent background, click-through when idle, non-intrusive.
"""
import tkinter as tk
import threading
import time
import logging

logger = logging.getLogger(__name__)

STATUS_COLORS = {
    "active": "#00ff88",
    "idle":   "#ffcc00",
    "lost":   "#ff4444",
}

GESTURE_LABELS = {
    "cursor_move":  "Moving",
    "click":        "Click",
    "double_click": "Dbl Click",
    "right_click":  "R-Click",
    "scroll_up":    "Scroll ↑",
    "scroll_down":  "Scroll ↓",
    "swipe_left":   "Swipe ←",
    "swipe_right":  "Swipe →",
    "grab":         "Grab",
    "drag_end":     "Release",
    "open_palm":    "Palm",
    "pinch":        "Pinch",
    "peace":        "Peace ✌",
    "idle":         "",
}


class HUD:
    """
    Tiny floating indicator pinned to a screen corner.
    Click it to show/hide the sidebar.
    """

    def __init__(self, cfg, on_toggle_sidebar):
        self.cfg              = cfg
        self.on_toggle_sidebar = on_toggle_sidebar
        self._status          = "lost"
        self._gesture         = ""
        self._context         = ""
        self._root            = None
        self._gesture_clear_job = None

    # ── public thread-safe API ────────────────────────────────────────────────

    def update_status(self, status: str):
        self._status = status
        if self._root:
            self._root.after(0, self._refresh)

    def update_gesture(self, gesture: str, context: str = ""):
        if gesture not in ("cursor_move", "idle", None):
            self._gesture = GESTURE_LABELS.get(gesture, gesture)
            self._context = context.split()[0] if context else ""
            if self._root:
                self._root.after(0, self._refresh)
                if self._gesture_clear_job:
                    self._root.after_cancel(self._gesture_clear_job)
                self._gesture_clear_job = self._root.after(1400, self._clear_gesture)

    def _clear_gesture(self):
        self._gesture = ""
        self._refresh()

    def run(self):
        """Call from main thread — blocks until window is closed."""
        self._root = tk.Tk()
        self._root.overrideredirect(True)          # no title bar
        self._root.attributes("-topmost", True)    # always on top
        self._root.attributes("-alpha", self.cfg.HUD_OPACITY)
        self._root.configure(bg="#0d1117")
        self._root.resizable(False, False)

        # ── widgets ───────────────────────────────────────────────────────────
        outer = tk.Frame(self._root, bg="#0d1117",
                         highlightbackground="#30363d", highlightthickness=1)
        outer.pack(padx=0, pady=0)

        inner = tk.Frame(outer, bg="#0d1117", padx=10, pady=6)
        inner.pack()

        self._dot = tk.Label(inner, text="●", font=("Segoe UI", 11),
                             bg="#0d1117", fg="#ff4444")
        self._dot.pack(side="left")

        self._g_lbl = tk.Label(inner, text="", font=("Segoe UI", 10, "bold"),
                               bg="#0d1117", fg="#00cfff", width=10, anchor="w")
        self._g_lbl.pack(side="left", padx=(6, 0))

        self._ctx_lbl = tk.Label(inner, text="", font=("Segoe UI", 9),
                                 bg="#0d1117", fg="#6e7681", width=8, anchor="w")
        self._ctx_lbl.pack(side="left", padx=(4, 0))

        sep = tk.Label(inner, text="|", bg="#0d1117", fg="#30363d",
                       font=("Segoe UI", 10))
        sep.pack(side="left", padx=6)

        self._toggle_btn = tk.Label(inner, text="☰", font=("Segoe UI", 12),
                                    bg="#0d1117", fg="#6e7681", cursor="hand2")
        self._toggle_btn.pack(side="left")
        self._toggle_btn.bind("<Button-1>", lambda e: self.on_toggle_sidebar())
        self._toggle_btn.bind("<Enter>",    lambda e: self._toggle_btn.config(fg="#00ff88"))
        self._toggle_btn.bind("<Leave>",    lambda e: self._toggle_btn.config(fg="#6e7681"))

        # ── drag to reposition ────────────────────────────────────────────────
        for w in [outer, inner, self._dot, self._g_lbl, self._ctx_lbl, sep]:
            w.bind("<ButtonPress-1>",   self._drag_start)
            w.bind("<B1-Motion>",       self._drag_motion)

        self._drag_x = self._drag_y = 0

        self._position()
        self._refresh()
        self._root.mainloop()

    def close(self):
        if self._root:
            self._root.after(0, self._root.destroy)

    # ── internals ─────────────────────────────────────────────────────────────

    def _refresh(self):
        color = STATUS_COLORS.get(self._status, "#ff4444")
        self._dot.config(fg=color)
        self._g_lbl.config(text=self._gesture)
        self._ctx_lbl.config(text=self._context)

    def _position(self):
        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        ww = self._root.winfo_reqwidth()
        wh = self._root.winfo_reqheight()
        pad = 12
        corner = self.cfg.HUD_CORNER
        x = sw - ww - pad if "right"  in corner else pad
        y = sh - wh - 48  if "bottom" in corner else pad   # 48 = taskbar offset
        self._root.geometry(f"+{x}+{y}")

    def _drag_start(self, e):
        self._drag_x = e.x_root - self._root.winfo_x()
        self._drag_y = e.y_root - self._root.winfo_y()

    def _drag_motion(self, e):
        x = e.x_root - self._drag_x
        y = e.y_root - self._drag_y
        self._root.geometry(f"+{x}+{y}")
