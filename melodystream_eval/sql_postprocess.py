"""
Extract executable SQL from model output and apply light normalization.

Models often wrap queries in markdown fences or add trailing commentary; this
module keeps evaluation focused on the first plausible SQL statement.
"""

from __future__ import annotations

import re
from typing import Optional


_FENCE_RE = re.compile(
    r"```(?:sql)?\s*([\s\S]*?)```",
    re.IGNORECASE,
)


def extract_sql(raw_text: str) -> Optional[str]:
    """
    Return the first SQL-looking string from model output.

    Priority:
    1. First fenced ``` or ```sql block
    2. If the trimmed text itself starts with SELECT/WITH (case-insensitive), use it
    """
    if not raw_text or not raw_text.strip():
        return None

    text = raw_text.strip()
    m = _FENCE_RE.search(text)
    if m:
        candidate = m.group(1).strip()
        if candidate:
            return _strip_trailing_semicolon(candidate)

    # Some models omit fences; accept leading SELECT/WITH
    upper = text.lstrip().upper()
    if upper.startswith("SELECT") or upper.startswith("WITH"):
        return _strip_trailing_semicolon(text)

    return None


def _strip_trailing_semicolon(sql: str) -> str:
    s = sql.rstrip()
    if s.endswith(";"):
        s = s[:-1].rstrip()
    return s


def is_read_only_sql(sql: str) -> bool:
    """
    Cheap guardrail: reject obvious DDL/DML (not a substitute for DB permissions).

    Allows SELECT and WITH ... SELECT patterns only at the start (after whitespace).
    """
    s = sql.lstrip().upper()
    return s.startswith("SELECT") or s.startswith("WITH")
