"""
ui/camera_window.py — Live camera preview window.

Shows:
  • Your live webcam feed with MediaPipe hand skeleton drawn on it
  • Current gesture name (large text, bottom of frame)
  • Tracking status bar (top of frame)
  • FPS counter
  • Gesture confidence indicator
  • Always-on-top toggle
  • Resizable, draggable window

Runs in its own thread, feeds frames from the pipeline via update().
"""
import tkinter as tk
import cv2
import numpy as np
import threading
import time
import logging
from PIL import Image, ImageTk

logger = logging.getLogger(__name__)

# Gesture display info: token → (display_name, color_BGR, emoji)
GESTURE_DISPLAY = {
    "cursor_move":  ("Moving Cursor",  (0, 255, 136),  "☝️"),
    "click":        ("Click",          (0, 207, 255),  "👌"),
    "double_click": ("Double Click",   (0, 207, 255),  "👌👌"),
    "right_click":  ("Right Click",    (0, 204, 255),  "🤙"),
    "scroll_up":    ("Scroll Up",      (0, 255, 136),  "✌️↑"),
    "scroll_down":  ("Scroll Down",    (0, 255, 136),  "✌️↓"),
    "swipe_right":  ("Swipe →",        (50, 107, 255), "👋"),
    "swipe_left":   ("Swipe ←",        (50, 107, 255), "👋"),
    "grab":         ("Grab / Drag",    (204, 68, 255), "✊"),
    "drag_end":     ("Released",       (0, 255, 136),  "🖐️"),
    "open_palm":    ("Open Palm",      (0, 255, 136),  "🖐️"),
    "pinch":        ("Pinch",          (255, 200, 0),  "🤏"),
    "peace":        ("Peace ✌",        (0, 255, 200),  "✌️"),
    "idle":         ("",               (60, 60, 60),   ""),
}

STATUS_COLORS = {
    "active": (0, 255, 136),
    "idle":   (0, 204, 255),
    "lost":   (60, 60, 255),
}


