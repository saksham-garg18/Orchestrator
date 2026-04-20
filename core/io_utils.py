from pathlib import Path
from typing import Tuple

import librosa as lb
import numpy as np
import soundfile as sf


def ensure_dir(path: str | Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_audio(
    path: str | Path,
    sr: int | None = None,
    mono: bool = False,
) -> Tuple[np.ndarray, int]:
    """Load audio with librosa. Returns (audio_array, sample_rate).
    If mono=False and the file is stereo, returns shape (2, N).
    """
    audio, sample_rate = lb.load(str(path), sr=sr, mono=mono)
    return audio, sample_rate


def save_audio(path: str | Path, audio: np.ndarray, sr: int) -> Path:
    """Save audio to a wav file. Handles mono (1-D) and stereo (2, N)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # soundfile expects (N, channels) for stereo
    if audio.ndim == 2 and audio.shape[0] == 2:
        audio = audio.T
    sf.write(str(path), audio, sr)
    return path