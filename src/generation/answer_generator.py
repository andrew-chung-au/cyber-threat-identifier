from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.generation.prompts import GENERATION_INSTRUCTIONS_V1, build_generation_prompt
from src.generation.schemas import AttackRecordContext, GeneratedAnswer
from src.llm_client import generate_structured_answer


@dataclass(slots=True)
class GenerationResult:
    answer: GeneratedAnswer
    prompt_version: str
    model_name: str
    usage: Any


def build_attack_record_contexts(
    retrieved_rows: list[dict[str, Any]],
) -> list[AttackRecordContext]:
    contexts: list[AttackRecordContext] = []

    for row in retrieved_rows:
        raw_tactics = row.get("tactics") or []
        raw_platforms = row.get("platforms") or []

        tactic_names = [
            tactic.strip()
            for tactic in raw_tactics
            if isinstance(tactic, str) and tactic.strip()
        ]

        platforms = [
            platform.strip()
            for platform in raw_platforms
            if isinstance(platform, str) and platform.strip()
        ]

        contexts.append(
            AttackRecordContext(
                attack_id=row["attack_id"],
                name=row["name"],
                is_subtechnique=bool(row.get("is_subtechnique", False)),
                parent_attack_id=row.get("parent_attack_id"),
                tactics=tactic_names,
                platforms=platforms,
                description_clean=row["description_clean"],
                source_url=row["source_url"],
            )
        )

    return contexts


def generate_candidate_answer(
    *,
    incident_narrative: str,
    retrieved_rows: list[dict[str, Any]],
    model_name: str | None = None,
    prompt_version: str = "v1",
) -> GenerationResult:
    if prompt_version != "v1":
        raise ValueError(f"Unsupported prompt_version: {prompt_version}")

    if not retrieved_rows:
        raise ValueError("retrieved_rows must contain at least one ATT&CK record.")

    contexts = build_attack_record_contexts(retrieved_rows)

    prompt = build_generation_prompt(
        incident_narrative=incident_narrative,
        retrieved_records=contexts,
    )

    answer, usage = generate_structured_answer(
        instructions=GENERATION_INSTRUCTIONS_V1,
        user_prompt=prompt,
        output_type=GeneratedAnswer,
        model=model_name,
    )

    return GenerationResult(
        answer=answer,
        prompt_version=prompt_version,
        model_name=model_name or "default",
        usage=usage,
    )