"""core/pipeline.py — Main processing loop. Pushes frames to camera window."""
import time, threading, logging, cv2
logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, cfg, on_status=None, on_gesture=None, on_chat=None,
                 on_context=None, camera_window=None):
        self.cfg          = cfg
        self._stop_ev     = threading.Event()
        self.voice        = None
        self._cam_win     = camera_window   # CameraWindow instance (optional)

        self._on_status  = on_status  or (lambda s: None)
        self._on_gesture = on_gesture or (lambda g, c: None)
        self._on_chat    = on_chat    or (lambda u, r: None)
        self._on_context = on_context or (lambda c: None)

        from core.camera        import CameraCapture
        from core.hand_tracker  import HandTracker
        from gestures.engine    import GestureEngine
        from core.action_mapper import ActionMapper
        from core.executor      import CommandExecutor
        from core.idle_manager  import IdleManager

        self.executor = CommandExecutor(cfg)
        self.tracker  = HandTracker(cfg)
        self.engine   = GestureEngine(cfg)
        self.mapper   = ActionMapper(cfg)
        self.idle     = IdleManager(cfg)
        self.camera   = CameraCapture(cfg)

        if cfg.VOICE_ENABLED:
            self._start_voice()

    def _start_voice(self):
        try:
            from ai.voice_assistant import VoiceAssistant
            self.voice = VoiceAssistant(
                self.cfg, self.executor,
                on_transcript=lambda u, r: self._on_chat(u, r),
            )
            threading.Thread(target=self.voice.listen_loop,
                             daemon=True, name="Voice").start()
            logger.info("Voice assistant started.")
        except Exception as e:
            logger.warning("Voice failed: %s", e)

    def run(self):
        self._stop_ev.clear()
        logger.info("Pipeline running.")
        prev_status = prev_ctx = None
        frame_times = []

        for frame in self.camera.frames():
            if self._stop_ev.is_set():
                break

            t0 = time.perf_counter()

            # ── hand tracking ─────────────────────────────────────────────────
            landmarks, present = self.tracker.process(frame)

            if present: self.idle.on_hand()
            else:       self.idle.on_no_hand()

            status = self.idle.status()
            if status != prev_status:
                self._on_status(status)
                prev_status = status

            # ── gesture + action ──────────────────────────────────────────────
            gesture = None
            if present and not self.idle.is_sleeping:
                gesture = self.engine.recognize(landmarks)
                action  = self.mapper.map(gesture, landmarks)
                if action:
                    self.executor.execute(action)

                ctx = self.mapper.get_context()
                if ctx != prev_ctx:
                    self._on_context(ctx)
                    prev_ctx = ctx

                if gesture and gesture not in ("cursor_move", "idle"):
                    self._on_gesture(gesture, ctx)

            # ── annotate frame ────────────────────────────────────────────────
            frame_times.append(time.perf_counter())
            frame_times = [t for t in frame_times if frame_times[-1] - t < 1.0]
            fps = len(frame_times)

            # Gesture label on frame
            if gesture and gesture not in ("cursor_move", "idle"):
                label = gesture.replace("_", " ").upper()
                h, w  = frame.shape[:2]
                cv2.rectangle(frame, (0, h-52), (w, h), (8,12,18), -1)
                cv2.rectangle(frame, (0, h-52), (4, h), (0,255,136), -1)
                cv2.putText(frame, label, (14, h-18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.92, (0,255,136), 2, cv2.LINE_AA)

            # Status bar on frame
            cv2.rectangle(frame, (0,0), (frame.shape[1], 36), (10,15,22), -1)
            scol  = {"active":(0,255,136),"idle":(0,204,255),"lost":(60,60,255)}.get(status,(60,60,255))
            slbl  = {"active":"● TRACKING","idle":"● IDLE","lost":"● NO HAND"}.get(status,"●")
            cv2.putText(frame, slbl, (12, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, scol, 2, cv2.LINE_AA)
            cv2.putText(frame, f"{fps} FPS", (frame.shape[1]-80, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.58, (80,120,100), 1, cv2.LINE_AA)

            # ── push to camera window ─────────────────────────────────────────
            if self._cam_win:
                self._cam_win.push_frame(frame, gesture, status)

            # ── optional debug cv2 window ─────────────────────────────────────
            if self.cfg.DEBUG:
                cv2.imshow("GestureOS debug", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            elapsed = time.perf_counter() - t0
            wait    = 1/self.cfg.TARGET_FPS - elapsed
            if wait > 0:
                time.sleep(wait)

        self.camera.release()
        self.tracker.close()
        if self.cfg.DEBUG:
            cv2.destroyAllWindows()
        logger.info("Pipeline stopped.")

    def stop(self):
        self._stop_ev.set()
        if self.voice:
            self.voice.stop()
