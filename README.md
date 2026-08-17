# Cyber Threat Identifier

Cyber Threat Identifier is an independent, evidence-oriented retrieval system that maps unstructured cyber incident narratives to likely Enterprise MITRE ATT&CK® techniques and sub-techniques. *(See [MITRE ATT&CK attribution](#mitre-attck-attribution) below).*

It helps analysts inspect ranked technique candidates, ATT&CK descriptions, and relevant metadata. It supports analyst judgement; it does not determine attribution, severity, incident-response actions, or complete behavioural coverage.

> **Project status (v1)**
>
> - The deployed retrieval path uses pgvector candidate retrieval plus local cross-encoder reranking.
> - The selected answer-generation model is `gemini-3.1-flash-lite`.
> - The application includes a Streamlit Query interface, monitoring dashboard, feedback capture, and blinded evaluation-review workflow.
> - Retrieval and answer-generation configurations were evaluated on a 226-case Expert-derived implementation-comparison set.
> - The current benchmark is not a frozen held-out final benchmark.
> - Docker Compose is the canonical local runtime and ingestion path.
> - The public demonstration uses synthetic or source-informed sample narratives in `data/sample_queries.json`; it does not expose restricted expert-evaluation narratives.

---

## Reviewer Navigation

*   **[Self-Assessment & Rubric Mapping](docs/self-assessment.md):** Start here for a direct map of project features to course evaluation criteria.
*   **[Live Demo](http://44.222.157.15:8501/):** Open the AWS EC2 deployment for a 5-minute review.
*   **[Runbook](docs/runbook.md):** Complete steps for local reproduction and evaluation benchmark execution.

---

## Project Highlights

For reviewers short on time, here is a high-level summary of the system's architecture and capabilities:

*   **Automated Data Pipeline:** A fully containerized ingestion script downloads official MITRE ATT&CK STIX 2.1 data, extracts active techniques, and loads them into a PostgreSQL database with pgvector.
*   **Advanced Retrieval:** The system moves beyond basic vector search by implementing a two-stage retrieval pipeline: initial semantic search via `all-MiniLM-L6-v2`, followed by local cross-encoder document reranking (`ms-marco-MiniLM-L-6-v2`) to dramatically improve candidate ordering.
*   **Grounded Answer Generation:** Using `gemini-3.1-flash-lite`, the system generates structured, analyst-friendly assessments that are strictly grounded in the retrieved ATT&CK context, complete with uncertainty flags.
*   **Rigorous Evaluation:** Models and retrieval methods were benchmarked against a 226-case expert-derived dataset. The final architecture was selected based on reciprocal pairwise LLM-as-judge evaluation and blinded human manual review.
*   **Full Containerization:** The database, Streamlit UI, and ingestion pipelines are entirely reproducible via Docker Compose.

---

## Live demo

**[Open Cyber Threat Identifier](http://44.222.157.15:8501/)**

The application is deployed temporarily on AWS EC2 for reviewer access. It runs the same Docker Compose stack documented for local reproduction.

The deployment is a demonstration environment, not a production service. It does not include HTTPS, a custom domain, managed secrets, backups, high availability, or production monitoring.

---

## Review in five minutes

You do not need to clone the repository to review the main application workflow.

1. Open the [live demo](http://44.222.157.15:8501/).
2. Select **Query**.
3. Choose a public sample query or paste a short incident narrative, for example:

   ```text
   Attackers used PowerShell scripts to download and execute malware on victim hosts.
   ```

4. Select **Analyze**.
5. Confirm that the interface shows:
   - A generated candidate assessment.
   - Retrieved ATT&CK techniques.
   - A retrieval-grounding note.
   - An uncertainty note.
   - Feedback controls.
6. Open **Dashboard** to inspect answer latency, retrieval comparison, judge preferences, judge agreement, and feedback charts.
7. Optionally open **Evaluation Review** to inspect the completed manual-review results.

The Query workflow uses the selected v1 path:

```text
Incident narrative
        ↓
Vector retrieval of top 20 ATT&CK candidates
        ↓
Local cross-encoder reranking
        ↓
Top 5 ATT&CK records used as answer context
        ↓
Structured candidate assessment using gemini-3.1-flash-lite
```

---

## Assessment evidence

| Criterion | Evidence |
|---|---|
| Problem and scope | [Problem](#problem), [Scope](#scope), [`docs/dataset-notes.md`](docs/dataset-notes.md) |
| Knowledge base plus LLM flow | [Data Flow](#data-flow), `src/retrieval/`, `src/generation/` |
| Retrieval evaluation | [Retrieval Evaluation Summary](#retrieval-evaluation-summary), [`docs/evaluation-notes.md`](docs/evaluation-notes.md) |
| LLM evaluation | [`docs/evaluation-notes.md`](docs/evaluation-notes.md), `data/evaluation_reports/reranked/` |
| Interface | [Live demo](http://44.222.157.15:8501/), `app/` |
| Automated ingestion | [`compose.yaml`](compose.yaml), `src/ingestion/`, `src/database/` |
| Monitoring | `app/dashboard.py`, `src/monitoring/feedback_store.py` |
| Containerization | [`app/Dockerfile`](app/Dockerfile), [`compose.yaml`](compose.yaml) |
| Reproducibility | [Local Reproduction](#local-reproduction--developer-rebuild), [`docs/runbook.md`](docs/runbook.md), `uv.lock` |
| Self-assessment | [`docs/self-assessment.md`](docs/self-assessment.md) |

---

## Problem

Security analysts are constantly inundated with unstructured material—alert notes, ticket comments, investigation summaries, and external threat reports. Extracting actionable intelligence from this text requires mapping observed adversary behaviours to standardized frameworks like MITRE ATT&CK.

Doing this manually is a slow, cognitively demanding, and inconsistent process because official ATT&CK guidance is vast and not trivially searchable by raw narrative text alone.

**Cyber Threat Identifier** solves this by providing a retrieval-augmented generation (RAG) assistant. Rather than relying on a general LLM's ungrounded advice, it semantically searches a curated ATT&CK corpus, retrieves the most relevant technique records, and generates a structured assessment. It explicitly surfaces its supporting evidence and uncertainty, keeping the human analyst in the loop while drastically reducing their manual search time.

---

## Scope

Version 1 focuses on a narrow incident-to-technique task: given an incident narrative, retrieve plausible Enterprise ATT&CK techniques and sub-techniques, then generate a candidate-focused summary for analyst review.

### Included

- Official Enterprise MITRE ATT&CK STIX 2.1 data
- Active ATT&CK techniques and sub-techniques only
- Technique IDs, names, tactics, platforms, descriptions, URLs, and timestamps
- PostgreSQL with pgvector for structured technique records and embeddings
- Vector retrieval plus local cross-encoder reranking
- Structured answer generation grounded in retrieved ATT&CK records
- Streamlit Query, Dashboard, and Evaluation Review interfaces
- User feedback capture
- Automated Docker Compose ingestion
- Public sample queries from `data/sample_queries.json`

### Out of scope

- Threat actor, group, or campaign attribution
- Incident severity assessment or triage decisions
- Incident-response recommendations or playbooks
- Attack-path planning or reconstruction
- Detection engineering automation
- Confirming that a technique definitively occurred in an incident
- ATT&CK groups, software, campaigns, mitigations, relationships, detection content, and data sources as primary retrieval units
- External incident reports or vendor intelligence as primary retrieval corpus records
- Public exposure of restricted expert-evaluation narratives

---

## Local Reproduction & Developer Rebuild

For full environment setup, database initialization, containerized execution, LLM configuration, and targeted rebuilds, please refer to the **[Runbook](docs/runbook.md)**.

---

## Data Flow

The project uses active Enterprise ATT&CK `attack-pattern` objects from the official ATT&CK STIX source. For extraction rules, schema details, and the full pipeline flow, please refer to the **[Dataset Notes](docs/dataset-notes.md)**.

---

## Retrieval Evaluation Summary

The selected v1 configuration utilizes vector retrieval plus local cross-encoder reranking. This approach improved every reported retrieval metric (including MRR and Hit rates) over baseline vector-only retrieval. For the complete benchmark methodology, detailed metric tables, and latency trade-offs, see the **[Evaluation Notes](docs/evaluation-notes.md)**.

The current retrieval and answer-generation results were produced using a 226-case Expert-derived implementation-comparison set. The derived benchmark input is not committed. Reviewers can obtain the upstream Expert dataset from the documented [Security-TTP-Mapping](https://github.com/tumeteor/mitre-ttp-mapping) source and exact revision, then follow the evaluation workflow to recreate or extend the benchmark. Source provenance, methodology, and the exact upstream revision are documented in [`docs/dataset-notes.md`](docs/dataset-notes.md).

---

## Current implementation

### Completed

- Download and provenance tracking for official Enterprise ATT&CK STIX data.
- Extraction of active Enterprise ATT&CK techniques and sub-techniques.
- Exclusion of deprecated and revoked objects from the active retrieval corpus.
- Processed ATT&CK corpus output at `data/processed/techniques.jsonl`.
- PostgreSQL + pgvector database initialisation.
- Technique loading, upserting, embedding generation, and ingestion audit records.
- Normalised local embeddings using `sentence-transformers/all-MiniLM-L6-v2`.
- Text retrieval baseline.
- Vector retrieval baseline.
- Hybrid retrieval baseline using Reciprocal Rank Fusion.
- Local document reranking using `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- Query rewriting evaluation with Gemini 3.1 Flash Lite (evaluated, not deployed).
- Retrieval benchmark scripts and per-case evaluation reports.
- External Expert-label compatibility validation.
- Structured answer-generation baseline with primary candidate, alternatives, supporting IDs, uncertainty, grounding note, and review-required output, using vector-plus-reranking retrieval.
- Pairwise LLM-as-judge evaluation of answer-generation outputs using `gemini-3.1-flash-lite` and `gemini-3.5-flash-lite`.
- Cross-judge agreement analysis and blinded manual review of all 55 reranked judge-disagreement cases.
- Model-selection decision: `gemini-3.1-flash-lite` selected as default v1 answer-generation model (DEC-021).
- Streamlit analyst-facing UI and monitoring dashboard.
- Persisted feedback capture.
- Application Dockerfile and Compose configuration for PostgreSQL, Streamlit, and automated ingestion.
- Committed evaluation artefacts for marker inspection.

### Planned

- Optional future work (beyond v1 assessment scope):
  - Formalise a human-readable answer-evaluation rubric and score an additional review subset.
  - Freeze curation rules using `expert_dev.tsv` and run a final held-out external evaluation against compatible curated `expert_test.tsv` cases.
  - Dynamic dashboard loading for retrieval-comparison benchmark values.
  - Production hardening beyond the current temporary EC2 demonstration deployment.

---

## User interface

The project includes a Streamlit-based analyst-facing UI and monitoring dashboard.

### Tabs

- **Home**: Overview, data sources, and ATT&CK usage information.
- **Query**: Incident narrative input, retrieval with reranking, structured answer generation, retrieved-technique inspection, and feedback capture.
- **Dashboard**: Monitoring dashboard with evaluation metrics and charts.
- **Evaluation Review**: Manual review workflow for cases where the two LLM judges disagree.

---

## Repository structure

_Representative structure (simplified and alphabetically ordered):_

```text
cyber-threat-identifier/
├── app/                          # Streamlit UI and monitoring dashboard
├── compose.yaml                  # Docker Compose runtime (PostgreSQL, Streamlit, ingestion)
├── data/                         # Processed corpus, evaluation inputs/outputs, feedback
│   ├── eval/                     # Expert-derived retrieval benchmark cases
│   ├── evaluation_reports/       # Retrieval and LLM-evaluation CSVs
│   ├── feedback/                 # Persisted user feedback
│   ├── processed/                # Reviewed ATT&CK techniques JSONL
│   └── source_manifest.csv       # ATT&CK source provenance
├── docs/                         # Documentation and assessment artefacts
│   ├── decisions.md              # Architecture and evaluation decisions (DEC-*)
│   ├── dataset-notes.md          # Corpus scope, schema, and processing rules
│   ├── evaluation-notes.md       # Benchmark design, metrics, and results
│   ├── runbook.md                # Local reproduction, commands, and troubleshooting
│   └── self-assessment.md        # Criterion-by-criterion self-assessment
├── pyproject.toml                # Python project metadata and dependencies
├── README.md                     # Project overview and assessment evidence map
├── src/                          # Python source code
│   ├── database/                 # PostgreSQL + pgvector initialisation and loading
│   ├── evaluation/               # Retrieval benchmarks, LLM-as-judge, and manual review
│   ├── generation/               # Answer-generation prompts and orchestration
│   ├── ingestion/                # ATT&CK download and extraction scripts
│   ├── monitoring/               # Feedback persistence and helpers
│   └── retrieval/                # Embedding, text, vector, hybrid, reranking, and rewriting
├── uv.lock                       # Locked Python dependency versions
└── .env.example                  # Example environment configuration
```

---

## Documentation

| Document | Purpose |
|---|---|
| [`docs/runbook.md`](docs/runbook.md) | Setup, pipeline commands, verification, rebuilds, benchmarks, answer-generation, UI, and troubleshooting |
| [`docs/dataset-notes.md`](docs/dataset-notes.md) | Corpus scope, provenance, schema, processing rules, artefact policy, and limitations |
| [`docs/decisions.md`](docs/decisions.md) | Stable architecture, corpus, retrieval, and evaluation decisions |
| [`docs/evaluation-notes.md`](docs/evaluation-notes.md) | Benchmark design, metrics, retrieval results, answer evaluation, LLM-as-judge analysis, and failure analysis |
| [`docs/project-log.md`](docs/project-log.md) | Chronological progress, discoveries, and immediate next steps |

---

## Limitations

- The retrieval corpus contains active Enterprise ATT&CK techniques and sub-techniques only.
- Results are ranked relevance suggestions for analyst review, not verified incident findings.
- The local reranker can improve ordering only within its first-stage vector candidate pool.
- The selected reranker is a compact general-domain model, not a cyber-security-specific reranker.
- Query rewriting improves retrieval quality but adds ~3.1 seconds median latency; it is evaluated but not deployed for interactive use.
- LLM-as-judge evaluation is not ground truth; both judges show a tendency to prefer `gemini-3.1-flash-lite` on the current dataset.
- The external Expert dataset is multi-label and does not provide a verified single primary technique.
- The current 226-case benchmark is not a frozen held-out benchmark.
- ATT&CK coverage does not guarantee complete behavioural, defensive, detection, or incident-response coverage.

---

## MITRE ATT&CK attribution

Cyber Threat Identifier is an independent project. It is not affiliated with, sponsored by, or endorsed by The MITRE Corporation.

MITRE ATT&CK is used as the project's source knowledge base. The project name does not use ATT&CK because MITRE branding guidance restricts ATT&CK use in product, service, company, and logo names.

The repository contains derived ATT&CK content. Any distributed corpus snapshot or derived artefact must retain applicable MITRE copyright, licence, and attribution wording.

- [MITRE ATT&CK Terms of Use](https://attack.mitre.org/resources/legal-and-branding/terms-of-use/)
- [MITRE ATT&CK Legal and Branding Guidance](https://attack.mitre.org/resources/legal-and-branding/)
- [Security-TTP-Mapping repository](https://github.com/tumeteor/mitre-ttp-mapping)