"""
16-band parametric equalizer.

Each band is implemented as a biquad IIR filter:
  - Low shelf  → band 0
  - High shelf → band 15
  - Peaking EQ → bands 1–14

Band centre frequencies (Hz):
  31, 63, 125, 250, 500, 1k, 2k, 3k, 4k, 6k, 8k, 10k, 12k, 14k, 16k, 20k
"""

from __future__ import annotations

import numpy as np
from scipy.signal import sosfilt, sosfilt_zi

# ──────────────────────────────────────────────────────────────────────────────
# Band definitions
# ──────────────────────────────────────────────────────────────────────────────

BAND_FREQS: list[float] = [
    31, 63, 125, 250, 500, 1_000, 2_000, 3_000,
    4_000, 6_000, 8_000, 10_000, 12_000, 14_000, 16_000, 20_000,
]

DEFAULT_Q = 1.41          # ~1 octave bandwidth per band
GAIN_RANGE_DB = (-18, 18) # UI slider range


# ──────────────────────────────────────────────────────────────────────────────
# Biquad coefficient builders
# ──────────────────────────────────────────────────────────────────────────────

def _peaking_sos(freq: float, gain_db: float, Q: float, sr: int) -> np.ndarray:
    """Return a (1, 6) SOS array for a peaking EQ biquad."""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * freq / sr
    cos_w0 = np.cos(w0)
    sin_w0 = np.sin(w0)
    alpha = sin_w0 / (2 * Q)

    b0 =  1 + alpha * A
    b1 = -2 * cos_w0
    b2 =  1 - alpha * A
    a0 =  1 + alpha / A
    a1 = -2 * cos_w0
    a2 =  1 - alpha / A

    return np.array([[b0/a0, b1/a0, b2/a0, 1.0, a1/a0, a2/a0]])


def _low_shelf_sos(freq: float, gain_db: float, Q: float, sr: int) -> np.ndarray:
    """Return a (1, 6) SOS array for a low-shelf biquad."""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * freq / sr
    cos_w0 = np.cos(w0)
    sin_w0 = np.sin(w0)
    alpha = sin_w0 / (2 * Q)
    sqrt_A = np.sqrt(A)

    b0 =  A * ((A + 1) - (A - 1) * cos_w0 + 2 * sqrt_A * alpha)
    b1 =  2 * A * ((A - 1) - (A + 1) * cos_w0)
    b2 =  A * ((A + 1) - (A - 1) * cos_w0 - 2 * sqrt_A * alpha)
    a0 =       (A + 1) + (A - 1) * cos_w0 + 2 * sqrt_A * alpha
    a1 = -2 *  ((A - 1) + (A + 1) * cos_w0)
    a2 =       (A + 1) + (A - 1) * cos_w0 - 2 * sqrt_A * alpha

    return np.array([[b0/a0, b1/a0, b2/a0, 1.0, a1/a0, a2/a0]])


def _high_shelf_sos(freq: float, gain_db: float, Q: float, sr: int) -> np.ndarray:
    """Return a (1, 6) SOS array for a high-shelf biquad."""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * freq / sr
    cos_w0 = np.cos(w0)
    sin_w0 = np.sin(w0)
    alpha = sin_w0 / (2 * Q)
    sqrt_A = np.sqrt(A)

    b0 =  A * ((A + 1) + (A - 1) * cos_w0 + 2 * sqrt_A * alpha)
    b1 = -2 * A * ((A - 1) + (A + 1) * cos_w0)
    b2 =  A * ((A + 1) + (A - 1) * cos_w0 - 2 * sqrt_A * alpha)
    a0 =       (A + 1) - (A - 1) * cos_w0 + 2 * sqrt_A * alpha
    a1 =  2 *  ((A - 1) - (A + 1) * cos_w0)
    a2 =       (A + 1) - (A - 1) * cos_w0 - 2 * sqrt_A * alpha

    return np.array([[b0/a0, b1/a0, b2/a0, 1.0, a1/a0, a2/a0]])


# ──────────────────────────────────────────────────────────────────────────────
# Main EQ builder
# ──────────────────────────────────────────────────────────────────────────────

