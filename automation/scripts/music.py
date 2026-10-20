"""An original, royalty-free background loop for reels, synthesised from scratch (no samples).

    python3 music.py SECONDS out.wav [--seed N]

Light 100 bpm groove: soft kick, shaker, bass and a marimba-like melody on a I-V-vi-IV
progression. The seed picks the key and the melody, so reels don't all sound the same.
"""
import sys
import wave

import numpy as np

SR = 44100


def env(n, attack=0.005, decay=0.35):
    t = np.arange(n) / SR
    a = np.clip(t / attack, 0, 1)
    return a * np.exp(-t / decay)


def tone(freq, seconds, decay=0.35, harmonics=((1, 1.0), (3, 0.25), (4.2, 0.08))):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    wave_ = sum(amp * np.sin(2 * np.pi * freq * h * t) for h, amp in harmonics)
    return wave_ * env(n, decay=decay)


def kick(seconds=0.35):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    f = 120 * np.exp(-t * 18) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def shaker(rng, seconds=0.08):
    n = int(seconds * SR)
    noise = rng.standard_normal(n)
    noise = np.diff(noise, prepend=0)  # crude high-pass
    return noise * np.exp(-np.arange(n) / SR * 45) * 0.25


def add(buf, sig, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    sig = sig[: len(buf) - i]
    buf[i:i + len(sig)] += sig


def make(seconds, seed=1):
    rng = np.random.default_rng(seed)
    bpm = 100
    beat = 60 / bpm
    root = 261.63 * 2 ** (int(rng.integers(-3, 4)) / 12)  # key around C
    semis = lambda s: root * 2 ** (s / 12)  # noqa: E731
    progression = [(0, [0, 4, 7]), (7, [7, 11, 14]), (9, [9, 12, 16]), (5, [5, 9, 12])]
    pent = [0, 2, 4, 7, 9, 12, 14, 16]
    total = int((seconds + 1) * SR)
    buf = np.zeros(total)
    bar = 4 * beat
    t = 0.0
    k = 0
    while t < seconds + 1:
        bass_root, chord = progression[k % 4]
        for b in range(4):
            at = t + b * beat
            add(buf, kick() * 0.55, at)
            add(buf, shaker(rng), at + beat / 2)
            add(buf, shaker(rng) * 0.6, at + beat * 0.75)
        add(buf, tone(semis(bass_root - 24), bar * 0.9, decay=0.9, harmonics=((1, 1.0), (2, 0.3))) * 0.35, t)
        add(buf, tone(semis(bass_root - 24), beat, decay=0.4, harmonics=((1, 1.0), (2, 0.3))) * 0.25, t + 2.5 * beat)
        for c in chord:  # soft pad stab
            add(buf, tone(semis(c), beat * 1.5, decay=0.6, harmonics=((1, 1.0), (2, 0.15))) * 0.07, t)
            add(buf, tone(semis(c), beat * 1.5, decay=0.6, harmonics=((1, 1.0), (2, 0.15))) * 0.05, t + 2 * beat)
        for step in range(8):  # marimba melody on eighths, with rests
            if rng.random() < 0.62:
                note = pent[int(rng.integers(0, len(pent)))] + 12
                add(buf, tone(semis(note), 0.5, decay=0.18) * 0.16, t + step * beat / 2)
        t += bar
        k += 1
    buf = buf[: int(seconds * SR)]
    fade = int(1.5 * SR)
    buf[-fade:] *= np.linspace(1, 0, fade)
    buf[: int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))
    return buf / (np.abs(buf).max() + 1e-9) * 0.8


def write_wav(path, samples, sr=SR):
    data = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    seed = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[3] == "--seed" else 1
    write_wav(sys.argv[2], make(float(sys.argv[1]), seed))
    print("wrote", sys.argv[2])
