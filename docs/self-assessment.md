# Self-assessment — Cyber Threat Identifier

This document maps the current Cyber Threat Identifier project state to the peer-review evaluation criteria. It is intended to provide an honest, easy-to-check evidence trail for reviewers and to identify remaining improvement areas.

For the project overview, architecture, and rubric evidence map, see the [README](../README.md).
For complete local reproduction and Docker Compose commands, see the [runbook](runbook.md).
For retrieval and answer-generation results, see the [evaluation notes](evaluation-notes.md).

---

## Live application

The application is currently running locally via Docker Compose and has been deployed to a lightweight Ubuntu-based AWS EC2 instance for reviewer access.

**Live deployed application:**

**[Cyber Threat Identifier — Streamlit app](http://32.199.23.249/:8501/)**

The instance runs the same Docker Compose stack used for local reproduction.

The deployed application exposes the selected default v1 RAG path:

- Vector retrieval plus local cross-encoder reranking
- Structured answer generation with `gemini-3.1-flash-lite`
- Evidence inspection with retrieved ATT&CK technique metadata
- PostgreSQL-backed runtime telemetry dashboard with feedback ratio, query volume, retrieved-technique frequency, retrieval latency, and recent query logs
- Evaluation Review tab for blinded manual adjudication of judge-disagreement cases

**Important:** The EC2 instance is a temporary demonstration environment. It does not include HTTPS, a custom domain, or managed secrets. It is intended for reviewer access and portfolio demonstration only.

---

## Reviewer quick check

A reviewer can verify the main implemented capabilities without rebuilding the project:

1. Open the live Streamlit application URL.
2. Paste a short cyber incident narrative into the **Query** tab.
3. Inspect the returned structured answer and retrieved ATT&CK technique evidence.
4. Open the **Dashboard** to verify live PostgreSQL telemetry: feedback ratio, query volume, retrieved-technique frequency, retrieval latency, and recent query logs.
5. Optionally open the **Evaluation Review** tab to inspect a sample disagreement case and the blinded review workflow.
6. Use the [README assessment evidence map](../README.md#assessment-evidence) to locate repository evidence for each criterion.

Reviewers can also reproduce the full stack locally using the runbook if preferred.

---

## Score summary

**Self-assessed core score: 18/18**

**Implemented bonus features (so far):**

- Hybrid search evaluation — +1
- Document reranking — +1
- User query rewriting — +1
- Cloud deployment — +2 (live on AWS EC2)

**Total self-assessed score:** 23/23

**Bonus points (optional, up to +3):**
The rubric allows up to three additional bonus points for exceptional work not covered by the standard bonus categories.

| Criterion | Self-assessed score | Summary |
|---|---:|---|
| Problem description | 2/2 | Clear problem, users, scope, and retrieval rationale |
| Retrieval flow | 2/2 | ATT&CK knowledge base plus grounded LLM answer generation |
| Retrieval evaluation | 2/2 | Text, vector, hybrid, reranked, and query-rewrite retrieval evaluated; best backend selected |
| LLM evaluation | 2/2 | Multiple answer-generation models evaluated with reciprocal judging and manual review; best model selected |
| Interface | 2/2 | Streamlit UI deployed for reviewer access (local and EC2) |
| Ingestion pipeline | 2/2 | Fully automated scripted ingestion via Docker Compose (no dedicated orchestrator required) |
| Monitoring | 2/2 | PostgreSQL-backed user feedback plus five live telemetry charts and a recent incident-log table |
| Containerization | 2/2 | Database, ingestion, and application services run through Docker Compose |
| Reproducibility | 2/2 | Accessible source data, pinned dependencies, runbook, corpus snapshot, and Docker runtime |
| Hybrid search | +1 | Implemented and evaluated |
| Document reranking | +1 | Implemented, evaluated, and selected as default retrieval |
| User query rewriting | +1 | Implemented and evaluated; retained as experimental |
| Cloud deployment | +2 | Live on AWS EC2; temporary demonstration environment |

---

## Criterion definitions

### Problem description

- **0 points:** The problem is not described.
- **1 point:** The problem is described but briefly or unclearly.
- **2 points:** The problem is well-described and it is clear what problem the project solves.

### Retrieval flow

- **0 points:** No knowledge base or LLM is used.
- **1 point:** No knowledge base is used, and the LLM is queried directly.
- **2 points:** Both a knowledge base and an LLM are used in the flow.

### Retrieval evaluation

- **0 points:** No evaluation of retrieval is provided.
- **1 point:** Only one retrieval approach is evaluated.
- **2 points:** Multiple retrieval approaches are evaluated, and the best one is used.

### LLM evaluation

- **0 points:** No evaluation of final LLM output is provided.
- **1 point:** Only one approach, such as one prompt, is evaluated.
- **2 points:** Multiple approaches are evaluated, and the best one is used.

### Interface

- **0 points:** No way to interact with the application at all.
- **1 point:** Command line interface, a script, or a Jupyter notebook.
- **2 points:** A UI, web application, or API is available.

### Ingestion pipeline

- **0 points:** No ingestion.
- **1 point:** Semi-automated ingestion of the dataset into the knowledge base, such as with scripts or a notebook.
- **2 points:** Automated ingestion with a dedicated orchestration tool, such as Kestra, dlt, Airflow, or Prefect.
  *Course guidance: a fully automated scripted pipeline (e.g., via Docker Compose) satisfies the 2/2 requirement.*

### Monitoring

- **0 points:** No monitoring.
- **1 point:** User feedback is collected or a monitoring dashboard exists.
- **2 points:** User feedback is collected and a dashboard contains at least five charts.

### Containerization

- **0 points:** No containerization.
- **1 point:** A Dockerfile is provided for the main application, or Docker Compose is used only for dependencies.
- **2 points:** The complete runtime is defined in Docker Compose.

### Reproducibility

- **0 points:** No instructions are provided, data is missing, or access is unclear.
- **1 point:** Instructions are incomplete, or code works but data is missing.
- **2 points:** Instructions are clear, the dataset is accessible, the project is easy to run, and dependency versions are specified.

---

## Problem description — 2/2

The project addresses a clear problem: security analysts must map unstructured incident narratives to relevant Enterprise MITRE ATT&CK techniques, but doing so manually is slow and inconsistent. Official ATT&CK guidance is large, structured, and not trivially searchable by narrative text alone.

Cyber Threat Identifier provides a retrieval-augmented assistant over a curated ATT&CK corpus. Rather than relying on general LLM advice alone, it retrieves relevant ATT&CK technique records and generates answers grounded in that material, explicitly surfacing uncertainty and evidence for analyst review.

**Evidence:**

- [README problem statement](../README.md#problem)
- [README project scope](../README.md#scope)
- [Dataset notes](dataset-notes.md)
- [Architecture decisions](decisions.md)

---

## Retrieval flow — 2/2

The project uses both a knowledge base and an LLM-supported answer flow.

Official Enterprise ATT&CK STIX data is downloaded, extracted to active techniques and sub-techniques, and loaded into PostgreSQL with pgvector embeddings and structured `embedding_text`. The selected UI path retrieves evidence using vector retrieval plus local cross-encoder reranking, then generates a structured answer from the top reranked ATT&CK records using `gemini-3.1-flash-lite`.

The LLM is also used in supporting evaluation stages, including answer generation, pairwise judging, and judge-agreement analysis.

**Evidence:**

- `data/processed/techniques.jsonl`
- `src/ingestion/download_attack_data.py`
- `src/ingestion/extract_attack_techniques.py`
- `src/database/db_init.py`
- `src/database/db_load_techniques.py`
- `src/database/db_build_embeddings.py`
- `src/retrieval/vector.py`
- `src/retrieval/reranked_vector.py`
- `src/generation/answer_generator.py`
- `src/llm_client.py`
- `app/home.py`

---

## Retrieval evaluation — 2/2

Retrieval quality is evaluated across multiple approaches using the same 226-case Expert-derived benchmark:

- Text retrieval
- Vector retrieval
- Hybrid retrieval (Reciprocal Rank Fusion)
- Vector retrieval plus local cross-encoder reranking
- Query rewriting plus vector retrieval and reranking

The benchmark is built from upstream Expert-derived incident narratives with externally supplied ATT&CK labels. Retrieval evaluation reports metrics including Recall@k, Hit@k, and MRR, plus latency breakdowns.

Vector-plus-reranking performed best on the current benchmark and is therefore used as the default downstream retrieval path in the UI and answer-generation workflow. Query rewriting improved metrics further but introduced unacceptable latency for interactive use and is retained as an evaluated experimental capability.

**Evidence:**

- `src/evaluation/run_expert_text_retrieval_benchmark.py`
- `src/evaluation/run_expert_vector_retrieval_benchmark.py`
- `src/evaluation/run_expert_hybrid_retrieval_benchmark.py`
- `src/evaluation/run_expert_reranked_vector_retrieval_benchmark.py`
- `src/evaluation/run_expert_query_rewrite_retrieval_benchmark.py`
- `data/eval/expert_retrieval_cases.csv`
- [Evaluation notes](evaluation-notes.md)
- [README retrieval and evaluation](../README.md#retrieval-evaluation)

---

## LLM evaluation — 2/2

The project compares multiple answer-generation models using the same 226-case Expert-derived set and a consistent reciprocal pairwise LLM-as-judge setup.

The evaluated answer artefacts include:

- `data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv`
- `data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv`
- `data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv`
- `data/evaluation_reports/reranked/judge_agreement_summary.csv`
- `data/evaluation_reports/reranked/judge_disagreements.csv`
- `data/evaluation_reports/reranked/manual_review_results.csv`

The evaluation compared:

- `gemini-3.1-flash-lite`
- `gemini-3.5-flash-lite`

Both models were judged by each other in a reciprocal pairwise setup with randomised A/B presentation. All 55 judge-disagreement cases were manually reviewed blind to model identity. Gemini 3.1 Flash-Lite won 56.8% of decisive comparisons and is selected as the default v1 answer-generation model.

This satisfies "multiple approaches are evaluated, and the best one is used" under the criterion, even though the evaluation uses LLM judges plus manual review rather than a formal rubric-scored human panel.

**Evidence:**

- `src/evaluation/run_expert_llm_comparison_reranked.py`
- `src/evaluation/run_llm_judge_pairwise.py`
- `src/evaluation/analyze_judge_agreement.py`
- `src/evaluation/build_manual_review_queue.py`
- `src/evaluation/summarize_manual_review.py`
- `app/evaluation.py`
- `data/evaluation_reports/reranked/`
- [Evaluation notes](evaluation-notes.md)
- [Decision DEC-020](decisions.md)
- [Decision DEC-021](decisions.md)

---

## Interface — 2/2

The project provides both command-line workflows and a deployed Streamlit UI.

The Streamlit application in `app/home.py` provides:

- **Home** — project overview, data sources, and ATT&CK attribution
- **Query** — incident narrative input, reranked retrieval, structured answer generation, retrieved-technique inspection, and feedback capture
- **Dashboard** — PostgreSQL-backed runtime telemetry dashboard with five operational views
- **Evaluation Review** — blinded adjudication of judge-disagreement cases

The application is accessible both locally and via the live EC2 deployment.

**Evidence:**

- `app/home.py`
- `app/query.py`
- `app/dashboard.py`
- `app/evaluation.py`
- `.streamlit/config.toml`

---

## Ingestion pipeline — 2/2

The ingestion pipeline is fully automated and reproducible through Docker Compose:

1. A downloader fetches official Enterprise ATT&CK STIX data and records provenance.
2. An extractor produces active techniques and sub-techniques as JSONL.
3. A reviewed corpus snapshot is preserved under `data/processed/techniques.jsonl`.
4. Scripts create PostgreSQL schema, load technique records, and build embeddings.
5. Docker Compose provides an automated ingestion profile for end-to-end runs.

This satisfies the course guidance that a fully automated scripted pipeline (e.g., via Docker Compose) qualifies for 2/2, even without a dedicated orchestration tool.

**Evidence:**

- `data/source_manifest.csv`
- `src/ingestion/download_attack_data.py`
- `src/ingestion/extract_attack_techniques.py`
- `src/database/db_init.py`
- `src/database/db_load_techniques.py`
- `src/database/db_build_embeddings.py`
- `compose.yaml`
- [Dataset notes](dataset-notes.md)
- [Runbook](runbook.md)

---

## Monitoring — 2/2

The Streamlit application includes user-feedback collection and a PostgreSQL-backed runtime telemetry dashboard.

After a successful analysis, the Query workflow attempts to write an `incident_queries` record to PostgreSQL. This record stores the incident narrative, generated answer, configured model ID, retrieved ATT&CK technique IDs, retrieval latency, and timestamp. Logging occurs independently of whether the user submits feedback.

When a user selects **Helpful** or **Not helpful**, the application writes the optional rating to the `feedback` table, linked to the original query through `query_id`.

The Dashboard queries live telemetry through a SQL `LEFT JOIN` and provides five charts:

1. **User Feedback Ratio**
2. **Incident Query Volume**
3. **Top Retrieved ATT&CK Techniques**
4. **Retrieval Latency**
5. **Feedback Volume Over Time**

It also provides a **Recent Incident Logs** table showing recent query timestamps, query IDs, model IDs, retrieval latency, feedback state, and truncated query text.

**Evidence:**

- `src/database/db_init.py`
- `src/monitoring/feedback_store.py`
- `app/query.py`
- `app/dashboard.py`
- PostgreSQL tables: `incident_queries` and `feedback`
- [Runbook](runbook.md)

---

## Containerization — 2/2

The complete application runtime is defined through Docker Compose.

The Compose configuration includes:

- `postgres` — PostgreSQL with pgvector
- `streamlit` — Streamlit application service
- `ingest` — on-demand ingestion profile for automated corpus build

The repository also includes a `Dockerfile` for the application image, named volumes for PostgreSQL and model caching, health checks, and Docker ignore rules.

**Evidence:**

- `app/Dockerfile`
- `compose.yaml`
- `.dockerignore`
- [Runbook Docker and deployment instructions](runbook.md)

---

## Reproducibility — 2/2

The project provides clear reproduction paths from a clean checkout.

Reproducibility support includes:

- Public ATT&CK source URLs defined in `data/source_manifest.csv`
- A reviewed JSONL corpus snapshot for strict baseline reproduction
- A fresh source-download and extraction path
- Pinned Python dependencies in `pyproject.toml` and `uv.lock`
- Documented `uv` commands for the local workflow
- A Docker Compose runtime for the database, ingestion process, and application
- A committed Streamlit configuration
- Step-by-step setup, evaluation, reset, and deployment instructions

A reviewer can follow the runbook to reproduce the corpus, index, retrieval evaluation, and local UI runtime. The EC2 deployment uses the same Docker Compose stack, ensuring consistent behaviour between local and cloud environments.

**Evidence:**

- [README setup](../README.md#marker-quickstart)
- [README usage](../README.md#developer-rebuild-and-evaluation)
- [Runbook](runbook.md)
- `pyproject.toml`
- `uv.lock`
- `app/Dockerfile`
- `compose.yaml`
- `data/source_manifest.csv`
- `data/processed/techniques.jsonl`

---

## Bonus implementation categories

### Hybrid search — implemented and evaluated

Hybrid retrieval combines text and vector results through reciprocal rank fusion. It was evaluated against the same benchmark as the other retrieval backends.

Hybrid retrieval improved slightly over vector-only retrieval on some metrics but did not outperform vector-plus-reranking. It is retained as an evaluated alternative and debugging aid rather than being selected as the default.

**Evidence:**

- `src/retrieval/hybrid.py`
- `src/evaluation/run_expert_hybrid_retrieval_benchmark.py`
- [Evaluation notes](evaluation-notes.md)

### Document reranking — implemented and selected

The project implements chunk reranking through `src/retrieval/reranked_vector.py`.

Vector-plus-reranking outperformed text, plain vector, and hybrid alternatives on the current benchmark. It is therefore the selected default retrieval backend for the Streamlit UI and current answer-generation path.

**Evidence:**

- `src/retrieval/reranked_vector.py`
- `src/evaluation/run_expert_reranked_vector_retrieval_benchmark.py`
- `app/query.py`
- [Evaluation notes](evaluation-notes.md)

### User query rewriting — implemented and evaluated

Query rewriting is implemented through `src/retrieval/query_rewriter.py` and was evaluated across vector-plus-reranking and query-rewrite-plus-reranking configurations.

It improved retrieval metrics but introduced unacceptable latency for interactive use. It was not adopted as the default but remains available for experimentation and future re-evaluation.

Not selecting rewriting as the production default reflects the evaluation result; the capability is still implemented and evaluated.

**Evidence:**

- `src/retrieval/query_rewriter.py`
- `src/retrieval/rewritten_reranked_vector.py`
- `src/evaluation/run_expert_query_rewrite_retrieval_benchmark.py`
- [Evaluation notes](evaluation-notes.md)
- [Decision DEC-019](decisions.md)

### Cloud deployment — implemented and live (+2)

The application has been deployed to a lightweight Ubuntu-based AWS EC2 instance for reviewer access.

The instance runs the same Docker Compose stack used for local reproduction:

- `postgres` service with pgvector
- `streamlit` service running Streamlit on port 8501
- Optional `ingest` profile for corpus rebuilds

The deployment is a temporary demonstration environment. It does not include HTTPS, a custom domain, or managed secrets. It is intended for reviewer access and portfolio demonstration only.

**Evidence:**

- Live deployed application URL
- `app/Dockerfile`
- `compose.yaml`
- [Runbook EC2 deployment instructions](runbook.md)
- [Decision DEC-022](decisions.md)
- [Decision DEC-024](decisions.md)
- [Decision DEC-025](decisions.md)
- [Decision DEC-026](decisions.md)

---

## Strengths

The strongest parts of the project are currently:

- A clearly scoped and well-documented problem
- A real knowledge-base-plus-LLM RAG flow rather than direct prompting
- Comparative retrieval evaluation across five backends
- Reciprocal pairwise judging plus manual review of disagreements for model selection
- Selected defaults based on recorded benchmark results
- A deployed Streamlit interface with inspectable evidence (local and EC2)
- PostgreSQL-backed query telemetry, linked user-feedback capture, five live telemetry charts, and a recent incident-log table
- Full Docker Compose runtime coverage
- Reproducible local and cloud deployment documentation
- Explicit separation of public sample queries from restricted expert-evaluation data

---

## Remaining gaps

The main remaining limitations are:

- The benchmark is expert-derived and relatively small, so results should not be interpreted as broad real-world performance claims.
- Query rewriting is implemented but not part of the default interactive path due to latency.
- The EC2 deployment is a temporary demonstration environment without production hardening (HTTPS, custom domain, managed secrets, backups, or high availability).

---

## Next steps

Potential next improvements are:

- Expand evaluation with more diverse or human-authored questions while preserving a held-out test set.
- Investigate selective query rewriting or additional reranking variants only when evaluated against the existing benchmark.
- Maintain clear Docker documentation for first-time bootstrap, normal restart, and full-reset workflows.
- If the project evolves beyond a portfolio demonstration, consider production hardening: HTTPS termination, restricted security-group rules, managed secrets, backups, and operational monitoring.

This document should be updated when the implementation or evidence changes. The criterion definitions should remain stable so changes in project maturity are easy to track.