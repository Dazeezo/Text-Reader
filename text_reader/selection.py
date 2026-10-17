import ctypes
import time

import keyboard
import win32clipboard
import win32con


def _open_clipboard(retries=10, delay=0.015):
    # Clipboard history / managers open the clipboard right after every
    # change, so a single OpenClipboard() attempt often fails transiently.
    for _ in range(retries):
        try:
            win32clipboard.OpenClipboard()
            return True
        except Exception:
            time.sleep(delay)
    return False


def _get_clipboard_text():
    if not _open_clipboard():
        return None
    try:
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        return None
    except Exception:
        return None
    finally:
        win32clipboard.CloseClipboard()


def _set_clipboard_text(text):
    if not _open_clipboard():
        return
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    except Exception:
        pass
    finally:
        win32clipboard.CloseClipboard()


def get_selected_text(timeout=0.5, poll_interval=0.02):
    """Copies the current selection and returns it, restoring the user's
    previous *text* clipboard afterwards. Returns None if nothing appears to
    be selected (clipboard did not change after Ctrl+C).

    Only text is restored: if the clipboard held an image or files, Ctrl+C has
    already replaced it, and we leave the copied text there rather than
    emptying the clipboard."""
    old_text = _get_clipboard_text()
    old_seq = ctypes.windll.user32.GetClipboardSequenceNumber()

    # This runs from a global hotkey callback, often while the user is still
    # physically holding that hotkey's keys down. If e.g. Alt is still held
    # when we send Ctrl+C, the target app sees Ctrl+Alt+C, which most apps
    # don't treat as Copy. Force a clean modifier state first.
    for key in ("alt", "shift", "windows", "ctrl"):
        keyboard.release(key)
    time.sleep(0.05)

    keyboard.send("ctrl+c")

    deadline = time.time() + timeout
    new_seq = old_seq
    while time.time() < deadline:
        new_seq = ctypes.windll.user32.GetClipboardSequenceNumber()
        if new_seq != old_seq:
            break
        time.sleep(poll_interval)

    if new_seq == old_seq:
        return None

    selected = None
    for _ in range(10):
        time.sleep(0.03)
        selected = _get_clipboard_text()
        if selected:
            break

    if old_text is not None:
        _set_clipboard_text(old_text)

    return selected
