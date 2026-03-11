<div align="center">

# 🖐️ GestureOS

**Control your entire Windows computer with hand gestures — no extra hardware.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.x-orange?logo=google)](https://mediapipe.dev)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.8%2B-green?logo=opencv)](https://opencv.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-lightblue?logo=windows)](https://microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

*A Natural User Interface (NUI) — your hand IS the mouse.*

</div>

---

## How It Works

```
Webcam  →  MediaPipe Landmarks  →  Gesture Engine  →  Win32 SendInput  →  OS
```

GestureOS runs silently in the background and translates hand gestures into real
mouse movements, clicks, scrolls, hotkeys, and voice commands — system-wide,
in any application.

**No extra hardware. Just your laptop webcam.**

---

## Features

- 🖱️ **Full mouse control** — move, left/right click, double-click, drag, scroll
- 👋 **10 built-in gestures** — all mapped to real OS actions
- 🧠 **Context-aware** — swipe behaves differently in Chrome vs PowerPoint vs Spotify
- 🎙️ **Voice commands** — 25+ built-in commands, Gemini fallback for anything else
- 💤 **Smart idle** — auto-sleeps when hand leaves frame, wakes on open palm
- ⚡ **Low latency** — Win32 `SendInput` directly, EMA cursor smoothing
- 🪟 **Minimal UI** — tiny corner HUD + slide-in sidebar, no taskbar clutter
- 📦 **Single `.exe`** — build with PyInstaller for one-click launch

---

## Gesture Reference

| Hand Shape | Gesture | Action |
|:---:|---|---|
| ☝️ | Index finger up | **Move cursor** |
| 👌 | Thumb meets index tip | **Left click** |
| 👌👌 | Two quick pinches | **Double click** |
| 🤏 | Thumb meets middle tip | **Right click** |
| ✌️↕ | Two fingers up + vertical motion | **Scroll up / down** |
| 👋→ | Open hand, fast rightward motion | **Swipe right** |
| 👋← | Open hand, fast leftward motion | **Swipe left** |
| ✊ | All fingers closed | **Start drag** |
| 🖐️ | All five fingers extended | **Release drag / wake** |
| 🤏 | Thumb + index only, close together | **Pinch** |

---

## Context-Aware Gestures

Gestures adapt automatically to the active app:

| App | Swipe Right | Swipe Left | Open Palm |
|-----|-------------|------------|-----------|
| Chrome / Edge / Firefox | Forward | Back | Focus URL bar |
| PowerPoint | Next slide | Previous slide | Start slideshow |
| VS Code | Next tab | Previous tab | Command palette |
| Spotify | Next track | Previous track | Play / pause |
| VLC | Seek forward | Seek back | Play / pause |
| Teams | — | — | Mute toggle |

---

## Quick Start

### 1. Clone
```bash
git clone https://github.com/YOUR_USERNAME/gestureos.git
cd gestureos
```

### 2. Create virtual environment
```bash
python -m venv myenv
myenv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

> **Voice support** (microphone) requires PyAudio:
> ```bash
> pip install pipwin
> pipwin install pyaudio
> ```

### 4. Run
```bash
python main.py
```

On first run, the MediaPipe hand model (~8 MB) downloads automatically into `assets/`.

---

## Usage

```bash
python main.py                    # Normal run
python main.py --demo             # No real mouse output (safe testing)
python main.py --no-voice         # Disable microphone
python main.py --debug            # Show camera feed + FPS overlay
python main.py --camera 1         # Use second camera
python main.py --sensitivity 1.5  # Faster cursor
python main.py --corner top-left  # HUD position
```

---

## Voice Commands

Say these out loud — recognised automatically via microphone:

**Launch apps:** `"Open Chrome"` · `"Open Spotify"` · `"Open VS Code"` · `"Open Terminal"`

**System:** `"Take a screenshot"` · `"Volume up/down"` · `"Mute"` · `"Lock screen"`

**Window:** `"Close window"` · `"Minimize"` · `"Maximize"` · `"Show desktop"`

**Editing:** `"Copy"` · `"Paste"` · `"Undo"` · `"Save"` · `"Select all"`

**AI chat:** anything else → sent to Gemini AI (requires API key)

---

## AI Assistant Setup (Optional)

Set your Gemini API key:

```bash
# Option 1: environment variable (recommended)
set GEMINI_API_KEY=AIza...

# Option 2: edit config/settings.py
GEMINI_API_KEY = "AIza..."
```

---

## Build Standalone .exe

```bash
pip install pyinstaller
python build.py
# → dist/GestureOS.exe
```

---

## Configuration

All settings in `config/settings.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `SENSITIVITY` | `1.2` | Cursor speed multiplier |
| `SMOOTHING` | `0.28` | Jitter reduction (lower = smoother) |
| `CLICK_DIST_PX` | `36` | Thumb–index distance to trigger click |
| `SCROLL_SPEED` | `10` | Scroll lines per gesture tick |
| `IDLE_TIMEOUT` | `2.5` | Seconds before sleep mode |
| `HUD_CORNER` | `bottom-right` | HUD position on screen |
| `DEMO_MODE` | `False` | Disable real mouse output |

---

## Project Structure

```
gestureos/
├── main.py                   # Entry point
├── build.py                  # PyInstaller .exe builder
├── requirements.txt
├── config/
│   └── settings.py           # All tunable parameters
├── core/
│   ├── camera.py             # Threaded webcam (zero buffer lag)
│   ├── hand_tracker.py       # MediaPipe 0.10 Tasks API wrapper
│   ├── cursor.py             # Win32 SendInput mouse control
│   ├── executor.py           # Executes action dicts
│   ├── action_mapper.py      # Gesture → action + context rules
│   ├── idle_manager.py       # Sleep/wake on hand presence
│   └── pipeline.py           # Main processing loop
├── gestures/
│   └── engine.py             # Geometric gesture recognition
├── ui/
│   ├── hud.py                # Corner indicator (always-on-top)
│   ├── sidebar.py            # Slide-in panel (context + AI chat)
│   └── tray.py               # System tray icon
├── ai/
│   └── voice_assistant.py    # Speech recognition + Gemini
└── assets/
    └── hand_landmarker.task  # Auto-downloaded on first run
```

---

## Requirements

- **OS:** Windows 10 / 11
- **Python:** 3.10+
- **Camera:** Standard webcam (720p+)
- **GPU:** Not required
- **CPU:** ~20–25% active, <5% idle (modern laptop)

---

## Roadmap

- [ ] Multi-hand gestures
- [ ] Custom gesture training
- [ ] Gesture-based virtual keyboard
- [ ] macOS / Linux support
- [ ] Plugin system for third-party gesture packs

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.
