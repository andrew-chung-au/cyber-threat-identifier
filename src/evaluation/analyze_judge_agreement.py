#!/usr/bin/env python3
"""
Analyze agreement between two judge models (3.1 vs 3.5 Flash-Lite).

Compares pairwise judgment results and computes:
- Overall agreement rate
- Per-model preference rates
- Disagreement cases (for manual review)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

DEFAULT_JUDGE_31_PATH = Path("data/evaluation_reports/expert_llm_judged_31_as_judge.csv")
DEFAULT_JUDGE_35_PATH = Path("data/evaluation_reports/expert_llm_judged_35_as_judge.csv")
DEFAULT_OUTPUT_PATH = Path("data/evaluation_reports/judge_agreement_summary.csv")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze agreement between two judge models."
    )
    parser.add_argument("--judge-31", type=Path, default=DEFAULT_JUDGE_31_PATH)
    parser.add_argument("--judge-35", type=Path, default=DEFAULT_JUDGE_35_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()
    
    if not args.judge_31.exists():
        raise FileNotFoundError(f"Missing judge-31 CSV: {args.judge_31}")
    if not args.judge_35.exists():
        raise FileNotFoundError(f"Missing judge-35 CSV: {args.judge_35}")
    
    # Load both judge results
    judge_31_df = pd.read_csv(args.judge_31)
    judge_35_df = pd.read_csv(args.judge_35)
    
    # Merge on eval_id
    merged = pd.merge(
        judge_31_df,
        judge_35_df,
        on='eval_id',
        suffixes=('_31', '_35'),
    )
    
    # Compute agreement
    merged['agree'] = merged['winner_31'] == merged['winner_35']
    agreement_rate = merged['agree'].mean()
    
    # Count preferences
    prefers_31_judge_31 = (merged['winner_31'] == 'gemini-3.1-flash-lite').sum()
    prefers_35_judge_31 = (merged['winner_31'] == 'gemini-3.5-flash-lite').sum()
    prefers_31_judge_35 = (merged['winner_35'] == 'gemini-3.1-flash-lite').sum()
    prefers_35_judge_35 = (merged['winner_35'] == 'gemini-3.5-flash-lite').sum()
    
    # Disagreement cases
    disagreements = merged[~merged['agree']][['eval_id', 'winner_31', 'winner_35', 'confidence_31', 'confidence_35']]
    
    # Summary stats
    summary = {
        "total_cases": len(merged),
        "agreement_count": merged['agree'].sum(),
        "agreement_rate": agreement_rate,
        "judge_31_prefers_31": prefers_31_judge_31,
        "judge_31_prefers_35": prefers_35_judge_31,
        "judge_35_prefers_31": prefers_31_judge_35,
        "judge_35_prefers_35": prefers_35_judge_35,
        "disagreement_count": len(disagreements),
    }
    
    # Print summary
    print()
    print("=" * 60)
    print("JUDGE AGREEMENT ANALYSIS")
    print("=" * 60)
    print(f"Total cases evaluated: {summary['total_cases']}")
    print(f"Agreement count: {summary['agreement_count']} / {summary['total_cases']}")
    print(f"Agreement rate: {summary['agreement_rate']:.2%}")
    print()
    print("Judge 3.1 Flash-Lite preferences:")
    print(f"  → Prefers 3.1 output: {summary['judge_31_prefers_31']} ({prefers_31_judge_31 / len(merged):.2%})")
    print(f"  → Prefers 3.5 output: {summary['judge_31_prefers_35']} ({prefers_35_judge_31 / len(merged):.2%})")
    print()
    print("Judge 3.5 Flash-Lite preferences:")
    print(f"  → Prefers 3.1 output: {summary['judge_35_prefers_31']} ({prefers_31_judge_35 / len(merged):.2%})")
    print(f"  → Prefers 3.5 output: {summary['judge_35_prefers_35']} ({prefers_35_judge_35 / len(merged):.2%})")
    print()
    print(f"Disagreement cases: {summary['disagreement_count']} ({len(disagreements) / len(merged):.2%})")
    print("=" * 60)
    print()
    
    # Save summary
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([summary]).to_csv(args.output, index=False)
    print(f"[INFO] Summary saved to {args.output}")
    
    # Save disagreement cases for manual review
    if len(disagreements) > 0:
        disagreement_path = args.output.parent / "judge_disagreements.csv"
        disagreements.to_csv(disagreement_path, index=False)
        print(f"[INFO] Disagreement cases saved to {disagreement_path}")
        print(f"  → Review these {len(disagreements)} cases manually for DEC-020")


if __name__ == "__main__":
    main()