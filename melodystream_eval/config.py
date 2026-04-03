"""
Central configuration for paths, model identifiers, and Fireworks endpoints.

Model IDs use the OpenAI-compatible `model` string returned by your account’s
`client.models.list()` (typically `accounts/fireworks/models/...`).

NOTE: `qwen2p5-coder-32b-instruct` and `llama-v3p1-8b-instruct` are not available
serverless on every account; this project defaults to two serverless models that
preserve the same evaluation story—**strong/capable** vs **faster/lighter**.
"""

from __future__ import annotations

from pathlib import Path

# Repository root (parent of this package)
REPO_ROOT = Path(__file__).resolve().parent.parent

# Default artifacts (provided by assessment repo; do not rename)
DEFAULT_DB_PATH = REPO_ROOT / "Chinook.db"
DEFAULT_EVAL_PATH = REPO_ROOT / "evaluation_data.json"

# Fireworks OpenAI-compatible API
FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"

# ---------------------------------------------------------------------------
# Serverless models (verified against this account’s model list + chat smoke test)
# ---------------------------------------------------------------------------
# Strong general + code/reasoning model (higher quality, typically higher latency/cost).
MODEL_CAPABLE = "accounts/fireworks/models/deepseek-v3p2"

# Lighter instruct MoE (good throughput; use as “fast baseline” in the 2×2 matrix).
MODEL_FAST = "accounts/fireworks/models/mixtral-8x22b-instruct"

# Backward-compatible names used elsewhere in the repo / take-home brief.
MODEL_QWEN_CODER = MODEL_CAPABLE
MODEL_LLAMA_FAST = MODEL_FAST

MODEL_ALIASES = {
    # Preferred aliases for this deployment
    "capable": MODEL_CAPABLE,
    "strong": MODEL_CAPABLE,
    "deepseek": MODEL_CAPABLE,
    "deepseek-v3p2": MODEL_CAPABLE,
    "mixtral": MODEL_FAST,
    "mixtral-8x22b-instruct": MODEL_FAST,
    # Original take-home aliases → current serverless substitutions
    "qwen": MODEL_CAPABLE,
    "coder": MODEL_CAPABLE,
    "qwen2p5-coder-32b-instruct": MODEL_CAPABLE,
    "llama": MODEL_FAST,
    "fast": MODEL_FAST,
    "llama-v3p1-8b-instruct": MODEL_FAST,
    # Full ids (pass-through)
    MODEL_CAPABLE: MODEL_CAPABLE,
    MODEL_FAST: MODEL_FAST,
}


# Generation defaults (conservative for reproducibility in evals)
DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 1024
