# Cyber Threat Identifier

Cyber Threat Identifier is an evidence-oriented retrieval system that maps unstructured cyber incident narratives to likely Enterprise MITRE ATT&CK® techniques and sub-techniques.

It helps analysts inspect ranked technique candidates, ATT&CK descriptions, and relevant metadata. It supports analyst judgement; it does not determine attribution, severity, incident-response actions, or complete behavioural coverage.

> **Project status (v1):**
> - The ATT&CK ingestion, PostgreSQL + pgvector database, text, vector, hybrid, and local document-reranking retrieval paths are implemented.
> - Vector retrieval plus local cross-encoder reranking is the selected v1 retrieval configuration based on the current 226-case Expert-derived benchmark.
> - Query rewriting with LLM (Gemini 3.1 Flash Lite) was evaluated and improved retrieval metrics but introduced unacceptable latency for interactive use; it is retained as an evaluated best-practice component.
> - The answer-generation pipeline uses vector retrieval plus local cross-encoder reranking and produces structured, retrieval-grounded outputs.
> - Pairwise LLM-as-judge evaluation (3.1 vs 3.5) and cross-judge agreement analysis over 226 expert-derived cases are implemented (DEC-020). All 55 judge-disagreement cases were manually reviewed blind to model identity.
> - Gemini 3.1 Flash-Lite is selected as the default v1 answer-generation model based on manual-review results (DEC-021).
> - An analyst-facing Streamlit UI and monitoring dashboard are implemented with four tabs: Home, Query, Dashboard, and Evaluation Review.
> - Feedback persistence is implemented; an empty feedback chart means no feedback has yet been submitted.
> - A frozen held-out external benchmark remains in progress.

---

## Problem

Security analysts often work from unstructured material such as alert notes, ticket comments, investigation summaries, and incident write-ups.

Mapping those narratives to adversary behaviours can be slow and inconsistent. Cyber Threat Identifier provides a transparent ATT&CK retrieval layer that returns ranked technique candidates and source-grounded evidence for analyst review.

```text
Incident narrative
        ↓
Ranked likely ATT&CK technique candidates
        ↓
ATT&CK descriptions and metadata
        ↓
Structured candidate assessment
        ↓
Analyst review
```

---

## Scope

Version 1 focuses on a narrow incident-to-technique task: given an incident narrative, retrieve plausible Enterprise ATT&CK techniques and sub-techniques, then generate a candidate-focused summary for analyst review.

### Included

- Official Enterprise MITRE ATT&CK STIX 2.1 data.
- Active ATT&CK techniques and sub-techniques only.
- Technique IDs, names, tactics, platforms, descriptions, URLs, and timestamps.
- Reproducible ATT&CK download, extraction, PostgreSQL loading, and embedding stages.
- Text, vector, hybrid, and vector-plus-reranking retrieval evaluation.
- Query-rewriting retrieval evaluation with LLM (Gemini 3.1 Flash Lite).
- A local CPU cross-encoder reranker over vector-retrieved ATT&CK candidates.
- An external Expert-derived evaluation source for retrieval and future answer evaluation.
- Structured answer generation grounded in retrieved ATT&CK records using vector-plus-reranking retrieval.
- Pairwise LLM-as-judge evaluation and judge-agreement analysis over 226 Expert-derived answer-generation cases (3.1 vs 3.5).
- Manual review of all 55 judge-disagreement cases blind to model identity.
- Streamlit analyst-facing UI and monitoring dashboard with four tabs: Home, Query, Dashboard, and Evaluation Review.
- Persisted feedback capture linked to query, answer, model, and retrieved techniques.

### Out of scope

- Threat actor, group, or campaign attribution.
- Incident severity assessment or triage decisions.
- Incident-response recommendations or playbooks.
- Attack-path planning or reconstruction.
- Detection engineering automation.
- Confirming that a technique definitively occurred in an incident.
- ATT&CK groups, software, campaigns, mitigations, relationships, detection content, and data sources as primary retrieval units.
- External incident reports or vendor intelligence as primary retrieval corpus records.

---

## Data and retrieval flow

The project uses active Enterprise ATT&CK `attack-pattern` objects from the official ATT&CK STIX source.

```text
Official Enterprise ATT&CK STIX source
        ↓
Extract active techniques and sub-techniques
        ↓
Processed JSONL corpus
        ↓
PostgreSQL + pgvector
        ↓
all-MiniLM-L6-v2 vector retrieval
        ↓
Top 20 ATT&CK candidates
        ↓
Local cross-encoder reranking
        ↓
Ranked candidate techniques
        ↓
Structured answer generation (gemini-3.1-flash-lite default)
        ↓
Analyst-facing retrieval and answer-generation integration
```

