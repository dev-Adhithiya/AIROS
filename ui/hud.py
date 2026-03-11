"""ui/hud.py — Tiny always-on-top corner indicator."""
import tkinter as tk
import logging
logger = logging.getLogger(__name__)

STATUS_COLORS = {"active":"#00ff88","idle":"#ffcc00","lost":"#ff4444"}

GESTURE_LABELS = {
    "cursor_move":"Moving","click":"Click","double_click":"Dbl Click",
    "right_click":"R-Click 🤙","scroll_up":"Scroll ↑","scroll_down":"Scroll ↓",
    "swipe_left":"Swipe ←","swipe_right":"Swipe →","grab":"Grab",
    "drag_end":"Release","open_palm":"Palm","pinch":"Pinch",
    "peace":"Peace ✌","idle":"",
}


class HUD:
    def __init__(self, cfg, on_toggle_sidebar, on_ready=None):
        self.cfg               = cfg
        self.on_toggle_sidebar = on_toggle_sidebar
        self._on_ready         = on_ready   # called with root once tkinter starts
        self._status           = "lost"
        self._gesture          = ""
        self._root             = None
        self._gesture_clear_job = None

    # ── public thread-safe API ────────────────────────────────────────────────

    def update_status(self, status):
        self._status = status
        if self._root: self._root.after(0, self._refresh)

    def update_gesture(self, gesture, context=""):
        if gesture not in ("cursor_move","idle",None):
            self._gesture = GESTURE_LABELS.get(gesture, gesture)
            if self._root:
                self._root.after(0, self._refresh)
                if self._gesture_clear_job:
                    self._root.after_cancel(self._gesture_clear_job)
                self._gesture_clear_job = self._root.after(1400, self._clear_gesture)

    def schedule(self, fn):
        """Run fn in the main tkinter thread."""
        if self._root: self._root.after(0, fn)

    def close(self):
        if self._root: self._root.after(0, self._root.destroy)

    # ── main thread ───────────────────────────────────────────────────────────

    def run(self):
        self._root = tk.Tk()
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", self.cfg.HUD_OPACITY)
        self._root.configure(bg="#0d1117")

        outer = tk.Frame(self._root, bg="#0d1117",
                         highlightbackground="#30363d", highlightthickness=1)
        outer.pack()
        inner = tk.Frame(outer, bg="#0d1117", padx=10, pady=6)
        inner.pack()

        self._dot = tk.Label(inner, text="●", font=("Segoe UI",11),
                             bg="#0d1117", fg="#ff4444")
        self._dot.pack(side="left")

        self._g_lbl = tk.Label(inner, text="", font=("Segoe UI",10,"bold"),
                               bg="#0d1117", fg="#00cfff", width=10, anchor="w")
        self._g_lbl.pack(side="left", padx=(6,0))

        tk.Label(inner, text="|", bg="#0d1117", fg="#30363d",
                 font=("Segoe UI",10)).pack(side="left", padx=6)

        # Camera toggle button
        self._cam_btn = tk.Label(inner, text="📷", font=("Segoe UI",11),
                                 bg="#0d1117", fg="#6e7681", cursor="hand2")
        self._cam_btn.pack(side="left", padx=(0,4))
        self._cam_btn.bind("<Button-1>", lambda e: self._on_cam_click())
        self._cam_btn.bind("<Enter>", lambda e: self._cam_btn.config(fg="#00ff88"))
        self._cam_btn.bind("<Leave>", lambda e: self._cam_btn.config(fg="#6e7681"))

        toggle_btn = tk.Label(inner, text="☰", font=("Segoe UI",12),
                              bg="#0d1117", fg="#6e7681", cursor="hand2")
        toggle_btn.pack(side="left")
        toggle_btn.bind("<Button-1>", lambda e: self.on_toggle_sidebar())
        toggle_btn.bind("<Enter>", lambda e: toggle_btn.config(fg="#00ff88"))
        toggle_btn.bind("<Leave>", lambda e: toggle_btn.config(fg="#6e7681"))

        for w in [outer, inner, self._dot, self._g_lbl]:
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_motion)
        self._drag_x = self._drag_y = 0

        self._position()
        self._refresh()

        # Notify that tkinter is ready — camera window can now attach
        if self._on_ready:
            self._root.after(200, lambda: self._on_ready(self._root))

        self._root.mainloop()

    # ── internals ─────────────────────────────────────────────────────────────

    def _on_cam_click(self):
        # Import here to avoid circular at module load
        # The cam_win toggle is wired via the schedule mechanism
        if hasattr(self, '_cam_toggle_fn') and self._cam_toggle_fn:
            self._cam_toggle_fn()

    def set_cam_toggle(self, fn):
        self._cam_toggle_fn = fn

    def _clear_gesture(self):
        self._gesture = ""
        self._refresh()

    def _refresh(self):
        color = STATUS_COLORS.get(self._status, "#ff4444")
        self._dot.config(fg=color)
        self._g_lbl.config(text=self._gesture)

    def _position(self):
        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        ww = self._root.winfo_reqwidth()
        wh = self._root.winfo_reqheight()
        pad = 12
        corner = self.cfg.HUD_CORNER
        x = sw - ww - pad if "right"  in corner else pad
        y = sh - wh - 48  if "bottom" in corner else pad
        self._root.geometry(f"+{x}+{y}")

    def _drag_start(self, e):
        self._drag_x = e.x_root - self._root.winfo_x()
        self._drag_y = e.y_root - self._root.winfo_y()

    def _drag_motion(self, e):
        self._root.geometry(f"+{e.x_root-self._drag_x}+{e.y_root-self._drag_y}")
