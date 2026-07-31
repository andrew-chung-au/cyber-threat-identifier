# Dataset notes

This document records the scope, provenance, structure, processing rules, data artefacts, quality checks, and limitations of the Cyber Threat Identifier corpus and external evaluation-data candidates.

It is the working reference for corpus design and source management.

For stable architectural choices, see [`decisions.md`](decisions.md).  
For chronological implementation history, see [`project-log.md`](project-log.md).  
For reproducible setup and pipeline commands, see [`runbook.md`](runbook.md).  
For retrieval experiments, benchmark design, and metrics, see [`evaluation-notes.md`](evaluation-notes.md).

---

## Corpus summary

### Initial corpus

Version 1 uses active Enterprise MITRE ATT&CK technique and sub-technique records extracted from the official ATT&CK STIX 2.1 Enterprise bundle.

The initial corpus contains one retrieval record for each retained technique or sub-technique.

### Intended use

The corpus supports an incident-to-technique retrieval task:

```text
Unstructured incident narrative
        ↓
Ranked likely ATT&CK techniques and sub-techniques
        ↓
Technique metadata and source-grounded evidence
        ↓
Analyst review
```

The corpus supports analyst investigation and technique identification. It is not intended to establish attribution, determine incident severity, prescribe incident-response actions, or guarantee complete coverage of adversary behaviour.

### Retrieval unit

The version 1 retrieval unit is:

```text
one active ATT&CK technique or sub-technique
=
one processed JSONL record
=
one PostgreSQL row
=
one embedding text field
=
one embedding vector
=
one retrieval result
```

Document-style chunking is not used for the initial technique corpus.

The rationale for this retrieval-unit choice is recorded in `DEC-008`. Vector-index strategy, including optional HNSW use, is recorded in `DEC-012`.

---

## Corpus boundaries

### Included in version 1

- Enterprise ATT&CK STIX 2.1 `attack-pattern` objects
- Active techniques
- Active sub-techniques
- ATT&CK IDs and STIX IDs
- Technique names
- Tactics and platforms
- Source descriptions
- Canonical ATT&CK source URLs
- Source creation and modification timestamps
- Cleaned descriptions for retrieval preparation
- Raw descriptions for evidence display and inspection

### Excluded in version 1

- Revoked ATT&CK objects
- Deprecated ATT&CK objects
- Mobile ATT&CK content
- ICS ATT&CK content
- ATT&CK groups
- ATT&CK software and malware
- ATT&CK campaigns
- ATT&CK mitigations
- STIX relationship objects
- Procedure examples
- Detection strategies
- Analytics
- Data sources and data components
- External incident reports as retrieval corpus sources
- Vendor threat-intelligence reports as retrieval corpus sources
- Long-form advisory documents as retrieval corpus sources

### Deferred boundary items

| Item | Potential future value | Reason deferred |
|---|---|---|
| Procedure examples | Connect techniques to observed adversary behaviour | Requires relationship traversal and a more complex retrieval design |
| Groups and software | Add contextual enrichment | Not required for the initial technique-identification baseline |
| Detection strategies and analytics | Support detection-oriented workflows | Outside the v1 incident-to-technique scope |
| Data sources and data components | Support telemetry and observability questions | Better suited to a later detection-gap feature |
| Public incident reports | Provide realistic narrative evidence | Require separate provenance, copyright, curation, and chunking decisions |
| Advisory documents | Add defensive guidance | Require long-document extraction and chunking |

---

## Source inventory

### Core source

| Field | Value |
|---|---|
| Source name | MITRE ATT&CK Enterprise STIX dataset |
| Role | Core retrieval corpus source |
| Format | STIX 2.1 JSON |
| Source repository | `mitre-attack/attack-stix-data` |
| Collection index | `https://raw.githubusercontent.com/mitre-attack/attack-stix-data/<ref>/index.json` |
| Enterprise bundle | `https://raw.githubusercontent.com/mitre-attack/attack-stix-data/<ref>/enterprise-attack/enterprise-attack.json` |
| Raw local directory | `data/raw/attack/` |
| Processed output | `data/processed/techniques.jsonl` |
| Retrieval role | Canonical source for technique and sub-technique retrieval records |
| Version approach | Default reference for refreshes; fixed release tag or commit for formal evaluation |

