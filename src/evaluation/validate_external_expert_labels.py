from __future__ import annotations

import ast
import csv
import json
from collections import Counter
from pathlib import Path


EXPERT_DATASET_DIR = Path("data/external_inspection/mitre-ttp-mapping/datasets/expert")
ATTACK_STIX_PATH = Path("data/raw/attack/enterprise-attack.json")
OUTPUT_PATH = Path("data/evaluation_reports/expert_label_compatibility.csv")

def load_expert_labels() -> dict[str, set[str]]:
    labels_by_split: dict[str, set[str]] = {}

    for split in ("train", "dev", "test"):
        path = EXPERT_DATASET_DIR / f"expert_{split}.tsv"
        labels: set[str] = set()

        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")

            for row in reader:
                labels.update(ast.literal_eval(row["labels"]))

        labels_by_split[split] = labels

    return labels_by_split


def load_attack_statuses() -> dict[str, dict[str, str | bool]]:
    with ATTACK_STIX_PATH.open(encoding="utf-8") as handle:
        bundle = json.load(handle)

    attack_records: dict[str, dict[str, str | bool]] = {}

    for obj in bundle["objects"]:
        if obj.get("type") != "attack-pattern":
            continue

        external_id = next(
            (
                ref["external_id"]
                for ref in obj.get("external_references", [])
                if ref.get("source_name") == "mitre-attack"
                and ref.get("external_id", "").startswith("T")
            ),
            None,
        )

        if external_id is None:
            continue

        domains = obj.get("x_mitre_domains", [])
        if "enterprise-attack" not in domains:
            continue

        attack_records[external_id] = {
            "name": obj.get("name", ""),
            "revoked": obj.get("revoked", False),
            "deprecated": obj.get("x_mitre_deprecated", False),
        }

    return attack_records


def classify_label(
    attack_id: str,
    attack_records: dict[str, dict[str, str | bool]],
) -> dict[str, str]:
    record = attack_records.get(attack_id)

    if record is None:
        return {
            "status": "absent",
            "technique_name": "",
        }

    if record["revoked"]:
        return {
            "status": "revoked",
            "technique_name": str(record["name"]),
        }

    if record["deprecated"]:
        return {
            "status": "deprecated",
            "technique_name": str(record["name"]),
        }

    return {
        "status": "active",
        "technique_name": str(record["name"]),
    }


def main() -> None:
    if not ATTACK_STIX_PATH.exists():
        raise FileNotFoundError(
            f"ATT&CK STIX file not found: {ATTACK_STIX_PATH}\n"
            "Update ATTACK_STIX_PATH to match your pinned local file."
        )

    labels_by_split = load_expert_labels()
    attack_records = load_attack_statuses()

    all_labels = sorted(set().union(*labels_by_split.values()))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    counts = Counter()

    for attack_id in all_labels:
        result = classify_label(attack_id, attack_records)
        splits = ",".join(
            split
            for split, labels in labels_by_split.items()
            if attack_id in labels
        )

        rows.append(
            {
                "attack_id": attack_id,
                "status": result["status"],
                "technique_name": result["technique_name"],
                "dataset_splits": splits,
            }
        )
        counts[result["status"]] += 1

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "attack_id",
                "status",
                "technique_name",
                "dataset_splits",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"ATT&CK STIX file: {ATTACK_STIX_PATH}")
    print(f"Unique Expert labels: {len(all_labels)}")
    print(f"Active: {counts['active']}")
    print(f"Deprecated: {counts['deprecated']}")
    print(f"Revoked: {counts['revoked']}")
    print(f"Absent: {counts['absent']}")
    print(f"Wrote: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()