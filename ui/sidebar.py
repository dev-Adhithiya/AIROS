"""
ui/sidebar.py — Slide-in panel: status, AI chat, gesture preview images.
"""
import tkinter as tk
from tkinter import ttk
import threading, time, logging
logger = logging.getLogger(__name__)

BG   = "#0d1117"; BG2 = "#161b22"; BG3 = "#21262d"
ACC  = "#00ff88"; AC2 = "#00cfff"; WARN= "#ffcc00"
DNG  = "#ff4444"; TXT = "#c9d1d9"; MUT = "#6e7681"
BDR  = "#30363d"

# ── Gesture SVG hand diagrams (inline, no files needed) ───────────────────────
# Each entry: (label, description, svg_path_data)
# SVG viewBox 0 0 60 80  — finger = line from knuckle to tip
# 1=extended(bright), 0=closed(dim), T=thumb

def _hand_svg(thumb, index, middle, ring, pinky, highlight_color="#00ff88"):
    """Generate a simple SVG hand diagram. 1=extended, 0=closed."""
    lines = []

    # Palm base
    lines.append('<rect x="18" y="45" width="24" height="20" rx="4" fill="#1a3040"/>')
    lines.append('<ellipse cx="30" cy="65" rx="12" ry="8" fill="#1a3040"/>')

    # Finger data: (base_x, base_y, tip_x_open, tip_y_open, tip_x_closed, tip_y_closed)
    fingers = [
        # index
        (24, 45, 20, 12, 23, 38),
        # middle
        (29, 43, 28,  8, 28, 36),
        # ring
        (34, 44, 36, 12, 33, 37),
        # pinky
        (38, 47, 44, 20, 38, 40),
    ]
    states = [index, middle, ring, pinky]
    colors = [highlight_color if s else "#2a4050" for s in states]

    for (bx, by, tx, ty, cx, cy), state, col in zip(fingers, states, colors):
        if state:
            lines.append(f'<line x1="{bx}" y1="{by}" x2="{tx}" y2="{ty}" stroke="{col}" stroke-width="4" stroke-linecap="round"/>')
            lines.append(f'<circle cx="{tx}" cy="{ty}" r="3" fill="{col}"/>')
        else:
            lines.append(f'<line x1="{bx}" y1="{by}" x2="{cx}" y2="{cy}" stroke="{col}" stroke-width="4" stroke-linecap="round"/>')

    # Thumb
    tcol = highlight_color if thumb else "#2a4050"
    if thumb:
        lines.append(f'<line x1="19" y1="52" x2="10" y2="42" stroke="{tcol}" stroke-width="4" stroke-linecap="round"/>')
        lines.append(f'<circle cx="10" cy="42" r="3" fill="{tcol}"/>')
    else:
        lines.append(f'<line x1="19" y1="52" x2="14" y2="46" stroke="{tcol}" stroke-width="4" stroke-linecap="round"/>')

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 80" width="60" height="80">'
        + "".join(lines)
        + "</svg>"
    )

