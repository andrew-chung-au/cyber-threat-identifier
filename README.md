# Cyber Threat Identifier

Cyber Threat Identifier is an evidence-oriented retrieval system that maps unstructured cyber incident narratives to likely Enterprise MITRE ATT&CK® techniques and sub-techniques.

It helps analysts review ranked technique candidates, source-grounded descriptions, and relevant metadata. It supports analyst judgement; it does not determine attribution, severity, incident-response actions, or complete behavioural coverage.

> **Project status:** The source-to-vector pipeline, text retrieval, vector retrieval, hybrid retrieval, and external benchmark label-compatibility check are implemented and benchmarked. Candidate-answer generation, benchmark curation, and formal answer evaluation are the next focus.

---

## Problem

Security analysts often work from unstructured material such as alert notes, ticket comments, investigation summaries, and case write-ups.

Mapping those narratives to adversary behaviours can be slow and inconsistent. Cyber Threat Identifier provides a transparent retrieval layer over Enterprise ATT&CK techniques, returning relevant candidate records and source evidence for analyst review.

```text
Incident narrative
        ↓
Ranked likely technique candidates
        ↓
Source-grounded evidence and metadata
        ↓
Analyst review
```

---

## Scope

Version 1 focuses on a narrow incident-to-technique retrieval task.

### Included

- Official Enterprise MITRE ATT&CK STIX 2.1 data.
- Active ATT&CK techniques and sub-techniques.
- Technique IDs, names, tactics, platforms, descriptions, URLs, and timestamps.
- Reproducible download, extraction, PostgreSQL loading, and embedding stages.
- A small internal benchmark concept for early pipeline checks.
- An external benchmark candidate based on expert-labelled threat-report narratives.
- Candidate-oriented answers grounded in retrieved ATT&CK records (planned).

### Out of scope

- Threat actor, group, or campaign attribution.
- Incident severity assessment.
- Incident-response recommendations.
- Attack-path planning or reconstruction.
- Detection engineering automation.
- ATT&CK groups, software, campaigns, mitigations, relationships, procedure examples, detection strategies, analytics, data sources, and data components as retrieval corpus records.
- External incident reports or vendor intelligence as primary retrieval corpus sources.
- Confirming that a technique occurred in an incident.

---

## Data and pipeline

The project uses the official Enterprise MITRE ATT&CK STIX 2.1 dataset. Version 1 extracts active Enterprise `attack-pattern` objects from the official ATT&CK STIX source.

```text
Official Enterprise ATT&CK STIX source
        ↓
Download raw STIX bundle
        ↓
Extract active techniques and sub-techniques
        ↓
Write processed JSONL corpus
        ↓
Load canonical records into PostgreSQL
        ↓
Generate embeddings with pgvector storage
        ↓
Retrieve technique candidates from incident narratives
        ↓
Evaluate retrieval and grounded answers
```

The retrieval unit is intentionally simple:

```text
one ATT&CK technique or sub-technique
=
one processed JSONL record
=
one PostgreSQL row
=
one embedding vector
=
one retrieval result
```

The initial corpus is not chunked. Each technique record is a compact, self-contained source unit that retains its identity, metadata, description, and provenance.

---

## Current implementation

Completed:

- Download official Enterprise ATT&CK STIX data and record acquisition provenance.
- Extract active Enterprise techniques and sub-techniques.
- Exclude deprecated and revoked ATT&CK technique records from the active retrieval corpus.
- Preserve raw descriptions alongside cleaned retrieval text.
- Write `data/processed/techniques.jsonl`.
- Initialise PostgreSQL with pgvector.
- Load and upsert canonical technique records.
- Generate normalised baseline embeddings with `sentence-transformers/all-MiniLM-L6-v2`.
- Record ingestion and embedding runs in an audit table.
- Implement a text-retrieval baseline over the active technique corpus.
- Implement a vector-retrieval baseline over the same corpus.
- Implement a hybrid retrieval baseline using Reciprocal Rank Fusion over text and vector ranked lists.
- Run retrieval benchmarks comparing text, vector, and hybrid retrieval over Expert-derived evaluation cases.
- Inspect an external expert-labelled threat-report dataset for future end-to-end evaluation.
- Validate external benchmark labels against the current active Enterprise ATT&CK corpus.

Planned:

- Candidate-answer generation grounded in retrieved records.
- Development-split benchmark curation and scoring-rubric design.
- Human-review answer evaluation for candidate validity, retrieval grounding, narrative grounding, uncertainty handling, and analyst usefulness.
- Evidence-based refinement of retrieval configuration, including the option to promote hybrid retrieval to default if future gains justify its added complexity and compute cost.
- Streamlit analyst interface.
- Optional monitoring and user feedback.

At the current retrieval benchmark, hybrid retrieval is slightly stronger than pure vector retrieval on some ranking metrics but identical at higher cutoffs. Vector is therefore the current default retrieval backend for v1 because it is simpler and cheaper to run, with hybrid retained as an evaluated alternative.

---

## Evaluation approach

Evaluation will distinguish retrieval quality from answer quality.

| Layer | Question | Example measures |
|---|---|---|
| Retrieval | Are relevant active ATT&CK records returned near the top? | Hit@K, Recall@K, MRR, latency |
| Answer generation | Is the answer concise, appropriately uncertain, and grounded in the narrative and retrieved records? | Human rubric for validity, grounding, and usefulness |
| Reproducibility | Can the same fixed corpus and configuration reproduce comparable results? | Pinned source version, fixed benchmark, logged model and prompt settings |

The project has identified the Expert subset of the public Security-TTP-Mapping dataset as an external benchmark candidate. Its held-out test split contains 157 expert-labelled threat-report narratives; 153 records contain only labels active in the current Enterprise ATT&CK corpus.

