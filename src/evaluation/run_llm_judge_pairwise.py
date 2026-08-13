#!/usr/bin/env python3
"""
Run pairwise LLM-as-Judge evaluation on expert answer generation results.

Compares gemini-3.1-flash-lite vs gemini-3.5-flash-lite outputs using a judge model.
Supports checkpointing: saves after each case, skips already-judged cases on resume.

Features:
- A/B randomization to reduce position bias
- Chain-of-thought prompting for better judgment quality
- Rate limiting (15 RPM by default)
- Checkpointing for resumability
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path
from typing import Any

import pandas as pd
from src.llm_client import generate_text_answer, RateLimiter

DEFAULT_INPUT_PATH = Path("data/evaluation_reports/expert_llm_comparison_v1.csv")
DEFAULT_OUTPUT_CSV_PATH = Path("data/evaluation_reports/expert_llm_judged.csv")

JUDGE_PROMPT_TEMPLATE = """
You are evaluating two AI-generated ATT&CK mapping answers for the same incident narrative.

Incident narrative:
{query_text}

Answer A:
{answer_a_summary}
Retrieved techniques: {retrieved_a_ids}

Answer B:
{answer_b_summary}
Retrieved techniques: {retrieved_b_ids}

Compare these answers on these dimensions:
1. Technique relevance (are suggested techniques supported by the narrative?)
2. Evidence grounding (does it cite specific phrases from the narrative?)
3. Uncertainty framing (does it clearly flag low-confidence mappings?)
4. Actionability (would an analyst find this useful for triage?)
5. Conciseness (is it tight and focused, or verbose?)

First, explain your reasoning step-by-step. Then, choose which answer is better for analyst use: A or B.

