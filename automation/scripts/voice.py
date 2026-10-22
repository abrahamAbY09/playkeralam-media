"""Malayalam voice-over with the Piper voices (Arjun, Meera) through sherpa-onnx, fully offline.

    from voice import speak
    samples, sample_rate = speak("ഇന്നത്തെ വാക്ക്...", voice="meera")

Write the text in Malayalam script only: names and film titles transliterated (Moonnam Mura -> മൂന്നാം മുറ),
numbers spelled out in words. Latin letters and digits come out garbled.
"""
import datetime as dt
import functools
import pathlib
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import CACHE  # noqa: E402

SPEED = {"arjun": 1.1, "meera": 1.0}


def voice_for_week(date_str):
    """Even ISO week: Arjun; odd: Meera."""
    y, m, d = map(int, date_str.split("-"))
    return "arjun" if dt.date(y, m, d).isocalendar()[1] % 2 == 0 else "meera"


@functools.lru_cache(maxsize=2)
def _tts(voice):
    import sherpa_onnx

    d = CACHE / "voices" / f"vits-piper-ml_IN-{voice}-medium"
    if not (d / "tokens.txt").exists():
        raise SystemExit(f"Voice {voice} not installed; run automation/scripts/setup.sh")
    cfg = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                model=str(d / f"ml_IN-{voice}-medium.onnx"), tokens=str(d / "tokens.txt"), data_dir=str(d / "espeak-ng-data")),
            num_threads=4,
        ))
    return sherpa_onnx.OfflineTts(cfg)


# The model's own "speed" setting barely changes the pace (Arjun stays near 1.6 words/second, which sounds
# slow for a reel). So the finished audio is sped up with ffmpeg's pitch-preserving tempo filter instead.
# 1.3 is about the limit before the voice starts to sound rushed or robotic.
TEMPO = {"arjun": 1.3, "meera": 1.2}


def _speed_up(samples, sr, tempo):
    """Time-stretch float32 mono audio by `tempo` without changing pitch; also trims leading/trailing silence."""
    if tempo == 1.0 or len(samples) == 0:
        return samples
    cmd = ["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "pipe:0",
           "-af", f"silenceremove=start_periods=1:start_threshold=-45dB,atempo={tempo}",
           "-f", "f32le", "-ar", str(sr), "-ac", "1", "pipe:1"]
    r = subprocess.run(cmd, input=samples.astype(np.float32).tobytes(), capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return samples  # fall back to the unstretched voice rather than fail the reel
    return np.frombuffer(r.stdout, dtype=np.float32).copy()


def speak(text, voice="meera"):
    audio = _tts(voice).generate(text, sid=0, speed=SPEED.get(voice, 1.0))
    samples = np.clip(np.array(audio.samples, dtype=np.float32), -1, 1)
    return np.clip(_speed_up(samples, audio.sample_rate, TEMPO.get(voice, 1.0)), -1, 1), audio.sample_rate
