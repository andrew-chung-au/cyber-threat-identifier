from __future__ import annotations

import pandas as pd


def parse_expected_ids(value: str) -> list[str]:
    if pd.isna(value) or not str(value).strip():
        return []
    return [item.strip() for item in str(value).split(";") if item.strip()]


def reciprocal_rank(retrieved_ids: list[str], expected_ids: set[str]) -> float:
    for rank, attack_id in enumerate(retrieved_ids, start=1):
        if attack_id in expected_ids:
            return 1.0 / rank
    return 0.0


def recall_at_k(retrieved_ids: list[str], expected_ids: set[str], k: int) -> float:
    if not expected_ids:
        return 0.0
    top_k = set(retrieved_ids[:k])
    hits = len(top_k.intersection(expected_ids))
    return hits / len(expected_ids)


def hit_at_k(retrieved_ids: list[str], expected_ids: set[str], k: int) -> int:
    top_k = set(retrieved_ids[:k])
    return int(bool(top_k.intersection(expected_ids)))