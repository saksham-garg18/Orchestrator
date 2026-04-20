from typing import Dict, Tuple

import librosa as lb
import numpy as np
from scipy.stats import pearsonr

PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Krumhansl-Schmuckler profiles
_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def _generate_key_profiles() -> Dict[str, np.ndarray]:
    profiles: Dict[str, np.ndarray] = {}
    for i in range(12):
        profiles[f"{PITCH_CLASSES[i]} major"] = np.roll(_MAJOR, i)
        profiles[f"{PITCH_CLASSES[i]} minor"] = np.roll(_MINOR, i)
    return {k: v / np.sum(v) for k, v in profiles.items()}


ALL_KEY_PROFILES: Dict[str, np.ndarray] = _generate_key_profiles()


def calculate_bpm(y: np.ndarray, sr: int) -> float:
    """Return BPM of the provided audio array."""
    onset_env = lb.onset.onset_strength(y=y, sr=sr)
    tempo, _ = lb.beat.beat_track(onset_envelope=onset_env, sr=sr)
    if isinstance(tempo, np.ndarray):
        tempo = tempo.item()
    return float(tempo)


def detect_key_krumhansl(audio_path: str) -> Tuple[str, float]:
    """Detect musical key using Krumhansl-Schmuckler correlation profiles.
    Returns (key_name, confidence) where confidence is the Pearson r value.
    """
    y, sr = lb.load(audio_path, mono=True)
    if y.size == 0:
        return "Unknown", 0.0

    chromagram = lb.feature.chroma_stft(y=y, sr=sr)
    profile = np.sum(chromagram, axis=1)

    if np.sum(profile) == 0:
        return "Unknown (No chromatic content)", 0.0

    profile = profile / np.sum(profile)

    best_key = "Unknown"
    best_corr = -2.0
    for key_name, key_profile in ALL_KEY_PROFILES.items():
        corr, _ = pearsonr(profile, key_profile)
        if np.isfinite(corr) and corr > best_corr:
            best_corr = corr
            best_key = key_name

    return best_key, float(best_corr)