"""
Prompt templates for baseline vs engineered text-to-SQL.

Few-shot examples are intentionally *not* taken from evaluation_data.json to avoid
verbatim leakage; they mirror common Chinook patterns (joins, aggregates).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PromptVariant(str, Enum):
    """Which prompt strategy to evaluate."""

    BASELINE = "baseline"
    IMPROVED = "improved"


# ---------------------------------------------------------------------------
# Few-shot examples (held out from the official 10-case eval set)
# ---------------------------------------------------------------------------
FEW_SHOT_BLOCK = """
### Examples (SQLite, Chinook-style)

**Q:** How many albums does each artist have? Sort by album count descending.
**SQL:**
```sql
SELECT ar.Name AS ArtistName, COUNT(al.AlbumId) AS AlbumCount
FROM Artist ar
JOIN Album al ON ar.ArtistId = al.ArtistId
GROUP BY ar.ArtistId, ar.Name
ORDER BY AlbumCount DESC;
```

**Q:** What is the total invoice amount for customer id 1?
**SQL:**
```sql
SELECT SUM(Total) AS TotalSpend
FROM Invoice
WHERE CustomerId = 1;
```

**Q:** List track names and genres for playlist id 5.
**SQL:**
```sql
SELECT t.Name AS TrackName, g.Name AS GenreName
FROM PlaylistTrack pt
JOIN Track t ON pt.TrackId = t.TrackId
JOIN Genre g ON t.GenreId = g.GenreId
WHERE pt.PlaylistId = 5;
```
""".strip()


SYSTEM_BASELINE = (
    "You are a SQL assistant. Output a single SQLite query that answers the question. "
    "Return only the SQL inside a fenced ```sql code block."
)


SYSTEM_IMPROVED = """You are an expert analytics engineer for MelodyStream.

Rules:
- Generate exactly one read-only SQLite SELECT (or WITH ... SELECT) query.
- Use only tables and columns described in the schema below.
- Prefer explicit JOINs and meaningful column aliases.
- For dates stored as TEXT, use SQLite date functions such as strftime.
- If the question implies ordering or "top N", include ORDER BY and LIMIT as needed.
- Output the SQL only inside a single fenced ```sql code block — no prose outside the fence.
"""


@dataclass(frozen=True)
class BuiltPrompt:
    """Chat messages ready for the OpenAI-compatible API."""

    system: str
    user: str


def build_baseline_user_message(question: str) -> str:
    """Original MelodyStream POC prompt (no schema, no examples)."""
    return f"Convert this question to SQL:\n{question}"


def build_improved_user_message(question: str, schema_markdown: str) -> str:
    """Schema-grounded prompt with few-shot demonstrations."""
    parts = [
        schema_markdown.strip(),
        "",
        FEW_SHOT_BLOCK,
        "",
        "### Task",
        f"Question: {question.strip()}",
        "",
        "Respond with ```sql ... ``` only.",
    ]
    return "\n".join(parts)


def build_prompt(
    variant: PromptVariant,
    question: str,
    schema_markdown: str,
) -> BuiltPrompt:
    """
    Construct system + user messages for the given strategy.

    For BASELINE, schema_markdown is ignored (keeps parity with the customer's POC).
    """
    if variant == PromptVariant.BASELINE:
        return BuiltPrompt(
            system=SYSTEM_BASELINE,
            user=build_baseline_user_message(question),
        )
    return BuiltPrompt(
        system=SYSTEM_IMPROVED,
        user=build_improved_user_message(question, schema_markdown),
    )