def build_eq_sos(
    gains_db: list[float],
    sr: int,
    Q: float = DEFAULT_Q,
) -> np.ndarray:
    """
    Build a stacked SOS filter array from 16 gain values.

    Parameters
    ----------
    gains_db : list of 16 floats, gain in dB for each band (-18 to +18)
    sr       : sample rate
    Q        : bandwidth factor (default 1.41 ≈ 1 octave)

    Returns
    -------
    sos : np.ndarray of shape (16, 6)
    """
    if len(gains_db) != 16:
        raise ValueError(f"Expected 16 band gains, got {len(gains_db)}")

    sections: list[np.ndarray] = []
    for i, (freq, gain) in enumerate(zip(BAND_FREQS, gains_db)):
        nyq = sr / 2
        # Clamp frequency to a safe range below Nyquist
        safe_freq = float(np.clip(freq, 20.0, nyq * 0.98))
        if i == 0:
            sos = _low_shelf_sos(safe_freq, gain, Q, sr)
        elif i == 15:
            sos = _high_shelf_sos(safe_freq, gain, Q, sr)
        else:
            sos = _peaking_sos(safe_freq, gain, Q, sr)
        sections.append(sos)

    return np.vstack(sections)   # (16, 6)


# ──────────────────────────────────────────────────────────────────────────────
# Apply EQ to audio
# ──────────────────────────────────────────────────────────────────────────────

def apply_eq(
    audio: np.ndarray,
    sr: int,
    gains_db: list[float],
    Q: float = DEFAULT_Q,
) -> np.ndarray:
    """
    Apply 16-band EQ to mono or stereo audio.

    Parameters
    ----------
    audio    : shape (N,) mono or (2, N) stereo, float32/float64
    sr       : sample rate
    gains_db : 16 gain values in dB
    Q        : filter bandwidth

    Returns
    -------
    Equalised audio, same shape and dtype as input.
    """
    # Skip processing if all bands are 0 dB (flat)
    if all(abs(g) < 1e-4 for g in gains_db):
        return audio

    sos = build_eq_sos(gains_db, sr, Q)
    dtype = audio.dtype

    if audio.ndim == 1:
        out = sosfilt(sos, audio.astype(np.float64)).astype(dtype)
    else:
        channels = [
            sosfilt(sos, audio[ch].astype(np.float64)).astype(dtype)
            for ch in range(audio.shape[0])
        ]
        out = np.vstack(channels)

    # Safety clip — heavy boosts can push past ±1
    return np.clip(out, -1.0, 1.0)


# ──────────────────────────────────────────────────────────────────────────────
# Frequency response (for visualisation)
# ──────────────────────────────────────────────────────────────────────────────

def eq_frequency_response(
    gains_db: list[float],
    sr: int,
    n_points: int = 512,
    Q: float = DEFAULT_Q,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute the combined frequency response of the EQ.

    Returns
    -------
    freqs : np.ndarray of shape (n_points,)  — frequency axis in Hz
    mag_db: np.ndarray of shape (n_points,)  — magnitude in dB
    """
    from scipy.signal import sosfreqz

    sos = build_eq_sos(gains_db, sr, Q)
    w, h = sosfreqz(sos, worN=n_points, fs=sr)
    mag_db = 20 * np.log10(np.abs(h) + 1e-12)
    return w, mag_db


# ──────────────────────────────────────────────────────────────────────────────
# Preset library
# ──────────────────────────────────────────────────────────────────────────────

EQ_PRESETS: dict[str, list[float]] = {
    "Flat": [0.0] * 16,

    "Bass Boost": [
         6,  5,  4,  3,  2,  1,  0,  0,
         0,  0,  0,  0,  0,  0,  0,  0,
    ],
    "Treble Boost": [
         0,  0,  0,  0,  0,  0,  0,  0,
         1,  2,  3,  4,  5,  6,  6,  5,
    ],
    "V-Shape": [
         6,  5,  3,  1,  0, -2, -3, -3,
        -3, -2,  0,  1,  3,  5,  6,  5,
    ],
    "Vocal Boost": [
        -2, -1,  0,  1,  2,  4,  5,  5,
         4,  3,  2,  1,  0, -1, -2, -2,
    ],
    "Lo-Fi": [
         3,  2,  1,  0, -1, -2, -3, -4,
        -5, -6, -6, -6, -6, -6, -6, -6,
    ],
    "Acoustic": [
         2,  3,  3,  2,  1,  0,  1,  2,
         3,  3,  2,  1,  1,  2,  2,  1,
    ],
    "Electronic": [
         4,  3,  2,  0, -1, -1,  1,  2,
         2,  1,  0,  1,  2,  3,  4,  4,
    ],
    "Rock": [
         4,  3,  2,  1,  0,  0,  1,  2,
         3,  3,  2,  1,  0,  1,  2,  3,
    ],
    "Classical": [
         0,  0,  0,  1,  1,  0, -1, -1,
         0,  1,  2,  2,  2,  2,  1,  0,
    ],
    "Night Mode": [
        -2, -1,  0,  2,  4,  5,  4,  3,
         2,  0, -1, -2, -3, -4, -5, -6,
    ],
}