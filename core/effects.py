import numpy as np
import librosa as lb
from scipy.signal import butter, lfilter


# ──────────────────────────────────────────────────────────────────────────────
# Basic transforms
# ──────────────────────────────────────────────────────────────────────────────

def time_stretch_audio(y: np.ndarray, rate: float) -> np.ndarray:
    """Time-stretch without changing pitch.  rate > 1 = faster."""
    return lb.effects.time_stretch(y, rate=rate)


def pitch_shift_audio(y: np.ndarray, sr: int, n_steps: float) -> np.ndarray:
    """Shift pitch by n_steps semitones without changing tempo."""
    return lb.effects.pitch_shift(y, sr=sr, n_steps=n_steps)


# ──────────────────────────────────────────────────────────────────────────────
# Stereo pan  (equal-power)
# ──────────────────────────────────────────────────────────────────────────────

def _to_stereo(audio: np.ndarray) -> np.ndarray:
    """Ensure the array is shape (2, N)."""
    if audio.ndim == 1:
        return np.vstack([audio, audio])
    if audio.ndim == 2 and audio.shape[0] != 2:
        audio = audio.T
    if audio.shape[0] != 2:
        mono = np.mean(audio, axis=0)
        return np.vstack([mono, mono])
    return audio.astype(np.float32)


def apply_stereo_pan(audio: np.ndarray, pan: float) -> np.ndarray:
    """
    Equal-power stereo pan.
    pan: -1.0 = full left, 0.0 = center, 1.0 = full right.
    Returns shape (2, N).
    """
    pan = float(np.clip(pan, -1.0, 1.0))
    stereo = _to_stereo(audio)
    angle = (pan + 1.0) * np.pi / 4.0          # maps [-1,1] → [0, π/2]
    left_gain  = np.cos(angle)
    right_gain = np.sin(angle)
    return np.vstack([stereo[0] * left_gain, stereo[1] * right_gain])


# ──────────────────────────────────────────────────────────────────────────────
# 8D audio
# ──────────────────────────────────────────────────────────────────────────────

def _smooth_pan_lfo(length: int, sr: int, rate_hz: float = 0.25) -> np.ndarray:
    """Return a band-limited LFO in [-1, 1] for smooth 8D panning.

    Uses a low-pass-filtered noise signal so the pan movement is organic
    rather than mechanical (no pure sine-wave sweep).
    """
    t = np.linspace(0, length / sr, length)
    # Superpose two sinusoids at slightly different rates for irregular feel
    lfo = (
        0.6 * np.sin(2 * np.pi * rate_hz * t)
        + 0.4 * np.sin(2 * np.pi * rate_hz * 1.618 * t + 0.8)
    )
    # Soften with a gentle low-pass
    nyq = sr * 0.5
    cutoff = min(rate_hz * 4, nyq * 0.95)
    b, a = butter(2, cutoff / nyq, btype="low")
    lfo = lfilter(b, a, lfo)
    peak = np.max(np.abs(lfo)) + 1e-8
    return (lfo / peak).astype(np.float32)


def apply_8d_effect(
    audio: np.ndarray,
    sr: int,
    depth: float = 1.0,
    pan_rate_hz: float = 0.25,
) -> np.ndarray:
    """
    Simulate 8D / binaural-style audio by continuously panning the mix
    between left and right.  Best experienced on headphones.

    Parameters
    ----------
    audio      : mono (N,) or stereo (2, N) numpy array
    sr         : sample rate
    depth      : 0.0 = no movement, 1.0 = full side-to-side sweep
    pan_rate_hz: how fast the pan sweeps back and forth (Hz)

    Returns
    -------
    Stereo array of shape (2, N).
    """
    depth = float(np.clip(depth, 0.0, 1.0))
    stereo = _to_stereo(audio)
    n = stereo.shape[1]

    # Mix to mono for a clean signal to pan
    mono = (stereo[0] + stereo[1]) * 0.5

    lfo = _smooth_pan_lfo(n, sr, rate_hz=pan_rate_hz) * depth  # [-depth, +depth]
    angle = (lfo + 1.0) * np.pi / 4.0                          # [0, π/2]

    left  = mono * np.cos(angle)
    right = mono * np.sin(angle)

    out = np.vstack([left, right])
    peak = np.max(np.abs(out))
    if peak > 1.0:
        out /= peak
    return out.astype(np.float32)