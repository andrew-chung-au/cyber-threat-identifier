from __future__ import annotations

import json

from src.generation.schemas import AttackRecordContext


GENERATION_INSTRUCTIONS_V1 = """
You are helping map an incident narrative to likely Enterprise MITRE ATT&CK techniques/sub-techniques.

You must follow these rules:
- Use only the retrieved ATT&CK records provided in the prompt.
- Do not invent techniques that are not present in the retrieved context.
- Do not provide attribution, severity, incident-response advice, or claims outside ATT&CK mapping.
- Select at most one primary ATT&CK ID and up to two alternatives.
- Prefer specific sub-techniques when the retrieved evidence clearly supports them.
- If support is weak or ambiguous, set review_required to true.
- The answer_summary must be short, practical, and analyst-facing.
- The retrieval_grounding_note must describe which retrieved ATT&CK records support the answer.
- The uncertainty_note must clearly explain ambiguity, weak evidence, or why review is required.
- supporting_attack_ids must contain only ATT&CK IDs from the retrieved context.
- alternative_attack_ids must not duplicate the primary_attack_id.
- If the retrieved context is insufficient for a confident mapping, say so clearly.
"""


def _pretty_tactic_name(value: str) -> str:
    return value.replace("-", " ").title()


def build_generation_prompt(
    *,
    incident_narrative: str,
    retrieved_records: list[AttackRecordContext],
) -> str:
    records_payload = []

    for record in retrieved_records:
        payload = record.model_dump()
        payload["tactics"] = [_pretty_tactic_name(tactic) for tactic in record.tactics]
        records_payload.append(payload)

    return (
        "Incident narrative:\n"
        f"{incident_narrative.strip()}\n\n"
        "Retrieved ATT&CK records:\n"
        f"{json.dumps(records_payload, ensure_ascii=False, indent=2)}\n\n"
        "Return a grounded structured answer using only the retrieved ATT&CK records."
    )