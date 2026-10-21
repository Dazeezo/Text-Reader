import threading

import numpy as np
import sounddevice as sd
from piper import PiperVoice
from piper.config import SynthesisConfig

from .voice_download import voice_path

BLOCK_SECONDS = 0.1


def _length_scale(rate):
    # App rates run -10..10 (SAPI style); 0 is normal speed, ~+1.0 per 10 steps.
    speed = 1.0 + rate * 0.1
    return 1.0 / max(speed, 0.3)


class PiperBackend:
    """Plays Piper neural voices. Each speak() runs on its own thread that
    synthesizes one sentence at a time and streams it to the sound card, so
    long selections start quickly and stop/pause respond within ~0.1 s."""

    def __init__(self):
        self._voices = {}
        self._load_lock = threading.Lock()
        self._generation = 0
        self._cancel = threading.Event()
        self._resume = threading.Event()
        self._resume.set()
        self.active = False

    def _load(self, stem):
        with self._load_lock:
            if stem not in self._voices:
                path = voice_path(stem)
                self._voices[stem] = PiperVoice.load(path, config_path=path + ".json")
            return self._voices[stem]

    def preload(self, stem):
        """Loads the model in the background so the first speak() starts fast."""

        def work():
            try:
                self._load(stem)
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def speak(self, text, stem, rate=0):
        self.stop()
        voice = self._load(stem)
        self._generation += 1
        generation = self._generation
        self._cancel = threading.Event()
        self._resume.set()
        self.active = True
        threading.Thread(
            target=self._play, args=(voice, text, rate, generation, self._cancel), daemon=True
        ).start()

    def _play(self, voice, text, rate, generation, cancel):
        config = SynthesisConfig(length_scale=_length_scale(rate))
        stream = None
        try:
            for chunk in voice.synthesize(text, config):
                if cancel.is_set():
                    return
                if stream is None:
                    stream = sd.OutputStream(
                        samplerate=chunk.sample_rate, channels=chunk.sample_channels, dtype="int16"
                    )
                    stream.start()
                audio = chunk.audio_int16_array
                block = max(1, int(chunk.sample_rate * BLOCK_SECONDS))
                for start in range(0, len(audio), block):
                    self._resume.wait()
                    if cancel.is_set():
                        return
                    stream.write(audio[start : start + block])
            if stream is not None and not cancel.is_set():
                stream.write(np.zeros(int(stream.samplerate * 0.15), dtype="int16"))
        except Exception:
            pass
        finally:
            if stream is not None:
                try:
                    stream.abort() if cancel.is_set() else stream.stop()
                    stream.close()
                except Exception:
                    pass
            if generation == self._generation:
                self.active = False

    def stop(self):
        self._cancel.set()
        self._resume.set()
        self.active = False

    def pause(self):
        self._resume.clear()

    def resume(self):
        self._resume.set()
