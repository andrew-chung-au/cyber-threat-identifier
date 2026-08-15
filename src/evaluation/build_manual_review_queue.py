#!/usr/bin/env python3
"""Build a blinded, enriched manual-review queue from reranked judge disagreements."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.database.db_connection import get_connection
from src.evaluation.metrics import parse_expected_ids


MODEL_31 = "gemini-3.1-flash-lite"
MODEL_35 = "gemini-3.5-flash-lite"

DEFAULT_COMPARISON_PATH = Path(
    "data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv"
)
DEFAULT_JUDGE_31_PATH = Path(
    "data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv"
)
DEFAULT_JUDGE_35_PATH = Path(
    "data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv"
)
DEFAULT_DISAGREEMENTS_PATH = Path(
    "data/evaluation_reports/reranked/judge_disagreements.csv"
)
DEFAULT_OUTPUT_PATH = Path(
    "data/evaluation_reports/reranked/manual_review_queue.csv"
)

ANSWER_FIELDS = [
    "primary_attack_id",
    "alternative_attack_ids",
    "supporting_attack_ids",
    "answer_summary",
    "retrieval_grounding_note",
    "uncertainty_note",
    "review_required",
]


def _stable_answer_order(eval_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"manual-review-v1:{eval_id}".encode()).digest()
    if digest[0] % 2 == 0:
        return MODEL_31, MODEL_35
    return MODEL_35, MODEL_31


def _lookup_techniques(
    connection: Any,
    attack_ids: list[str],
) -> list[dict[str, Any]]:
    if not attack_ids:
        return []

    sql = """
        SELECT attack_id, name, description_clean, tactics, platforms, source_url
        FROM techniques
        WHERE attack_id = ANY(%s)
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, (attack_ids,))
        rows = cursor.fetchall()

    by_id = {
        row[0]: {
            "attack_id": row[0],
            "name": row[1],
            "description": row[2],
            "tactics": row[3] or [],
            "platforms": row[4] or [],
            "source_url": row[5],
        }
        for row in rows
    }

    return [
        by_id.get(
            attack_id,
            {
                "attack_id": attack_id,
                "name": "Not found in local ATT&CK database",
                "description": "",
                "tactics": [],
                "platforms": [],
                "source_url": "",
            },
        )
        for attack_id in attack_ids
    ]


def _answer_payload(row: pd.Series) -> dict[str, Any]:
    return {
        field: ("" if pd.isna(row[field]) else row[field])
        for field in ANSWER_FIELDS
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a static enriched queue for blinded manual review."
    )
    parser.add_argument("--comparison", type=Path, default=DEFAULT_COMPARISON_PATH)
    parser.add_argument("--judge-31", type=Path, default=DEFAULT_JUDGE_31_PATH)
    parser.add_argument("--judge-35", type=Path, default=DEFAULT_JUDGE_35_PATH)
    parser.add_argument("--disagreements", type=Path, default=DEFAULT_DISAGREEMENTS_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    for path in [args.comparison, args.judge_31, args.judge_35, args.disagreements]:
        if not path.exists():
            raise FileNotFoundError(f"Required input file not found: {path}")

    comparison = pd.read_csv(args.comparison)
    judge_31 = pd.read_csv(args.judge_31).set_index("eval_id")
    judge_35 = pd.read_csv(args.judge_35).set_index("eval_id")
    disagreements = pd.read_csv(args.disagreements)

    rows_by_eval_model = {
        (row.eval_id, row.model): row
        for row in comparison.itertuples(index=False)
    }

    queue_rows: list[dict[str, Any]] = []
    with get_connection() as connection:
        for disagreement in disagreements.itertuples(index=False):
            eval_id = disagreement.eval_id
            row_31 = rows_by_eval_model.get((eval_id, MODEL_31))
            row_35 = rows_by_eval_model.get((eval_id, MODEL_35))

            if row_31 is None or row_35 is None:
                raise ValueError(f"Missing one or both model outputs for {eval_id}.")
            if eval_id not in judge_31.index or eval_id not in judge_35.index:
                raise ValueError(f"Missing one or both judge outputs for {eval_id}.")

            row_31_series = pd.Series(row_31._asdict())
            row_35_series = pd.Series(row_35._asdict())
            model_a, model_b = _stable_answer_order(eval_id)
            answer_a = row_31_series if model_a == MODEL_31 else row_35_series
            answer_b = row_35_series if model_b == MODEL_35 else row_31_series

            expected_ids = parse_expected_ids(row_31_series["expected_attack_ids"])
            retrieved_31_ids = parse_expected_ids(row_31_series["retrieved_attack_ids"])
            retrieved_35_ids = parse_expected_ids(row_35_series["retrieved_attack_ids"])

            judge_31_row = judge_31.loc[eval_id]
            judge_35_row = judge_35.loc[eval_id]

            queue_rows.append(
                {
                    "eval_id": eval_id,
                    "query_text": row_31_series["query_text"],
                    "expected_attack_ids": ";".join(expected_ids),
                    "expected_techniques_json": json.dumps(
                        _lookup_techniques(connection, expected_ids)
                    ),
                    "retrieved_attack_ids_31": ";".join(retrieved_31_ids),
                    "retrieved_techniques_31_json": json.dumps(
                        _lookup_techniques(connection, retrieved_31_ids)
                    ),
                    "retrieved_attack_ids_35": ";".join(retrieved_35_ids),
                    "retrieved_techniques_35_json": json.dumps(
                        _lookup_techniques(connection, retrieved_35_ids)
                    ),
                    "model_a": model_a,
                    "answer_a_json": json.dumps(_answer_payload(answer_a)),
                    "model_b": model_b,
                    "answer_b_json": json.dumps(_answer_payload(answer_b)),
                    "winner_31": judge_31_row["winner"],
                    "reasoning_31": judge_31_row["reasoning"],
                    "confidence_31": judge_31_row["confidence"],
                    "winner_35": judge_35_row["winner"],
                    "reasoning_35": judge_35_row["reasoning"],
                    "confidence_35": judge_35_row["confidence"],
                    "retrieval_method": row_31_series.get("retrieval_method", ""),
                    "reranker_model": row_31_series.get("reranker_model", ""),
                    "candidate_k": row_31_series.get("candidate_k", ""),
                    "top_k": row_31_series.get("top_k", ""),
                }
            )

    queue = pd.DataFrame(queue_rows).sort_values("eval_id")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    queue.to_csv(args.output, index=False)

    print(f"[OK] Built {len(queue)} blinded manual-review cases.")
    print(f"  Output: {args.output}")
    print("  Context: expected labels and model-specific retrieved ATT&CK records.")


if __name__ == "__main__":
    main()
