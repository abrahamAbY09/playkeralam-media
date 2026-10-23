"""Original synthesized sound for reels: an upbeat 124 bpm music bed and short effects (pop, tick, whoosh,
ding, boom). Everything is made from sine waves and noise, so it is royalty-free and needs no downloads."""
import numpy as np

SR = 44100


def _t(sec):
    return np.arange(int(sec * SR)) / SR


def _env(n, attack=0.004, decay=0.3):
    t = np.arange(n) / SR
    return np.clip(t / attack, 0, 1) * np.exp(-t / decay)


def _lowpass(x, a):
    """One-pole low-pass; a in (0,1), smaller = darker. a may be an array (sweep)."""
    y = np.empty_like(x)
    acc = 0.0
    a = np.broadcast_to(a, x.shape)
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def pop():
    t = _t(0.09)
    f = 950 * np.exp(-t * 30) + 260
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 40) * 0.9


def tick():
    t = _t(0.05)
    rng = np.random.default_rng(7)
    return (np.sin(2 * np.pi * 2100 * t) * 0.6 + rng.standard_normal(len(t)) * 0.25) * np.exp(-t * 90)


def whoosh(sec=0.28):
    rng = np.random.default_rng(3)
    n = int(sec * SR)
    noise = rng.standard_normal(n)
    sweep = np.linspace(0.02, 0.35, n) ** 1.5
    x = _lowpass(noise, sweep)
    x = x - _lowpass(x, 0.02)
    shape = np.sin(np.linspace(0, np.pi, n)) ** 2
    return x * shape * 1.8


def ding():
    t = _t(1.3)
    f0 = 1046.5
    x = (np.sin(2 * np.pi * f0 * t) * 1.0 + np.sin(2 * np.pi * f0 * 2.0 * t) * 0.35
         + np.sin(2 * np.pi * f0 * 2.76 * t) * 0.2 + np.sin(2 * np.pi * f0 * 1.5 * t) * 0.25)
    return x * _env(len(t), decay=0.45) * 0.5


def boom():
    t = _t(0.5)
    f = 90 * np.exp(-t * 10) + 38
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6) * 0.9


SFX = {"pop": pop, "tick": tick, "whoosh": whoosh, "ding": ding, "boom": boom}


def _tone(freq, sec, decay=0.3, harmonics=((1, 1.0), (3, 0.22), (4.2, 0.07))):
    t = _t(sec)
    return sum(a * np.sin(2 * np.pi * freq * h * t) for h, a in harmonics) * _env(len(t), decay=decay)


def _kick():
    t = _t(0.3)
    f = 130 * np.exp(-t * 20) + 48
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11)


def _hat(rng):
    n = int(0.05 * SR)
    x = np.diff(rng.standard_normal(n), prepend=0)
    return x * np.exp(-np.arange(n) / SR * 70) * 0.18


def _clap(rng):
    n = int(0.12 * SR)
    x = rng.standard_normal(n)
    x = x - _lowpass(x, 0.15)
    return x * np.exp(-np.arange(n) / SR * 28) * 0.35


def _add(buf, sig, at):
    i = int(at * SR)
    if i >= len(buf) or i < 0:
        return
    sig = sig[: len(buf) - i]
    buf[i:i + len(sig)] += sig


def bed(seconds, seed=1, bpm=124):
    """Upbeat four-on-the-floor loop with a pentatonic pluck melody; the seed picks key and melody."""
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    root = 261.63 * 2 ** (int(rng.integers(-3, 4)) / 12)
    semi = lambda s: root * 2 ** (s / 12)  # noqa: E731
    prog = [(0, [0, 4, 7]), (9, [9, 12, 16]), (5, [5, 9, 12]), (7, [7, 11, 14])]
    pent = [0, 2, 4, 7, 9, 12, 14, 16]
    buf = np.zeros(int((seconds + 1) * SR))
    t, k = 0.0, 0
    while t < seconds + 1:
        r, chord = prog[k % 4]
        for b in range(4):
            at = t + b * beat
            _add(buf, _kick() * 0.6, at)
            _add(buf, _hat(rng), at + beat / 2)
            if b in (1, 3):
                _add(buf, _clap(rng), at)
        for e in range(8):
            _add(buf, _tone(semi(r - 24), beat / 2 * 0.9, decay=0.15, harmonics=((1, 1.0), (2, 0.4))) * 0.32, t + e * beat / 2)
        for c in chord:
            _add(buf, _tone(semi(c), beat * 1.2, decay=0.5, harmonics=((1, 1.0), (2, 0.15))) * 0.05, t)
        for s in range(8):
            if rng.random() < 0.55:
                _add(buf, _tone(semi(pent[int(rng.integers(0, len(pent)))] + 12), 0.35, decay=0.12) * 0.14, t + s * beat / 2)
        t += 4 * beat
        k += 1
    buf = buf[: int(seconds * SR)]
    return (buf / (np.abs(buf).max() + 1e-9)).astype(np.float32)