GESTURES = [
    {
        "token":  "cursor_move",
        "emoji":  "☝️",
        "label":  "Move Cursor",
        "desc":   "Index finger only up.\nHand moves → cursor follows.",
        "thumb":0,"index":1,"middle":0,"ring":0,"pinky":0,
        "color": ACC,
    },
    {
        "token":  "click",
        "emoji":  "👌",
        "label":  "Left Click",
        "desc":   "Bring thumb tip to\nindex finger tip.",
        "thumb":1,"index":1,"middle":0,"ring":0,"pinky":0,
        "color": AC2,
    },
    {
        "token":  "double_click",
        "emoji":  "👌👌",
        "label":  "Double Click",
        "desc":   "Same as click but\ntwo times quickly.",
        "thumb":1,"index":1,"middle":0,"ring":0,"pinky":0,
        "color": AC2,
    },
    {
        "token":  "right_click",
        "emoji":  "🤙",
        "label":  "Right Click",
        "desc":   "PINKY finger only up.\n(All others closed)",
        "thumb":0,"index":0,"middle":0,"ring":0,"pinky":1,
        "color": WARN,
    },
    {
        "token":  "scroll_up",
        "emoji":  "✌️↑",
        "label":  "Scroll Up",
        "desc":   "Index + middle up.\nMove hand upward.",
        "thumb":0,"index":1,"middle":1,"ring":0,"pinky":0,
        "color": ACC,
    },
    {
        "token":  "scroll_down",
        "emoji":  "✌️↓",
        "label":  "Scroll Down",
        "desc":   "Index + middle up.\nMove hand downward.",
        "thumb":0,"index":1,"middle":1,"ring":0,"pinky":0,
        "color": ACC,
    },
    {
        "token":  "swipe_right",
        "emoji":  "👋→",
        "label":  "Swipe Right",
        "desc":   "Open hand, move\nquickly rightward.",
        "thumb":1,"index":1,"middle":1,"ring":1,"pinky":1,
        "color": "#ff6b35",
    },
    {
        "token":  "swipe_left",
        "emoji":  "👋←",
        "label":  "Swipe Left",
        "desc":   "Open hand, move\nquickly leftward.",
        "thumb":1,"index":1,"middle":1,"ring":1,"pinky":1,
        "color": "#ff6b35",
    },
    {
        "token":  "grab",
        "emoji":  "✊",
        "label":  "Grab / Drag",
        "desc":   "All fingers closed\nfist = hold & drag.",
        "thumb":0,"index":0,"middle":0,"ring":0,"pinky":0,
        "color": "#cc44ff",
    },
    {
        "token":  "open_palm",
        "emoji":  "🖐️",
        "label":  "Open Palm",
        "desc":   "All 5 fingers spread.\nReleases drag / wake.",
        "thumb":1,"index":1,"middle":1,"ring":1,"pinky":1,
        "color": ACC,
    },
]