The retrieval unit is intentionally simple:

```text
one ATT&CK technique or sub-technique
= one processed JSONL record
= one PostgreSQL row
= one structured embedding_text field
= one embedding vector
= one retrieval result
```

Version 1 does not chunk ATT&CK technique records. Each record remains a complete source-native unit with technique identity, tactics, platforms, description, and provenance retained together.

---

## Retrieval evaluation

The current retrieval benchmark uses 226 Expert-derived cases in:

```text
data/eval/expert_retrieval_cases.csv
```

It compares text-only retrieval, vector retrieval, hybrid retrieval using Reciprocal Rank Fusion, and vector retrieval plus local document reranking.

| Method | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Hit@3 | Hit@10 | MRR |
|---|---:|---:|---:|---:|---:|---:|---:|
| Text | 0.0088 | 0.0133 | 0.0133 | 0.0133 | 0.0133 | 0.0133 | 0.0111 |
| Vector | 0.1098 | 0.1940 | 0.2710 | 0.3551 | 0.3540 | 0.5619 | 0.3134 |
| Hybrid | 0.1120 | 0.2029 | 0.2710 | 0.3551 | 0.3628 | 0.5619 | 0.3151 |
| Vector + reranking | 0.1462 | 0.2526 | 0.3104 | 0.3866 | 0.4159 | 0.5973 | 0.3578 |
| Query rewrite + vector + rerank | 0.1495 | 0.2966 | 0.3507 | 0.4581 | 0.4690 | 0.6726 | 0.3940 |

The selected v1 configuration is:

```text
sentence-transformers/all-MiniLM-L6-v2
        ↓
pgvector cosine-similarity retrieval of top 20 records
        ↓
cross-encoder/ms-marco-MiniLM-L-6-v2 reranking on local CPU
        ↓
Ranked ATT&CK candidates
```

Vector-plus-reranking improved every reported retrieval metric over vector-only retrieval. MRR increased from 0.3134 to 0.3578, and Hit@3 increased from 0.3540 to 0.4159.

Query rewriting further improved all metrics (MRR: 0.3940, Hit@3: 0.4690) but introduced substantial latency: median total retrieval time was 4,362 ms (vs 1,255 ms for vector + rerank), with median query-rewrite time of 3,184 ms. This latency is unacceptable for interactive analyst-assist workflows.

The quality improvement has a latency cost: median end-to-end retrieval time was 1,254.79 ms, p95 end-to-end latency was 1,451.74 ms, median reranking time was 1,223.29 ms, and p95 reranking time was 1,414.23 ms on the current local CPU benchmark. This trade-off is accepted for the v1 analyst-assist workflow.

These results are implementation-comparison results, not final held-out performance. The current 226-case input includes development- and test-derived records; final external evaluation will use frozen development-split curation rules before evaluation against the held-out Expert test split.

Full benchmark methodology, results, and limitations are documented in [`docs/evaluation-notes.md`](docs/evaluation-notes.md).

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
- Pairwise LLM-as-judge evaluation of answer-generation outputs using:
  - `src.evaluation.run_llm_judge_pairwise` with `gemini-3.1-flash-lite` and `gemini-3.5-flash-lite` as judges.
  - Randomised A/B presentation of model outputs.
  - JSON-structured verdicts including reasoning, winner, and confidence.
- Cross-judge agreement analysis using `src.evaluation.analyze_judge_agreement` and persisted outputs:
  - `data/evaluation_reports/reranked/judge_agreement_summary.csv`
  - `data/evaluation_reports/reranked/judge_disagreements.csv`
- Manual review of all 55 reranked judge-disagreement cases blind to model identity using `app/evaluation.py`.
- Model-selection decision: `gemini-3.1-flash-lite` selected as default v1 answer-generation model (DEC-021).
- Streamlit analyst-facing UI and monitoring dashboard:
  - Main app (`app/home.py`) with Home, Query, Dashboard, and Evaluation Review tabs.
  - Query interface (`app/query.py`) for incident-to-ATT&CK mapping with vector-plus-reranking retrieval and structured answer generation.
  - Monitoring dashboard (`app/dashboard.py`) with evaluation charts for latency, both judges' preferences, retrieval comparison, agreement rate, and user feedback.
  - Evaluation Review tab for manual adjudication of judge-disagreement cases.
- Persisted feedback capture through `src.monitoring.feedback_store.save_feedback`.
- Application Dockerfile for Streamlit (`app/Dockerfile`).

### Planned

- Finalise a human-readable answer-evaluation rubric and score a review subset.
- Freeze curation rules using `expert_dev.tsv`.
- Run final held-out external evaluation against compatible curated `expert_test.tsv` cases.
- Dynamic dashboard loading for retrieval-comparison benchmark values.
- Full application Docker Compose configuration for production deployment.

