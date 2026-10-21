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

Windows' built-in voices (David, Mark, Zira) are the old, robotic kind. (Windows' newer
"Natural" voices only work inside Narrator and Edge, not in other apps, so they can't be
used here.) For much more natural speech, the app supports free, offline neural voices
from [Piper](https://github.com/OHF-Voice/piper1-gpl):

1. In the settings window, pick a voice under **Get more natural voices** (e.g. Lessac,
   Amy, Alan) and click **Download** (~60 MB each, one time, needs internet only for
   the download).
2. Choose it in the **Voice** dropdown (it appears as "Piper: ..."), or from the tray's
   Voice submenu.

Piper voices run entirely on your PC. Speed, pause/resume, and stop all work with them.
Voice files are stored in `%APPDATA%\TextReaderoices`.

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
