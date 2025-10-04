# Common utilities for resolution combos (defaults + JSON loader)
import os
import json
from typing import List, Tuple

# Defaults (used when JSON is missing)
DEFAULT_COMBOS: List[Tuple[int, int]] = [
    (1024, 1024), (1088, 1088), (1152, 1152), (1216, 1216),
    (1280, 1280), (1344, 1344), (1408, 1408), (1472, 1472),
    (1536, 1536), (1600, 1600), (1664, 1664), (1728, 1728),
    (1792, 1792), (1856, 1856), (1920, 1920), (1984, 1984),
    (2048, 2048),
    (896, 1152), (832, 1216), (768, 1280), (704, 1344),
    (640, 1408), (576, 1472), (512, 1536),
    (1408, 1664), (1344, 1728), (1280, 1792), (1216, 1856),
    (1152, 1920), (1088, 1984), (1024, 2048),
    (1920, 2048), (1856, 2048), (1792, 2048), (1728, 2048),
    (1664, 2048), (1600, 2048), (1536, 2048),
    (1152, 896), (1216, 832), (1280, 768), (1344, 704),
    (1408, 640), (1472, 576), (1536, 512),
    (1664, 1408), (1728, 1344), (1792, 1280), (1856, 1216),
    (1920, 1152), (1984, 1088), (2048, 1024),
    (2048, 1920), (2048, 1856), (2048, 1792), (2048, 1728),
    (2048, 1664), (2048, 1600), (2048, 1536),
]

_CONFIG_DIR = "config"
_CONFIG_NAME = "resolution_combos.json"

def resolution_config_path() -> str:
    """Absolute path to config/resolution_combos.json (relative to extension root)."""
    base = os.path.dirname(__file__)  # extension root (this file lives here)
    return os.path.join(base, _CONFIG_DIR, _CONFIG_NAME)

def _validate_pairs(data) -> List[Tuple[int, int]]:
    if not (
        isinstance(data, list)
        and len(data) > 0
        and all(
            isinstance(x, (list, tuple)) and len(x) == 2
            and isinstance(x[0], int) and isinstance(x[1], int)
            for x in data
        )
    ):
        raise ValueError(f"{_CONFIG_NAME} must be a non-empty list of [width, height] integer pairs.")
    return [tuple(x) for x in data]  # type: ignore

def load_resolution_combos() -> List[Tuple[int, int]]:
    """
    Load combos from JSON; raise on parse/format errors; fallback to DEFAULT_COMBOS when file is missing.
    (Exceptions bubble to UI; do not print duplicate logs.)
    """
    path = resolution_config_path()
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)  # may raise JSONDecodeError
        return _validate_pairs(data)
    return DEFAULT_COMBOS

def get_resolution_config_mtime() -> float:
    """Return mtime for fingerprinting; 0 if missing or error."""
    path = resolution_config_path()
    try:
        return os.path.getmtime(path) if os.path.isfile(path) else 0.0
    except Exception:
        return 0.0