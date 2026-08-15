#!/usr/bin/env python3
"""Compare vector-only vs reranked retrieval for the same evaluation cases."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_VECTOR_CSV = Path(
    "data/evaluation_reports/expert_llm_comparison_v1.csv"
)
DEFAULT_RERANKED_CSV = Path(
    "data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv"
)
DEFAULT_OUTPUT = Path(
    "data/evaluation_reports/retrieval_diff_summary.csv"
)


def parse_ids(value: str) -> list[str]:
    if pd.isna(value) or not str(value).strip():
        return []
    return [item.strip() for item in str(value).split(";") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare vector-only vs reranked retrieval for the same eval_ids."
    )
    parser.add_argument("--vector", type=Path, default=DEFAULT_VECTOR_CSV)
    parser.add_argument("--reranked", type=Path, default=DEFAULT_RERANKED_CSV)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.vector.exists():
        raise FileNotFoundError(f"Vector comparison CSV not found: {args.vector}")
    if not args.reranked.exists():
        raise FileNotFoundError(f"Reranked comparison CSV not found: {args.reranked}")

    vector = pd.read_csv(args.vector)
    reranked = pd.read_csv(args.reranked)

    vector = vector[vector["model"] == "gemini-3.1-flash-lite"].copy()
    reranked = reranked[reranked["model"] == "gemini-3.1-flash-lite"].copy()

    vector = vector.set_index("eval_id")
    reranked = reranked.set_index("eval_id")

    common_ids = vector.index.intersection(reranked.index)

    if len(common_ids) == 0:
        raise ValueError("No common eval_ids found between vector and reranked CSVs.")

    vector = vector.loc[common_ids].reset_index()
    reranked = reranked.loc[common_ids].reset_index()

    def _hits(row: pd.Series) -> tuple[int, int, int]:
        expected = set(parse_ids(row["expected_attack_ids"]))
        retrieved = set(parse_ids(row["retrieved_attack_ids"]))
        hits = len(expected & retrieved)
        return len(expected), hits, len(retrieved)

    vector_expected = []
    vector_hits = []
    vector_retrieved = []
    reranked_expected = []
    reranked_hits = []
    reranked_retrieved = []

    for _, row in vector.iterrows():
        exp, hits, ret = _hits(row)
        vector_expected.append(exp)
        vector_hits.append(hits)
        vector_retrieved.append(ret)

    for _, row in reranked.iterrows():
        exp, hits, ret = _hits(row)
        reranked_expected.append(exp)
        reranked_hits.append(hits)
        reranked_retrieved.append(ret)

    diff = pd.DataFrame(
        {
            "eval_id": common_ids,
            "expected_count": vector_expected,
            "vector_hits": vector_hits,
            "reranked_hits": reranked_hits,
            "vector_retrieved_count": vector_retrieved,
            "reranked_retrieved_count": reranked_retrieved,
            "vector_retrieved_ids": vector["retrieved_attack_ids"],
            "reranked_retrieved_ids": reranked["retrieved_attack_ids"],
        }
    )

    diff["hits_diff"] = diff["reranked_hits"] - diff["vector_hits"]
    diff["retrieved_diff"] = (
        diff["reranked_retrieved_count"] - diff["vector_retrieved_count"]
    )

    diff["reranking_helped"] = diff["hits_diff"] > 0
    diff["reranking_hurt"] = diff["hits_diff"] < 0
    diff["reranking_neutral"] = diff["hits_diff"] == 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    diff.to_csv(args.output, index=False)

    print(f"[OK] Retrieval comparison summary: {len(diff)} cases")
    print(f"  Output: {args.output}")
    print()
    print("Hit improvement from reranking:")
    print(f"  Improved:   {(diff['hits_diff'] > 0).sum()}")
    print(f"  Unchanged:  {(diff['hits_diff'] == 0).sum()}")
    print(f"  Worse:      {(diff['hits_diff'] < 0).sum()}")
    print()
    print("Example cases where reranking improved hits:")
    improved = diff[diff["hits_diff"] > 0].sort_values("hits_diff", ascending=False)
    if not improved.empty:
        for _, row in improved.head(5).iterrows():
            print(
                f"  {row['eval_id']}: "
                f"vector hits={row['vector_hits']}, reranked hits={row['reranked_hits']}"
            )
    else:
        print("  (none)")


if __name__ == "__main__":
    main()