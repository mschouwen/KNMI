from pathlib import Path
import os
from datetime import datetime

# Single source of truth for KNMI input/output folder.
# Optional override: set KNMI_DATA_DIR environment variable.
DATA_DIR = Path(os.getenv("KNMI_DATA_DIR", r"d:\temp"))

# Shared date range used by calc_tci.py
TCI_START_DATE = datetime(2003, 1, 1)
TCI_END_DATE = datetime(2026, 1, 1)


def data_path(*parts: str) -> Path:
    return DATA_DIR.joinpath(*parts)
