import os
import sys

import PyInstaller.__main__ as pyinstaller

os.chdir(os.path.dirname(os.path.abspath(__file__)))

DATA = (["PIRATE_ICON.ico", "PIRATE_ICON.png", "PIRATE_ICON_BLACK.ico", "PIRATE_ICON_BLACK.png",
         "PIRATE_ICON_WHITE.ico", "PIRATE_ICON_WHITE.png", "Sound Stop.wav"]
        + [f"Sound {i}.wav" for i in range(1, 10)])

missing = [f for f in ["PIRATE_TOKEN_BOT.py"] + DATA if not os.path.exists(f)]
if missing:
    print("ERROR: missing files:", ", ".join(missing))
    sys.exit(1)

args = ["PIRATE_TOKEN_BOT.py", "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", "PIRATE TOKEN BOT", "--icon", "PIRATE_ICON.ico",
        "--collect-all", "pyautogui", "--collect-all", "keyboard",
        "--hidden-import", "PIL._tkinter_finder"]
for f in DATA:
    args += ["--add-data", f + os.pathsep + "."]

pyinstaller.run(args)
