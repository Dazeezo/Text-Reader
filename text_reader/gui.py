import threading

import customtkinter as ctk
import keyboard

from . import voice_download
from .tray_icon import RATE_PRESETS

MODIFIER_NAMES = {"ctrl", "alt", "shift", "windows"}
CAPTURE_TIMEOUT_MS = 15000


class SettingsWindow(ctk.CTk):
    # Works around a customtkinter bug where its automatic Windows titlebar
    # dark-mode sync can leave the window stuck in a withdrawn (invisible)
    # state right after construction.
    _deactivate_windows_window_header_manipulation = True

    def __init__(self, app):
        super().__init__()
        self.app = app

        self._capture_action = None
        self._capture_handle = None
        self._capture_pressed = {}
        self._capture_timeout_id = None
        self._hotkey_value_labels = {}
        self._hotkey_error_labels = {}
        self._hotkey_buttons = {}
        self._message_revert_id = None

        self.title("Text Reader")
        self.geometry("420x620")
        self.minsize(380, 580)
        self.protocol("WM_DELETE_WINDOW", self.app.full_shutdown)
        self.bind("<Unmap>", self._on_unmap)

        self._voice_by_label = {desc: vid for desc, vid in app.voices}
        self._label_by_voice = {vid: desc for desc, vid in app.voices}
        self._rate_by_label = dict(RATE_PRESETS)
        self._label_by_rate = {rate: label for label, rate in RATE_PRESETS}

        self._build_widgets()
        self.refresh_from_config()
        self.deiconify()

    def _build_widgets(self):
        pad = {"padx": 16, "pady": (12, 0)}

        ctk.CTkLabel(self, text="Text Reader", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 4))
        self.status_label = ctk.CTkLabel(self, text="Idle", text_color="gray60")
        self.status_label.pack(pady=(0, 12))

        voice_frame = ctk.CTkFrame(self, fg_color="transparent")
        voice_frame.pack(fill="x", **pad)
        ctk.CTkLabel(voice_frame, text="Voice").pack(anchor="w")
        self.voice_menu = ctk.CTkOptionMenu(
            voice_frame, values=list(self._voice_by_label.keys()) or ["(no voices found)"], command=self._on_voice_change
        )
        self.voice_menu.pack(fill="x", pady=(4, 0))

        more_frame = ctk.CTkFrame(self, fg_color="transparent")
        more_frame.pack(fill="x", **pad)
        self.download_label = ctk.CTkLabel(
            more_frame, text="Get more natural voices (offline, ~60 MB each)", anchor="w", text_color="gray60"
        )
        self.download_label.pack(fill="x")
        more_row = ctk.CTkFrame(more_frame, fg_color="transparent")
        more_row.pack(fill="x", pady=(4, 0))
        self.catalog_menu = ctk.CTkOptionMenu(more_row, values=[name for name, _, _ in voice_download.CATALOG])
        self.catalog_menu.pack(side="left", fill="x", expand=True)
        self.download_button = ctk.CTkButton(more_row, text="Download", width=90, command=self._on_download)
        self.download_button.pack(side="right", padx=(8, 0))

        speed_frame = ctk.CTkFrame(self, fg_color="transparent")
        speed_frame.pack(fill="x", **pad)
        ctk.CTkLabel(speed_frame, text="Speed").pack(anchor="w")
        self.speed_menu = ctk.CTkOptionMenu(
            speed_frame, values=[label for label, _ in RATE_PRESETS], command=self._on_speed_change
        )
        self.speed_menu.pack(fill="x", pady=(4, 0))

        hotkeys_frame = ctk.CTkFrame(self, fg_color="transparent")
        hotkeys_frame.pack(fill="x", **pad)
        ctk.CTkLabel(hotkeys_frame, text="Hotkeys").pack(anchor="w")
        self._build_hotkey_row(hotkeys_frame, "read", "Read Selection")
        self._build_hotkey_row(hotkeys_frame, "stop", "Stop")

        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.pack(fill="x", padx=16, pady=(16, 0))
        ctk.CTkButton(
            controls_frame, text="Read Selection", command=lambda: self.app.read_selection_async(from_window=True)
        ).pack(
            side="left", expand=True, fill="x", padx=(0, 6)
        )
        ctk.CTkButton(controls_frame, text="Pause / Resume", command=self.app.toggle_pause).pack(
            side="left", expand=True, fill="x", padx=6
        )
        ctk.CTkButton(controls_frame, text="Stop", command=self.app.stop).pack(
            side="left", expand=True, fill="x", padx=(6, 0)
        )

        ctk.CTkButton(self, text="Minimize to Tray", command=self.iconify).pack(pady=(20, 0))

    def _build_hotkey_row(self, parent, action, label):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(row, text=f"{label}:", width=110, anchor="w").pack(side="left")
        value_label = ctk.CTkLabel(row, text="", anchor="w")
        value_label.pack(side="left", fill="x", expand=True)
        button = ctk.CTkButton(row, text="Record", width=80, command=lambda: self._start_capture(action))
        button.pack(side="right")
        self._hotkey_value_labels[action] = value_label
        self._hotkey_buttons[action] = button

        error_label = ctk.CTkLabel(parent, text="", text_color="#e05555", anchor="w")
        error_label.pack(fill="x")
        self._hotkey_error_labels[action] = error_label

    # --- cross-thread-safe entry points ---

    def show(self):
        self.refresh_from_config()
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()

    def set_status(self, status):
        self._cancel_message_revert()
        self.status_label.configure(text=status.capitalize(), text_color="gray60")

    def show_message(self, text):
        self._cancel_message_revert()
        self.status_label.configure(text=text, text_color="#e05555")
        self._message_revert_id = self.after(3000, self._revert_status)

    def _revert_status(self):
        self._message_revert_id = None
        self.set_status(self.app.engine.status)

    def _cancel_message_revert(self):
        if self._message_revert_id is not None:
            self.after_cancel(self._message_revert_id)
            self._message_revert_id = None

    def rebuild_voices(self):
        voices = self.app.voices
        self._voice_by_label = {desc: vid for desc, vid in voices}
        self._label_by_voice = {vid: desc for desc, vid in voices}
        self.voice_menu.configure(values=list(self._voice_by_label) or ["(no voices found)"])
        self.refresh_from_config()

    def _on_download(self):
        choice = self.catalog_menu.get()
        entry = next((e for e in voice_download.CATALOG if e[0] == choice), None)
        if not entry:
            return
        _, stem, repo_path = entry
        if voice_download.is_installed(stem):
            self.download_label.configure(text=f"{choice} is already installed", text_color="gray60")
            return
        self.download_button.configure(state="disabled")

        def progress(done, total):
            if total:
                self.after(0, self.download_label.configure, {"text": f"Downloading {choice}... {done * 100 // total}%"})

        def work():
            try:
                voice_download.download(stem, repo_path, progress)
            except Exception as error:
                self.after(0, self._download_finished, f"Download failed: {error}", False)
                return
            self.after(0, self._download_finished, f"{choice} installed. Pick it in Voice.", True)

        self.download_label.configure(text=f"Downloading {choice}...", text_color="gray60")
        threading.Thread(target=work, daemon=True).start()

    def _download_finished(self, message, ok):
        self.download_button.configure(state="normal")
        self.download_label.configure(text=message, text_color="gray60" if ok else "#e05555")
        if ok:
            self.app.refresh_voices()

    def refresh_from_config(self):
        cfg = self.app.config
        if cfg.voice_id and cfg.voice_id in self._label_by_voice:
            self.voice_menu.set(self._label_by_voice[cfg.voice_id])
        elif self._voice_by_label:
            self.voice_menu.set(next(iter(self._voice_by_label)))
        self.speed_menu.set(self._label_by_rate.get(cfg.rate, self._label_by_rate.get(0, "1x (Normal)")))
        self._hotkey_value_labels["read"].configure(text=cfg.hotkey_read)
        self._hotkey_value_labels["stop"].configure(text=cfg.hotkey_stop)

    # --- widget callbacks (already on the Tk thread) ---

    def _on_voice_change(self, label):
        voice_id = self._voice_by_label.get(label)
        if voice_id:
            self.app.set_voice(voice_id)

    def _on_speed_change(self, label):
        rate = self._rate_by_label.get(label)
        if rate is not None:
            self.app.set_rate(rate)

    def _on_unmap(self, event):
        if event.widget is self and self.state() == "iconic":
            self.withdraw()

    # --- hotkey capture ---

    def _start_capture(self, action):
        if self._capture_action is not None:
            return
        self._capture_action = action
        self._capture_pressed = {}
        self._hotkey_error_labels[action].configure(text="")
        self._hotkey_buttons[action].configure(text="Press keys...")
        self._capture_handle = keyboard.hook(lambda e: self._on_capture_event(action, e), suppress=False)
        self._capture_timeout_id = self.after(CAPTURE_TIMEOUT_MS, self._cancel_capture, action)

    def _on_capture_event(self, action, event):
        if event.event_type == keyboard.KEY_DOWN:
            self._capture_pressed[event.scan_code] = event.name
        elif event.event_type == keyboard.KEY_UP:
            if not self._capture_pressed:
                return
            combo = keyboard.get_hotkey_name(list(self._capture_pressed.values()))
            self.after(0, self._finish_capture, action, combo)

    def _finish_capture(self, action, combo):
        if self._capture_action != action:
            return
        self._end_capture_hook()
        self._capture_action = None
        self._hotkey_buttons[action].configure(text="Record")

        if not combo or combo in ("esc", "escape"):
            return

        parts = combo.split("+")
        if not any(p in MODIFIER_NAMES for p in parts):
            self._hotkey_error_labels[action].configure(text="Include Ctrl, Alt, Shift, or Win in the combo")
            return

        ok, err = self.app.rebind_hotkey(action, combo)
        if ok:
            self._hotkey_value_labels[action].configure(text=combo)
        else:
            self._hotkey_error_labels[action].configure(text=err)

    def _cancel_capture(self, action):
        if self._capture_action != action:
            return
        self._end_capture_hook()
        self._capture_action = None
        self._hotkey_buttons[action].configure(text="Record")

    def _end_capture_hook(self):
        if self._capture_handle is not None:
            keyboard.unhook(self._capture_handle)
            self._capture_handle = None
        if self._capture_timeout_id is not None:
            self.after_cancel(self._capture_timeout_id)
            self._capture_timeout_id = None