### External evaluation candidate

| Field | Value |
|---|---|
| Source name | Security-TTP-Mapping |
| Repository | `https://github.com/tumeteor/mitre-ttp-mapping` |
| Candidate configuration | Expert |
| Role | Future external answer-evaluation benchmark candidate |
| Format | Tab-separated values (`.tsv`) |
| Text field | `text1` |
| Label field | `labels` |
| Label format | String representation of a Python-style list of ATT&CK IDs |
| Local inspection directory | `data/external_inspection/mitre-ttp-mapping/` |
| Upstream splits | `expert_train.tsv`, `expert_dev.tsv`, `expert_test.tsv` |
| Upstream licence declaration | Repository README declares Creative Commons CC BY 4.0 |
| Public repository policy | Upstream download remains ignored until third-party report-text redistribution treatment is resolved |

### Source coverage

The Enterprise STIX bundle contains multiple object types. Version 1 retains only active `attack-pattern` objects representing techniques and sub-techniques.

The source provides the initial fields needed for evidence-oriented retrieval:

- ATT&CK external ID, such as `T1059` or `T1059.001`
- STIX object ID
- Technique or sub-technique name
- Description
- ATT&CK tactic associations
- Platform associations
- Canonical ATT&CK URL
- Source creation timestamp
- Source modification timestamp
- Revoked and deprecated status fields

---

## Provenance and versioning

### ATT&CK download provenance

Each ATT&CK source download is recorded in:

```text
data/source_manifest.csv
```

The manifest records:

- `downloaded_at_utc`
- `source_name`
- `domain`
- `version`
- `source_url`
- `local_path`
- `sha256`
- `notes`

This creates an acquisition trail between the official source bundle and the derived processed corpus.

### Source references

The downloader supports two source-reference modes:

| Mode | Purpose | Appropriate use |
|---|---|---|
| Default repository reference | Refresh the corpus against the current upstream source state | Development and current-data inspection |
| Fixed release tag or commit | Rebuild a stable corpus version | Retrieval experiments, reported metrics, and reproducible portfolio results |

A reported evaluation result must identify:

- The ATT&CK source reference, release tag, or commit
- Relevant source checksum from the manifest
- Processed corpus version or repository commit
- Embedding model
- Retrieval configuration
- Benchmark version or upstream dataset revision

### External dataset provenance

The external Expert dataset is inspected from a local Git clone. Record the exact upstream revision before using it in development or final evaluation:

```bash
git -C data/external_inspection/mitre-ttp-mapping rev-parse HEAD
```

Any future curated benchmark metadata must preserve:

- Upstream repository URL
- Upstream Git commit
- Dataset configuration: `Expert`
- Upstream split
- Upstream row index
- Original upstream expected label list
- Local pinned ATT&CK release
- Inclusion or exclusion reason

### Authoritative source

The official Enterprise ATT&CK STIX bundle is the authoritative source for the retrieval corpus.

`data/processed/techniques.jsonl` is a derived project artefact. It is retained as an inspectable corpus snapshot, not as a replacement for the upstream STIX source.

The Security-TTP-Mapping Expert subset is an external evaluation-data candidate, not a retrieval corpus source.

---

## Repository artefacts

The project uses a hybrid artefact policy: important derived data is committed for inspection, while reproducible upstream downloads remain local.

### Committed artefacts

The following artefacts should be version controlled:

```text
data/source_manifest.csv
data/processed/techniques.jsonl
data/evaluation_reports/expert_label_compatibility.csv
```

Reasons:

- `techniques.jsonl` lets reviewers inspect the real retrieval corpus without setting up PostgreSQL or downloading STIX data.
- `source_manifest.csv` preserves ATT&CK source provenance and checksums.
- `expert_label_compatibility.csv` documents compatibility between the candidate external dataset labels and the active local ATT&CK corpus without reproducing threat-report text.

### Ignored artefacts

The following upstream files should not be committed:

```text
data/raw/attack/attack-stix-index.json
data/raw/attack/enterprise-attack.json
data/external_inspection/
```

Raw ATT&CK files are regenerated by the downloader from the recorded source reference.

`data/external_inspection/` contains cloned external source repositories downloaded for feasibility inspection. It may contain third-party threat-report text and must remain ignored unless a separate provenance and redistribution decision changes this policy.

The repository should also exclude local runtime state, including `.env`, virtual environments, Python caches, and Docker database volumes.

### Future benchmark artefacts

Do not commit a final external benchmark containing copied `text1` narratives until the redistribution and provenance position is explicitly resolved.

Until then, a public evaluation artefact may include:

- Upstream repository and revision
- Upstream split and row index
- ATT&CK labels
- Compatibility status
- Inclusion and exclusion decisions
- Aggregate metrics
- Retrieval rankings
- Human-review scores
- Failure categories

Avoid publishing copied threat-report paragraphs unless their reuse is confirmed.

### Corpus refresh policy

When intentionally refreshing the ATT&CK corpus:

1. Download the selected upstream source reference.
2. Regenerate `data/processed/techniques.jsonl`.
3. Review changes to the processed corpus and manifest.
4. Commit the updated processed snapshot and manifest together when appropriate.
5. Rebuild database records and embeddings locally.
6. Re-run external-label compatibility validation if the active ATT&CK release changes.

Operational commands for this process are maintained in [`runbook.md`](runbook.md).

---

## Extraction rules

### Input and output

| Item | Location |
|---|---|
| Raw input bundle | `data/raw/attack/enterprise-attack.json` |
| Extraction module | `src/ingestion/extract_attack_techniques.py` |
| Processed corpus | `data/processed/techniques.jsonl` |

### Object selection

The extractor retains a record only when all of the following are true:

- The object type is STIX `attack-pattern`
- The object is not revoked
- The object is not deprecated
- The object has a non-empty STIX ID
- The object has a non-empty technique name
- The object has a non-empty description
- The object has a MITRE ATT&CK external reference
- The external ATT&CK ID matches an expected technique or sub-technique format

Expected ATT&CK ID patterns:

```text
Technique:     T####
Sub-technique: T####.###
```

### Duplicate handling

If multiple valid objects resolve to the same ATT&CK ID, the extractor retains the record with the newest `modified` timestamp.

### Description handling

The extractor preserves two description fields:

| Field | Purpose |
|---|---|
| `description_raw` | Original source-preserved description for evidence display and inspection |
| `description_clean` | Retrieval-oriented description with inline citation markers removed and whitespace normalised |

The cleaner does not rewrite source meaning or generate new content.

### Tactic handling

The extractor:

- Retains only `kill_chain_phases` associated with `mitre-attack`
- Preserves tactic short names
- Creates readable display names
- Removes duplicate tactics within a record

### Platform handling

The extractor:

- Reads `x_mitre_platforms`
- Keeps non-empty string values
- Removes duplicates
- Sorts platform values for consistency

---

## Processed record schema

Each line in `data/processed/techniques.jsonl` is one JSON object.

| Field | Type | Description |
|---|---|---|
| `stix_id` | string | STIX identifier for the ATT&CK object |
| `attack_id` | string | ATT&CK technique or sub-technique ID |
| `name` | string | Technique or sub-technique name |
| `is_subtechnique` | boolean | Whether the record is a sub-technique |
| `parent_attack_id` | string or null | Parent technique ID when available |
| `tactics` | list | Associated ATT&CK tactics with display and short names |
| `platforms` | list | Associated Enterprise platform names |
| `description_raw` | string | Original ATT&CK description retained as evidence |
| `description_clean` | string | Cleaned description used for retrieval preparation |
| `source_url` | string | Canonical ATT&CK technique URL |
| `created` | string or null | Source creation timestamp |
| `modified` | string or null | Source modification timestamp |

### Example record

