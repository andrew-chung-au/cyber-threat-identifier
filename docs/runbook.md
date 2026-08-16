# Runbook

## Purpose

This runbook explains how to reproduce and operate the current **Cyber Threat Identifier** v1 system from a clean checkout.

It covers:

- Environment setup and required configuration
- Docker Compose startup for PostgreSQL with pgvector and Streamlit
- Automated ATT&CK ingestion, extraction, database loading, and embedding generation
- Database, embedding, and application connectivity verification
- Retrieval benchmark execution: text, vector, hybrid, reranked vector, and query-rewrite-plus-rerank
- Local cross-encoder reranker setup and verification
- Reranked answer-generation comparison
- Reciprocal pairwise LLM-as-judge evaluation and agreement analysis
- Blinded manual review of judge-disagreement cases
- Streamlit Query, Dashboard, Evaluation Review, and feedback workflows
- External benchmark inspection and Expert-label compatibility validation
- Reset, rebuild, and troubleshooting procedures

For corpus scope, provenance, schema, and data-artifact policy, see [`dataset-notes.md`](dataset-notes.md).  
For stable design decisions, see [`decisions.md`](decisions.md).  
For benchmark design, metrics, results, and limitations, see [`evaluation-notes.md`](evaluation-notes.md).  
For chronological implementation history, see [`project-log.md`](project-log.md).

---

## Quick start

For the normal local application path, run:

```bash
cp .env.example .env
# Edit .env and add LLM_API_KEY if you want generated answers.

make up
make ingest
```

Then open:

```text
http://localhost:8501
```

`make up` starts PostgreSQL with pgvector and the Streamlit application.  
`make ingest` runs the complete source-to-vector ingestion pipeline through Docker Compose.

After a successful clean ingestion run, the database should contain:

```text
total_techniques | embedded_techniques | missing_embeddings
-----------------+---------------------+------------------
697              | 697                 | 0
```

The first ingestion run downloads the ATT&CK source data and local embedding model, so it may take several minutes. Later runs reuse the persisted model cache.

---

## Prerequisites

Install:

- Git
- Docker Desktop, including Docker Compose
- `uv` and the Python version declared in `pyproject.toml` only if you will run host-side developer, benchmark, or evaluation commands

Check the available tools:

```bash
git --version
docker --version
docker compose version
uv --version
python --version
```

Run all commands from the repository root:

```bash
cd cyber-threat-identifier
```

The current reranking implementation is designed for local CPU execution. GPU hardware and ONNX Runtime are not required for v1.

---

## Configuration

### Create `.env`

Create a local environment file:

```bash
cp .env.example .env
```

Do not commit `.env` or disclose its API key values.

The selected v1 answer-generation model is:

```dotenv
MODEL_ID=gemini-3.1-flash-lite
```

To enable answer generation, query rewriting, and LLM-as-judge workflows, configure Gemini through the OpenAI-compatible endpoint:

```dotenv
LLM_API_KEY=<your-gemini-api-key>
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
```

The answer-comparison and reciprocal-judge workflows also use:

```text
gemini-3.5-flash-lite
```

as an evaluated alternative and judge model.

### Database URLs

The host-side default connection is:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cyber_threat_identifier
```

Docker Compose services use the Compose network and connect to PostgreSQL through the `postgres` service hostname rather than `localhost`.

---

## Docker Compose operation

### Start the stack

Start PostgreSQL and Streamlit:

```bash
make up
```

Equivalent Compose command:

```bash
docker compose up -d
```

Check service health:

```bash
docker compose ps
```

Wait for the `postgres` service to become healthy before running host-side database operations or benchmarks.

View logs when needed:

```bash
docker compose logs -f postgres
docker compose logs -f streamlit
```

### Stop the stack

Stop containers while retaining the database and model-cache volumes:

```bash
make down
```

Equivalent command:

```bash
docker compose down
```

### Open the application

After `make up`, open:

```text
http://localhost:8501
```

The application includes:

- **Home** — project scope, ATT&CK attribution, architecture, and configured system information
- **Query** — incident narrative analysis, reranked retrieval, structured answer generation, evidence inspection, and feedback capture
- **Dashboard** — evaluation metrics, judge preferences, retrieval comparison, agreement rate, and user feedback
- **Evaluation Review** — blinded manual review of LLM-judge disagreement cases

---

## Automated ingestion

### Canonical ingestion path

Run the complete ingestion workflow through Docker Compose:

```bash
make ingest
```

The `ingest` Compose profile performs:

```text
Download ATT&CK STIX source
  → Extract active Enterprise techniques and sub-techniques
  → Initialise PostgreSQL and pgvector schema
  → Load processed technique records
  → Generate local embedding vectors
