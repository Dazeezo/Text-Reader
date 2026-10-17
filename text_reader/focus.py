import ctypes
import os
import threading
import time

import win32api
import win32con
import win32gui
import win32process

POLL_INTERVAL = 0.1

SHELL_CLASSES = {
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    "NotifyIconOverflowWindow",
    "TopLevelWindowForOverflowXamlIsland",
    "XamlExplorerHostIslandWindow",
    "MultitaskingViewFrame",
    "#32768",
    "Windows.UI.Core.CoreWindow",
    "Progman",
    "WorkerW",
}


def _is_external_app_window(hwnd):
    """A real application window that isn't ours and isn't taskbar/Start/menu chrome."""
    try:
        if not hwnd or not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
            return False
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid == os.getpid():
            return False
        return win32gui.GetClassName(hwnd) not in SHELL_CLASSES
    except win32gui.error:
        return False


def _wait_for_foreground(hwnd, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if win32gui.GetForegroundWindow() == hwnd:
            return True
        time.sleep(0.02)
    return win32gui.GetForegroundWindow() == hwnd


def _bring_to_front(hwnd, timeout):
    try:
        win32gui.SetForegroundWindow(hwnd)
    except win32gui.error:
        pass
    if _wait_for_foreground(hwnd, timeout):
        return True

    # Windows' foreground lock refused the plain call; borrow the current
    # foreground thread's input queue for the duration of the switch.
    foreground = win32gui.GetForegroundWindow()
    foreground_tid = win32process.GetWindowThreadProcessId(foreground)[0] if foreground else 0
    my_tid = win32api.GetCurrentThreadId()
    attached = False
    try:
        if foreground_tid and foreground_tid != my_tid:
            win32process.AttachThreadInput(my_tid, foreground_tid, True)
            attached = True
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
    except win32gui.error:
        pass
    finally:
        if attached:
            win32process.AttachThreadInput(my_tid, foreground_tid, False)
    if _wait_for_foreground(hwnd, timeout):
        return True

    # Last resort: the call Alt+Tab uses, which the foreground lock tolerates.
    ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
    return _wait_for_foreground(hwnd, timeout)


class ForegroundTracker:
    """Remembers the last real application window the user was in, so that
    actions triggered from our own window or tray menu (which steal focus)
    can hand focus back before simulating Ctrl+C."""

    def __init__(self):
        self.last_external_hwnd = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            try:
                hwnd = win32gui.GetForegroundWindow()
                if _is_external_app_window(hwnd):
                    self.last_external_hwnd = hwnd
            except win32gui.error:
                pass
            self._stop.wait(POLL_INTERVAL)

    def focus_last_external(self, timeout=0.6):
        """Makes sure an external app window is in the foreground. No-op when
        one already is (the hotkey path). Returns False if it couldn't."""
        if _is_external_app_window(win32gui.GetForegroundWindow()):
            return True

        target = self.last_external_hwnd
        try:
            if not target or not win32gui.IsWindow(target):
                return False
            if win32gui.IsIconic(target):
                win32gui.ShowWindow(target, win32con.SW_RESTORE)
        except win32gui.error:
            return False

        if not _bring_to_front(target, timeout):
            return False

        # Let the app restore its caret/selection focus before we send Ctrl+C.
        time.sleep(0.08)
        return True
