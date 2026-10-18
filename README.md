# Text Reader

Highlight-to-read for Windows: select text in any app, press a hotkey, hear it read aloud.

## Setup

Double-click **`Install.bat`** — it creates a `venv` folder and installs everything
from `requirements.txt` into it. Re-running it later just reuses the existing venv and
updates packages, so it's safe to run again after a `git pull`.

Prefer the command line, or setting up manually?

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

On launch you get a settings window plus a tray icon. Only one copy of the app can run
at a time — launching it again just brings the existing window to the front.

## Launch

Double-click **`TextReader.bat`** to start the app (no console window, uses the venv
above). For development, or to see errors, run `python run.py` from an activated venv
instead.

## Usage

- **Ctrl+Alt+Space** — read the current text selection
- **Ctrl+Alt+Backspace** — stop reading
- Both hotkeys can be changed from the settings window: click **Record** next to a
  hotkey, then press the new combo. It's saved immediately.
- The settings window also has Voice, Speed, and manual Read Selection / Pause-Resume /
  Stop buttons.
- **Minimize to Tray** (or the window's minimize button) hides the window to the system
  tray. Left-click the tray icon to bring it back.
- The **X** button fully exits the app (stops the engine, unhooks the hotkeys, removes
  the tray icon). Minimizing does not exit it — use X or the tray's Exit for that.
- The window's Read Selection button and the tray menu's Read Selection act on the last app
  you were using: the app hands focus back to it, copies your highlighted text, then speaks
  it. The hotkey is still the fastest path.
- The tray's right-click menu still has Read Selection, Pause/Resume, Stop, Voice, and
  Speed, in addition to the settings window.

Voice, speed, and hotkey choices are remembered between runs
(`%APPDATA%\TextReader\config.json`).

## How it works

There's no universal "get selected text" API across Windows apps, so the app uses the same
trick most screen readers use: pressing the hotkey simulates `Ctrl+C`, reads the clipboard,
restores your previous clipboard contents, and sends the text to the Windows SAPI speech
engine (the same one behind Narrator). Voice quality/available voices come from whatever
SAPI voices are installed on your PC — Settings > Time & Language > Speech lets you add more.

## Getting better voices

By default Windows only ships two robotic "Desktop" voices (David, Zira). For much more
natural-sounding, free, on-device voices — the closest local equivalent to the quality
of Claude's own read-aloud:

1. Open Settings > Time & Language > Speech > Manage voices > Add voices (on some
   builds: Settings > Accessibility > Narrator > Natural voices).
2. Download any of the "Natural" voices — e.g. Microsoft Aria, Guy, Ava, Andrew, Jenny.
   No account or payment needed.
3. Restart Text Reader. The new voice appears automatically in the tray's **Voice**
   submenu — no update needed.

The app reads voices from Windows' OneCore voice category (the same one Narrator uses),
so it also picks up voices like "Mark" that are already installed but hidden from the
older legacy voice list. You may see the same-sounding voice listed more than once
(a legacy "Desktop" version and a OneCore version) — that's expected, just pick whichever
sounds best.

## Notes / limitations

- Only works on real selectable text, not text inside images or scanned PDFs.
- If the frontmost app is running elevated (as Administrator) and this app isn't, the hotkey
  won't reach it — run `python run.py` as Administrator too in that case.
- To run without a console window, use `pythonw run.py` instead of `python run.py`.
- If the tray icon doesn't appear (window still works fine otherwise), Windows'
  notification area has occasionally gotten stuck during heavy testing/dev cycles on this
  machine. Signing out and back in (or rebooting) clears it; the window itself is
  unaffected either way.

## Packaging as a standalone .exe (optional)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name TextReader run.py
```

The executable will be in `dist/TextReader.exe`.
