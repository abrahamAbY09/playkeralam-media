"""Malayalam voice-over: ElevenLabs lines from the committed voice cache, or the offline Piper voices.

ElevenLabs (from 25 Nov 2026, Abr): the reel's lines are voiced ONCE through the ElevenLabs connector and the
audio is saved in automation/voice-cache/eleven/ (committed), named by a hash of model + voice + settings + text.
The renderer only ever reads that cache; it never calls ElevenLabs, so re-rendering a reel costs no credits. A
line that is not in the cache stops the render (see voice_lines.py: plan, put, usage). Piper stays as the free
fallback when ElevenLabs is not connected or the month's credits are short.

Piper (Arjun, Meera) through sherpa-onnx, fully offline:

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
import hashlib
import json
import pathlib
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import AUTOMATION, CACHE, CONFIG  # noqa: E402

VOICE_CACHE = AUTOMATION / "voice-cache" / "eleven"
PIPER_CAST = {"ammachi": "meera", "meenu": "meera", "uncle": "arjun", "appu": "arjun"}


def eleven_cfg():
    return CONFIG["voice"].get("eleven", {})


def provider_for(spec):
    return spec.get("voiceProvider") or CONFIG["voice"].get("provider", "piper")


def eleven_voice(speaker):
    cast = eleven_cfg().get("cast", {})
    vid = cast.get(speaker or "narrator") or cast.get("narrator")
    if not vid:
        raise SystemExit(f"No ElevenLabs voice set for '{speaker}' in config.json voice.eleven.cast")
    return vid


def line_key(text, voice_id, model=None, settings=None):
    """Cache key for one ElevenLabs line: the same text, voice, model and settings are never voiced twice."""
    cfg = eleven_cfg()
    model = model or cfg.get("model", "eleven_v3")
    settings = settings if settings is not None else cfg.get("settings", {})
    raw = json.dumps([model, voice_id, settings, text.strip()], ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def line_file(text, speaker):
    return VOICE_CACHE / f"{line_key(text, eleven_voice(speaker))}.mp3"


def _decode(path, sr=44100):
    """An ElevenLabs line from the cache: natural speed (no time-stretch), leading and trailing silence cut."""
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-af",
           "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse",
           "-f", "f32le", "-ar", str(sr), "-ac", "1", "pipe:1"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise SystemExit(f"could not decode {path}: {r.stderr.decode()[:300]}")
    y = np.frombuffer(r.stdout, dtype=np.float32).copy()
    n = int(0.008 * sr)
    if len(y) > 2 * n:
        y[:n] *= np.linspace(0, 1, n)
        y[-n:] *= np.linspace(1, 0, n)
    return np.clip(y, -1, 1), sr


def speak_line(text, speaker=None, provider="piper", date=None, voice=None):
    """One beat's voice as float32 mono samples. ElevenLabs lines come only from the cache (never the network);
    Piper picks a voice by character (female cast -> meera, male -> arjun), else the voice of the week."""
    if provider == "eleven":
        f = line_file(text, speaker)
        if not f.exists():
            raise FileNotFoundError(str(f))
        return _decode(f)
    v = voice or PIPER_CAST.get(speaker or "") or voice_for_week(date or dt.date.today().isoformat())
    return speak(text, v)

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
