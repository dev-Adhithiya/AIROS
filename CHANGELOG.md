# Changelog

All notable changes to GestureOS will be documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Planned
- Multi-hand gesture support
- Custom gesture training UI
- Gesture-based virtual keyboard
- Plugin/extension system

---

## [1.0.0] — 2026-03-07

### Added
- Real-time hand tracking via MediaPipe 0.10.x Tasks API
- 10 built-in gestures: move, click, double-click, right-click, scroll, swipe, grab, drag, pinch, open palm
- Win32 `SendInput` cursor control for lowest possible latency
- EMA cursor smoothing with configurable sensitivity
- Context-aware gesture mapping (Chrome, Firefox, Edge, VS Code, PowerPoint, Spotify, VLC, Teams)
- Idle/sleep detection — auto-suspends after configurable timeout
- Compact slide-in sidebar (context display + AI chat)
- Corner HUD indicator (always-on-top status dot)
- System tray icon with Start / Stop / Quit
- Voice assistant with 25+ built-in commands (no internet required)
- OpenAI GPT fallback for natural language commands
- Auto-download of MediaPipe hand landmarker model on first run
- `--demo` mode for testing without real mouse control
- `--debug` flag for camera feed + FPS overlay
- PyInstaller `build.py` for single `.exe` packaging
