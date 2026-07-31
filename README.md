# Cyber Threat Identifier

Cyber Threat Identifier is an evidence-oriented retrieval system that maps unstructured cyber incident narratives to likely Enterprise MITRE ATT&CK® techniques and sub-techniques.

It helps analysts review ranked technique candidates, source-grounded descriptions, and relevant metadata. It supports analyst judgement; it does not determine attribution, severity, incident-response actions, or complete behavioural coverage.

> **Project status (v1):**  
> - Source-to-vector pipeline, text retrieval, vector retrieval, hybrid retrieval, and external label-compatibility checks are implemented and tested.  
> - Vector retrieval is the default candidate backend; hybrid is a slightly stronger but more complex alternative kept as a benchmarked option.  
> - Candidate-answer generation is implemented and under evaluation; benchmark curation and human-review scoring are in progress.

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

Version 1 focuses on a narrow incident-to-technique task: given a narrative, retrieve plausible Enterprise ATT&CK techniques and sub-techniques and generate a candidate-focused summary for analyst review.

### Included

- Official Enterprise MITRE ATT&CK STIX 2.1 data.
- Active ATT&CK techniques and sub-techniques only.
- Technique IDs, names, tactics, platforms, descriptions, URLs, and timestamps.
- Reproducible download, extraction, PostgreSQL loading, and embedding stages.
- A small internal benchmark for early pipeline checks.
- An external benchmark candidate based on expert-labelled threat-report narratives.
- Candidate-oriented answers grounded in retrieved ATT&CK records (initial implementation).

### Out of scope

- Threat actor, group, or campaign attribution.
- Incident severity assessment or triage decisions.
- Incident-response recommendations or playbooks.
- Attack-path planning or reconstruction.
- Detection engineering automation.
- ATT&CK groups, software, campaigns, mitigations, relationships, detection content, and data sources as primary retrieval units.
- External incident reports or vendor intelligence as primary retrieval corpus records.
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
Generate grounded candidate answers
        ↓
