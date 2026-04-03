"""
Command-line entry points for MelodyStream SQL evaluation.

Examples:
  python -m melodystream_eval.cli sanity-check
  python -m melodystream_eval.cli run --model qwen --prompt improved
  python -m melodystream_eval.cli compare-matrix --output results/matrix.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from melodystream_eval.config import DEFAULT_DB_PATH, DEFAULT_EVAL_PATH, MODEL_QWEN_CODER
from melodystream_eval.env_loader import load_env_file
from melodystream_eval.paths import ensure_repo_on_path
from melodystream_eval.prompts import PromptVariant
from melodystream_eval.runner import run_evaluation, sanity_check_gold_sql


def _prompt_variant(name: str) -> PromptVariant:
    try:
        return PromptVariant(name.lower())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"prompt must be baseline or improved, got {name!r}") from exc


def cmd_sanity_check(_args: argparse.Namespace) -> int:
    """Ensure gold SQL in evaluation_data.json matches expected_result rows."""
    summary = sanity_check_gold_sql(
        db_path=Path(_args.db),
        eval_path=Path(_args.eval),
    )
    print(
        f"Sanity check: {summary.n_results_match}/{summary.n_cases} cases match expected_result "
        f"(executions ok: {summary.n_execution_ok}/{summary.n_cases})"
    )
    for c in summary.case_results:
        if not c.results_match:
            print(f"  FAIL idx={c.case_index} detail={c.match_detail!r} err={c.execution_error!r}")
    return 0 if summary.n_results_match == summary.n_cases else 1


def cmd_run(args: argparse.Namespace) -> int:
    """Run a single model + prompt combination."""
    load_env_file()
    ensure_repo_on_path()

    summary = run_evaluation(
        model=args.model,
        prompt_variant=_prompt_variant(args.prompt),
        db_path=Path(args.db),
        eval_path=Path(args.eval),
    )

    _print_summary(summary)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(summary.to_dict(), indent=2),
            encoding="utf-8",
        )
        print(f"Wrote {args.output}")
    return 0 if summary.n_results_match == summary.n_cases else 1


def cmd_compare_matrix(args: argparse.Namespace) -> int:
    """
    Run 2×2 matrix: baseline/improved × Llama 8B / Qwen2.5-Coder 32B.

    Intended for the assessment's model + prompt comparison table.
    """
    load_env_file()
    ensure_repo_on_path()

    models = [args.fast_model, args.coder_model]
    variants = [PromptVariant.BASELINE, PromptVariant.IMPROVED]
    matrix = []

    for variant in variants:
        for model in models:
            print(f"\n=== Running variant={variant.value} model={model} ===\n", flush=True)
            summary = run_evaluation(
                model=model,
                prompt_variant=variant,
                db_path=Path(args.db),
                eval_path=Path(args.eval),
            )
            matrix.append(summary.to_dict())
            _print_summary(summary)

    out_path = Path(args.output) if args.output else None
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(matrix, indent=2), encoding="utf-8")
        print(f"\nWrote matrix to {out_path}")

    # Matrix run completed successfully; imperfect accuracy is an expected outcome
    # for smaller models — inspect JSON / printed summaries for trade-offs.
    return 0


def _print_summary(summary) -> None:
    print(
        f"model={summary.model}\n"
        f"prompt={summary.prompt_variant}\n"
        f"functional_accuracy={summary.functional_accuracy:.2%} "
        f"({summary.n_results_match}/{summary.n_cases})\n"
        f"execution_rate={summary.execution_rate:.2%} "
        f"({summary.n_execution_ok}/{summary.n_cases})\n"
        f"mean_llm_latency_s={summary.mean_llm_latency_s:.3f}\n"
        f"tokens in/out (sum)={summary.total_prompt_tokens}/{summary.total_completion_tokens}"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="MelodyStream / Chinook text-to-SQL evaluation (Fireworks AI)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to Chinook.db")
    common.add_argument("--eval", default=str(DEFAULT_EVAL_PATH), help="Path to evaluation_data.json")

    s = sub.add_parser("sanity-check", parents=[common], help="Verify gold SQL vs expected_result")
    s.set_defaults(func=cmd_sanity_check)

    r = sub.add_parser("run", parents=[common], help="Single model + prompt eval")
    r.add_argument(
        "--model",
        default=MODEL_QWEN_CODER,
        help="Fireworks model id or alias (qwen, llama, coder, fast)",
    )
    r.add_argument(
        "--prompt",
        choices=[e.value for e in PromptVariant],
        default=PromptVariant.IMPROVED.value,
    )
    r.add_argument("--output", default=None, help="Optional JSON report path")
    r.set_defaults(func=cmd_run)

    m = sub.add_parser(
        "compare-matrix",
        parents=[common],
        help="Run baseline+improved × two models (full assessment matrix)",
    )
    m.add_argument(
        "--fast-model",
        default="llama",
        help="Alias or full id for the fast baseline model (default: llama / llama-v3p1-8b-instruct)",
    )
    m.add_argument(
        "--coder-model",
        default="qwen",
        help="Alias or full id for the code-specialized model (default: qwen / qwen2p5-coder-32b-instruct)",
    )
    m.add_argument(
        "--output",
        default="results/compare_matrix.json",
        help="Write all four runs as JSON array",
    )
    m.set_defaults(func=cmd_compare_matrix)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
