from pathlib import Path
from typing import Dict

import numpy as np

from .io_utils import load_audio, save_audio, ensure_dir
from .analysis import calculate_bpm, detect_key_krumhansl
from .effects import (
    time_stretch_audio,
    pitch_shift_audio,
    apply_8d_effect,
    apply_stereo_pan,
)
from .mastering import reduce_noise_if_available, loudness_normalize
from .separation import separate_stems_demucs


# ──────────────────────────────────────────────────────────────────────────────
# Single-file pipeline
# ──────────────────────────────────────────────────────────────────────────────

def process_audio_file(
    input_path: str,
    output_dir: str,
    stretch_rate: float = 1.0,
    pitch_steps: float = 0.0,
    apply_noise_reduction: bool = False,
    apply_mastering: bool = False,
    enable_8d: bool = False,
    pan: float | None = None,
    mastering_target_lufs: float = -14.0,
    mastering_peak_dbfs: float = -1.0,
) -> dict:
    """
    Load → analyse → transform → save.

    Returns a dict with bpm, key, key_confidence, sample_rate, output_path.
    """
    out_dir = ensure_dir(output_dir)
    audio, sr = load_audio(input_path, mono=False)

    # Mono mix used for analysis only
    mono_ref = np.mean(audio, axis=0) if audio.ndim == 2 else audio

    bpm = calculate_bpm(mono_ref, sr)
    key, confidence = detect_key_krumhansl(input_path)

    processed = audio.copy()

    # ── 1. Time stretch ──────────────────────────────────────────────────────
    if stretch_rate != 1.0:
        if processed.ndim == 1:
            processed = time_stretch_audio(processed, stretch_rate)
        else:
            processed = np.vstack(
                [time_stretch_audio(ch, stretch_rate) for ch in processed]
            )

    # ── 2. Pitch shift ───────────────────────────────────────────────────────
    if pitch_steps != 0.0:
        if processed.ndim == 1:
            processed = pitch_shift_audio(processed, sr, pitch_steps)
        else:
            processed = np.vstack(
                [pitch_shift_audio(ch, sr, pitch_steps) for ch in processed]
            )

    # ── 3. Noise reduction ───────────────────────────────────────────────────
    if apply_noise_reduction:
        if processed.ndim == 1:
            processed = reduce_noise_if_available(processed, sr)
        else:
            processed = np.vstack(
                [reduce_noise_if_available(ch, sr) for ch in processed]
            )

    # ── 4. Loudness mastering ────────────────────────────────────────────────
    if apply_mastering:
        processed = loudness_normalize(
            processed, sr,
            target_lufs=mastering_target_lufs,
            target_peak_dbfs=mastering_peak_dbfs,
        )

    # ── 5. 8D effect ─────────────────────────────────────────────────────────
    if enable_8d:
        processed = apply_8d_effect(processed, sr)

    # ── 6. Manual stereo pan ─────────────────────────────────────────────────
    if pan is not None:
        processed = apply_stereo_pan(processed, pan)

    output_path = Path(out_dir) / "processed.wav"
    save_audio(output_path, processed, sr)

    return {
        "bpm": bpm,
        "key": key,
        "key_confidence": confidence,
        "sample_rate": sr,
        "output_path": str(output_path),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Stem spatial mix pipeline
# ──────────────────────────────────────────────────────────────────────────────

def process_stems_with_positions(
    stems_dir: str,
    output_dir: str,
    positions: Dict[str, float],
    apply_8d: bool = False,
    eight_d_depth: float = 0.5,
) -> str:
    """
    Load each stem from stems_dir, pan to its position, optionally add a
    light 8D motion pass, sum everything, and save to output_dir/stem_mix.wav.

    positions: {"vocals": 0.0, "drums": -0.3, "bass": 0.2, "other": 0.6}
    """
    stems_dir = Path(stems_dir)
    out_dir = ensure_dir(output_dir)

    mix: np.ndarray | None = None
    sr_final: int | None = None

    for stem_name, pan_value in positions.items():
        # Accept wav, mp3, flac …
        candidates = (
            list(stems_dir.glob(f"{stem_name}.wav"))
            + list(stems_dir.glob(f"{stem_name}.mp3"))
            + list(stems_dir.glob(f"{stem_name}.flac"))
        )
        if not candidates:
            print(f"[warn] stem '{stem_name}' not found in {stems_dir}, skipping.")
            continue

        audio, sr = load_audio(candidates[0], mono=False)
        stem_audio = apply_stereo_pan(audio, pan_value)

        if apply_8d:
            stem_audio = apply_8d_effect(stem_audio, sr, depth=eight_d_depth)

        if mix is None:
            mix = stem_audio
            sr_final = sr
        else:
            min_len = min(mix.shape[1], stem_audio.shape[1])
            mix = mix[:, :min_len] + stem_audio[:, :min_len]

    if mix is None or sr_final is None:
        raise FileNotFoundError(
            f"No matching stems found in {stems_dir}. "
            "Check that Demucs separation has run."
        )

    # Prevent clipping after summing stems
    peak = np.max(np.abs(mix))
    if peak > 1.0:
        mix /= peak

    output_path = out_dir / "stem_mix.wav"
    save_audio(output_path, mix, sr_final)
    return str(output_path)


def separate_and_render_stems(
    input_path: str,
    output_dir: str,
    positions: Dict[str, float],
    model: str = "htdemucs",
    apply_8d: bool = False,
    eight_d_depth: float = 0.5,
) -> dict:
    """
    End-to-end: separate with Demucs → pan each stem → optional 8D pass → mix.

    Returns {"stems_dir": ..., "mix_path": ...}
    """
    stems_dir = separate_stems_demucs(input_path, output_dir, model=model)
    active_stems = {k: v for k, v in positions.items() if k in selected_stems}
    mix_path = process_stems_with_positions(
        str(stems_dir),
        output_dir,
        positions,
        apply_8d=apply_8d,
        eight_d_depth=eight_d_depth,
    )
    return {"stems_dir": str(stems_dir), "mix_path": mix_path}