Return JSON in this exact format:
{{"reasoning": "...", "winner": "A" or "B", "confidence": "low" or "medium" or "high"}}
"""


def parse_judge_response(response_text: str) -> dict[str, Any]:
    """Parse judge LLM response, extracting JSON from text."""
    # Try to find JSON in response
    start_idx = response_text.find('{')
    end_idx = response_text.rfind('}') + 1
    
    if start_idx == -1 or end_idx == 0:
        # No JSON found, return default
        return {
            "reasoning": response_text.strip(),
            "winner": "A",  # Default
            "confidence": "low",
        }
    
    json_str = response_text[start_idx:end_idx]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Invalid JSON, return default
        return {
            "reasoning": response_text.strip(),
            "winner": "A",
            "confidence": "low",
        }


def run_judge_on_case(
    eval_id: str,
    row_31: Any,
    row_35: Any,
    judge_model: str,
    rate_limiter: RateLimiter,
) -> dict[str, Any]:
    """Run pairwise judge on a single case (comparing 3.1 vs 3.5 outputs)."""
    
    # A/B randomization: randomly swap which model is "A" or "B"
    if random.random() < 0.5:
        # 3.1 is A, 3.5 is B
        answer_a_summary = row_31.answer_summary
        answer_a_model = "gemini-3.1-flash-lite"
        retrieved_a_ids = row_31.retrieved_attack_ids
        
        answer_b_summary = row_35.answer_summary
        answer_b_model = "gemini-3.5-flash-lite"
        retrieved_b_ids = row_35.retrieved_attack_ids
        
        true_winner_map = {"A": "gemini-3.1-flash-lite", "B": "gemini-3.5-flash-lite"}
    else:
        # 3.5 is A, 3.1 is B (swapped)
        answer_a_summary = row_35.answer_summary
        answer_a_model = "gemini-3.5-flash-lite"
        retrieved_a_ids = row_35.retrieved_attack_ids
        
        answer_b_summary = row_31.answer_summary
        answer_b_model = "gemini-3.1-flash-lite"
        retrieved_b_ids = row_31.retrieved_attack_ids
        
        true_winner_map = {"A": "gemini-3.5-flash-lite", "B": "gemini-3.1-flash-lite"}
    
    # Build judge prompt
    judge_prompt = JUDGE_PROMPT_TEMPLATE.format(
        query_text=row_31.query_text,
        answer_a_summary=answer_a_summary,
        retrieved_a_ids=retrieved_a_ids,
        answer_b_summary=answer_b_summary,
        retrieved_b_ids=retrieved_b_ids,
    )
    
    # Call judge LLM
    response_text, usage = generate_text_answer(
        instructions="You are an expert cybersecurity analyst evaluating ATT&CK mapping answers. Be objective and detailed in your reasoning.",
        user_prompt=judge_prompt,
        model=judge_model,
        rate_limiter=rate_limiter,
        verbose=True,
    )
    
    # Parse response
    parsed = parse_judge_response(response_text)
    
    # Map winner back to actual model
    winner = true_winner_map.get(parsed.get("winner", "A"), "gemini-3.1-flash-lite")
    
    return {
        "eval_id": eval_id,
        "judge_model": judge_model,
        "winner": winner,
        "reasoning": parsed.get("reasoning", ""),
        "confidence": parsed.get("confidence", "low"),
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run pairwise LLM-as-Judge evaluation on expert answer generation results."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_CSV_PATH)
    parser.add_argument("--judge-model", required=True, help="Model to use as judge (e.g., gemini-3.1-flash-lite)")
    parser.add_argument("--pause-between-calls", type=float, default=0.0, help="Extra pause between API calls (seconds)")
    args = parser.parse_args()
    
    if not args.input.exists():
        raise FileNotFoundError(f"Missing input CSV: {args.input}")
    
    input_df = pd.read_csv(args.input)
    
    # Checkpoint: Load existing output and skip already-judged eval_ids
    if args.output.exists():
        existing_df = pd.read_csv(args.output)
        judged_eval_ids = set(existing_df['eval_id'])
        print(f"[INFO] Found {len(judged_eval_ids)} already-judged cases in {args.output}")
        print(f"[INFO] Resuming from checkpoint, skipping completed cases...")
        
        output_rows = existing_df.to_dict('records')
    else:
        judged_eval_ids = set()
        output_rows = []
    
    # Group input by eval_id (each case has 2 rows: 3.1 and 3.5 outputs)
    cases = input_df.groupby('eval_id')
    
    # Filter to unjudged cases
    remaining_cases = [
        (eval_id, group)
        for eval_id, group in cases
        if eval_id not in judged_eval_ids
    ]
    
    if len(remaining_cases) == 0:
        print("[OK]   All cases already judged, nothing to do")
        print(f"  Output file: {args.output}")
        return
    
    print(f"[INFO] Judging {len(remaining_cases)} remaining cases with {args.judge_model}")
    
    # Rate limiter: 15 RPM (free tier limit)
    rate_limiter = RateLimiter(max_calls=15, window_seconds=60)
    
    for idx, (eval_id, group) in enumerate(remaining_cases, start=1):
        print(f"[INFO] Judging case {idx}/{len(remaining_cases)}: {eval_id}")
        
        # Get rows for each model
        row_31 = group[group['model'] == 'gemini-3.1-flash-lite'].iloc[0]
        row_35 = group[group['model'] == 'gemini-3.5-flash-lite'].iloc[0]
        
        # Run judge
        result = run_judge_on_case(
            eval_id=eval_id,
            row_31=row_31,
            row_35=row_35,
            judge_model=args.judge_model,
            rate_limiter=rate_limiter,
        )
        
        output_rows.append(result)
        
        # Extra pause if requested
        if args.pause_between_calls > 0:
            time.sleep(args.pause_between_calls)
        
        # Save checkpoint after each case
        args.output.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(output_rows).to_csv(args.output, index=False)
        
        if idx % 20 == 0 or idx == len(remaining_cases):
            print(f"[INFO] Judged {idx}/{len(remaining_cases)} cases, checkpoint saved")
    
    print()
    print("[OK]   Pairwise judge run completed")
    print(f"  CSV output: {args.output}")
    print(f"  Total judgments: {len(output_rows)}")


if __name__ == "__main__":
    main()