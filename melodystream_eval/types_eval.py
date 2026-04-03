"""
Typed structures for per-case evaluation records and aggregate summaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CaseResult:
    """Outcome for one benchmark row from evaluation_data.json."""

    case_index: int
    question: str
    gold_sql: str
    generated_sql: Optional[str]
    execution_ok: bool
    execution_error: Optional[str]
    results_match: bool
    match_detail: str
    llm_latency_s: float
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    raw_model_output: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_index": self.case_index,
            "question": self.question,
            "gold_sql": self.gold_sql,
            "generated_sql": self.generated_sql,
            "execution_ok": self.execution_ok,
            "execution_error": self.execution_error,
            "results_match": self.results_match,
            "match_detail": self.match_detail,
            "llm_latency_s": self.llm_latency_s,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "raw_model_output": self.raw_model_output,
        }


@dataclass
class EvalSummary:
    """Roll-up metrics across all cases."""

    model: str
    prompt_variant: str
    n_cases: int
    n_execution_ok: int
    n_results_match: int
    mean_llm_latency_s: float
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    case_results: List[CaseResult] = field(default_factory=list)

    @property
    def execution_rate(self) -> float:
        return self.n_execution_ok / self.n_cases if self.n_cases else 0.0

    @property
    def functional_accuracy(self) -> float:
        """Fraction of cases where SQL ran and matched expected_result multiset."""
        return self.n_results_match / self.n_cases if self.n_cases else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "prompt_variant": self.prompt_variant,
            "n_cases": self.n_cases,
            "n_execution_ok": self.n_execution_ok,
            "n_results_match": self.n_results_match,
            "execution_rate": self.execution_rate,
            "functional_accuracy": self.functional_accuracy,
            "mean_llm_latency_s": self.mean_llm_latency_s,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "cases": [c.to_dict() for c in self.case_results],
        }
