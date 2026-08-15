from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEEDBACK_PATH = PROJECT_ROOT / "data" / "feedback" / "feedback.csv"

FIELDNAMES = [
    "timestamp_utc",
    "query_id",
    "feedback",
    "model_id",
    "query_text",
    "answer_text",
    "retrieved_technique_ids",
]


def save_feedback(
    *,
    query_id: str,
    feedback: str,
    model_id: str,
    query_text: str,
    answer_text: str,
    retrieved_technique_ids: list[str],
) -> Path:
    if feedback not in {"thumbs_up", "thumbs_down"}:
        raise ValueError(f"Unsupported feedback value: {feedback}")

    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)

    file_exists = FEEDBACK_PATH.exists() and FEEDBACK_PATH.stat().st_size > 0

    with FEEDBACK_PATH.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)

        if not file_exists:
            writer.writeheader()

        writer.writerow(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "query_id": query_id,
                "feedback": feedback,
                "model_id": model_id,
                "query_text": query_text,
                "answer_text": answer_text,
                "retrieved_technique_ids": "|".join(
                    retrieved_technique_ids
                ),
            }
        )

    return FEEDBACK_PATH