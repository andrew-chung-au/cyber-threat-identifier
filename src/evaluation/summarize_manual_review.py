#!/usr/bin/env python3
"""Summarise manual-review outcomes for model-selection evaluation."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


MODEL_31 = "gemini-3.1-flash-lite"
MODEL_35 = "gemini-3.5-flash-lite"

DEFAULT_RESULTS_PATH = Path(
    "data/evaluation_reports/reranked/manual_review_results.csv"
)


def _count_judge_agreement(
    decisive_results: pd.DataFrame,
    column: str,
) -> int:
    return int(
        decisive_results[column]
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("true")
        .sum()
    )


def _failure_mode_counts(results: pd.DataFrame) -> pd.Series:
    values = (
        results["failure_modes"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    modes: list[str] = []

    for value in values:
        if not value:
            continue

        modes.extend(
            mode.strip()
            for mode in value.split(" | ")
            if mode.strip()
        )

    if not modes:
        return pd.Series(dtype="int64")

    return pd.Series(modes).value_counts()


def _recommendation(
    wins_31: int,
    wins_35: int,
    ties: int,
    decisive_count: int,
) -> str:
    if decisive_count == 0:
        return (
            "No model-selection recommendation: all reviewed cases were ties. "
            "Use latency/cost and collect additional evidence."
        )

    win_margin = abs(wins_31 - wins_35)
    leader = MODEL_31 if wins_31 > wins_35 else MODEL_35
    leader_wins = max(wins_31, wins_35)
    leader_rate = leader_wins / decisive_count
    tie_rate = ties / (decisive_count + ties)

    if wins_31 == wins_35:
        return (
            "Human wins are tied. Prefer the lower-latency or lower-cost model, "
            "and document practical quality parity."
        )

    if leader_rate >= 0.55 and win_margin >= 3:
        return (
            f"Select {leader}. It won {leader_wins}/{decisive_count} decisive "
            f"human comparisons ({leader_rate:.1%}) with a {win_margin}-case margin."
        )

    return (
        f"{leader} has a narrow directional lead ({leader_wins}/{decisive_count} "
        f"decisive wins; margin {win_margin}). Do not claim a decisive quality "
        f"advantage; use latency/cost as the tiebreaker and report the {tie_rate:.1%} tie rate."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarise manual-review results for model selection."
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=DEFAULT_RESULTS_PATH,
        help="Manual review CSV to summarise.",
    )
    args = parser.parse_args()

    if not args.results.exists():
        raise FileNotFoundError(
            f"Manual-review results not found: {args.results}"
        )

    results = pd.read_csv(args.results)

    required_columns = {
        "eval_id",
        "winner",
        "failure_modes",
        "judge_31_agrees",
        "judge_35_agrees",
    }
    missing_columns = required_columns - set(results.columns)

    if missing_columns:
        raise ValueError(
            f"Results file is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    total = len(results)
    if total == 0:
        raise ValueError("Manual-review results file contains no reviews.")

    winners = results["winner"].value_counts()
    wins_31 = int(winners.get(MODEL_31, 0))
    wins_35 = int(winners.get(MODEL_35, 0))
    ties = int(winners.get("tie", 0))

    unknown_winners = total - wins_31 - wins_35 - ties
    if unknown_winners:
        raise ValueError(
            f"Found {unknown_winners} invalid winner value(s). Expected only "
            f"'{MODEL_31}', '{MODEL_35}', or 'tie'."
        )

    decisive = results[
        results["winner"].isin([MODEL_31, MODEL_35])
    ].copy()
    decisive_count = len(decisive)

    judge_31_agree = _count_judge_agreement(
        decisive,
        "judge_31_agrees",
    )
    judge_35_agree = _count_judge_agreement(
        decisive,
        "judge_35_agrees",
    )

    mode_counts = _failure_mode_counts(results)

    print()
    print("=" * 68)
    print("MANUAL REVIEW SUMMARY")
    print("=" * 68)
    print(f"Results file: {args.results}")
    print(f"Total cases reviewed: {total}")
    print()
    print("Manual winner distribution:")
    print(
        f"  Gemini 3.1 Flash-Lite: {wins_31} "
        f"({wins_31 / total:.1%})"
    )
    print(
        f"  Gemini 3.5 Flash-Lite: {wins_35} "
        f"({wins_35 / total:.1%})"
    )
    print(f"  Tie:                   {ties} ({ties / total:.1%})")
    print()
    print(f"Decisive cases: {decisive_count}")

    if decisive_count:
        print(
            "  Judge 3.1 agreement with human: "
            f"{judge_31_agree}/{decisive_count} "
            f"({judge_31_agree / decisive_count:.1%})"
        )
        print(
            "  Judge 3.5 agreement with human: "
            f"{judge_35_agree}/{decisive_count} "
            f"({judge_35_agree / decisive_count:.1%})"
        )
    else:
        print("  No decisive cases: judge agreement is not applicable.")

    if not mode_counts.empty:
        print()
        print("Observed failure modes:")
        for mode, count in mode_counts.items():
            print(f"  {mode}: {count}")

    print("=" * 68)
    print()
    print("Recommendation:")
    print(
        _recommendation(
            wins_31=wins_31,
            wins_35=wins_35,
            ties=ties,
            decisive_count=decisive_count,
        )
    )


if __name__ == "__main__":
    main()