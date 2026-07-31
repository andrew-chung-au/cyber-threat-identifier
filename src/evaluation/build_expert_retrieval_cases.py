#!/usr/bin/env python3

from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd


DATASET_DIR = Path("data/external_inspection/mitre-ttp-mapping/datasets/expert")
DEV_PATH = DATASET_DIR / "expert_dev.tsv"
TEST_PATH = DATASET_DIR / "expert_test.tsv"
OUTPUT_PATH = Path("data/eval/expert_retrieval_cases.csv")


def parse_labels(value: str) -> list[str]:
    if pd.isna(value):
        raise ValueError("labels value is missing")

    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError) as exc:
        raise ValueError(f"Could not parse labels: {value!r}") from exc

    if not isinstance(parsed, list):
        raise ValueError(f"labels is not a list: {value!r}")

    cleaned = [str(x).strip() for x in parsed if str(x).strip()]
    if not cleaned:
        raise ValueError(f"labels list is empty: {value!r}")

    return cleaned


def build_split_df(path: Path, split_name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    df = pd.read_csv(path, sep="\t", encoding="utf-8")

    required_cols = {"text1", "labels"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

    df = df.copy()
    df["upstream_split"] = split_name
    df["upstream_row_index"] = df.index
    df["parsed_labels"] = df["labels"].apply(parse_labels)
    df["expected_attack_ids"] = df["parsed_labels"].apply(lambda xs: ";".join(xs))
    df["word_count"] = df["text1"].fillna("").apply(lambda x: len(str(x).split()))
    df["eval_id"] = df["upstream_split"] + "-" + df["upstream_row_index"].map(lambda x: f"{x:04d}")

    return df[
        [
            "eval_id",
            "upstream_split",
            "upstream_row_index",
            "text1",
            "expected_attack_ids",
            "word_count",
        ]
    ]


def main() -> None:
    dev_df = build_split_df(DEV_PATH, "dev")
    test_df = build_split_df(TEST_PATH, "test")

    out_df = pd.concat([dev_df, test_df], ignore_index=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    print(f"Wrote {len(out_df)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()