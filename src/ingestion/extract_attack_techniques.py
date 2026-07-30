#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

ATTACK_ID_PATTERN = re.compile(r"^T\d{4}(?:\.\d{3})?$")
CITATION_PATTERN = re.compile(r"\s*\(Citation:\s*[^)]+\)")
WHITESPACE_PATTERN = re.compile(r"\s+")


def info(message: str) -> None:
    print(f"[INFO] {message}")


def ok(message: str) -> None:
    print(f"[OK]   {message}")


def clean_description(text: str) -> str:
    """Remove ATT&CK citation markers and normalise whitespace."""
    without_citations = CITATION_PATTERN.sub("", text)
    return WHITESPACE_PATTERN.sub(" ", without_citations).strip()


def get_mitre_attack_reference(
    external_references: Iterable[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return the first external reference identified as MITRE ATT&CK."""
    for reference in external_references:
        if reference.get("source_name") == "mitre-attack":
            return reference

    return None


def get_tactics(
    kill_chain_phases: Iterable[dict[str, Any]],
) -> list[dict[str, str]]:
    """Extract Enterprise ATT&CK tactics from STIX kill-chain phases."""
    tactics: list[dict[str, str]] = []
    seen: set[str] = set()

    for phase in kill_chain_phases:
        if phase.get("kill_chain_name") != "mitre-attack":
            continue

        short_name = phase.get("phase_name")

        if not isinstance(short_name, str) or not short_name:
            continue

        if short_name in seen:
            continue

        seen.add(short_name)
        tactics.append(
            {
                "name": short_name.replace("-", " ").title(),
                "short_name": short_name,
            }
        )

    return tactics


def parse_modified_timestamp(value: Any) -> datetime:
    """Parse a STIX modified timestamp for duplicate resolution."""
    if not isinstance(value, str):
        return datetime.min

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min


def extract_technique_record(obj: dict[str, Any]) -> dict[str, Any] | None:
    """Convert one STIX attack-pattern object into a retrieval-ready record."""
    stix_id = obj.get("id")
    name = obj.get("name")
    description_raw = obj.get("description", "")

    if not isinstance(stix_id, str) or not stix_id:
        return None

    if not isinstance(name, str) or not name.strip():
        return None

    if not isinstance(description_raw, str) or not description_raw.strip():
        return None

    external_references = obj.get("external_references", [])
    if not isinstance(external_references, list):
        return None

    mitre_reference = get_mitre_attack_reference(external_references)
    if not mitre_reference:
        return None

    attack_id = mitre_reference.get("external_id")
    if not isinstance(attack_id, str):
        return None

    if not ATTACK_ID_PATTERN.fullmatch(attack_id):
        return None

    source_url = mitre_reference.get("url")
    if not isinstance(source_url, str) or not source_url:
        source_url = (
            f"https://attack.mitre.org/techniques/"
            f"{attack_id.replace('.', '/')}/"
        )

    kill_chain_phases = obj.get("kill_chain_phases", [])
    if not isinstance(kill_chain_phases, list):
        kill_chain_phases = []

    platforms = obj.get("x_mitre_platforms", [])
    if not isinstance(platforms, list):
        platforms = []

    cleaned_platforms = sorted(
        {
            platform.strip()
            for platform in platforms
            if isinstance(platform, str) and platform.strip()
        }
    )

    return {
        "stix_id": stix_id,
        "attack_id": attack_id,
        "name": name.strip(),
        "is_subtechnique": bool(obj.get("x_mitre_is_subtechnique", False)),
        "parent_attack_id": None,
        "tactics": get_tactics(kill_chain_phases),
        "platforms": cleaned_platforms,
        "description_raw": description_raw.strip(),
        "description_clean": clean_description(description_raw),
        "source_url": source_url,
        "created": obj.get("created")
        if isinstance(obj.get("created"), str)
        else None,
        "modified": obj.get("modified")
        if isinstance(obj.get("modified"), str)
        else None,
    }


def write_jsonl(output_path: Path, records: list[dict[str, Any]]) -> None:
    """Write one UTF-8 JSON object per line."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract retrieval-ready Enterprise ATT&CK technique records "
            "from a STIX JSON bundle."
        )
    )
    parser.add_argument(
        "--input",
        default="data/raw/attack/enterprise-attack.json",
        help="Path to the downloaded Enterprise ATT&CK STIX bundle.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/techniques.jsonl",
        help="Path for the generated technique-record JSONL file.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input bundle not found: {input_path}\n"
            "Run: uv run python -m src.ingestion.download_attack_data"
        )

    info(f"Reading STIX bundle: {input_path}")

    with input_path.open("r", encoding="utf-8") as file:
        bundle = json.load(file)

    objects = bundle.get("objects", [])
    if not isinstance(objects, list):
        raise ValueError("Invalid STIX bundle: expected an 'objects' list.")

    total_objects = len(objects)
    attack_patterns_found = 0
    excluded_inactive = 0
    malformed_skipped = 0
    duplicates_found = 0

    records_by_attack_id: dict[str, dict[str, Any]] = {}

    for obj in objects:
        if not isinstance(obj, dict) or obj.get("type") != "attack-pattern":
            continue

        attack_patterns_found += 1

        if obj.get("revoked") is True or obj.get("x_mitre_deprecated") is True:
            excluded_inactive += 1
            continue

        record = extract_technique_record(obj)
        if record is None:
            malformed_skipped += 1
            continue

        attack_id = record["attack_id"]

        if attack_id in records_by_attack_id:
            duplicates_found += 1
            current = records_by_attack_id[attack_id]

            if parse_modified_timestamp(
                record["modified"]
            ) > parse_modified_timestamp(current["modified"]):
                records_by_attack_id[attack_id] = record
        else:
            records_by_attack_id[attack_id] = record

    records = sorted(
        records_by_attack_id.values(),
        key=lambda item: item["attack_id"],
    )

    write_jsonl(output_path, records)

    info("Extraction summary")
    print(f"  Total STIX objects read:       {total_objects}")
    print(f"  Attack-pattern objects found:  {attack_patterns_found}")
    print(f"  Revoked/deprecated excluded:   {excluded_inactive}")
    print(f"  Malformed records skipped:     {malformed_skipped}")
    print(f"  Duplicate ATT&CK IDs resolved: {duplicates_found}")
    print(f"  Final technique records:       {len(records)}")
    ok(f"Saved JSONL dataset: {output_path}")


if __name__ == "__main__":
    main()