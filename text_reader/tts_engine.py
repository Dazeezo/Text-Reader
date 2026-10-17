import queue
import threading

import pythoncom
import win32com.client

SPEAK = "speak"
STOP = "stop"
PAUSE = "pause"
RESUME = "resume"
SET_RATE = "set_rate"
SET_VOICE = "set_voice"
SHUTDOWN = "shutdown"

SVSF_ASYNC = 1
SVSF_PURGE_BEFORE_SPEAK = 2

LEGACY_CATEGORY_ID = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices"
ONECORE_CATEGORY_ID = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices"


def _tokens_in_category(category_id):
    try:
        category = win32com.client.Dispatch("SAPI.SpObjectTokenCategory")
        category.SetId(category_id, False)
        return list(category.EnumerateTokens())
    except Exception:
        return []


def _all_voice_tokens():
    """Legacy SAPI5 'desktop' voices plus the OneCore voices used by Narrator
    and modern apps (which also cover any free 'Natural' voices the user has
    downloaded via Windows Settings). Deduped by token id, OneCore wins."""
    tokens = _tokens_in_category(LEGACY_CATEGORY_ID) + _tokens_in_category(ONECORE_CATEGORY_ID)
    seen = set()
    unique = []
    for t in tokens:
        if t.Id not in seen:
            seen.add(t.Id)
            unique.append(t)
    return unique


def list_voices():
    """Returns [(description, voice_id), ...] for the installed SAPI voices."""
    pythoncom.CoInitialize()
    try:
        return [(t.GetDescription(), t.Id) for t in _all_voice_tokens()]
    finally:
        pythoncom.CoUninitialize()


class TTSEngine:
    """Owns a single SAPI voice on a dedicated worker thread (COM objects
    are apartment-bound, so all calls to the voice happen on that one
    thread) and exposes a thread-safe queue-based API to the rest of the app."""

    def __init__(self, on_status_change=None):
        self._queue = queue.Queue()
        self._on_status_change = on_status_change
        self.status = "idle"
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def speak(self, text, rate=None, voice_id=None):
        self._queue.put((SPEAK, {"text": text, "rate": rate, "voice_id": voice_id}))

    def stop(self):
        self._queue.put((STOP, None))

    def pause(self):
        self._queue.put((PAUSE, None))

    def resume(self):
        self._queue.put((RESUME, None))

    def set_rate(self, rate):
        self._queue.put((SET_RATE, rate))

    def set_voice(self, voice_id):
        self._queue.put((SET_VOICE, voice_id))

    def shutdown(self):
        self._queue.put((SHUTDOWN, None))
        self._thread.join(timeout=2)

    def _set_status(self, status):
        self.status = status
        if self._on_status_change:
            self._on_status_change(status)

    def _select_voice(self, sapi_voice, voice_id):
        for t in _all_voice_tokens():
            if t.Id == voice_id:
                sapi_voice.Voice = t
                return

    def _run(self):
        pythoncom.CoInitialize()
        sapi_voice = win32com.client.Dispatch("SAPI.SpVoice")
        watching = False
        try:
            while True:
                try:
                    cmd, payload = self._queue.get(timeout=0.15)
                except queue.Empty:
                    if watching and sapi_voice.Status.RunningState == 1:
                        watching = False
                        self._set_status("idle")
                    continue

                if cmd == SHUTDOWN:
                    sapi_voice.Speak("", SVSF_PURGE_BEFORE_SPEAK)
                    break
                elif cmd == SPEAK:
                    sapi_voice.Speak("", SVSF_PURGE_BEFORE_SPEAK)
                    if payload.get("rate") is not None:
                        sapi_voice.Rate = payload["rate"]
                    if payload.get("voice_id"):
                        self._select_voice(sapi_voice, payload["voice_id"])
                    sapi_voice.Speak(payload["text"], SVSF_ASYNC)
                    watching = True
                    self._set_status("speaking")
                elif cmd == STOP:
                    sapi_voice.Speak("", SVSF_PURGE_BEFORE_SPEAK)
                    watching = False
                    self._set_status("idle")
                elif cmd == PAUSE:
                    sapi_voice.Pause()
                    self._set_status("paused")
                elif cmd == RESUME:
                    sapi_voice.Resume()
                    watching = True
                    self._set_status("speaking")
                elif cmd == SET_RATE:
                    sapi_voice.Rate = payload
                elif cmd == SET_VOICE:
                    self._select_voice(sapi_voice, payload)
        finally:
            pythoncom.CoUninitialize()
