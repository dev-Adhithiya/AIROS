"""ui/sidebar.py — Slide-in/out panel showing active context + AI chat.

Triggered by clicking the HUD ☰ button or by a specific gesture.
Slides in from the right edge of the screen, always-on-top.
"""
import tkinter as tk
from tkinter import ttk
import threading
import time
import logging

logger = logging.getLogger(__name__)

BG      = "#0d1117"
BG2     = "#161b22"
BG3     = "#21262d"
ACCENT  = "#00ff88"
ACCENT2 = "#00cfff"
WARN    = "#ffcc00"
DANGER  = "#ff4444"
TEXT    = "#c9d1d9"
MUTED   = "#6e7681"
BORDER  = "#30363d"


class Sidebar:
    """
    Compact slide-in sidebar.
    Always on top, transparent background, slides from right edge.
    """

    def __init__(self, cfg, on_voice_command=None):
        self.cfg              = cfg
        self.on_voice_command = on_voice_command
        self._visible         = False
        self._root            = None
        self._chat_lines      = []
        self._context         = "—"
        self._status          = "lost"
        self._gesture         = "—"
        self._anim_running    = False

    # ── public thread-safe API ────────────────────────────────────────────────

    def toggle(self):
        if self._root:
            self._root.after(0, self._do_toggle)

    def update_context(self, ctx: str):
        self._context = ctx.split()[0].capitalize() if ctx and ctx != "default" else "—"
        if self._root and self._visible:
            self._root.after(0, self._refresh_status_bar)

    def update_status(self, status: str, gesture: str = ""):
        self._status  = status
        self._gesture = gesture or "—"
        if self._root and self._visible:
            self._root.after(0, self._refresh_status_bar)

    def add_chat(self, user_text: str, ai_reply: str):
        self._chat_lines.append(("user", user_text))
        self._chat_lines.append(("ai",   ai_reply))
        if self._root:
            self._root.after(0, self._refresh_chat)

    def run(self):
        """Call from main thread — blocks until destroyed."""
        self._root = tk.Tk()
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 0.96)
        self._root.configure(bg=BG)
        self._root.resizable(False, False)

        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        w  = self.cfg.SIDEBAR_WIDTH
        h  = sh - 80          # full height minus taskbar
        self._sw = sw
        self._sh = sh
        self._w  = w
        self._h  = h

        # Start off-screen to the right
        self._x_hidden  = sw + 10
        self._x_visible = sw - w - 4
        self._root.geometry(f"{w}x{h}+{self._x_hidden}+4")

        self._build_ui()
        self._root.mainloop()

    def close(self):
        if self._root:
            self._root.after(0, self._root.destroy)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = self._root

        # Outer border frame
        border = tk.Frame(root, bg=BORDER, padx=1, pady=1)
        border.pack(fill="both", expand=True)

        main = tk.Frame(border, bg=BG)
        main.pack(fill="both", expand=True)

        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(main, bg=BG2, padx=14, pady=10)
        header.pack(fill="x")

        tk.Label(header, text="GESTURE", font=("Segoe UI", 14, "bold"),
                 bg=BG2, fg=TEXT).pack(side="left")
        tk.Label(header, text="OS", font=("Segoe UI", 14, "bold"),
                 bg=BG2, fg=ACCENT).pack(side="left")

        close_btn = tk.Label(header, text="✕", font=("Segoe UI", 13),
                             bg=BG2, fg=MUTED, cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self._do_toggle())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg=DANGER))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg=MUTED))

        # ── Status bar ────────────────────────────────────────────────────────
        status_frame = tk.Frame(main, bg=BG3, padx=14, pady=8)
        status_frame.pack(fill="x")

        self._status_dot = tk.Label(status_frame, text="●", font=("Segoe UI", 10),
                                    bg=BG3, fg=DANGER)
        self._status_dot.pack(side="left")

        self._status_lbl = tk.Label(status_frame, text="Not detected",
                                    font=("Segoe UI", 10), bg=BG3, fg=MUTED)
        self._status_lbl.pack(side="left", padx=(5, 0))

        tk.Label(status_frame, text="App:", font=("Segoe UI", 10),
                 bg=BG3, fg=MUTED).pack(side="right", padx=(0, 0))
        self._ctx_lbl = tk.Label(status_frame, text="—",
                                 font=("Segoe UI", 10, "bold"), bg=BG3, fg=ACCENT2)
        self._ctx_lbl.pack(side="right", padx=(0, 4))

        # ── Gesture display ───────────────────────────────────────────────────
        gest_frame = tk.Frame(main, bg=BG, padx=14, pady=10)
        gest_frame.pack(fill="x")

        tk.Label(gest_frame, text="ACTIVE GESTURE", font=("Segoe UI", 9),
                 bg=BG, fg=MUTED).pack(anchor="w")

        self._gesture_lbl = tk.Label(
            gest_frame, text="—",
            font=("Segoe UI", 20, "bold"),
            bg=BG, fg=ACCENT,
        )
        self._gesture_lbl.pack(anchor="w", pady=(2, 0))

        # ── Divider ───────────────────────────────────────────────────────────
        tk.Frame(main, bg=BORDER, height=1).pack(fill="x", padx=14)

        # ── AI Chat section ───────────────────────────────────────────────────
        chat_header = tk.Frame(main, bg=BG, padx=14, pady=8)
        chat_header.pack(fill="x")
        tk.Label(chat_header, text="AI ASSISTANT", font=("Segoe UI", 9),
                 bg=BG, fg=MUTED).pack(side="left")
        tk.Label(chat_header, text="🎙️ voice activated",
                 font=("Segoe UI", 8), bg=BG, fg=BORDER).pack(side="right")

        # Chat scroll area
        chat_outer = tk.Frame(main, bg=BG2, padx=1, pady=1)
        chat_outer.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        chat_canvas = tk.Canvas(chat_outer, bg=BG2, highlightthickness=0)
        scrollbar   = tk.Scrollbar(chat_outer, orient="vertical",
                                   command=chat_canvas.yview)
        self._chat_frame = tk.Frame(chat_canvas, bg=BG2)
        self._chat_frame.bind("<Configure>",
                              lambda e: chat_canvas.configure(
                                  scrollregion=chat_canvas.bbox("all")))
        chat_canvas.create_window((0, 0), window=self._chat_frame, anchor="nw")
        chat_canvas.configure(yscrollcommand=scrollbar.set)
        chat_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._chat_canvas = chat_canvas

        # Input row
        input_frame = tk.Frame(main, bg=BG, padx=14, pady=8)
        input_frame.pack(fill="x", side="bottom")

        self._input_var = tk.StringVar()
        entry = tk.Entry(input_frame, textvariable=self._input_var,
                         bg=BG3, fg=TEXT, insertbackground=ACCENT,
                         relief="flat", font=("Segoe UI", 11),
                         highlightbackground=BORDER, highlightthickness=1)
        entry.pack(side="left", fill="x", expand=True, ipady=6)
        entry.bind("<Return>", self._on_send)

        send_btn = tk.Label(input_frame, text="→", font=("Segoe UI", 14),
                            bg=BG3, fg=ACCENT, padx=10, cursor="hand2")
        send_btn.pack(side="left", padx=(4, 0))
        send_btn.bind("<Button-1>", self._on_send)

        # ── Gesture reference quick-card ──────────────────────────────────────
        tk.Frame(main, bg=BORDER, height=1).pack(fill="x", padx=14)
        ref_frame = tk.Frame(main, bg=BG, padx=14, pady=8)
        ref_frame.pack(fill="x", side="bottom")

        ref_pairs = [
            ("☝️ Move","→ cursor"),("👌 Pinch","→ click"),
            ("✌️ Two","→ scroll"),("👉👈 Swipe","→ nav"),
            ("✊ Grab","→ drag"),("🖐️ Palm","→ release"),
        ]
        ref_grid = tk.Frame(ref_frame, bg=BG)
        ref_grid.pack(fill="x")
        for i, (g, a) in enumerate(ref_pairs):
            tk.Label(ref_grid, text=g, font=("Segoe UI", 9, "bold"),
                     bg=BG, fg=ACCENT2, anchor="w").grid(row=i//2, column=(i%2)*2, sticky="w", padx=(0,4), pady=1)
            tk.Label(ref_grid, text=a, font=("Segoe UI", 9),
                     bg=BG, fg=MUTED, anchor="w").grid(row=i//2, column=(i%2)*2+1, sticky="w", padx=(0,14), pady=1)

    # ── refresh helpers ───────────────────────────────────────────────────────

    def _refresh_status_bar(self):
        colors = {"active":ACCENT, "idle":WARN, "lost":DANGER}
        labels = {"active":"Tracking active", "idle":"Idle / sleeping", "lost":"Hand not detected"}
        c = colors.get(self._status, DANGER)
        self._status_dot.config(fg=c)
        self._status_lbl.config(text=labels.get(self._status, "Unknown"))
        self._ctx_lbl.config(text=self._context)
        from ui.hud import GESTURE_LABELS
        self._gesture_lbl.config(text=GESTURE_LABELS.get(self._gesture, self._gesture))

    def _refresh_chat(self):
        for w in self._chat_frame.winfo_children():
            w.destroy()

        for role, text in self._chat_lines[-20:]:   # keep last 20 msgs
            if role == "user":
                bubble = tk.Frame(self._chat_frame, bg=BG3, padx=10, pady=6)
                bubble.pack(fill="x", pady=(4, 0), padx=6)
                tk.Label(bubble, text="You", font=("Segoe UI", 8, "bold"),
                         bg=BG3, fg=ACCENT2).pack(anchor="w")
                tk.Label(bubble, text=text, font=("Segoe UI", 10),
                         bg=BG3, fg=TEXT, wraplength=self.cfg.SIDEBAR_WIDTH - 50,
                         anchor="w", justify="left").pack(anchor="w")
            else:
                bubble = tk.Frame(self._chat_frame, bg=BG, padx=10, pady=6)
                bubble.pack(fill="x", pady=(2, 4), padx=6)
                tk.Label(bubble, text="AI", font=("Segoe UI", 8, "bold"),
                         bg=BG, fg=ACCENT).pack(anchor="w")
                tk.Label(bubble, text=text, font=("Segoe UI", 10),
                         bg=BG, fg=TEXT, wraplength=self.cfg.SIDEBAR_WIDTH - 50,
                         anchor="w", justify="left").pack(anchor="w")

        self._chat_canvas.update_idletasks()
        self._chat_canvas.yview_moveto(1.0)

    # ── slide animation ───────────────────────────────────────────────────────

    def _do_toggle(self):
        if self._anim_running:
            return
        self._visible = not self._visible
        target = self._x_visible if self._visible else self._x_hidden
        self._animate_to(target)
        if self._visible:
            self._refresh_status_bar()
            self._refresh_chat()

    def _animate_to(self, target_x):
        self._anim_running = True
        steps   = 12
        cur_x   = self._root.winfo_x()
        step_dx = (target_x - cur_x) / steps

        def _step(n=0):
            if n >= steps:
                self._root.geometry(f"+{target_x}+4")
                self._anim_running = False
                return
            nx = int(cur_x + step_dx * (n + 1))
            self._root.geometry(f"+{nx}+4")
            self._root.after(self.cfg.SIDEBAR_SLIDE_MS // steps, _step, n + 1)

        _step()

    # ── input ─────────────────────────────────────────────────────────────────

    def _on_send(self, _event=None):
        text = self._input_var.get().strip()
        if not text:
            return
        self._input_var.set("")
        if self.on_voice_command:
            self.on_voice_command(text)