The external source remains local during feasibility and development work. The project does not currently redistribute copied third-party threat-report passages.

Vector retrieval is the current default method for ATT&CK candidate retrieval. Hybrid retrieval is implemented and benchmarked as a slightly stronger but more complex alternative that may be promoted later if future lexical improvements or corpus changes increase its advantage.

---

## Quick start

### Prerequisites

- Python version specified in `pyproject.toml`.
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop.
- Git.

### Install and configure

```bash
git clone <repository-url>
cd cyber-threat-identifier

uv sync

cp .env.example .env

docker compose up -d
docker compose ps
```

Wait until PostgreSQL reports as healthy before running database stages.

### Build the corpus

Run these commands from the repository root:

```bash
uv run python -m src.ingestion.download_attack_data

uv run python -m src.ingestion.extract_attack_techniques

uv run python -m src.database.db_init

uv run python -m src.database.db_load_techniques

uv run python -m src.database.db_build_embeddings
```

The pipeline produces:

```text
data/processed/techniques.jsonl
data/source_manifest.csv
```

It also creates and populates these PostgreSQL tables:

```text
techniques
ingestion_runs
```

For setup details, database checks, rebuild instructions, retrieval-benchmark commands, and troubleshooting, see [`docs/runbook.md`](docs/runbook.md).

---

## Reproducibility

The downloader uses the current upstream reference by default. For a fixed evaluation baseline, use a release tag or commit:

```bash
uv run python -m src.ingestion.download_attack_data --ref <release-tag-or-commit>
```

For example:

```bash
uv run python -m src.ingestion.download_attack_data --ref v19.1
```

Each download is recorded in `data/source_manifest.csv` with the source URL, reference, local path, timestamp, SHA-256 checksum, and notes.

The repository includes the processed corpus snapshot, `data/processed/techniques.jsonl`, so reviewers can inspect retrieval records without downloading the raw STIX bundle. Raw upstream downloads are regenerated by the ingestion pipeline and excluded from Git.

External datasets used only for feasibility inspection are stored in `data/external_inspection/` and excluded from Git. The label-compatibility report contains only ATT&CK identifiers and statuses, not copied threat-report text.

---

## Repository structure

```text
cyber-threat-identifier/
├── README.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── compose.yaml
├── app.py
│
├── src/
│   ├── __init__.py
│   ├── db.py
│   ├── llm_client.py
│   ├── pricing.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── download_attack_data.py
│   │   └── extract_attack_techniques.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db_init.py
│   │   ├── db_load_techniques.py
│   │   └── db_build_embeddings.py
│   ├── retrieval/
│   │   └── __init__.py
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── run_expert_text_retrieval_benchmark.py
│   │   ├── run_expert_vector_retrieval_benchmark.py
│   │   ├── run_expert_hybrid_retrieval_benchmark.py
│   │   └── validate_external_expert_labels.py
│   └── monitoring/
│       └── __init__.py
│
├── data/
│   ├── raw/
│   │   └── attack/
│   ├── processed/
│   │   └── techniques.jsonl
│   ├── eval/
│   │   └── expert_retrieval_cases.csv
│   ├── evaluation_reports/
│   │   ├── expert_text_retrieval_results.csv
│   │   ├── expert_vector_retrieval_results.csv
│   │   ├── expert_hybrid_retrieval_results.csv
│   │   └── expert_label_compatibility.csv
│   ├── external_inspection/
│   └── source_manifest.csv
│
├── docs/
│   ├── project-log.md
│   ├── decisions.md
│   ├── dataset-notes.md
│   ├── evaluation-notes.md
│   └── runbook.md
│
└── tests/
```

---

## Documentation

| Document | Purpose |
|---|---|
| [`docs/runbook.md`](docs/runbook.md) | Setup, pipeline execution, verification, reset, retrieval-benchmark commands, and troubleshooting |
| [`docs/dataset-notes.md`](docs/dataset-notes.md) | Corpus scope, provenance, schema, processing, artefact policy, and limitations |
| [`docs/decisions.md`](docs/decisions.md) | Stable architecture, corpus, evaluation, and publication decisions |
| [`docs/evaluation-notes.md`](docs/evaluation-notes.md) | Benchmark design, metrics, experiments, retrieval results, and failure analysis |
| [`docs/project-log.md`](docs/project-log.md) | Chronological implementation progress, discoveries, and next steps |

---

## Limitations

- The v1 retrieval corpus contains active Enterprise ATT&CK techniques and sub-techniques only.
- Returned results are relevance suggestions for analyst review, not verified incident findings.
- The embedding model is an initial baseline and has not yet been chosen through comparative answer evaluation.
- ATT&CK coverage does not guarantee that every observed behaviour or technique variation is represented.
- The project does not currently perform attribution, severity assessment, attack-path analysis, or incident-response planning.
- The external benchmark candidate is multi-label and must be curated using frozen development-split rules before final held-out evaluation.
- An external benchmark narrative may legitimately correspond to several techniques; a single returned candidate does not establish complete behavioural coverage.

---

## MITRE ATT&CK attribution

Cyber Threat Identifier is an independent project. It is not affiliated with, sponsored by, or endorsed by The MITRE Corporation.

MITRE ATT&CK® is used as the project’s source knowledge base. The project name does not use ATT&CK because MITRE’s branding guidance restricts use of ATT&CK in product, service, company, and logo names.

The repository contains derived ATT&CK content. Before distributing a corpus snapshot or other derived artefact, retain the applicable MITRE copyright, licence, and attribution wording.

- [MITRE ATT&CK Terms of Use](https://attack.mitre.org/resources/legal-and-branding/terms-of-use/)
- [MITRE ATT&CK Legal and Branding Guidance](https://attack.mitre.org/resources/legal-and-branding/)