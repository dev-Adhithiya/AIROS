# AIROS — AI-Powered Hand Gesture OS Controller

Control your computer entirely with hand gestures detected through your webcam. No extra hardware needed.

## Features
- 🖱️ Full mouse control (move, click, right-click, double-click, scroll, drag)
- 🧠 Context-aware gestures (Chrome, PowerPoint, Spotify, VS Code, etc.)
- 🎙️ Voice commands + Gemini AI assistant
- ⚡ Under 30ms latency via Win32 SendInput
- 📷 Works with any webcam including low-res

## Quick Start

```bash
git clone https://github.com/dev-Adhithiya/AIROS.git
cd AIROS
python -m venv myenv
myenv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Requirements
- Windows 10 / 11
- Python 3.9 – 3.12
- Any webcam

## Usage
```bash
python main.py                 # normal run
python main.py --demo          # safe test mode (no real mouse)
python main.py --no-voice      # disable microphone
python main.py --camera 1      # use second webcam
python main.py --debug         # show FPS + debug logs
python main.py --no-preview    # hide camera preview window
```

## Gestures
| Gesture | Shape | Action |
|---------|-------|--------|
| Move Cursor | ☝️ Index finger only | Moves mouse cursor |
| Left Click | 👌 Thumb + index pinch | Left click |
| Double Click | 👌👌 Two quick pinches | Double click |
| Right Click | 🤙 Pinky only up | Right click |
| Scroll | ✌️ Index+middle, move up/down | Scroll page |
| Swipe | 👋 3+ fingers, fast horizontal | Navigate |
| Grab | ✊ All fingers closed | Drag |
| Open Palm | 🖐️ All 5 fingers spread | Release / Wake |

## Optional: Gemini AI Voice
Get a free key at https://aistudio.google.com/app/apikey then:
```bash
set GEMINI_API_KEY=YOUR_KEY_HERE
python main.py
```
Or edit `config/settings.py` and set `GEMINI_API_KEY = "your_key"`.

## Optional: Voice Support (pyaudio)
```bash
pip install pipwin
pipwin install pyaudio
```

## Building .exe
```bash
pip install pyinstaller
pyinstaller GestureOS.spec
xcopy assets dist\assets /E /I
# Output: dist\GestureOS.exe
```

## Project Structure
```
AIROS/
├── main.py                  # Entry point
├── requirements.txt
├── GestureOS.spec           # PyInstaller build config
├── config/
│   └── settings.py          # All tunable parameters
├── core/
│   ├── camera.py            # Webcam capture (threaded)
│   ├── hand_tracker.py      # MediaPipe Tasks API
│   ├── cursor.py            # Win32 cursor with EMA smoothing
│   ├── executor.py          # Dispatches mouse/keyboard actions
│   ├── action_mapper.py     # Maps gestures to actions per app
│   ├── idle_manager.py      # Sleep/wake on hand presence
│   └── pipeline.py          # Main processing loop
├── gestures/
│   └── engine.py            # Gesture recognition engine
├── ui/
│   ├── hud.py               # Corner status indicator
│   ├── sidebar.py           # Slide-in AI chat panel
│   ├── camera_window.py     # Live webcam preview
│   └── tray.py              # System tray icon
├── ai/
│   └── voice_assistant.py   # Gemini AI + voice commands
├── assets/                  # Hand model downloaded here on first run
└── website/
    └── index.html           # Landing page with live gesture demo
```

## Troubleshooting
| Error | Fix |
|-------|-----|
| `No module named 'mediapipe'` | Run `myenv\Scripts\activate` first |
| `No module named 'cv2'` | `pip install opencv-python` |
| Camera not found | Try `--camera 1` |
| Voice not working | `pipwin install pyaudio` |
| Python version error | Use Python 3.9–3.12 only |

## License
MIT — see LICENSE