Evaluate retrieval and answers
```

The retrieval unit is intentionally simple:

```text
one ATT&CK technique or sub-technique
= one processed JSONL record
= one PostgreSQL row
= one embedding vector
= one retrieval result
```

There is no chunking in v1. Each technique record is a compact, self-contained source unit that retains its identity, metadata, description, and provenance.

---

## Current implementation

### Completed

- Download official Enterprise ATT&CK STIX data and record acquisition provenance.
- Extract active Enterprise techniques and sub-techniques; exclude deprecated and revoked records from the active retrieval corpus.
- Preserve raw descriptions alongside cleaned retrieval text.
- Write `data/processed/techniques.jsonl`.
- Initialise PostgreSQL with pgvector and create `techniques` and `ingestion_runs` tables.
- Load and upsert canonical technique records.
- Generate normalised baseline embeddings with `sentence-transformers/all-MiniLM-L6-v2`.
- Record ingestion and embedding runs in an audit table.
- Implement:
  - a text-retrieval baseline over the active technique corpus,
  - a vector-retrieval backend over the same corpus,
  - a hybrid retrieval baseline using Reciprocal Rank Fusion over text and vector ranked lists.
- Run retrieval benchmarks comparing text, vector, and hybrid retrieval over Expert-derived evaluation cases.
- Inspect an external expert-labelled threat-report dataset for future end-to-end evaluation.
- Validate external benchmark labels against the current active Enterprise ATT&CK corpus.
- Implement a first answer-generation path that:
  - retrieves top-k ATT&CK candidates via vector search,
  - asks an LLM to select a primary and alternate techniques,
  - constrains the answer to retrieved ATT&CK records,
  - records uncertainty and a review-required flag.

### Planned

- Refine candidate-answer prompts and format based on retrieval and rubric results.
- Curate the external Expert development split and freeze inclusion rules before using the held-out test split.
- Run scored human-review evaluations using a rubric for:
  - candidate validity,
  - retrieval grounding,
  - narrative grounding,
  - uncertainty handling,
  - analyst usefulness.
- Use failure analysis to refine retrieval configuration (e.g., vector depth, hybrid parameters) and answer prompts.
- Implement an analyst-facing Streamlit interface to:
  - accept incident narratives,
  - show ranked ATT&CK candidates and evidence,
  - display generated answers and metadata,
  - capture human-review scores and notes.
- Add optional monitoring and user feedback hooks.

At the current retrieval benchmark, hybrid retrieval is slightly stronger than pure vector retrieval on some ranking metrics (e.g., Recall@1/3, Hit@3, MRR) but identical at higher cutoffs. Vector retrieval is therefore the current default retrieval backend for v1 because it is simpler and cheaper to run, with hybrid retained as an evaluated alternative that can be promoted later if future gains justify the additional complexity.

---

## Evaluation overview

Evaluation distinguishes retrieval quality from answer quality.

| Layer | Question | Example measures |
|---|---|---|
| Retrieval | Are relevant active ATT&CK records returned near the top? | Hit@k, Recall@k, MRR, latency |
| Answer generation | Is the answer concise, appropriately uncertain, and grounded in the narrative and retrieved records? | Human rubric for validity, grounding, and usefulness |
| Reproducibility | Can the same fixed corpus and configuration reproduce comparable results? | Pinned source version, fixed benchmark, logged model and prompt settings |

The project uses:

- an internal small benchmark for early pipeline checks, and
- the Expert subset of the public Security-TTP-Mapping dataset as an external candidate benchmark.

The external Expert test split contains 157 expert-labelled threat-report narratives; 153 records contain only labels active in the current Enterprise ATT&CK corpus. External narratives remain local during feasibility and development; the project does not redistribute copied third-party threat-report passages.

Details of metrics, benchmark design, and experiment results live in `docs/evaluation-notes.md`.

---

## Quick start

### Prerequisites

- Python version specified in `pyproject.toml`.
- [uv](https://docs.astral.sh/uv/) for environment and dependency management.
- Docker Desktop (or compatible Docker engine).
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

and populates the PostgreSQL tables:

```text
techniques
ingestion_runs
```

For setup details, database checks, rebuild instructions, retrieval-benchmark commands, and troubleshooting, see `docs/runbook.md`.

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
│   │   ├── __init__.py
│   │   ├── text.py
│   │   ├── vector.py
│   │   ├── hybrid.py
│   │   └── embedding_model.py
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── metrics.py
│   │   ├── run_expert_text_retrieval_benchmark.py
│   │   ├── run_expert_vector_retrieval_benchmark.py
│   │   ├── run_expert_hybrid_retrieval_benchmark.py
│   │   ├── run_expert_answer_generation.py
│   │   ├── run_expert_answer_judge.py
│   │   └── validate_external_expert_labels.py
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── prompts.py
│   │   └── answer_generator.py
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
│   │   ├── expert_label_compatibility.csv
│   │   └── expert_answer_generation_v1.csv
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
| `docs/runbook.md` | Setup, pipeline execution, verification, reset, retrieval and generation commands, troubleshooting |
| `docs/dataset-notes.md` | Corpus scope, provenance, schema, processing, artefact policy, limitations |
| `docs/decisions.md` | Stable architecture, corpus, evaluation, and publication decisions |
| `docs/evaluation-notes.md` | Benchmark design, metrics, experiments, retrieval and answer results, failure analysis |
| `docs/project-log.md` | Chronological implementation progress, discoveries, and next steps |

---

## Limitations

- The v1 retrieval corpus contains active Enterprise ATT&CK techniques and sub-techniques only.
- Returned results are relevance suggestions for analyst review, not verified incident findings.
- The embedding model (`all-MiniLM-L6-v2`) is a baseline and may change after comparative answer evaluation.
- ATT&CK coverage does not guarantee that every observed behaviour or technique variation is represented.
- The external benchmark candidate is multi-label and must be curated using frozen development-split rules before final held-out evaluation.
- An external benchmark narrative may legitimately correspond to several techniques; a single returned candidate does not establish complete behavioural coverage.

---

## MITRE ATT&CK attribution

Cyber Threat Identifier is an independent project. It is not affiliated with, sponsored by, or endorsed by The MITRE Corporation.

MITRE ATT&CK® is used as the project’s source knowledge base. The project name does not use ATT&CK because MITRE’s branding guidance restricts use of ATT&CK in product, service, company, and logo names.

The repository contains derived ATT&CK content. Before distributing a corpus snapshot or other derived artefact, retain the applicable MITRE copyright, licence, and attribution wording.

- MITRE ATT&CK Terms of Use  
- MITRE ATT&CK Legal and Branding Guidance  