from __future__ import annotations

from typing import Any


def fetch_records_for_generation(
    connection: Any,
    attack_ids: list[str],
) -> list[dict[str, Any]]:
    if not attack_ids:
        return []

    sql = """
        SELECT
            attack_id,
            name,
            is_subtechnique,
            parent_attack_id,
            tactics,
            platforms,
            description_clean,
            source_url
        FROM techniques
        WHERE attack_id = ANY(%s)
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, (attack_ids,))
        rows = cursor.fetchall()

    rows_by_attack_id = {
        row[0]: {
            "attack_id": row[0],
            "name": row[1],
            "is_subtechnique": row[2],
            "parent_attack_id": row[3],
            "tactics": row[4],
            "platforms": row[5],
            "description_clean": row[6],
            "source_url": row[7],
        }
        for row in rows
    }

    return [
        rows_by_attack_id[attack_id]
        for attack_id in attack_ids
        if attack_id in rows_by_attack_id
    ]