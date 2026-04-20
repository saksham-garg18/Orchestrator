from dataclasses import dataclass, field
from typing import Dict


@dataclass
class MasteringConfig:
    target_lufs: float = -14.0
    target_peak_dbfs: float = -1.0
    compressor_threshold_db: float = -20.0
    compressor_ratio: float = 4.0
    compressor_attack_ms: float = 5.0
    compressor_release_ms: float = 150.0


@dataclass
class StereoStemConfig:
    """
    Pan positions per stem: -1.0 = hard left, 0.0 = center, 1.0 = hard right.
    """
    positions: Dict[str, float] = field(default_factory=lambda: {
        "vocals": 0.0,
        "drums": 0.0,
        "bass":   0.0,
        "other":  0.0,
    })