```

The ingestion service runs the locked environment through `uv run python` and exits immediately if a stage fails.

The equivalent direct Compose command is:

```bash
docker compose --profile ingest run --rm ingest
```

### Generated artefacts

The automated pipeline writes or updates:

```text
data/raw/attack/                      Raw ATT&CK download; ignored by Git
data/source_manifest.csv              Download provenance and checksums
data/processed/techniques.jsonl       Processed inspectable corpus snapshot
PostgreSQL techniques table           Canonical loaded technique records
PostgreSQL ingestion_runs table       Pipeline audit records
```

### Pinned source option

The default acquisition reference is the current upstream `master` branch. For a reproducible source baseline, use a pinned tag or commit through the host-side command:

```bash
uv run python -m src.ingestion.download_attack_data \
  --ref <release-tag-or-commit>
```

Then run extraction, database initialisation, loading, and embedding generation as described in [Host-side pipeline commands](#host-side-pipeline-commands).

Do not describe results as formally comparable across time unless the ATT&CK source reference is pinned and recorded.

---

## Verify the build

Run these checks after `make ingest`, particularly after a clean rebuild.

### Check processed corpus records

```bash
wc -l data/processed/techniques.jsonl
```

### Check PostgreSQL connectivity

```bash
docker compose exec postgres \
  psql -U postgres -d cyber_threat_identifier -c "SELECT 1;"
```

### Check tables and pgvector

```bash
docker compose exec postgres \
  psql -U postgres -d cyber_threat_identifier -c "\dt"
```

```bash
docker compose exec postgres \
  psql -U postgres -d cyber_threat_identifier -c "
    SELECT extname
    FROM pg_extension
    WHERE extname = 'vector';
  "
```

### Check loaded and embedded record counts

```bash
docker compose exec postgres psql \
  -U postgres \
  -d cyber_threat_identifier \
  -c "
    SELECT
      COUNT(*) AS total_techniques,
      COUNT(embedding) AS embedded_techniques,
      COUNT(*) - COUNT(embedding) AS missing_embeddings
    FROM techniques;
  "
```

Expected clean-build result:

```text
 total_techniques | embedded_techniques | missing_embeddings
------------------+---------------------+--------------------
              697 |                 697 |                  0
```

### Check the application container database connection

```bash
docker compose exec streamlit sh -lc '
  uv run python -c "
from src.database.db_connection import get_connection

