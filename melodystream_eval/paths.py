"""
Ensure the repository root is on sys.path so `utils` (assessment module) resolves.

Call `ensure_repo_on_path()` before any import that depends on root-level `utils.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def ensure_repo_on_path() -> None:
    """Insert REPO_ROOT at the front of sys.path if missing."""
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