```json
{
  "stix_id": "attack-pattern--example",
  "attack_id": "T1059",
  "name": "Command and Scripting Interpreter",
  "is_subtechnique": false,
  "parent_attack_id": null,
  "tactics": [
    {
      "name": "Execution",
      "short_name": "execution"
    }
  ],
  "platforms": [
    "Linux",
    "macOS",
    "Windows"
  ],
  "description_raw": "Original source description...",
  "description_clean": "Cleaned source description...",
  "source_url": "https://attack.mitre.org/techniques/T1059/",
  "created": "YYYY-MM-DDTHH:MM:SSZ",
  "modified": "YYYY-MM-DDTHH:MM:SSZ"
}
```

---

## Size and chunking

### Initial size analysis

The active Enterprise technique corpus had the following cleaned-description lengths during the initial size analysis:

| Measure | Description words |
|---|---:|
| Minimum | Approximately 30 |
| Median | Approximately 151 |
| Average | Approximately 168 |
| 90th percentile | Approximately 273 |
| 95th percentile | Approximately 312 |
| 99th percentile | Approximately 435 |
| Maximum | Approximately 555 |

### Current approach

The corpus is not chunked.

Technique and sub-technique records are already compact, source-native units. Keeping each record intact preserves the connection between technique identity, tactic and platform metadata, source description, and provenance.

### Future trigger

Introduce a separate document-chunking process only if the corpus expands to long-form materials, such as:

- Incident reports
- Government advisories
- Vendor threat reports
- Procedure examples
- Detection guidance
- Long mitigation documentation

A future expanded architecture may contain:

```text
techniques       # Canonical ATT&CK technique records
document_chunks  # Passages from long supporting documents
```

---

## Database representation

The processed corpus is loaded into the PostgreSQL `techniques` table.

One processed technique record maps to one database row.

The loader creates an `embedding_text` field from:

```text
ATT&CK ID: <attack_id>
Technique: <name>
Tactics: <display tactic names>
Platforms: <platform names>

Description:
<description_clean>
```

This keeps technique identity and useful metadata associated with the source description used for semantic retrieval.

Embeddings are generated after structured records are loaded. The current local baseline model and vector-index strategy are implementation decisions recorded in `DEC-011` and `DEC-012`.

Database setup, embedding commands, and verification checks are maintained in [`runbook.md`](runbook.md).

---

## External benchmark checks

### Dataset structure

The Expert external dataset contains three pre-split TSV files:

```text
expert_train.tsv
expert_dev.tsv
expert_test.tsv
```

Each record contains:

| Field | Type | Purpose |
|---|---|---|
| `text1` | string | Threat-report paragraph |
| `labels` | string | Python-style list of ATT&CK technique or sub-technique IDs |

### Split policy

| Split | Intended project use |
|---|---|
| `expert_train.tsv` | Optional exploratory analysis only |
| `expert_dev.tsv` | Develop and freeze curation rules, retrieval settings, prompt format, and human scoring rubric |
| `expert_test.tsv` | Held-out final external evaluation only |

The held-out test split must not be used to tune retrieval configuration, embedding models, prompts, LLM settings, answer format, or curation thresholds.

### Label compatibility rule

A future external benchmark record is eligible only if every upstream expected ATT&CK ID is active in the project's pinned local Enterprise ATT&CK corpus.

Records with one or more `deprecated`, `revoked`, or `absent` expected IDs are excluded from the curated benchmark. The original upstream files are never edited.

### Compatibility validation

The validation module is:

```text
src/evaluation/validate_external_expert_labels.py
```

It compares all Expert labels with active local Enterprise ATT&CK `attack-pattern` records.

The report is written to:

```text
data/evaluation_reports/expert_label_compatibility.csv
```

Initial result across all Expert splits:

| Status | Unique labels |
|---|---:|
| Active | 281 |
| Deprecated | 3 |
| Revoked | 6 |
| Absent | 0 |
| Total | 290 |

### Held-out test compatibility

The upstream Expert test split contains 157 records.

Four records contain one or more non-active expected labels in the current local corpus:

```text
12
17
32
130
```

Therefore, 153 source records remain technically compatible before later curation for narrative quality, text length, label count, and answer-evaluation suitability.

---

## Data-quality checks

### Current ATT&CK corpus checks

The pipeline currently checks:

