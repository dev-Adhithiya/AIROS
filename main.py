"""main.py — AIROS entry point."""
import sys, os, argparse, threading, logging

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("airos.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("AIROS.main")


def parse_args():
    p = argparse.ArgumentParser(description="AIROS NUI")
    p.add_argument("--demo",        action="store_true")
    p.add_argument("--no-voice",    action="store_true")
    p.add_argument("--debug",       action="store_true")
    p.add_argument("--camera",      type=int, default=0)
    p.add_argument("--sensitivity", type=float, default=1.2)
    p.add_argument("--corner",      default="bottom-right",
                   choices=["top-left","top-right","bottom-left","bottom-right"])
    p.add_argument("--no-preview",  action="store_true")
    return p.parse_args()


def main():
    args = parse_args()

    from config.settings  import Settings
    cfg = Settings()
    cfg.CAMERA_ID     = args.camera
    cfg.SENSITIVITY   = args.sensitivity
    cfg.DEMO_MODE     = args.demo
    cfg.VOICE_ENABLED = not args.no_voice
    cfg.DEBUG         = args.debug
    cfg.HUD_CORNER    = args.corner
    cfg.NO_PREVIEW    = args.no_preview

    from ui.hud           import HUD
    from ui.sidebar       import Sidebar
    from ui.tray          import TrayIcon
    from ui.camera_window import CameraWindow

    pipeline = None
    cam_win  = CameraWindow(cfg)

    # Start with preview visible unless --no-preview
    cam_win.visible = not args.no_preview

    sidebar = Sidebar(cfg, on_voice_command=lambda text: (
        pipeline.voice._handle(text) if pipeline and pipeline.voice else None
    ))

    hud = HUD(cfg, on_toggle_sidebar=sidebar.toggle)

    # ── wire 📷 button in HUD to toggle cam_win.visible ───────────────────────
    def toggle_preview():
        cam_win.visible = not cam_win.visible
        state = "shown" if cam_win.visible else "hidden"
        logger.info(f"Camera preview {state}")

    hud.set_cam_toggle(toggle_preview)

    # ── callbacks ─────────────────────────────────────────────────────────────
    def on_status(s):
        hud.update_status(s)
        sidebar.update_status(s)

    def on_gesture(g, ctx):
        hud.update_gesture(g, ctx)

    def on_chat(u, r):   sidebar.add_chat(u, r)
    def on_context(ctx): sidebar.update_context(ctx)

    _pipe_thread = None

    def start_pipeline():
        nonlocal pipeline, _pipe_thread
        if pipeline:
            return
        from core.pipeline import Pipeline
        pipeline = Pipeline(
            cfg,
            on_status=on_status, on_gesture=on_gesture,
            on_chat=on_chat,     on_context=on_context,
            camera_window=cam_win,
        )
        _pipe_thread = threading.Thread(target=pipeline.run,
                                        daemon=True, name="Pipeline")
        _pipe_thread.start()
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
        logger.info("AIROS quit.")
        os._exit(0)

    tray = TrayIcon(
        on_start=start_pipeline, on_stop=stop_pipeline,
        on_toggle_sidebar=sidebar.toggle, on_quit=quit_all,
        on_toggle_preview=toggle_preview,
    )

    threading.Thread(target=tray.run,    daemon=True, name="Tray").start()
    threading.Thread(target=sidebar.run, daemon=True, name="Sidebar").start()

    start_pipeline()

    logger.info("AIROS running.")
    logger.info("  Camera preview: H/Q/X = hide  |  click 📷 in HUD to reopen")

    hud.run()   # blocks — tkinter must be on main thread


if __name__ == "__main__":
    main()
