"""Demucs entrypoint with torchaudio.load patched to soundfile.

This avoids torchcodec runtime issues on environments where torchaudio's
new default decoder backend is unavailable.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchaudio as ta


# Demucs only needs ta.load for reading input tracks.
def _load_with_soundfile(path: str, *args, **kwargs):
    audio, sr = sf.read(path, dtype="float32", always_2d=True)
    # soundfile returns [time, channels]; torchaudio expects [channels, time].
    waveform = torch.from_numpy(np.ascontiguousarray(audio.T))
    return waveform, sr


def _save_with_soundfile(path, waveform, sample_rate: int, *args, **kwargs):
    out_path = Path(path)
    audio = waveform.detach().cpu().numpy()
    if audio.ndim == 1:
        audio = audio[:, None]
    elif audio.ndim == 2:
        # torchaudio uses [channels, time]; soundfile expects [time, channels].
        audio = audio.T

    bits_per_sample = kwargs.get("bits_per_sample", 16)
    encoding = kwargs.get("encoding")

    if out_path.suffix.lower() == ".wav":
        if encoding == "PCM_F":
            subtype = "FLOAT"
        else:
            subtype = {16: "PCM_16", 24: "PCM_24", 32: "PCM_32"}.get(bits_per_sample, "PCM_16")
        sf.write(out_path, audio, sample_rate, subtype=subtype)
        return

    if out_path.suffix.lower() == ".flac":
        subtype = {16: "PCM_16", 24: "PCM_24"}.get(bits_per_sample, "PCM_16")
        sf.write(out_path, audio, sample_rate, subtype=subtype)
        return

    raise ValueError(f"Unsupported audio extension for patched save: {out_path.suffix}")


def main() -> None:
    ta.load = _load_with_soundfile
    ta.save = _save_with_soundfile
    from demucs.separate import main as demucs_main

    demucs_main()


if __name__ == "__main__":
    main()
