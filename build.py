"""
build.py — Packages GestureOS into a single Windows .exe using PyInstaller.

Usage:
    pip install pyinstaller
    python build.py

Output: dist/GestureOS.exe
"""
import subprocess, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))

# Find mediapipe package location to collect it fully
import mediapipe
mp_path = os.path.dirname(mediapipe.__file__)

import google.generativeai
genai_path = os.path.dirname(google.generativeai.__file__)
google_path = os.path.dirname(genai_path)  # the 'google' namespace folder

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",                           # no console window
    "--name", "GestureOS",
    "--icon", os.path.join(HERE, "assets", "icon.ico")
              if os.path.exists(os.path.join(HERE, "assets", "icon.ico"))
              else "NONE",

    # ── source packages ───────────────────────────────────────────────────────
    "--add-data", f"{HERE}/config{os.pathsep}config",
    "--add-data", f"{HERE}/core{os.pathsep}core",
    "--add-data", f"{HERE}/gestures{os.pathsep}gestures",
    "--add-data", f"{HERE}/ui{os.pathsep}ui",
    "--add-data", f"{HERE}/ai{os.pathsep}ai",
    "--add-data", f"{HERE}/assets{os.pathsep}assets",

    # ── mediapipe (needs full collect — contains .so/.pyd + model files) ──────
    "--collect-all", "mediapipe",

    # ── google-generativeai ───────────────────────────────────────────────────
    "--collect-all", "google.generativeai",
    "--collect-all", "google.ai",
    "--collect-all", "google.protobuf",

    # ── opencv ────────────────────────────────────────────────────────────────
    "--collect-all", "cv2",

    # ── hidden imports that PyInstaller misses ────────────────────────────────
    "--hidden-import", "mediapipe",
    "--hidden-import", "mediapipe.tasks",
    "--hidden-import", "mediapipe.tasks.python",
    "--hidden-import", "mediapipe.tasks.python.vision",
    "--hidden-import", "mediapipe.tasks.python.core",
    "--hidden-import", "mediapipe.python",
    "--hidden-import", "mediapipe.python._framework_bindings",
    "--hidden-import", "cv2",
    "--hidden-import", "numpy",
    "--hidden-import", "pyautogui",
    "--hidden-import", "pystray",
    "--hidden-import", "PIL",
    "--hidden-import", "PIL.Image",
    "--hidden-import", "PIL.ImageTk",
    "--hidden-import", "PIL.ImageDraw",
    "--hidden-import", "speech_recognition",
    "--hidden-import", "win32gui",
    "--hidden-import", "win32process",
    "--hidden-import", "win32api",
    "--hidden-import", "win32con",
    "--hidden-import", "psutil",
    "--hidden-import", "google.generativeai",
    "--hidden-import", "google.protobuf",
    "--hidden-import", "tkinter",
    "--hidden-import", "tkinter.ttk",
    "--hidden-import", "pyautogui",
    "--hidden-import", "pynput",

    os.path.join(HERE, "main.py"),
]

print("=" * 60)
print("Building GestureOS.exe ...")
print("This takes 5–10 minutes, please wait.")
print("=" * 60)

result = subprocess.run(cmd, cwd=HERE)

if result.returncode == 0:
    exe = os.path.join(HERE, "dist", "GestureOS.exe")
    print("\n" + "=" * 60)
    print(f"✅  Build successful!")
    print(f"    → {exe}")
    print("\nIMPORTANT: Copy your assets folder next to the exe:")
    print(f"    xcopy {HERE}\\assets {HERE}\\dist\\assets /E /I")
    print("=" * 60)
else:
    print("\n❌  Build failed. Check output above.")
    sys.exit(1)