- Raw bundle existence before extraction
- JSON validity during extraction
- Expected STIX `objects` list structure
- Required technique fields
- ATT&CK ID format
- Revoked and deprecated status
- Duplicate ATT&CK ID resolution
- JSONL validity before database loading
- Duplicate processed `attack_id` values before database loading
- SHA-256 fingerprinting of processed JSONL input

### Current external benchmark checks

The external dataset feasibility process currently checks:

- Presence of Expert train, development, and test splits
- Expected `text1` and `labels` fields
- ATT&CK label ID pattern
- Presence of explicit ATT&CK IDs in the narrative text
- Explicit MITRE, ATT&CK, or mapping wording in the narrative text
- Exact and substring overlap with procedure-example text
- Compatibility of all expected labels with the active local Enterprise ATT&CK corpus
- Test-record eligibility where every expected label is active

### Planned checks

- Automated corpus-profile report with counts and missing-value checks
- Sampled manual review of extracted ATT&CK records
- Record-count comparison against the selected source release
- Parent-technique relationship validation for sub-techniques
- Database row-count comparison against processed JSONL
- Embedding completeness check
- Source URL spot checks
- Development-split review of external narrative content types
- Frozen curation rules for the external benchmark
- Retrieval-result inspection against the curated benchmark
- Human review of candidate validity, retrieval grounding, narrative grounding, uncertainty handling, and analyst usefulness

Evaluation-specific checks and retrieval metrics belong in [`evaluation-notes.md`](evaluation-notes.md).

---

## Known limitations

- The retrieval corpus contains ATT&CK techniques and sub-techniques only; it does not contain observed real-world incident narratives.
- The corpus excludes procedure examples, relationships, software, groups, campaigns, mitigations, detections, data sources, and data components.
- `parent_attack_id` may remain `null` until parent-technique enrichment is implemented.
- The corpus can change when built from the moving upstream default reference.
- ATT&CK descriptions may not use the same wording as an analyst's incident narrative.
- Retrieval results are relevance suggestions for analyst review, not verified incident findings.
- ATT&CK coverage does not guarantee complete behavioural, detection, defensive, or incident-response coverage.
- The external Expert dataset is multi-label, and its label lists do not identify a verified single primary technique.
- The external dataset's README declares CC BY 4.0, but it does not itemise the provenance or original redistribution terms for each underlying threat-report paragraph.
- The external benchmark remains a candidate until development-split curation rules, answer format, and evaluation rubric are frozen.

---

## Source attribution

Cyber Threat Identifier uses MITRE ATT&CK content under MITRE's terms of use.

The repository and any distributed derived corpus artefact must retain applicable MITRE copyright, licence, and attribution wording.

Cyber Threat Identifier is independent and must not imply affiliation with, sponsorship by, or endorsement from The MITRE Corporation.

Use **MITRE ATT&CK®** for the first substantive public reference, then use **ATT&CK** where appropriate. Do not use ATT&CK in the project, product, repository, service, company, or logo name.

The Security-TTP-Mapping repository requests citation of its associated EACL 2024 paper. If the Expert subset is used in final evaluation, record the repository revision, cite the upstream work, link the repository, and state that any project benchmark was filtered or adapted from the upstream Expert data.

See:

- [MITRE ATT&CK Terms of Use](https://attack.mitre.org/resources/legal-and-branding/terms-of-use/)
- [MITRE ATT&CK Legal and Branding Guidance](https://attack.mitre.org/resources/legal-and-branding/)
- [Security-TTP-Mapping repository](https://github.com/tumeteor/mitre-ttp-mapping)

---

## Open dataset questions

- Which ATT&CK release tag or commit should become the first fixed formal evaluation baseline?
- Should `parent_attack_id` be populated in the next extraction iteration?
- Which metadata fields improve semantic retrieval without biasing results too strongly?
- Should tactics and platforms be retrieval-ranking features, optional filters, or both?
- When should procedure examples be added as a separate evidence layer?
- What frozen curation thresholds should be selected from `expert_dev.tsv`?
- What public artefact, if any, may contain external threat-report narrative text after provenance and redistribution review?