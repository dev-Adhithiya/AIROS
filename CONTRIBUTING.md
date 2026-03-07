# Contributing to GestureOS

Thanks for your interest in contributing!

## Getting Started

1. Fork the repo
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/gestureos.git
   cd gestureos
   ```
3. Create a virtual environment:
   ```bash
   python -m venv myenv
   myenv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```
4. Create a branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Project Structure

```
gestureos/
├── core/           # Camera, hand tracking, cursor, pipeline
├── gestures/       # Gesture recognition engine
├── ui/             # HUD, sidebar, system tray
├── ai/             # Voice assistant
├── config/         # Settings
└── assets/         # Model files (auto-downloaded, not committed)
```

## Adding a New Gesture

1. Open `gestures/engine.py`
2. Add detection logic in `recognize()` — use landmark geometry
3. Add the token to `DEFAULT_MAP` in `core/action_mapper.py`
4. Add it to the reference card in `ui/sidebar.py`

## Adding a New Context Rule

Open `core/action_mapper.py` → `CONTEXT_MAP` dict.
Key = substring of process name (lowercase), value = `{gesture: action}`.

## Adding a Voice Command

Open `ai/voice_assistant.py`:
- Built-in app launch → add to `_LAUNCH` dict
- System shortcut → add to `_CMDS` dict

## Pull Request Guidelines

- One feature / fix per PR
- Test on Windows with a real webcam
- Keep `config/settings.py` backward compatible
- Don't commit `.env`, `assets/*.task`, or log files
