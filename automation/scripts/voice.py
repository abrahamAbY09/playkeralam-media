"""Malayalam voice-over with the Piper voices (Arjun, Meera) through sherpa-onnx, fully offline.

    from voice import speak
    samples, sample_rate = speak("ഇന്നത്തെ വാക്ക്...", voice="meera")

Write the text in Malayalam script only: names and film titles transliterated (Moonnam Mura -> മൂന്നാം മുറ),
numbers spelled out in words. Latin letters and digits come out garbled.
"""
import datetime as dt
import functools
import pathlib
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


def speak(text, voice="meera"):
    audio = _tts(voice).generate(text, sid=0, speed=SPEED.get(voice, 1.0))
    return np.clip(np.array(audio.samples, dtype=np.float32), -1, 1), audio.sample_rate