class Sidebar:
    def __init__(self, cfg, on_voice_command=None):
        self.cfg             = cfg
        self.on_voice_command= on_voice_command
        self._visible        = False
        self._root           = None
        self._chat_lines     = []
        self._context        = "—"
        self._status         = "lost"
        self._gesture        = "—"
        self._anim_running   = False
        self._show_preview   = True    # gesture preview toggle

    # ── public API ────────────────────────────────────────────────────────────

    def toggle(self):
        if self._root:
            self._root.after(0, self._do_toggle)

    def update_context(self, ctx):
        self._context = ctx.split()[0].capitalize() if ctx and ctx != "default" else "—"
        if self._root and self._visible:
            self._root.after(0, self._refresh_status_bar)

    def update_status(self, status, gesture=""):
        self._status  = status
        if gesture and gesture not in ("cursor_move","idle",""):
            self._gesture = gesture
        if self._root and self._visible:
            self._root.after(0, self._refresh_status_bar)
            if gesture and gesture not in ("cursor_move","idle",""):
                self._root.after(0, lambda g=gesture: self._highlight_gesture(g))

    def add_chat(self, user_text, ai_reply):
        self._chat_lines.append(("user", user_text))
        self._chat_lines.append(("ai",   ai_reply))
        if self._root:
            self._root.after(0, self._refresh_chat)

    def run(self):
        self._root = tk.Tk()
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 0.97)
        self._root.configure(bg=BG)

        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        w  = self.cfg.SIDEBAR_WIDTH
        h  = sh - 80
        self._sw=sw; self._w=w; self._h=h
        self._x_hidden  = sw + 10
        self._x_visible = sw - w - 4
        self._root.geometry(f"{w}x{h}+{self._x_hidden}+4")

        self._build_ui()
        self._root.mainloop()

    def close(self):
        if self._root:
            self._root.after(0, self._root.destroy)

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = self._root

        border = tk.Frame(root, bg=BDR, padx=1, pady=1)
        border.pack(fill="both", expand=True)
        main = tk.Frame(border, bg=BG)
        main.pack(fill="both", expand=True)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(main, bg=BG2, padx=14, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="GESTURE", font=("Segoe UI",14,"bold"), bg=BG2, fg=TXT).pack(side="left")
        tk.Label(hdr, text="OS",      font=("Segoe UI",14,"bold"), bg=BG2, fg=ACC).pack(side="left")
        close_btn = tk.Label(hdr, text="✕", font=("Segoe UI",13), bg=BG2, fg=MUT, cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self._do_toggle())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg=DNG))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg=MUT))

        # ── Status bar ────────────────────────────────────────────────────────
        sf = tk.Frame(main, bg=BG3, padx=14, pady=7)
        sf.pack(fill="x")
        self._sdot = tk.Label(sf, text="●", font=("Segoe UI",10), bg=BG3, fg=DNG)
        self._sdot.pack(side="left")
        self._slbl = tk.Label(sf, text="Not detected", font=("Segoe UI",10), bg=BG3, fg=MUT)
        self._slbl.pack(side="left", padx=(5,0))
        tk.Label(sf, text="App:", font=("Segoe UI",10), bg=BG3, fg=MUT).pack(side="right")
        self._ctxlbl = tk.Label(sf, text="—", font=("Segoe UI",10,"bold"), bg=BG3, fg=AC2)
        self._ctxlbl.pack(side="right", padx=(0,4))

        # ── Tabs: Chat | Gestures ─────────────────────────────────────────────
        tab_bar = tk.Frame(main, bg=BG2)
        tab_bar.pack(fill="x")

        self._tab_content = tk.Frame(main, bg=BG)
        self._tab_content.pack(fill="both", expand=True)

        self._chat_frame_outer  = self._build_chat_tab()
        self._gesture_frame_outer = self._build_gesture_tab()

        self._chat_tab_btn = tk.Label(tab_bar, text="AI Chat",
            font=("Segoe UI",10,"bold"), bg=BG3, fg=ACC,
            padx=18, pady=7, cursor="hand2")
        self._gesture_tab_btn = tk.Label(tab_bar, text="Gestures",
            font=("Segoe UI",10), bg=BG2, fg=MUT,
            padx=18, pady=7, cursor="hand2")
        self._chat_tab_btn.pack(side="left")
        self._gesture_tab_btn.pack(side="left")

        self._chat_tab_btn.bind("<Button-1>",    lambda e: self._show_tab("chat"))
        self._gesture_tab_btn.bind("<Button-1>", lambda e: self._show_tab("gestures"))

        self._show_tab("chat")

        # ── Input row (always visible at bottom) ──────────────────────────────
        inp = tk.Frame(main, bg=BG, padx=14, pady=8)
        inp.pack(fill="x", side="bottom")
        self._inp_var = tk.StringVar()
        entry = tk.Entry(inp, textvariable=self._inp_var, bg=BG3, fg=TXT,
                         insertbackground=ACC, relief="flat",
                         font=("Segoe UI",11),
                         highlightbackground=BDR, highlightthickness=1)
        entry.pack(side="left", fill="x", expand=True, ipady=6)
        entry.bind("<Return>", self._on_send)
        send = tk.Label(inp, text="→", font=("Segoe UI",14),
                        bg=BG3, fg=ACC, padx=10, cursor="hand2")
        send.pack(side="left", padx=(4,0))
        send.bind("<Button-1>", self._on_send)

        tk.Frame(main, bg=BDR, height=1).pack(fill="x", side="bottom")

    def _build_chat_tab(self):
        outer = tk.Frame(self._tab_content, bg=BG)

        info = tk.Label(outer, text="🎙️  Speak or type a command",
                        font=("Segoe UI",9), bg=BG, fg=MUT)
        info.pack(anchor="w", padx=14, pady=(8,4))

        canvas_outer = tk.Frame(outer, bg=BG2, padx=1, pady=1)
        canvas_outer.pack(fill="both", expand=True, padx=14, pady=(0,4))

        canvas = tk.Canvas(canvas_outer, bg=BG2, highlightthickness=0)
        vsb    = tk.Scrollbar(canvas_outer, orient="vertical", command=canvas.yview)
        self._chat_inner = tk.Frame(canvas, bg=BG2)
        self._chat_inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=self._chat_inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._chat_canvas = canvas

        return outer

    def _build_gesture_tab(self):
        outer = tk.Frame(self._tab_content, bg=BG)

        # Toggle preview button
        toggle_row = tk.Frame(outer, bg=BG, padx=14, pady=6)
        toggle_row.pack(fill="x")
        tk.Label(toggle_row, text="Hand Diagrams", font=("Segoe UI",9,"bold"),
                 bg=BG, fg=MUT).pack(side="left")
        self._preview_toggle = tk.Label(toggle_row, text="Hide",
            font=("Segoe UI",9), bg=BG3, fg=ACC, padx=8, pady=2, cursor="hand2")
        self._preview_toggle.pack(side="right")
        self._preview_toggle.bind("<Button-1>", self._toggle_preview)

        # Scrollable gesture list
        scroll_outer = tk.Frame(outer, bg=BG)
        scroll_outer.pack(fill="both", expand=True)

        canvas  = tk.Canvas(scroll_outer, bg=BG, highlightthickness=0)
        vsb     = tk.Scrollbar(scroll_outer, orient="vertical", command=canvas.yview)
        self._gesture_list_frame = tk.Frame(canvas, bg=BG)
        self._gesture_list_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=self._gesture_list_frame, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120),"units"))

        self._gesture_canvas = canvas
        self._gesture_cards  = {}
        self._build_gesture_cards()

        return outer

    def _build_gesture_cards(self):
        for w in self._gesture_list_frame.winfo_children():
            w.destroy()
        self._gesture_cards = {}

        for g in GESTURES:
            card = tk.Frame(self._gesture_list_frame, bg=BG2,
                            highlightbackground=BDR, highlightthickness=1)
            card.pack(fill="x", padx=10, pady=4)

            # Left: emoji + text
            left = tk.Frame(card, bg=BG2, padx=10, pady=8)
            left.pack(side="left", fill="y")

            tk.Label(left, text=g["emoji"], font=("Segoe UI",16),
                     bg=BG2).pack(anchor="w")
            tk.Label(left, text=g["label"], font=("Segoe UI",11,"bold"),
                     bg=BG2, fg=g["color"]).pack(anchor="w")
            tk.Label(left, text=g["desc"],  font=("Segoe UI",9),
                     bg=BG2, fg=MUT, justify="left").pack(anchor="w")

            # Right: SVG hand diagram (rendered as canvas drawing)
            if self._show_preview:
                right = tk.Frame(card, bg=BG2, padx=6, pady=6)
                right.pack(side="right")
                self._draw_hand_canvas(right,
                    g["thumb"], g["index"], g["middle"], g["ring"], g["pinky"],
                    g["color"])

            self._gesture_cards[g["token"]] = card

    def _draw_hand_canvas(self, parent, thumb, index, middle, ring, pinky, color):
        """Draw hand diagram on a tkinter Canvas (no SVG renderer needed)."""
        c  = tk.Canvas(parent, width=60, height=76, bg=BG2,
                       highlightthickness=0)
        c.pack()

        dim = "#1e3040"

        # Palm
        c.create_rectangle(18, 46, 42, 68, fill="#142030", outline="")
        c.create_oval(18, 58, 42, 72, fill="#142030", outline="")

        # Fingers: (base_x, base_y, tip_x_open, tip_y_open, tip_x_closed, tip_y_closed)
        fdata = [
            (24, 46, 20, 10, 23, 38),   # index
            (29, 44, 28,  5, 28, 36),   # middle
            (34, 45, 37, 10, 33, 38),   # ring
            (38, 48, 44, 18, 38, 40),   # pinky
        ]
        states = [index, middle, ring, pinky]
        for (bx,by,tx,ty,cx,cy), state in zip(fdata, states):
            col = color if state else dim
            ex, ey = (tx,ty) if state else (cx,cy)
            c.create_line(bx,by,ex,ey, fill=col, width=4, capstyle="round")
            if state:
                c.create_oval(ex-3,ey-3,ex+3,ey+3, fill=col, outline="")

        # Thumb
        tcol = color if thumb else dim
        if thumb:
            c.create_line(19,52, 9,42, fill=tcol, width=4, capstyle="round")
            c.create_oval(6,39,12,45, fill=tcol, outline="")
        else:
            c.create_line(19,52, 14,46, fill=tcol, width=4, capstyle="round")

    def _highlight_gesture(self, gesture):
        """Flash the matching gesture card green when detected."""
        for token, card in self._gesture_cards.items():
            if token == gesture:
                card.configure(highlightbackground=ACC, highlightthickness=2)
                self._root.after(800, lambda c=card: c.configure(
                    highlightbackground=BDR, highlightthickness=1))

    def _toggle_preview(self, _=None):
        self._show_preview = not self._show_preview
        self._preview_toggle.config(text="Hide" if self._show_preview else "Show")
        self._build_gesture_cards()
        self._gesture_canvas.configure(scrollregion=self._gesture_canvas.bbox("all"))

    # ── tab switching ─────────────────────────────────────────────────────────

    def _show_tab(self, tab):
        self._chat_frame_outer.pack_forget()
        self._gesture_frame_outer.pack_forget()
        if tab == "chat":
            self._chat_frame_outer.pack(fill="both", expand=True)
            self._chat_tab_btn.config(bg=BG3, fg=ACC, font=("Segoe UI",10,"bold"))
            self._gesture_tab_btn.config(bg=BG2, fg=MUT, font=("Segoe UI",10))
        else:
            self._gesture_frame_outer.pack(fill="both", expand=True)
            self._gesture_tab_btn.config(bg=BG3, fg=ACC, font=("Segoe UI",10,"bold"))
            self._chat_tab_btn.config(bg=BG2, fg=MUT, font=("Segoe UI",10))

    # ── status bar refresh ────────────────────────────────────────────────────

    def _refresh_status_bar(self):
        colors = {"active":ACC,"idle":WARN,"lost":DNG}
        labels = {"active":"Tracking active","idle":"Idle / sleeping","lost":"Hand not detected"}
        c = colors.get(self._status, DNG)
        self._sdot.config(fg=c)
        self._slbl.config(text=labels.get(self._status,"Unknown"))
        self._ctxlbl.config(text=self._context)

    # ── chat refresh ──────────────────────────────────────────────────────────

    def _refresh_chat(self):
        for w in self._chat_inner.winfo_children():
            w.destroy()
        for role, text in self._chat_lines[-24:]:
            if role == "user":
                b = tk.Frame(self._chat_inner, bg=BG3, padx=10, pady=6)
                b.pack(fill="x", pady=(4,0), padx=6)
                tk.Label(b, text="You", font=("Segoe UI",8,"bold"),
                         bg=BG3, fg=AC2).pack(anchor="w")
                tk.Label(b, text=text, font=("Segoe UI",10),
                         bg=BG3, fg=TXT, wraplength=self.cfg.SIDEBAR_WIDTH-50,
                         anchor="w", justify="left").pack(anchor="w")
            else:
                b = tk.Frame(self._chat_inner, bg=BG, padx=10, pady=6)
                b.pack(fill="x", pady=(2,4), padx=6)
                tk.Label(b, text="AI", font=("Segoe UI",8,"bold"),
                         bg=BG, fg=ACC).pack(anchor="w")
                tk.Label(b, text=text, font=("Segoe UI",10),
                         bg=BG, fg=TXT, wraplength=self.cfg.SIDEBAR_WIDTH-50,
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
        steps  = 12
        cur_x  = self._root.winfo_x()
        step_dx= (target_x - cur_x) / steps
        def _step(n=0):
            if n >= steps:
                self._root.geometry(f"+{target_x}+4")
                self._anim_running = False
                return
            nx = int(cur_x + step_dx*(n+1))
            self._root.geometry(f"+{nx}+4")
            self._root.after(self.cfg.SIDEBAR_SLIDE_MS//steps, _step, n+1)
        _step()

    def _on_send(self, _=None):
        text = self._inp_var.get().strip()
        if not text:
            return
        self._inp_var.set("")
        if self.on_voice_command:
            threading.Thread(target=self.on_voice_command, args=(text,), daemon=True).start()
