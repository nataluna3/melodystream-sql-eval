"""
Compare query result sets to benchmark `expected_result` rows.

Uses multiset (bag) equality so duplicate rows in evaluation_data.json (e.g.
playlists) are handled correctly. Floats are compared with a small tolerance to
absorb SQLite/pandas rounding differences.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from typing import Any, Dict, List, Mapping, Tuple


def normalize_cell(value: Any) -> Any:
    """
    Normalize a single cell for stable JSON hashing.

    - float: rounded stable representation via isclose-friendly quantize
    - int stays int
    - None stays None
    - other types: unchanged (strings, bools)
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return value
        # Round to mitigate 1e-16 drift while preserving business precision
        return round(value, 6)
    if isinstance(value, int):
        return value
    return value


def normalize_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Sort columns lexicographically so key order does not affect equality."""
    return {k: normalize_cell(row[k]) for k in sorted(row.keys())}


def row_fingerprint(row: Mapping[str, Any]) -> str:
    """Stable string key for multiset Counter entries."""
    normalized = normalize_row(row)
    return json.dumps(normalized, sort_keys=True, ensure_ascii=False)


def multiset_from_rows(rows: List[Mapping[str, Any]]) -> Counter:
    return Counter(row_fingerprint(r) for r in rows)


def results_match(
    expected: List[Mapping[str, Any]],
    actual: List[Mapping[str, Any]],
) -> Tuple[bool, str]:
    """
    Return (ok, reason). ok is True when multisets of normalized rows match.

    Also verifies column keys match per row fingerprint (implicit via JSON), but
    if shapes differ (missing columns), fingerprints differ → mismatch with detail.
    """
    exp_c = multiset_from_rows(list(expected))
    act_c = multiset_from_rows(list(actual))
    if exp_c == act_c:
        return True, "multiset_match"

    if len(expected) != len(actual):
        return False, f"row_count_mismatch expected={len(expected)} actual={len(actual)}"

    # Helpful diff: first fingerprint mismatch
    only_exp = exp_c - act_c
    only_act = act_c - exp_c
    if only_exp or only_act:
        detail = f"multiset_diff only_in_expected={dict(only_exp)} only_in_actual={dict(only_act)}"
        return False, detail[:500]

    return False, "unknown_mismatch"


def dataframe_to_row_dicts(df) -> List[Dict[str, Any]]:
    """Convert pandas DataFrame to list[dict] with native Python scalars."""
    # pandas may use numpy types; .to_dict records gives Python ints/floats often
    return df.to_dict(orient="records")