with get_connection() as connection:
    with connection.cursor() as cursor:
        cursor.execute(\"SELECT COUNT(*) FROM techniques\")
        print(\"Technique count:\", cursor.fetchone())
"
'
```

Expected result:

```text
Technique count: 697
```

### Preview retrieval and reranker text

```bash
docker compose exec postgres psql \
  -U postgres \
  -d cyber_threat_identifier \
  -c "
    SELECT
      attack_id,
      name,
      substring(embedding_text FROM 1 FOR 1000) AS embedding_text_preview
    FROM techniques
    ORDER BY attack_id
    LIMIT 1;
  "
```

### Check recent pipeline audits

```bash
docker compose exec postgres psql \
  -U postgres \
  -d cyber_threat_identifier \
  -c "
    SELECT
      stage,
      status,
      records_processed,
      started_at,
      completed_at
    FROM ingestion_runs
    ORDER BY id DESC
    LIMIT 10;
  "
```

A successful build has:

- A non-empty `data/processed/techniques.jsonl`
- `techniques` and `ingestion_runs` tables
- The `vector` extension enabled
- One loaded database record per processed technique record
- No missing embeddings after the embedding stage
- Non-empty `embedding_text` values available for retrieval and reranking
- A Streamlit-container database connection that can query `techniques`

---

## Host-side pipeline commands

Use this section only for development, targeted debugging, source pinning, or running individual stages. For standard local setup, prefer `make ingest`.

First install the locked host-side environment:

```bash
uv sync
```

Start PostgreSQL if it is not already running:

```bash
make up
```

### 1. Download ATT&CK data

```bash
uv run python -m src.ingestion.download_attack_data
```

For a fixed baseline:

```bash
uv run python -m src.ingestion.download_attack_data \
  --ref <release-tag-or-commit>
```

### 2. Extract active techniques

```bash
uv run python -m src.ingestion.extract_attack_techniques
```

Expected output:

```text
data/processed/techniques.jsonl
```

### 3. Initialise the database

```bash
uv run python -m src.database.db_init
```

### 4. Load technique records

```bash
uv run python -m src.database.db_load_techniques
```

This stage loads canonical technique fields and constructs structured `embedding_text`. It does not generate embedding vectors.

### 5. Build embeddings

```bash
uv run python -m src.database.db_build_embeddings
```

Optionally create an HNSW index for an explicitly documented performance experiment:

```bash
uv run python -m src.database.db_build_embeddings \
  --create-hnsw-index
```

HNSW is optional. Exact cosine-distance search remains the reproducible v1 baseline for the compact ATT&CK corpus.

---

## Verify the reranker

The selected reranker is:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

It runs locally on CPU through `sentence-transformers`.

Run this smoke test before reranking benchmarks or host-side Streamlit usage:

```bash
uv run python -c "
from src.retrieval.reranker import get_reranker_model

get_reranker_model()
print('Reranker loaded successfully')
"
```

On the first run, Hugging Face downloads the model into the local cache. Docker Compose persists a separate Hugging Face cache volume for container-based operation.

An unauthenticated Hugging Face Hub warning does not necessarily prevent model loading. Configure `HF_TOKEN` only if download rate limits or reliability become a practical issue.

A reranking benchmark must fail if the reranker cannot load. Do not treat a vector-only fallback as a valid reranking benchmark result.

---

## Retrieval benchmarks

The benchmark input is:

```text
data/eval/expert_retrieval_cases.csv
```

The current file contains 226 Expert-derived cases. It is an implementation-comparison set that includes development- and test-derived records; it is **not** a frozen held-out final benchmark.

The implemented retrieval methods are:

- Text-only retrieval
- Vector retrieval
- Hybrid retrieval using Reciprocal Rank Fusion
- Vector retrieval plus local cross-encoder reranking
- Query rewriting plus vector retrieval and reranking

Run retrieval benchmarks from the host after `uv sync`, `make up`, and a successful ingestion build.

### Text retrieval

```bash
uv run python -m src.evaluation.run_expert_text_retrieval_benchmark
```

Expected output:

```text
data/evaluation_reports/expert_text_retrieval_results.csv
```

### Vector retrieval

```bash
uv run python -m src.evaluation.run_expert_vector_retrieval_benchmark \
  --top-k 10 \
  --output data/evaluation_reports/expert_vector_retrieval_results.csv
```

Expected output:

```text
data/evaluation_reports/expert_vector_retrieval_results.csv
```

### Hybrid retrieval

```bash
uv run python -m src.evaluation.run_expert_hybrid_retrieval_benchmark
```

Expected output:

```text
data/evaluation_reports/expert_hybrid_retrieval_results.csv
```

### Vector-plus-reranking

Run a smoke test first:

```bash
uv run python -m src.evaluation.run_expert_reranked_vector_retrieval_benchmark \
  --limit 3 \
  --candidate-k 20 \
  --top-k 10
```

Run the full benchmark:

```bash
uv run python -m src.evaluation.run_expert_reranked_vector_retrieval_benchmark \
  --candidate-k 20 \
  --top-k 10 \
  --output data/evaluation_reports/expert_vector_reranked_retrieval_results.csv
```

Expected output:

```text
data/evaluation_reports/expert_vector_reranked_retrieval_results.csv
```

The reranked retrieval flow is:

```text
Incident narrative
  → all-MiniLM-L6-v2 query embedding
  → Top 20 pgvector candidates
  → Local CPU cross-encoder reranking
  → Top 10 ranked candidates for evaluation
```

The report includes first-stage vector candidate IDs, original ranks, reranker scores, final ranks, and timing fields.

### Query rewriting plus reranking

This experiment requires valid LLM configuration in `.env`.

Run a smoke test first:

```bash
uv run python -m src.evaluation.run_expert_query_rewrite_retrieval_benchmark \
  --limit 5 \
  --candidate-k 20 \
  --top-k 10
```

Run the full rate-limited benchmark:

```bash
uv run python -m src.evaluation.run_expert_query_rewrite_retrieval_benchmark \
  --candidate-k 20 \
  --top-k 10 \
  --output data/evaluation_reports/local/expert_query_rewrite_retrieval_results.csv
```

Disable rate limiting only if the API plan supports the request volume:

```bash
uv run python -m src.evaluation.run_expert_query_rewrite_retrieval_benchmark \
  --candidate-k 20 \
  --top-k 10 \
  --no-rate-limit \
  --output data/evaluation_reports/local/expert_query_rewrite_retrieval_results.csv
```

The query-rewriting flow is:

```text
Incident narrative
  → LLM query rewriting with gemini-3.1-flash-lite
  → all-MiniLM-L6-v2 query embedding
  → Top 20 pgvector candidates
  → Local CPU cross-encoder reranking
  → Top 10 ranked candidates for evaluation
```

The output is stored under `data/evaluation_reports/local/` because it may contain external narrative text and should remain local unless its redistribution status has been reviewed.

### Interpretation

Reference metrics are documented in [`evaluation-notes.md`](evaluation-notes.md).

The selected v1 retrieval configuration is vector retrieval plus local cross-encoder reranking. It improved every reported retrieval metric over vector-only retrieval in the current 226-case comparison.

Do not describe these metrics as final held-out performance.

---

## Answer-generation comparison

The current answer-generation comparison uses the selected reranked retrieval backend:

```text
Incident narrative
  → Top 20 vector candidates
  → Local cross-encoder reranking
  → Top 5 ATT&CK records as answer context
  → Structured answer generation
```

The compared models are:

```text
gemini-3.1-flash-lite
gemini-3.5-flash-lite
```

The selected runtime default is:

```text
gemini-3.1-flash-lite
```

### Verify LLM configuration

```bash
uv run python - <<'PY'
from src.llm_client import get_default_model, get_client

print("MODEL_ID:", get_default_model())
client = get_client()
print("Client initialised:", type(client).__name__)
PY
```

### Run the comparison

```bash
uv run python -m src.evaluation.run_expert_llm_comparison_reranked
```

Use a small smoke test first if the script supports `--limit`:

```bash
uv run python -m src.evaluation.run_expert_llm_comparison_reranked \
  --limit 10
```

Expected output:

```text
data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv
```

The output includes structured answers for both models, retrieved ATT&CK IDs, expected labels, selected candidates, answer summaries, uncertainty fields, review-required status, and available token and latency metadata.

Inspect the first rows:

```bash
head -n 3 data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv
```

The completed artefact is committed for inspection. Re-run this API-bound comparison only when intentionally evaluating changed prompts, models, retrieval settings, or schemas.

---

## Pairwise LLM-as-judge evaluation

This workflow reproduces the reciprocal pairwise evaluation recorded in DEC-020.

### Run Gemini 3.1 Flash-Lite as judge

```bash
uv run python -m src.evaluation.run_llm_judge_pairwise \
  --input data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv \
  --output data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv \
  --judge-model gemini-3.1-flash-lite
```

### Run Gemini 3.5 Flash-Lite as judge

```bash
uv run python -m src.evaluation.run_llm_judge_pairwise \
  --input data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv \
  --output data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv \
  --judge-model gemini-3.5-flash-lite
```

The script:

- Randomises which underlying model appears as Answer A or Answer B
- Presents the incident narrative, answer summaries, and retrieved ATT&CK IDs
- Judges technique relevance, narrative grounding, uncertainty, actionability, and conciseness
- Requires structured `reasoning`, `winner`, and `confidence` output
- Maps Answer A or B back to the underlying model identity
- Uses retries, backoff, and checkpointing

If a run is interrupted or rate-limited, re-run the same command. Existing completed `eval_id` records are loaded and skipped.

### Analyse agreement

```bash
uv run python -m src.evaluation.analyze_judge_agreement \
  --judge-31 data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv \
  --judge-35 data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv
```

Expected outputs:

```text
data/evaluation_reports/reranked/judge_agreement_summary.csv
data/evaluation_reports/reranked/judge_disagreements.csv
```

The completed evaluation reported:

| Measure | Result |
|---|---:|
| Cases evaluated | 226 |
| Cross-judge agreement | 171 / 226 |
| Cross-judge agreement rate | 75.66% |
| Cross-judge disagreements | 55 / 226 |
| Cross-judge disagreement rate | 24.34% |
| 3.1-as-judge preferred 3.1 | 153 / 226 |
| 3.1-as-judge preferred 3.5 | 73 / 226 |
| 3.5-as-judge preferred 3.1 | 142 / 226 |
| 3.5-as-judge preferred 3.5 | 84 / 226 |

Inspect the stored summary without creating new API calls:

```bash
uv run python - <<'PY'
import pandas as pd

summary = pd.read_csv(
    "data/evaluation_reports/reranked/judge_agreement_summary.csv"
)
print(summary.to_string(index=False))
PY
```

---

## Manual review workflow

The Streamlit Evaluation Review workflow supports blinded human adjudication of reciprocal-judge disagreement cases.

### Build the reranked review queue

```bash
uv run python -m src.evaluation.build_manual_review_queue \
  --judge-31 data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv \
  --judge-35 data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv \
  --output data/evaluation_reports/reranked/manual_review_queue.csv
```

### Build the vector-only baseline queue

This is a diagnostic historical baseline, not the deployed v1 configuration:

```bash
uv run python -m src.evaluation.build_manual_review_queue \
  --judge-31 data/evaluation_reports/vector/expert_llm_judged_31_as_judge.csv \
  --judge-35 data/evaluation_reports/vector/expert_llm_judged_35_as_judge.csv \
  --output data/evaluation_reports/vector/manual_review_queue.csv
```

The queue includes:

- Incident narrative
- Expected ATT&CK labels and definitions
- Retrieved ATT&CK context
- Blinded Answer A and Answer B outputs
- Stable Answer A/B randomisation
- Judge rationales and confidence values, hidden until review submission

### Run the review interface

Use the main application:

```bash
make up
```

Then open the **Evaluation Review** tab.

For host-side standalone development:

```bash
PYTHONPATH=. uv run streamlit run app/evaluation.py \
  --server.fileWatcherType=none
```

The reviewer:

1. Selects the reranked v1 or vector-only dataset.
2. Reviews the narrative, expected labels, and retrieved evidence.
3. Compares blinded Answer A and Answer B.
4. Selects **Answer A**, **Answer B**, or **Tie**.
5. Optionally records failure-mode tags and notes.
6. Saves the decision.
7. Sees model identities and judge rationales only after saving.

Saved outputs:

```text
data/evaluation_reports/reranked/manual_review_results.csv
data/evaluation_reports/vector/manual_review_results.csv
```

### Summarise review outcomes

Reranked v1:

```bash
uv run python -m src.evaluation.summarize_manual_review \
  --results data/evaluation_reports/reranked/manual_review_results.csv
```

Vector-only diagnostic baseline:

```bash
uv run python -m src.evaluation.summarize_manual_review \
  --results data/evaluation_reports/vector/manual_review_results.csv
```

The completed reranked v1 review found:

| Measure | Result |
|---|---:|
| Cases reviewed | 55 |
| Gemini 3.1 wins | 21 |
| Gemini 3.5 wins | 16 |
| Ties | 18 |
| Decisive comparisons | 37 |
| 3.1 share of decisive wins | 56.8% |
| 3.5 share of decisive wins | 43.2% |

This evidence informed the selection of `gemini-3.1-flash-lite` as the v1 default answer-generation model.

Do not overwrite completed review files without first making a backup:

```bash
cp data/evaluation_reports/reranked/manual_review_results.csv \
  data/evaluation_reports/reranked/manual_review_results.backup.csv
```

---

## Streamlit interface and dashboard

### Query workflow

The Query tab:

1. Accepts a pasted incident narrative or a sample query.
2. Embeds the narrative.
3. Retrieves the top 20 vector candidates.
4. Reranks candidates locally.
5. Uses the top 5 reranked records as answer context.
6. Generates a structured answer using `MODEL_ID`.
7. Displays the answer summary, grounding note, uncertainty note, and retrieved technique evidence.
8. Allows **Helpful** or **Not helpful** feedback.

The Query tab requires:

- A healthy PostgreSQL service
- Loaded technique records and embeddings
- A locally available reranker
- Valid LLM configuration for answer generation

### Feedback persistence

Feedback is saved through `src.monitoring.feedback_store.save_feedback`:

```text
data/feedback/feedback.csv
```

A feedback record includes:

- Query ID
- Feedback type
- Configured model ID
- Original query text
- Generated structured answer
- Retrieved ATT&CK technique IDs

Runtime feedback remains local and is not treated as representative production-quality evidence.

### Dashboard charts

The Dashboard displays six charts:

1. **Answer Generation Latency Distribution**
2. **Judge Preferences: Gemini 3.5 Flash-Lite as Judge**
3. **Judge Preferences: Gemini 3.1 Flash-Lite as Judge**
4. **Retrieval Method Comparison (MRR & Hit@3)**
5. **Judge Agreement Rate**
6. **User Feedback Distribution**

The dashboard reads completed answer-generation and judge artefacts where available. If a required artefact is missing, the relevant chart should report that problem without failing the full app.

The retrieval-comparison chart currently uses explicit accepted benchmark values in `app/dashboard.py`. It does not dynamically load retrieval benchmark CSV files. Update the constants if the accepted benchmark baseline changes.

If no feedback has been submitted, the dashboard correctly displays:

```text
No feedback collected yet. Use the main app to submit feedback!
```

This is an empty-state message, not a feedback-store failure.

### Host-side Streamlit commands

Main app:

```bash
PYTHONPATH=. uv run streamlit run app/home.py \
  --server.fileWatcherType=none
```

Dashboard only:

```bash
PYTHONPATH=. uv run streamlit run app/dashboard.py \
  --server.fileWatcherType=none
```

The recommended `--server.fileWatcherType=none` setting avoids noisy optional `torchvision` import warnings caused by Streamlit module inspection.

---

## External benchmark inspection

This optional workflow supports inspection and provenance validation of the Security-TTP-Mapping Expert dataset. It is not part of ATT&CK corpus ingestion.

The local clone directory is:

```text
data/external_inspection/mitre-ttp-mapping/
```

Keep this directory ignored by Git because it can contain externally sourced threat-report text.

### Clone the upstream repository

```bash
mkdir -p data/external_inspection

git clone https://github.com/tumeteor/mitre-ttp-mapping.git \
  data/external_inspection/mitre-ttp-mapping
```

Record the exact revision:

```bash
git -C data/external_inspection/mitre-ttp-mapping rev-parse HEAD
```

The revision used for the current evaluation artefacts is:

```text
a16856a6438ca2b7888c5cadfba6d7c854f04a55
```

### Build combined retrieval cases

The current 226-case implementation-comparison input combines Expert development and test cases:

```bash
uv run python -m src.evaluation.build_expert_retrieval_cases
```

Do not use this combined file as a final held-out benchmark.

### Validate Expert labels

Validate upstream labels against the active local ATT&CK corpus:

```bash
uv run python -m src.evaluation.validate_external_expert_labels
```

Expected report:

```text
data/evaluation_reports/expert_label_compatibility.csv
```

Inspect non-active labels:

```bash
awk -F',' 'NR == 1 || $2 != "active"' \
  data/evaluation_reports/expert_label_compatibility.csv
```

---

## Rebuild from scratch

Use this procedure only when it is safe to remove the local PostgreSQL and model-cache volumes.

### Full Compose reset

```bash
docker compose down -v
make up
make ingest
```

This deletes local database data and model-cache volumes, then rebuilds the ATT&CK corpus, database records, and embeddings.

Verify the result:

```bash
docker compose exec postgres psql \
  -U postgres \
  -d cyber_threat_identifier \
  -c "
    SELECT
      COUNT(*) AS total_techniques,
      COUNT(embedding) AS embedded_techniques,
      COUNT(*) - COUNT(embedding) AS missing_embeddings
    FROM techniques;
  "
```

### Rebuild after a source refresh

For an intentional ATT&CK refresh, pin a source reference where reproducibility matters:

```bash
uv run python -m src.ingestion.download_attack_data \
  --ref <release-tag-or-commit>

uv run python -m src.ingestion.extract_attack_techniques
uv run python -m src.database.db_init
uv run python -m src.database.db_load_techniques
uv run python -m src.database.db_build_embeddings
```

After a corpus refresh, rerun compatibility validation:

```bash
uv run python -m src.evaluation.validate_external_expert_labels
```

Re-run retrieval, answer-generation, and review workflows only when an intentional change affects corpus content, retrieval, reranking, prompts, models, answer schemas, or evaluation logic.

---

## Common issues

### `DATABASE_URL is not set`

Create `.env`:

```bash
cp .env.example .env
```

Confirm it contains a valid host-side `DATABASE_URL`.

For Docker Compose, check the service environment configuration rather than changing the host-side URL to a Compose-only hostname.

---

### PostgreSQL connection refused

Start the stack and inspect its status:

```bash
make up
docker compose ps
```

Inspect PostgreSQL logs:

```bash
docker compose logs postgres
```

Wait until the service reports healthy before running host-side workflows.

---

### Docker Compose ingestion fails with missing Python dependencies

The ingestion service must use the locked environment through `uv run python`.

Check the service command in `compose.yaml` and ensure it does not invoke plain system `python`.

Rebuild if the Docker image or dependency lock file changed:

```bash
docker compose build --no-cache
make up
make ingest
```

---

### ATT&CK source or processed corpus is missing

Download raw ATT&CK data:

```bash
uv run python -m src.ingestion.download_attack_data
```

Extract processed records:

```bash
uv run python -m src.ingestion.extract_attack_techniques
```

For the full standard path, use:

```bash
make ingest
```

---

### Embeddings are missing

Check the database:

```bash
docker compose exec postgres psql \
  -U postgres \
  -d cyber_threat_identifier \
  -c "
    SELECT
      COUNT(*) AS total_techniques,
      COUNT(embedding) AS embedded_techniques,
      COUNT(*) - COUNT(embedding) AS missing_embeddings
    FROM techniques;
  "
```

Rebuild embeddings host-side:

```bash
uv run python -m src.database.db_build_embeddings
```

Or rerun the complete Compose ingestion workflow:

```bash
make ingest
```

---

### Reranker cannot load

Install the locked environment:

```bash
uv sync
```

Run the isolated smoke test:

```bash
uv run python -c "
from src.retrieval.reranker import get_reranker_model

get_reranker_model()
print('Reranker loaded successfully')
"
```

Ensure internet access is available for the initial Hugging Face download. After a successful first load, the model should be available in the local or Compose cache.

Do not report vector-only fallback output as a reranking benchmark.

---

### Streamlit shows `torchvision` warnings

Some Streamlit file-watcher configurations inspect optional image dependencies inside `transformers`, producing warnings even though text retrieval and reranking work.

Use:

```bash
PYTHONPATH=. uv run streamlit run app/home.py \
  --server.fileWatcherType=none
```

These warnings do not alter retrieval, answer generation, stored evaluation results, or feedback persistence when the application otherwise functions normally.

---

### Query-rewriting benchmark is slow

The benchmark uses Gemini 3.1 Flash-Lite with rate limiting by default.

Run without rate limiting only when the API plan supports it:

```bash
uv run python -m src.evaluation.run_expert_query_rewrite_retrieval_benchmark \
  --candidate-k 20 \
  --top-k 10 \
  --no-rate-limit
```

If API responses return HTTP 429 errors, keep rate limiting enabled and rerun the job. The experiment is intentionally not part of the default interactive workflow because its latency is substantially higher than local reranking.

---

### LLM authentication fails

Check local configuration without displaying the key value:

```bash
grep -E "^(MODEL_ID|LLM_BASE_URL|LLM_API_KEY)=" .env | sed 's/LLM_API_KEY=.*/LLM_API_KEY=<configured-or-empty>/'
```

Confirm:

- `LLM_API_KEY` is configured
- `LLM_BASE_URL` is correct
- The selected model is available to the configured account
- The account has available quota

---

### Judge outputs or agreement reports are missing

Check expected files:

```bash
ls -lh \
  data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv \
  data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv \
  data/evaluation_reports/reranked/judge_agreement_summary.csv \
  data/evaluation_reports/reranked/judge_disagreements.csv
```

If a judge run was interrupted, rerun the original command. Checkpointing should skip completed cases.

---

### Manual-review files are missing

Check the review files:

```bash
ls -lh \
  data/evaluation_reports/reranked/manual_review_queue.csv \
  data/evaluation_reports/reranked/manual_review_results.csv
```

If the queue is missing, rebuild it with `src.evaluation.build_manual_review_queue`.

If results are missing, open the **Evaluation Review** tab and complete the blinded review workflow.

---

### Dashboard chart errors

Check the required reranked evaluation artefacts:

```bash
ls -lh \
  data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv \
  data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv \
  data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv \
  data/evaluation_reports/reranked/judge_agreement_summary.csv
```

The repository includes completed artefacts for inspection. Re-run the underlying workflow only if you intentionally need regenerated results.

---

### Dashboard shows no feedback

The empty-state message means that `data/feedback/feedback.csv` is absent, empty, or contains no usable feedback values.

To create feedback:

1. Open the Query tab.
2. Run an analysis.
3. Select **Helpful** or **Not helpful**.
4. Confirm the app reports that feedback was saved.

Then inspect the output:

```bash
ls -lh data/feedback/feedback.csv
head -n 5 data/feedback/feedback.csv
```

---

### External benchmark test data is being used too early

If iterative work begins tuning retrieval, prompts, models, or rubrics against `expert_test.tsv`:

- Stop using the test split for tuning.
- Return to `expert_dev.tsv` for development.
- Freeze curation and evaluation rules.
- Use the held-out test split only for final external evaluation.

---

## Current limits

This runbook covers:

- ATT&CK acquisition and extraction
- PostgreSQL with pgvector
- Database initialisation, loading, and embeddings
- Docker Compose application startup and automated ingestion
- Text, vector, hybrid, reranked, and query-rewrite retrieval experiments
- Local CPU cross-encoder reranking
- Reranked answer-generation comparison
- Reciprocal pairwise LLM-as-judge evaluation
- Blinded manual review of judge disagreements
- Persisted local feedback capture
- Streamlit Query, Dashboard, and Evaluation Review workflows
- External Expert-dataset inspection and label compatibility validation

This runbook does not yet cover:

- A frozen held-out end-to-end external benchmark
- Dynamic loading of dashboard retrieval-comparison metrics from versioned benchmark reports
- Concurrent or production-grade feedback storage
- Production secret management, observability, service networking, scaling, or deployment
- A final Docker Compose production deployment configuration beyond the validated local demonstration stack