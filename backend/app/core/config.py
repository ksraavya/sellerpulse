"""Lightweight path configuration.

The seller data directory is resolved from this file's location so it does
not depend on the process working directory. Set SELLER_DATA_DIR to override it.
"""

import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SELLER_DATA_DIR = BACKEND_ROOT / "data" / "sellers"


def get_seller_data_dir() -> Path:
    """Return the directory that holds one JSON file per seller."""
    override = os.getenv("SELLER_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_SELLER_DATA_DIR
