"""
build.py — Packages GestureOS into a single Windows .exe using PyInstaller.

Usage:
    pip install pyinstaller
    python build.py

Output: dist/GestureOS.exe  (single file, ~120-180 MB)
"""
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",                        # single .exe
    "--windowed",                       # no console window
    "--name", "GestureOS",
    "--icon", os.path.join(HERE, "assets", "icon.ico") if os.path.exists(
        os.path.join(HERE, "assets", "icon.ico")) else "NONE",
    "--add-data", f"{HERE}/config;config",
    "--add-data", f"{HERE}/core;core",
    "--add-data", f"{HERE}/gestures;gestures",
    "--add-data", f"{HERE}/ui;ui",
    "--add-data", f"{HERE}/ai;ai",
    "--hidden-import", "mediapipe",
    "--hidden-import", "cv2",
    "--hidden-import", "pyautogui",
    "--hidden-import", "pystray",
    "--hidden-import", "PIL",
    "--hidden-import", "speech_recognition",
    "--hidden-import", "win32gui",
    "--hidden-import", "win32process",
    "--hidden-import", "psutil",
    "--collect-all", "mediapipe",
    "--collect-all", "cv2",
    os.path.join(HERE, "main.py"),
]

print("Building GestureOS.exe ...")
result = subprocess.run(cmd, cwd=HERE)
if result.returncode == 0:
    print("\n✅  Build successful!  →  dist/GestureOS.exe")
else:
    print("\n❌  Build failed. Check output above.")
    sys.exit(1)
