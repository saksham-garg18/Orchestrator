from pathlib import Path
import subprocess
import sys


def separate_stems_demucs(
    input_path: str,
    output_dir: str,
    model: str = "htdemucs",
    mp3: bool = False,
    mp3_bitrate: int = 320,
) -> Path:
    """
    Run Demucs stem separation on input_path and return the directory
    containing the separated stems.

    Parameters
    ----------
    input_path  : path to source audio file
    output_dir  : root output folder
    model       : demucs model name ('htdemucs', 'mdx_extra_q', etc.)
    mp3         : export stems as mp3 instead of wav
    mp3_bitrate : bitrate when mp3=True

    Returns
    -------
    Path to the stems directory, e.g. output_dir/htdemucs/<track_name>/
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # Run Demucs through a local wrapper that patches torchaudio loading.
    cmd = [sys.executable, "-m", "core.demucs_runner", "-n", model, input_path, "-o", str(output)]
    if mp3:
        cmd += ["--mp3", "--mp3-bitrate", str(mp3_bitrate)]

    subprocess.run(cmd, check=True)

    return output / model / Path(input_path).stem