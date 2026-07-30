#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

REPOSITORY = "https://raw.githubusercontent.com/mitre-attack/attack-stix-data"


def info(message: str) -> None:
    print(f"[INFO] {message}")


def ok(message: str) -> None:
    print(f"[OK]   {message}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def fetch_bytes(url: str) -> bytes:
    info(f"Downloading {url}")

    request = Request(
        url,
        headers={"User-Agent": "CyberThreatIdentifier/0.1"},
    )

    with urlopen(request, timeout=60) as response:
        return response.read()


def fetch_json(url: str) -> dict:
    return json.loads(fetch_bytes(url).decode("utf-8"))


def write_manifest_row(manifest_path: Path, row: dict[str, str]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "downloaded_at_utc",
        "source_name",
        "domain",
        "version",
        "source_url",
        "local_path",
        "sha256",
        "notes",
    ]

    write_header = not manifest_path.exists()

    with manifest_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if write_header:
            writer.writeheader()

        writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Enterprise MITRE ATT&CK STIX 2.1 data."
    )
    parser.add_argument(
        "--ref",
        default="master",
        help=(
            "Git reference to download, for example 'master' for the latest "
            "snapshot or a release tag such as 'v19.1'."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="data/raw/attack",
        help="Directory for downloaded ATT&CK files.",
    )
    parser.add_argument(
        "--source-manifest",
        default="data/source_manifest.csv",
        help="Append-only CSV log of downloaded source files.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    manifest_path = Path(args.source_manifest)

    base_url = f"{REPOSITORY}/{args.ref}"
    index_url = f"{base_url}/index.json"
    enterprise_url = f"{base_url}/enterprise-attack/enterprise-attack.json"

    info("Starting ATT&CK data download")
    info(f"Using repository reference: {args.ref}")

    output_dir.mkdir(parents=True, exist_ok=True)
    ok(f"Output directory ready: {output_dir}")

    info("Fetching ATT&CK collection index")
    index_json = fetch_json(index_url)
    index_path = output_dir / "attack-stix-index.json"
    index_path.write_text(
        json.dumps(index_json, indent=2),
        encoding="utf-8",
    )
    ok(f"Saved collection index: {index_path}")

    info("Fetching Enterprise ATT&CK STIX bundle")
    enterprise_bytes = fetch_bytes(enterprise_url)
    enterprise_path = output_dir / "enterprise-attack.json"
    enterprise_path.write_bytes(enterprise_bytes)
    ok(f"Saved Enterprise bundle: {enterprise_path}")

    downloaded_at = datetime.now(UTC).replace(microsecond=0).isoformat()

    info("Updating download manifest")

    write_manifest_row(
        manifest_path,
        {
            "downloaded_at_utc": downloaded_at,
            "source_name": "MITRE ATT&CK STIX collection index",
            "domain": "all",
            "version": args.ref,
            "source_url": index_url,
            "local_path": str(index_path),
            "sha256": sha256_file(index_path),
            "notes": "Machine-readable index of ATT&CK STIX collections",
        },
    )

    write_manifest_row(
        manifest_path,
        {
            "downloaded_at_utc": downloaded_at,
            "source_name": "MITRE ATT&CK Enterprise STIX 2.1",
            "domain": "enterprise",
            "version": args.ref,
            "source_url": enterprise_url,
            "local_path": str(enterprise_path),
            "sha256": sha256_file(enterprise_path),
            "notes": "Enterprise ATT&CK STIX 2.1 collection bundle",
        },
    )

    ok(f"Updated download manifest: {manifest_path}")

    print()
    ok("Download completed successfully")
    print("Files created:")
    print(f"  - {index_path}")
    print(f"  - {enterprise_path}")
    print(f"  - {manifest_path}")


if __name__ == "__main__":
    main()