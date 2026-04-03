"""
Build human-readable schema context for text-to-SQL prompts.

Introspects the live SQLite database using the assessment's `utils` module so
the prompt always matches the actual Chinook instance (including any drift if
the DB file is regenerated).
"""

from __future__ import annotations

import sqlite3
from typing import Dict, List

# Assessment-provided helpers (must not be edited as part of this deliverable)
from utils import get_schema


def _format_column_line(col: Dict[str, str | int | None]) -> str:
    """Single column description for markdown-style schema blocks."""
    name = col["name"]
    ctype = col["type"] or "ANY"
    parts: List[str] = [f"`{name}` {ctype}"]
    if col.get("pk"):
        parts.append("PRIMARY KEY")
    if col.get("notnull"):
        parts.append("NOT NULL")
    if col.get("dflt_value") is not None:
        parts.append(f"DEFAULT {col['dflt_value']}")
    return "  - " + ", ".join(parts)


def build_schema_markdown(conn: sqlite3.Connection) -> str:
    """
    Produce a stable, model-friendly schema summary sorted by table name.

    Includes every user table from sqlite_master; skips internal sqlite_% tables.
    """
    schema = get_schema(conn)
    lines: List[str] = [
        "### Database schema (SQLite — Chinook)",
        "",
        "Use only these tables and columns. Prefer explicit JOINs over guessing names.",
        "",
    ]
    for table in sorted(schema.keys()):
        cols = schema[table]
        lines.append(f"**{table}** ({len(cols)} columns)")
        for col in cols:
            lines.append(_format_column_line(col))
        lines.append("")
    return "\n".join(lines).rstrip()


def build_compact_schema_ddl(conn: sqlite3.Connection) -> str:
    """
    Optional compact form: pseudo-DDL one-liners per table (easier for some models).
    """
    schema = get_schema(conn)
    chunks: List[str] = []
    for table in sorted(schema.keys()):
        col_defs = []
        for col in schema[table]:
            col_defs.append(f"{col['name']} {col['type'] or 'ANY'}")
        chunks.append(f"{table}({', '.join(col_defs)})")
    return "Tables: " + "; ".join(chunks)
