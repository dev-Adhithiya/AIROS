"""
main.py — GestureOS entry point.

Architecture:
  • Pipeline runs in a background thread (camera → gesture → Win32 mouse/keyboard)
  • HUD runs in main thread (tiny tkinter corner indicator)
  • Sidebar runs in a second tkinter thread (slide-in panel)
  • Tray runs in a third thread (pystray)

Usage:
    python main.py
    python main.py --demo       # no real mouse/keyboard output
    python main.py --no-voice   # disable microphone
    python main.py --debug      # show camera feed window + FPS
    python main.py --camera 1   # use camera index 1
"""
import sys
import os
import argparse
import threading
import logging

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("gestureos.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("GestureOS.main")


def parse_args():
    p = argparse.ArgumentParser(description="GestureOS NUI")
    p.add_argument("--demo",        action="store_true")
    p.add_argument("--no-voice",    action="store_true")
    p.add_argument("--debug",       action="store_true")
    p.add_argument("--camera",      type=int,   default=0)
    p.add_argument("--sensitivity", type=float, default=1.2)
    p.add_argument("--corner",      default="bottom-right",
                   choices=["top-left","top-right","bottom-left","bottom-right"])
    return p.parse_args()


def main():
    args = parse_args()

    from config.settings import Settings
    cfg = Settings()
    cfg.CAMERA_ID     = args.camera
    cfg.SENSITIVITY   = args.sensitivity
    cfg.DEMO_MODE     = args.demo
    cfg.VOICE_ENABLED = not args.no_voice
    cfg.DEBUG         = args.debug
    cfg.HUD_CORNER    = args.corner

    from core.pipeline import Pipeline
    from ui.hud        import HUD
    from ui.sidebar    import Sidebar
    from ui.tray       import TrayIcon

    # ── create pipeline (no camera yet — camera starts in run()) ──────────────
    pipeline: Pipeline = None

    # ── sidebar ───────────────────────────────────────────────────────────────
    sidebar = Sidebar(cfg, on_voice_command=lambda text: (
        pipeline.voice._handle(text) if pipeline and pipeline.voice else None
    ))

    # ── HUD ───────────────────────────────────────────────────────────────────
    hud = HUD(cfg, on_toggle_sidebar=sidebar.toggle)

    # ── pipeline callbacks ────────────────────────────────────────────────────
    def on_status(s):
        hud.update_status(s)
        sidebar.update_status(s)
        if tray:
            tray.set_status(s)

    def on_gesture(g, ctx):
        hud.update_gesture(g, ctx)
        sidebar.update_status(sidebar._status, g)

    def on_chat(u, r):
        sidebar.add_chat(u, r)

    def on_context(ctx):
        sidebar.update_context(ctx)

    # ── tray ──────────────────────────────────────────────────────────────────
    _pipeline_thread = None

    def start_pipeline():
        nonlocal pipeline, _pipeline_thread
        if pipeline:
            return
        pipeline = Pipeline(
            cfg,
            on_status=on_status,
            on_gesture=on_gesture,
            on_chat=on_chat,
            on_context=on_context,
        )
        _pipeline_thread = threading.Thread(
            target=pipeline.run, daemon=True, name="Pipeline"
        )
        _pipeline_thread.start()
        logger.info("Pipeline started.")

    def stop_pipeline():
        nonlocal pipeline
        if pipeline:
            pipeline.stop()
            pipeline = None
        logger.info("Pipeline stopped.")

    def quit_all():
        stop_pipeline()
        hud.close()
        sidebar.close()
        logger.info("GestureOS quit.")
        os._exit(0)

    tray = TrayIcon(
        on_start          = start_pipeline,
        on_stop           = stop_pipeline,
        on_toggle_sidebar = sidebar.toggle,
        on_quit           = quit_all,
    )

    # ── start tray + sidebar in background threads ────────────────────────────
    threading.Thread(target=tray.run,    daemon=True, name="Tray").start()
    threading.Thread(target=sidebar.run, daemon=True, name="Sidebar").start()

    # Auto-start pipeline immediately
    start_pipeline()

    logger.info("GestureOS running.  Right-click tray icon to stop/quit.")
    logger.info("HUD pinned to %s — click ☰ to toggle sidebar.", cfg.HUD_CORNER)

    # HUD runs in the main thread (tkinter requirement)
    hud.run()


if __name__ == "__main__":
    main()
