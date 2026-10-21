import os
import urllib.request

from .config import CONFIG_DIR

VOICES_DIR = os.path.join(CONFIG_DIR, "voices")
BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

# (display name, file stem, path under the Piper voices repo)
CATALOG = [
    ("Lessac (US)", "en_US-lessac-medium", "en/en_US/lessac/medium"),
    ("Amy (US)", "en_US-amy-medium", "en/en_US/amy/medium"),
    ("Alan (UK)", "en_GB-alan-medium", "en/en_GB/alan/medium"),
]


def voice_path(stem):
    return os.path.join(VOICES_DIR, stem + ".onnx")


def is_installed(stem):
    return os.path.exists(voice_path(stem)) and os.path.exists(voice_path(stem) + ".json")


def installed_voices():
    """[(description, voice_id)] for every Piper voice in the voices folder."""
    if not os.path.isdir(VOICES_DIR):
        return []
    names = {stem: display for display, stem, _ in CATALOG}
    result = []
    for filename in sorted(os.listdir(VOICES_DIR)):
        if filename.endswith(".onnx"):
            stem = filename[: -len(".onnx")]
            if is_installed(stem):
                result.append((f"Piper: {names.get(stem, stem)}", f"piper:{stem}"))
    return result


def download(stem, repo_path, progress=None):
    """Downloads a voice (model + config). progress(done_bytes, total_bytes)."""
    os.makedirs(VOICES_DIR, exist_ok=True)
    for suffix in (".onnx.json", ".onnx"):
        url = f"{BASE_URL}/{repo_path}/{stem}{suffix}"
        target = os.path.join(VOICES_DIR, stem + suffix)
        part = target + ".part"
        with urllib.request.urlopen(url, timeout=30) as response, open(part, "wb") as out:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = response.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
        os.replace(part, target)
