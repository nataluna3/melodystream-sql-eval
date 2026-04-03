"""
Lightweight .env loader so we do not require extra dependencies beyond pyproject.toml.

Loads KEY=value pairs from a .env file at the repository root into os.environ
without overwriting variables already set in the shell (12-factor friendly).
"""

from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: Path | None = None) -> None:
    """
    Parse a simple dotenv file and call os.environ.setdefault for each key.

    - Ignores blank lines and lines starting with '#'
    - Strips optional single/double quotes around values
    - Does not expand variable references inside values
    """
    env_path = path or Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)
