from __future__ import annotations

from pydantic import BaseModel, Field


class AttackRecordContext(BaseModel):
    attack_id: str = Field(..., description="MITRE ATT&CK technique or sub-technique ID.")
    name: str = Field(..., description="ATT&CK technique or sub-technique name.")
    is_subtechnique: bool = Field(..., description="Whether the ATT&CK record is a sub-technique.")
    parent_attack_id: str | None = Field(
        default=None,
        description="Parent ATT&CK technique ID when the record is a sub-technique.",
    )
    tactics: list[str] = Field(
        default_factory=list,
        description="ATT&CK tactic names associated with the record.",
    )
    platforms: list[str] = Field(
        default_factory=list,
        description="Platforms associated with the record.",
    )
    description_clean: str = Field(
        ...,
        description="Cleaned ATT&CK description used for retrieval and grounding.",
    )
    source_url: str = Field(..., description="Canonical ATT&CK technique URL.")


class GeneratedAnswer(BaseModel):
    primary_attack_id: str | None = Field(
        default=None,
        description="Best single ATT&CK technique/sub-technique candidate, if supported.",
    )
    alternative_attack_ids: list[str] = Field(
        default_factory=list,
        description="Up to two plausible alternative ATT&CK candidates from retrieved context.",
    )
    supporting_attack_ids: list[str] = Field(
        default_factory=list,
        description="Retrieved ATT&CK records that directly support the answer.",
    )
    answer_summary: str = Field(
        ...,
        description="Short analyst-facing explanation grounded in retrieved ATT&CK records.",
    )
    retrieval_grounding_note: str = Field(
        ...,
        description="Short note describing which retrieved ATT&CK records and fields support the answer.",
    )
    uncertainty_note: str = Field(
        ...,
        description="Short note describing uncertainty, ambiguity, or why review is needed.",
    )
    review_required: bool = Field(
        ...,
        description="Whether a human analyst should explicitly review the answer before using it.",
    )