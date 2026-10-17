import sys
import threading
import time

import keyboard

from .config import Config
from .focus import ForegroundTracker
from .gui import SettingsWindow
from .selection import get_selected_text
from .single_instance import SingleInstance
from .tray_icon import build_icon
from .tts_engine import TTSEngine, list_voices


class TextReaderApp:
    def __init__(self):
        self.config = Config.load()
        self.voices = list_voices()
        self.icon = None
        self.gui = None
        self.root = None
        self.single_instance = None
        self.focus_tracker = ForegroundTracker()
        self._shutdown_started = False
        self._hotkey_handlers = {}

        self.engine = TTSEngine(on_status_change=self._on_status_change)
        if self.config.voice_id:
            self.engine.set_voice(self.config.voice_id)
        if self.config.rate:
            self.engine.set_rate(self.config.rate)

    def _on_status_change(self, status):
        if self.icon:
            self.icon.title = f"Text Reader — {status.capitalize()}"
        if self.root:
            self.root.after(0, self.gui.set_status, status)

    def _notify(self, message):
        if self.icon:
            self.icon.notify(message, "Text Reader")
        if self.root:
            self.root.after(0, self.gui.show_message, message)

    def read_selection(self):
        # The window button and tray menu take focus from the app holding the
        # highlighted text; hand it back so the simulated Ctrl+C lands there.
        if not self.focus_tracker.focus_last_external():
            self._notify("Couldn't switch back to your app. Click your text again and retry.")
            return
        text = get_selected_text()
        if not text or not text.strip():
            self._notify("No text is selected.")
            return
        self.engine.speak(text, rate=self.config.rate, voice_id=self.config.voice_id)

    def read_selection_async(self, from_window=False):
        def work():
            self.read_selection()
            if from_window:
                self.show_window()

        threading.Thread(target=work, daemon=True).start()

    def toggle_pause(self):
        if self.engine.status == "speaking":
            self.engine.pause()
        elif self.engine.status == "paused":
            self.engine.resume()

    def stop(self):
        self.engine.stop()

    def set_voice(self, voice_id):
        self.config.voice_id = voice_id
        self.config.save()
        self.engine.set_voice(voice_id)

    def set_rate(self, rate):
        self.config.rate = rate
        self.config.save()
        self.engine.set_rate(rate)

    # --- hotkeys ---

    def _register_initial_hotkeys(self):
        keyboard.add_hotkey(self.config.hotkey_read, self.read_selection)
        keyboard.add_hotkey(self.config.hotkey_stop, self.stop)
        self._hotkey_handlers["read"] = self.config.hotkey_read
        self._hotkey_handlers["stop"] = self.config.hotkey_stop

    def rebind_hotkey(self, action, new_combo):
        other = "stop" if action == "read" else "read"
        if new_combo == self._hotkey_handlers.get(action):
            return True, None
        if new_combo == self._hotkey_handlers.get(other):
            return False, f"Already assigned to {other.capitalize()}"

        callback = self.read_selection if action == "read" else self.stop
        try:
            keyboard.add_hotkey(new_combo, callback)
        except Exception:
            return False, "Not a valid key combination"

        old_combo = self._hotkey_handlers.get(action)
        if old_combo:
            keyboard.remove_hotkey(old_combo)
        self._hotkey_handlers[action] = new_combo
        setattr(self.config, f"hotkey_{action}", new_combo)
        self.config.save()
        return True, None

    # --- window / tray / lifecycle ---

    def show_window(self):
        if self.root:
            self.root.after(0, self.gui.show)

    def request_shutdown(self):
        if self.root:
            self.root.after(0, self.full_shutdown)

    def full_shutdown(self):
        if self._shutdown_started:
            return
        self._shutdown_started = True
        try:
            self.focus_tracker.stop()
            if self.gui:
                self.gui._end_capture_hook()
            self.engine.shutdown()
            keyboard.unhook_all_hotkeys()
            if self.single_instance:
                self.single_instance.close()
            if self.icon:
                self.icon.stop()
        finally:
            if self.root:
                self.root.destroy()

    def _setup_icon(self, icon):
        # On Windows, Shell_NotifyIcon's initial NIM_ADD sometimes reports
        # success but the icon never actually renders when other threads
        # (the keyboard hook, the TTS worker) are active at startup. Toggling
        # it off and back on reliably makes it appear.
        icon.visible = True
        time.sleep(0.3)
        icon.visible = False
        time.sleep(0.1)
        icon.visible = True

    def _run_gui(self):
        # pystray's tray icon only renders reliably on this machine when
        # icon.run() blocks the real main thread, so the GUI's mainloop
        # (also a native Windows message pump) runs on its own thread
        # instead. tkinter is fine with this on Windows as long as a given
        # root's widgets are created and driven from a single, consistent
        # thread, which this does.
        self.gui = SettingsWindow(self)
        self.root = self.gui
        self.root.mainloop()

    def run(self):
        self.focus_tracker.start()
        self._register_initial_hotkeys()
        self.icon = build_icon(self)
        self.single_instance.start_listening(self.show_window)

        gui_thread = threading.Thread(target=self._run_gui, daemon=True)
        gui_thread.start()

        self.icon.run(setup=self._setup_icon)


def main():
    single_instance = SingleInstance()
    if not single_instance.try_acquire():
        single_instance.notify_primary()
        sys.exit(0)

    app = TextReaderApp()
    app.single_instance = single_instance
    app.run()


if __name__ == "__main__":
    main()
