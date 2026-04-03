"""
Core evaluation loop: load benchmark JSON, call Fireworks, execute SQL, score results.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from melodystream_eval.config import (
    DEFAULT_DB_PATH,
    DEFAULT_EVAL_PATH,
    MODEL_ALIASES,
)
from melodystream_eval.fireworks_client import ChatCompletionResult, chat_completion, create_client
from melodystream_eval.paths import ensure_repo_on_path
from melodystream_eval.prompts import BuiltPrompt, PromptVariant, build_prompt
from melodystream_eval.result_matching import dataframe_to_row_dicts, results_match
from melodystream_eval.sql_postprocess import extract_sql, is_read_only_sql
from melodystream_eval.types_eval import CaseResult, EvalSummary

# Assessment `utils` — available after ensure_repo_on_path()
ensure_repo_on_path()
from utils import load_db, query_db  # noqa: E402


def resolve_model_id(model: str) -> str:
    """Map short aliases to full Fireworks model strings."""
    key = model.strip().lower()
    return MODEL_ALIASES.get(key, model)


def load_eval_cases(eval_path: Path) -> List[Dict[str, Any]]:
    with eval_path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("evaluation_data.json must be a JSON array")
    return data


def run_single_case(
    conn: sqlite3.Connection,
    case_index: int,
    case: Dict[str, Any],
    built: BuiltPrompt,
    model: str,
    client,
) -> CaseResult:
    """Generate SQL for one question and compare execution to expected_result."""
    question = case["question"]
    gold_sql = case["sql"]
    expected = case["expected_result"]

    llm: ChatCompletionResult = chat_completion(
        client,
        model=model,
        system=built.system,
        user=built.user,
    )

    raw = llm.text
    gen_sql = extract_sql(raw)
    if gen_sql and not is_read_only_sql(gen_sql):
        return CaseResult(
            case_index=case_index,
            question=question,
            gold_sql=gold_sql,
            generated_sql=gen_sql,
            execution_ok=False,
            execution_error="rejected_non_read_only_sql",
            results_match=False,
            match_detail="non_read_only",
            llm_latency_s=llm.latency_seconds,
            prompt_tokens=llm.prompt_tokens,
            completion_tokens=llm.completion_tokens,
            raw_model_output=raw,
        )

    if not gen_sql:
        return CaseResult(
            case_index=case_index,
            question=question,
            gold_sql=gold_sql,
            generated_sql=None,
            execution_ok=False,
            execution_error="no_sql_extracted",
            results_match=False,
            match_detail="no_sql",
            llm_latency_s=llm.latency_seconds,
            prompt_tokens=llm.prompt_tokens,
            completion_tokens=llm.completion_tokens,
            raw_model_output=raw,
        )

    try:
        df = query_db(conn, gen_sql, return_as_df=True)
        actual_rows = dataframe_to_row_dicts(df)
        ok, detail = results_match(expected, actual_rows)
        return CaseResult(
            case_index=case_index,
            question=question,
            gold_sql=gold_sql,
            generated_sql=gen_sql,
            execution_ok=True,
            execution_error=None,
            results_match=ok,
            match_detail=detail,
            llm_latency_s=llm.latency_seconds,
            prompt_tokens=llm.prompt_tokens,
            completion_tokens=llm.completion_tokens,
            raw_model_output=raw,
        )
    except Exception as exc:  # noqa: BLE001 — surface DB errors in eval report
        return CaseResult(
            case_index=case_index,
            question=question,
            gold_sql=gold_sql,
            generated_sql=gen_sql,
            execution_ok=False,
            execution_error=str(exc),
            results_match=False,
            match_detail="execution_error",
            llm_latency_s=llm.latency_seconds,
            prompt_tokens=llm.prompt_tokens,
            completion_tokens=llm.completion_tokens,
            raw_model_output=raw,
        )


def run_evaluation(
    model: str,
    prompt_variant: PromptVariant,
    db_path: Path = DEFAULT_DB_PATH,
    eval_path: Path = DEFAULT_EVAL_PATH,
    client=None,
) -> EvalSummary:
    """
    Execute the full benchmark: one model × one prompt strategy.

    Opens one DB connection for the whole run for efficiency.
    """
    ensure_repo_on_path()
    model_id = resolve_model_id(model)
    if client is None:
        client = create_client()

    cases = load_eval_cases(eval_path)
    conn = load_db(str(db_path))

    from melodystream_eval.schema_context import build_schema_markdown

    schema_md = build_schema_markdown(conn)

    results: List[CaseResult] = []
    total_pt = 0
    total_ct = 0
    latencies: List[float] = []

    for i, case in enumerate(cases):
        built = build_prompt(prompt_variant, case["question"], schema_md)
        cr = run_single_case(
            conn=conn,
            case_index=i,
            case=case,
            built=built,
            model=model_id,
            client=client,
        )
        results.append(cr)
        latencies.append(cr.llm_latency_s)
        if cr.prompt_tokens is not None:
            total_pt += cr.prompt_tokens
        if cr.completion_tokens is not None:
            total_ct += cr.completion_tokens

    conn.close()

    n_ok = sum(1 for r in results if r.execution_ok)
    n_match = sum(1 for r in results if r.results_match)
    mean_lat = sum(latencies) / len(latencies) if latencies else 0.0

    return EvalSummary(
        model=model_id,
        prompt_variant=prompt_variant.value,
        n_cases=len(cases),
        n_execution_ok=n_ok,
        n_results_match=n_match,
        mean_llm_latency_s=mean_lat,
        total_prompt_tokens=total_pt,
        total_completion_tokens=total_ct,
        case_results=results,
    )


def sanity_check_gold_sql(
    db_path: Path = DEFAULT_DB_PATH,
    eval_path: Path = DEFAULT_EVAL_PATH,
) -> EvalSummary:
    """
    Verify evaluation_data.json is internally consistent with Chinook.db.

    Does not call Fireworks — useful before burning API credits.
    """
    ensure_repo_on_path()
    cases = load_eval_cases(eval_path)
    conn = load_db(str(db_path))
    results: List[CaseResult] = []

    for i, case in enumerate(cases):
        gold_sql = case["sql"]
        expected = case["expected_result"]
        try:
            df = query_db(conn, gold_sql, return_as_df=True)
            actual_rows = dataframe_to_row_dicts(df)
            ok, detail = results_match(expected, actual_rows)
            results.append(
                CaseResult(
                    case_index=i,
                    question=case["question"],
                    gold_sql=gold_sql,
                    generated_sql=gold_sql,
                    execution_ok=True,
                    execution_error=None,
                    results_match=ok,
                    match_detail=detail,
                    llm_latency_s=0.0,
                    raw_model_output="",
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                CaseResult(
                    case_index=i,
                    question=case["question"],
                    gold_sql=gold_sql,
                    generated_sql=gold_sql,
                    execution_ok=False,
                    execution_error=str(exc),
                    results_match=False,
                    match_detail="gold_execution_error",
                    llm_latency_s=0.0,
                    raw_model_output="",
                )
            )

    conn.close()
    n_ok = sum(1 for r in results if r.execution_ok)
    n_match = sum(1 for r in results if r.results_match)

    return EvalSummary(
        model="sanity_check",
        prompt_variant="gold_sql_only",
        n_cases=len(cases),
        n_execution_ok=n_ok,
        n_results_match=n_match,
        mean_llm_latency_s=0.0,
        case_results=results,
    )
