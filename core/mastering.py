import numpy as np
import pyloudnorm as pyln


def reduce_noise_if_available(y: np.ndarray, sr: int) -> np.ndarray:
    """Apply noisereduce if the package is installed, otherwise return unchanged."""
    try:
        import noisereduce as nr
        return nr.reduce_noise(y=y, sr=sr)
    except Exception:
        return y


def loudness_normalize(
    y: np.ndarray,
    sr: int,
    target_lufs: float = -14.0,
    target_peak_dbfs: float = -1.0,
    compressor_threshold_db: float = -20.0,
    compressor_ratio: float = 4.0,
    compressor_attack_ms: float = 5.0,
    compressor_release_ms: float = 150.0,
) -> np.ndarray:
    """
    Measure LRA, apply dynamic range compression if needed, then
    normalize integrated loudness to target_lufs with a peak ceiling.

    Matches the notebook logic:
      - LRA outside 7-16 LU  → simple LUFS gain
      - LRA inside  7-16 LU  → compressor + LUFS renormalize
      - Safety peak limiter always applied last
    """
    mono = y if y.ndim == 1 else np.mean(y, axis=0)
    meter = pyln.Meter(sr)

    og_lufs = meter.integrated_loudness(mono)
    og_lra  = meter.loudness_range(mono)
    target_peak_linear = 10 ** (target_peak_dbfs / 20.0)

    processed = mono.copy().astype(np.float32)

    if og_lra < 7.0 or og_lra > 16.0:
        gain_linear = 10 ** ((target_lufs - og_lufs) / 20.0)
        processed = processed * gain_linear
    else:
        try:
            from pedalboard import Pedalboard, Compressor, Limiter, Gain
            board = Pedalboard([
                Compressor(
                    threshold_db=compressor_threshold_db,
                    ratio=compressor_ratio,
                    attack_ms=compressor_attack_ms,
                    release_ms=compressor_release_ms,
                ),
                Limiter(threshold_db=target_peak_dbfs, release_ms=50.0),
            ])
            processed = board(processed, sample_rate=sr)
            compressed_lufs = meter.integrated_loudness(processed)
            gain_board = Pedalboard([Gain(gain_db=target_lufs - compressed_lufs)])
            processed = gain_board(processed, sample_rate=sr)
        except Exception:
            # Fallback: plain gain normalize if pedalboard unavailable
            gain_linear = 10 ** ((target_lufs - og_lufs) / 20.0)
            processed = processed * gain_linear

    # Safety peak ceiling
    peak = np.max(np.abs(processed))
    if peak > target_peak_linear and peak > 0:
        processed = processed * (target_peak_linear / peak)

    return processed.astype(np.float32)