def _draw_overlay(frame, gesture, status, fps):
    """Draw all HUD elements onto the frame."""
    h, w = frame.shape[:2]

    # ── Top status bar ────────────────────────────────────────────────────────
    cv2.rectangle(frame, (0, 0), (w, 36), (10, 15, 22), -1)

    # Status dot + text
    scol  = STATUS_COLORS.get(status, (60,60,255))
    slbl  = {"active":"● TRACKING","idle":"● IDLE","lost":"● NO HAND"}.get(status,"●")
    cv2.putText(frame, slbl, (12, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, scol, 2, cv2.LINE_AA)

    # FPS (right side)
    cv2.putText(frame, f"{fps:.0f} FPS", (w - 80, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 120, 100), 1, cv2.LINE_AA)

    # App title (centre)
    cv2.putText(frame, "GestureOS", (w//2 - 48, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 80, 60), 1, cv2.LINE_AA)

    # ── Bottom gesture label ──────────────────────────────────────────────────
    info = GESTURE_DISPLAY.get(gesture or "idle", ("", (60,60,60), ""))
    label, color, emoji = info

    if label:
        # Dark pill background
        bar_h = 52
        cv2.rectangle(frame, (0, h - bar_h), (w, h), (8, 12, 18), -1)

        # Coloured left accent bar
        cv2.rectangle(frame, (0, h - bar_h), (4, h), color, -1)

        # Gesture name — large
        cv2.putText(frame, label, (16, h - bar_h + 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.95, color, 2, cv2.LINE_AA)

        # Instruction hint — small
        hints = {
            "cursor_move":  "Point index finger to move",
            "click":        "Thumb + index together",
            "double_click": "Quick double pinch",
            "right_click":  "Pinky only extended",
            "scroll_up":    "Two fingers up, move up",
            "scroll_down":  "Two fingers up, move down",
            "swipe_right":  "Fast rightward motion",
            "swipe_left":   "Fast leftward motion",
            "grab":         "Fist closed — dragging",
            "open_palm":    "All 5 fingers open",
            "pinch":        "Thumb + index close",
        }
        hint = hints.get(gesture or "", "")
        if hint:
            cv2.putText(frame, hint, (16, h - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (80, 110, 90), 1, cv2.LINE_AA)

    # ── Landmark dot count indicator (top right corner) ───────────────────────
    if status == "active":
        cv2.putText(frame, "21 pts", (w - 72, h - (bar_h + 6) if label else h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (40, 80, 60), 1, cv2.LINE_AA)

    return frame


class CameraWindow:
    """
    Standalone tkinter window showing live annotated camera feed.
    Feed frames via .push_frame(frame, gesture, status).
    Toggle visibility via .toggle().
    """

    def __init__(self, cfg):
        self.cfg       = cfg
        self._root     = None
        self._label    = None
        self._visible  = False
        self._latest   = None   # latest (frame, gesture, status) tuple
        self._lock     = threading.Lock()
        self._fps_times = []
        self._on_top   = True

    # ── public API ────────────────────────────────────────────────────────────

    def push_frame(self, frame, gesture, status):
        """Called from pipeline thread — non-blocking."""
        with self._lock:
            self._latest = (frame.copy(), gesture, status)

    def toggle(self):
        if self._root:
            self._root.after(0, self._do_toggle)

    def show(self):
        if self._root:
            self._root.after(0, self._do_show)

    def hide(self):
        if self._root:
            self._root.after(0, self._do_hide)

    def run(self):
        """Call from a dedicated thread — blocks."""
        self._root = tk.Tk()
        self._root.title("GestureOS — Camera Preview")
        self._root.configure(bg="#0d1117")
        self._root.resizable(True, True)
        self._root.attributes("-topmost", True)
        self._root.protocol("WM_DELETE_WINDOW", self._do_hide)

        # Default size — 480×290 (compact)
        self._root.geometry("480x320+20+20")

        self._build_ui()
        self._tick()   # start update loop
        self._root.mainloop()

    def close(self):
        if self._root:
            self._root.after(0, self._root.destroy)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # Control bar
        ctrl = tk.Frame(self._root, bg="#161b22", pady=4)
        ctrl.pack(fill="x")

        tk.Label(ctrl, text="📷  Camera Preview",
                 font=("Segoe UI", 10, "bold"),
                 bg="#161b22", fg="#00ff88").pack(side="left", padx=10)

        # Always-on-top toggle
        self._ontop_var = tk.BooleanVar(value=True)
        ontop_cb = tk.Checkbutton(ctrl, text="Always on top",
                                  variable=self._ontop_var,
                                  command=self._toggle_ontop,
                                  bg="#161b22", fg="#6e7681",
                                  selectcolor="#0d1117",
                                  activebackground="#161b22",
                                  font=("Segoe UI", 9))
        ontop_cb.pack(side="right", padx=10)

        hide_btn = tk.Label(ctrl, text="✕ Hide",
                            font=("Segoe UI", 9), bg="#161b22",
                            fg="#6e7681", cursor="hand2", padx=8)
        hide_btn.pack(side="right")
        hide_btn.bind("<Button-1>", lambda e: self._do_hide())
        hide_btn.bind("<Enter>",    lambda e: hide_btn.config(fg="#ff4444"))
        hide_btn.bind("<Leave>",    lambda e: hide_btn.config(fg="#6e7681"))

        # Camera feed label
        self._label = tk.Label(self._root, bg="#0d1117")
        self._label.pack(fill="both", expand=True)

        # Bottom info bar
        self._info_bar = tk.Label(self._root, text="Waiting for camera...",
                                  font=("Segoe UI", 9),
                                  bg="#161b22", fg="#6e7681", pady=4)
        self._info_bar.pack(fill="x")

    # ── update loop ───────────────────────────────────────────────────────────

    def _tick(self):
        """Runs every 33ms in tkinter main loop — pulls latest frame and displays it."""
        with self._lock:
            data = self._latest

        if data is not None and self._visible:
            frame, gesture, status = data

            # FPS calculation
            now = time.perf_counter()
            self._fps_times.append(now)
            self._fps_times = [t for t in self._fps_times if now - t < 1.0]
            fps = len(self._fps_times)

            # Draw overlay
            annotated = _draw_overlay(frame.copy(), gesture, status, fps)

            # Resize to fit window
            win_w = self._label.winfo_width()  or 480
            win_h = self._label.winfo_height() or 280
            if win_w > 10 and win_h > 10:
                fh, fw = annotated.shape[:2]
                scale  = min(win_w / fw, win_h / fh)
                nw, nh = int(fw * scale), int(fh * scale)
                annotated = cv2.resize(annotated, (nw, nh), interpolation=cv2.INTER_LINEAR)

            # BGR → RGB → PIL → ImageTk
            rgb  = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            img  = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(image=img)

            self._label.configure(image=imgtk)
            self._label.image = imgtk  # keep reference

            # Update info bar
            info = GESTURE_DISPLAY.get(gesture or "idle", ("—", None, ""))
            g_name = info[0] or "—"
            self._info_bar.config(
                text=f"Gesture: {g_name}   |   Status: {status}   |   {fps} FPS"
            )

        self._root.after(33, self._tick)   # ~30 FPS refresh

    # ── visibility ────────────────────────────────────────────────────────────

    def _do_toggle(self):
        if self._visible:
            self._do_hide()
        else:
            self._do_show()

    def _do_show(self):
        self._visible = True
        self._root.deiconify()
        self._root.lift()

    def _do_hide(self):
        self._visible = False
        self._root.withdraw()

    def _toggle_ontop(self):
        self._on_top = self._ontop_var.get()
        self._root.attributes("-topmost", self._on_top)