---

## Quick start

### Prerequisites

- Python version specified in `pyproject.toml`.
- [uv](https://docs.astral.sh/uv/).
- Docker Desktop or compatible Docker engine.
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

Wait until PostgreSQL reports as healthy before continuing.

### Build the corpus

```bash
uv run python -m src.ingestion.download_attack_data

uv run python -m src.ingestion.extract_attack_techniques

uv run python -m src.database.db_init

uv run python -m src.database.db_load_techniques

uv run python -m src.database.db_build_embeddings
```

This produces:

```text
data/processed/techniques.jsonl
data/source_manifest.csv
```

and populates:

```text
techniques
ingestion_runs
```

### Run the selected retrieval benchmark

Verify that the local reranker can load:

```bash
uv run python -c "
from src.retrieval.reranker import get_reranker_model

get_reranker_model()
print('Reranker loaded successfully')
"
```

Run vector retrieval plus reranking:

```bash
uv run python -m src.evaluation.run_expert_reranked_vector_retrieval_benchmark \
  --candidate-k 20 \
  --top-k 10 \
  --output data/evaluation_reports/expert_vector_reranked_retrieval_results.csv
```

For answer-generation, LLM-as-judge evaluation, manual review, and UI commands, see the detailed steps in [`docs/runbook.md`](docs/runbook.md).

---

## User interface

The project includes a Streamlit-based analyst-facing UI and monitoring dashboard.

### Run the UI

Install Streamlit dependencies:

```bash
make install
# or:
uv pip install streamlit plotly matplotlib
```

Start the main application:

```bash
make app
# or:
PYTHONPATH=. uv run streamlit run app/home.py --server.fileWatcherType=none
```

The app opens at `http://localhost:8501` (or the port specified in `.env` via `STREAMLIT_PORT`).

### Tabs

- **Home**: Overview, data sources, and ATT&CK usage information.
- **Query**: Incident narrative input, retrieval with reranking, structured answer generation using the configured `MODEL_ID`, retrieved-technique inspection, and feedback capture.
- **Dashboard**: Monitoring dashboard with evaluation metrics and charts.
- **Evaluation Review**: Manual review workflow for cases where the two LLM judges disagree. Supports both the reranked v1 and vector-only baseline disagreement sets, with blinded answers, expected labels, retrieved context, failure-mode tagging, and auditability.

### Run the dashboard standalone

```bash
make dashboard
# or:
PYTHONPATH=. uv run streamlit run app/dashboard.py --server.fileWatcherType=none
```

The dashboard includes charts for:

1. Answer-generation latency distribution.
2. Judge preferences: Gemini 3.5 Flash-Lite as judge.
3. Judge preferences: Gemini 3.1 Flash-Lite as judge.
4. Retrieval method comparison (MRR & Hit@3).
5. Judge agreement rate.
6. User feedback distribution.

### Notes and limitations

- Feedback buttons persist submissions to `data/feedback/feedback.csv`, linked to the query, generated answer, model, and retrieved techniques. An empty feedback chart means no feedback has yet been submitted.
- The retrieval-comparison chart currently uses hard-coded metrics from DEC-018 and DEC-019; future versions can read dynamically from benchmark CSVs.
- The dashboard assumes evaluation reports exist; if files are missing, it displays informative error messages.
- The application Dockerfile runs `streamlit run app/home.py` and requires database and LLM environment variables at runtime.
- Optional `torchvision` import warnings from `transformers` modules do not affect retrieval, answer generation, or stored evaluation results; they can be avoided by running Streamlit with `--server.fileWatcherType=none`.

For full details, see [`docs/runbook.md`](docs/runbook.md).

---

## Repository structure

_Representative structure (simplified; some files omitted for brevity):_

```text
cyber-threat-identifier/
├── README.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── compose.yaml
│
├── app/                     # Streamlit UI
│   ├── home.py              # Main tabs (Home / Query / Dashboard / Evaluation Review)
│   ├── query.py             # Query interface
│   ├── dashboard.py         # Monitoring dashboard
│   └── evaluation.py        # Manual-review workflow for judge disagreements
│
├── src/
│   ├── llm_client.py
│   ├── ingestion/
│   │   ├── download_attack_data.py
│   │   └── extract_attack_techniques.py
│   ├── database/
│   │   ├── db_init.py
│   │   ├── db_load_techniques.py
│   │   └── db_build_embeddings.py
│   ├── retrieval/
│   │   ├── embedding_model.py
│   │   ├── schemas.py
│   │   ├── text.py
│   │   ├── vector.py
│   │   ├── hybrid.py
│   │   ├── reranker.py
│   │   ├── reranked_vector.py
│   │   ├── query_rewriter.py
│   │   └── rewritten_reranked_vector.py
│   ├── generation/
│   │   ├── schemas.py
│   │   ├── prompts.py
│   │   └── answer_generator.py
│   ├── evaluation/
│   │   ├── metrics.py
│   │   ├── build_expert_retrieval_cases.py
│   │   ├── run_expert_text_retrieval_benchmark.py
│   │   ├── run_expert_vector_retrieval_benchmark.py
│   │   ├── run_expert_hybrid_retrieval_benchmark.py
│   │   ├── run_expert_reranked_vector_retrieval_benchmark.py
│   │   ├── run_expert_query_rewrite_retrieval_benchmark.py
│   │   ├── run_expert_llm_comparison_reranked.py
│   │   ├── run_llm_judge_pairwise.py
│   │   ├── analyze_judge_agreement.py
│   │   ├── build_manual_review_queue.py
│   │   ├── summarize_manual_review.py
│   │   └── validate_external_expert_labels.py
│   └── monitoring/
│
├── data/
│   ├── processed/
│   │   └── techniques.jsonl
│   ├── eval/
│   │   └── expert_retrieval_cases.csv
│   ├── evaluation_reports/
│   │   └── reranked/
│   └── source_manifest.csv
│
└── docs/
    ├── project-log.md
    ├── decisions.md
    ├── dataset-notes.md
    ├── evaluation-notes.md
    └── runbook.md
```

---

## Documentation

| Document | Purpose |
|---|---|
| [`docs/runbook.md`](docs/runbook.md) | Setup, pipeline commands, verification, rebuilds, benchmarks, answer-generation, LLM-as-judge evaluation, manual review, UI, and troubleshooting |
| [`docs/dataset-notes.md`](docs/dataset-notes.md) | Corpus scope, provenance, schema, processing rules, artefact policy, and limitations |
| [`docs/decisions.md`](docs/decisions.md) | Stable architecture, corpus, retrieval, and evaluation decisions (e.g. DEC‑017, DEC‑018, DEC‑019, DEC‑020, DEC‑021) |
| [`docs/evaluation-notes.md`](docs/evaluation-notes.md) | Benchmark design, metrics, retrieval results, answer evaluation, LLM-as-judge analysis, manual review, and failure analysis |
| [`docs/project-log.md`](docs/project-log.md) | Chronological progress, discoveries, and immediate next steps |

---

## Limitations

- The retrieval corpus contains active Enterprise ATT&CK techniques and sub-techniques only.
- Results are ranked relevance suggestions for analyst review, not verified incident findings.
- The local reranker can improve ordering only within its first-stage vector candidate pool; it cannot recover techniques absent from the vector top 20.
- The selected reranker is a compact general-domain model, not a cyber-security-specific reranker.
- Local CPU reranking adds approximately 1.2 seconds median latency in the current benchmark.
- Query rewriting improves retrieval quality but adds ~3.1 seconds median latency; it is evaluated but not deployed for interactive use.
- The current answer-generation pipeline uses vector-plus-reranking retrieval and a selected default model (`gemini-3.1-flash-lite`); prompt, abstention behaviour, and rubric-scored quality are still under evaluation.
- LLM-as-judge evaluation is not ground truth; both judges show a tendency to prefer `gemini-3.1-flash-lite` on the current dataset, and approximately 24% of cases involve judge disagreement.
- The manual review of 55 disagreements found 3.1 winning 56.8% of decisive comparisons with a 5-case margin; 32.7% of cases were ties.
- The external Expert dataset is multi-label and does not provide a verified single primary technique.
- The current 226-case benchmark is not a frozen held-out benchmark.
- ATT&CK coverage does not guarantee complete behavioural, defensive, detection, or incident-response coverage.

---

## MITRE ATT&CK attribution

Cyber Threat Identifier is an independent project. It is not affiliated with, sponsored by, or endorsed by The MITRE Corporation.

MITRE ATT&CK® is used as the project's source knowledge base. The project name does not use ATT&CK because MITRE branding guidance restricts ATT&CK use in product, service, company, and logo names.

The repository contains derived ATT&CK content. Any distributed corpus snapshot or derived artefact must retain applicable MITRE copyright, licence, and attribution wording.

- [MITRE ATT&CK Terms of Use](https://attack.mitre.org/resources/legal-and-branding/terms-of-use/)
- [MITRE ATT&CK Legal and Branding Guidance](https://attack.mitre.org/resources/legal-and-branding/)
- [Security-TTP-Mapping repository](https://github.com/tumeteor/mitre-ttp-mapping)