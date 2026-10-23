"""Malayalam voice-over with the Piper voices (Arjun, Meera) through sherpa-onnx, fully offline.

    from voice import speak
    samples, sample_rate = speak("ഇന്നത്തെ വാക്ക്...", voice="meera")

Write the text in Malayalam script only: names and film titles transliterated (Moonnam Mura -> മൂന്നാം മുറ),
numbers spelled out in words. Latin letters and digits come out garbled.

Pace (approved by Abr, Oct 2026): the voice runs at about 1.5x the first routine's voice (roughly 3 words a
second). Leading and trailing silence is cut and any pause inside a line is squeezed to 0.12 s, so the
renderer can place lines back to back with no dead air. Don't change MODEL_SPEED or TEMPO without asking him:
"almost twice as fast" was too fast; this is the "slightly slower" setting he signed off.
"""
import datetime as dt
import functools
import pathlib
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import CACHE  # noqa: E402

# Piper's own length scale (sherpa "speed"); it shortens phonemes natively.
MODEL_SPEED = {"arjun": 1.7, "meera": 1.6}
# Then a pitch-preserving time-stretch on top (ffmpeg atempo).
TEMPO = {"arjun": 1.3, "meera": 1.2}


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


def _ffmpeg(samples, sr, af):
    cmd = ["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "pipe:0",
           "-af", af, "-f", "f32le", "-ar", str(sr), "-ac", "1", "pipe:1"]
    r = subprocess.run(cmd, input=samples.astype(np.float32).tobytes(), capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None
    return np.frombuffer(r.stdout, dtype=np.float32).copy()


def speak(text, voice="meera"):
    """One voice line as float32 mono samples, trimmed tight at both ends."""
    audio = _tts(voice).generate(text, sid=0, speed=MODEL_SPEED.get(voice, 1.6))
    sr = audio.sample_rate
    x = np.clip(np.array(audio.samples, dtype=np.float32), -1, 1)
    af = ("silenceremove=start_periods=1:start_threshold=-42dB,"
          "silenceremove=stop_periods=-1:stop_duration=0.12:stop_threshold=-42dB,"
          f"atempo={TEMPO.get(voice, 1.2)},areverse,silenceremove=start_periods=1:start_threshold=-42dB,areverse")
    y = _ffmpeg(x, sr, af)
    if y is None or len(y) == 0:
        y = x  # fall back to the unprocessed voice rather than fail the reel
    n = int(0.008 * sr)  # 8 ms fades so cuts never click
    if len(y) > 2 * n:
        y[:n] *= np.linspace(0, 1, n)
        y[-n:] *= np.linspace(1, 0, n)
    return np.clip(y, -1, 1), sr
