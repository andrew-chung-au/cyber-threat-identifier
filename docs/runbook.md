# Runbook

## Purpose

This runbook explains how to reproduce the current Cyber Threat Identifier ingestion, database, embedding, retrieval-benchmark, document-reranking, query-rewriting, answer-generation, LLM-evaluation, manual-review, feedback, and Streamlit UI baselines from a clean checkout.

It covers:

- Environment setup
- Local PostgreSQL with pgvector
- ATT&CK data download and extraction
- Database loading and embedding generation
- Basic verification
- Retrieval benchmark execution: text, vector, hybrid, vector-plus-reranking, and query-rewrite-plus-reranking
- Local cross-encoder reranker setup and verification
- Query-rewriting benchmark execution with optional rate limiting
- Reranked answer-generation comparison
- Reciprocal pairwise LLM-as-judge evaluation and agreement analysis
- Blinded manual review of judge-disagreement cases
- Streamlit UI, persisted feedback, and monitoring dashboard execution
- External benchmark repository inspection
- External Expert-label compatibility validation
- Local development reset and troubleshooting

For corpus scope, provenance, schema, and committed-data policy, see [`dataset-notes.md`](dataset-notes.md).  
For stable design decisions, see [`decisions.md`](decisions.md).  
For benchmark design, evaluation rules, and results, see [`evaluation-notes.md`](evaluation-notes.md).

---

## Prerequisites

Install:

- The Python version specified in `pyproject.toml`
- `uv`
- Docker Desktop
- Git

Check local tools:

```bash
python --version
uv --version
docker --version
docker compose version
```

Run all commands below from the repository root.

The current reranking and query-rewriting benchmarks are designed for local CPU execution. A GPU and ONNX runtime are not required for the current implementation.

---

## Setup

Clone the repository:

```bash
git clone <repository-url>
cd cyber-threat-identifier
```

Create the environment and install locked dependencies:

```bash
uv sync
```

Install Streamlit and plotting dependencies if they are not already included in the locked environment:

```bash
make install
# or equivalently:
uv pip install streamlit plotly matplotlib
```

Create a local environment file:

```bash
cp .env.example .env
```

The default local database connection is:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cyber_threat_identifier
```

Set LLM configuration in `.env`. Do not commit `.env`.

The selected v1 default answer-generation model is Gemini 3.1 Flash-Lite:

```dotenv
MODEL_ID=gemini-3.1-flash-lite
LLM_API_KEY=<your-gemini-api-key>
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
```

The answer-generation comparison and pairwise judging workflows also use `gemini-3.5-flash-lite` as an evaluated alternative and reciprocal judge.

Do not commit `.env` or share API keys.

---

## Start the database

Start local PostgreSQL with pgvector:

```bash
make docker-up
# or equivalently:
docker compose up -d
```

Check service status:

```bash
docker compose ps
```

Wait until the `postgres` service reports a healthy status before running database or benchmark commands.

If the service remains in `health: starting`, wait a few seconds and run:

```bash
docker compose ps
```

If `psql` is available locally, verify the connection:

```bash
psql "$DATABASE_URL" -c "SELECT 1;"
```

If `psql` is not installed locally, run the check inside the container:

```bash
docker compose exec postgres \
  psql -U postgres -d cyber_threat_identifier -c "SELECT 1;"
```

---

## Build the ATT&CK corpus

Run each stage in order when building from a clean checkout.

### 1. Download ATT&CK data

Download the default upstream reference:

```bash
uv run python -m src.ingestion.download_attack_data
```

For a fixed release baseline, use a pinned upstream tag or commit:

```bash
uv run python -m src.ingestion.download_attack_data --ref <release-tag-or-commit>
```

The downloader writes raw STIX files to:

```text
data/raw/attack/
```

It appends source provenance to:

```text
data/source_manifest.csv
```

### 2. Extract active techniques

Extract active Enterprise ATT&CK techniques and sub-techniques:

```bash
uv run python -m src.ingestion.extract_attack_techniques
```

Expected output:

```text
data/processed/techniques.jsonl
```

### 3. Initialise the database

Create project tables and enable pgvector:

```bash
uv run python -m src.database.db_init
```

### 4. Load technique records

Load processed technique records into PostgreSQL:

```bash
uv run python -m src.database.db_load_techniques
```

This stage loads canonical technique fields and creates structured `embedding_text`. It does not generate embedding vectors.

### 5. Build embeddings

Generate vectors for loaded technique records:

```bash
uv run python -m src.database.db_build_embeddings
```

Optionally create an HNSW index for later vector-search performance experiments:

```bash
uv run python -m src.database.db_build_embeddings \
  --create-hnsw-index
```

HNSW is optional. Exact cosine-distance search remains a valid and reproducible baseline for the current compact ATT&CK corpus.

---

## Verify the build

Check that processed records exist:

```bash
wc -l data/processed/techniques.jsonl
```

Check database tables:

```bash
psql "$DATABASE_URL" -c "\dt"
```

Check that the pgvector extension is enabled:

```bash
psql "$DATABASE_URL" -c "
SELECT extname
FROM pg_extension
WHERE extname = 'vector';
"
```

Check loaded and embedded record counts:

```bash
psql "$DATABASE_URL" -c "
SELECT
  COUNT(*) AS total_techniques,
  COUNT(embedding) AS embedded_techniques,
  COUNT(*) - COUNT(embedding) AS missing_embeddings
FROM techniques;
"
```

Preview one structured record used for vector retrieval and reranking:

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

Check the most recent pipeline audit entries:

```bash
psql "$DATABASE_URL" -c "
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
- One loaded database row per processed technique record
- No missing embedding vectors after embedding generation
- Non-empty `embedding_text` values available for retrieval and reranking

---

## Verify the local reranker

The selected reranker is:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

It runs locally on CPU and is loaded through `sentence-transformers`.

Run this smoke test before running the reranking benchmark or Streamlit query interface:

```bash
uv run python -c "
from src.retrieval.reranker import get_reranker_model

get_reranker_model()
print('Reranker loaded successfully')
"
```

On the first run, Hugging Face downloads the model into the local cache.

A warning about unauthenticated Hugging Face Hub requests does not prevent the model from loading. Configure an `HF_TOKEN` only if rate limits or download reliability become a problem.

The benchmark must fail if the reranker cannot load. Do not treat vector-only fallback as a valid reranking benchmark result.

---

## Run retrieval benchmarks

This section reproduces retrieval results over the current Expert-derived evaluation cases.

The benchmark input file is:

```text
data/eval/expert_retrieval_cases.csv
```

The current benchmark contains 226 Expert-derived cases. It is used for implementation comparison and is not a frozen held-out final benchmark.

The implemented methods are:

- Text-only retrieval
- Vector retrieval
- Hybrid retrieval using Reciprocal Rank Fusion
- Vector retrieval plus local cross-encoder document reranking
- Query rewriting plus vector retrieval plus reranking

### 1. Run text retrieval benchmark

```bash
uv run python -m src.evaluation.run_expert_text_retrieval_benchmark
```

Expected output:

```text
data/evaluation_reports/expert_text_retrieval_results.csv
```

### 2. Run vector retrieval benchmark

```bash
uv run python -m src.evaluation.run_expert_vector_retrieval_benchmark \
  --top-k 10 \
  --output data/evaluation_reports/expert_vector_retrieval_results.csv
```

Expected output:

```text
data/evaluation_reports/expert_vector_retrieval_results.csv
```

### 3. Run hybrid retrieval benchmark

```bash
uv run python -m src.evaluation.run_expert_hybrid_retrieval_benchmark
```

Expected output:

```text
data/evaluation_reports/expert_hybrid_retrieval_results.csv
```

### 4. Run vector-plus-reranking benchmark

Run a small smoke test first:

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

The reranking benchmark uses this flow:

```text
Incident narrative
  → all-MiniLM-L6-v2 query embedding
  → top 20 pgvector candidates
  → local CPU cross-encoder reranking
  → top 10 ranked candidates for evaluation
```

The CSV includes first-stage vector candidate IDs, original vector ranks, reranker scores, reranked ranks, and timing data.

### 5. Run query-rewrite retrieval benchmark

Run a small smoke test first:

```bash
uv run python -m src.evaluation.run_expert_query_rewrite_retrieval_benchmark \
  --limit 5 \
  --candidate-k 20 \
  --top-k 10
```

Run the full benchmark with rate limiting:

```bash
uv run python -m src.evaluation.run_expert_query_rewrite_retrieval_benchmark \
  --candidate-k 20 \
  --top-k 10 \
  --output data/evaluation_reports/local/expert_query_rewrite_retrieval_results.csv
```

Run without rate limiting only if the API plan supports a higher request rate:

```bash
uv run python -m src.evaluation.run_expert_query_rewrite_retrieval_benchmark \
  --candidate-k 20 \
  --top-k 10 \
  --no-rate-limit \
  --output data/evaluation_reports/local/expert_query_rewrite_retrieval_results.csv
```

Expected output:

```text
data/evaluation_reports/local/expert_query_rewrite_retrieval_results.csv
```

This file is written to `data/evaluation_reports/local/`, which is ignored by Git because it contains external narrative text.

The query-rewriting benchmark uses this flow:

```text
Incident narrative
  → LLM query rewriting (gemini-3.1-flash-lite)
  → all-MiniLM-L6-v2 query embedding
  → top 20 pgvector candidates
  → local CPU cross-encoder reranking
  → top 10 ranked candidates for evaluation
```

### Reference results

Reference results for the current 226-case benchmark are recorded in [`evaluation-notes.md`](evaluation-notes.md).

The selected v1 retrieval configuration is vector retrieval plus local cross-encoder reranking. It improved all reported metrics over vector-only retrieval in the current benchmark.

Do not describe these results as final held-out performance because the current benchmark contains development- and test-derived cases.

---

## Run answer-generation comparison (reranked v1)

The current answer-generation comparison uses vector retrieval plus local cross-encoder reranking as its retrieval backend.

The comparison evaluates:

```text
gemini-3.1-flash-lite
gemini-3.5-flash-lite
```

The selected v1 runtime default is:

```text
gemini-3.1-flash-lite
```

### 1. Verify LLM configuration

```bash
uv run python - <<'PY'
from src.llm_client import get_default_model, get_client

print("MODEL_ID:", get_default_model())
client = get_client()
print("Client initialised:", type(client).__name__)
PY
```

### 2. Generate both models' reranked answers

Run the complete comparison:

```bash
uv run python -m src.evaluation.run_expert_llm_comparison_reranked
```

Run a smaller development smoke test if your script supports `--limit`:

```bash
uv run python -m src.evaluation.run_expert_llm_comparison_reranked \
  --limit 10
```

Expected output:

```text
data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv
```

The comparison output contains one structured answer per model per evaluation case, including evaluation metadata, retrieved ATT&CK IDs, selected candidates, grounding and uncertainty fields, review-required status, and available latency or token metadata.

Inspect its first rows:

```bash
head -n 3 data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv
```

---

## Run pairwise LLM-as-judge evaluation

This section reproduces DEC-020. It compares the two answer-generation models using reciprocal LLM judging under the reranked v1 retrieval configuration.

### 1. Run 3.1 as judge

```bash
uv run python -m src.evaluation.run_llm_judge_pairwise \
  --input data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv \
  --output data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv \
  --judge-model gemini-3.1-flash-lite
```

### 2. Run 3.5 as judge

```bash
uv run python -m src.evaluation.run_llm_judge_pairwise \
  --input data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv \
  --output data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv \
  --judge-model gemini-3.5-flash-lite
```

The judge script:

- Randomly assigns underlying model outputs to Answer A and Answer B.
- Shows the incident narrative, both answer summaries, and retrieved ATT&CK IDs.
- Judges technique relevance, narrative grounding, uncertainty framing, analyst actionability, and conciseness.
- Requires a structured verdict containing `reasoning`, `winner`, and `confidence`.
- Maps the selected answer back to its model identifier.
- Uses retry/backoff and checkpoints completed cases.

If a judge run is interrupted or rate-limited, re-run the same command. Existing judged `eval_id` values are loaded from the output file and skipped.

### 3. Analyse judge agreement

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

The current completed reranked run contains:

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

Inspect the stored summary without changing any results:

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

## Run manual review of judge disagreements

This section explains how to create manual-review queues, use the blinded review workflow, and summarise saved outcomes.

### 1. Build the reranked manual-review queue

```bash
uv run python -m src.evaluation.build_manual_review_queue \
  --judge-31 data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv \
  --judge-35 data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv \
  --output data/evaluation_reports/reranked/manual_review_queue.csv
```

### 2. Build the vector-only baseline queue

```bash
uv run python -m src.evaluation.build_manual_review_queue \
  --judge-31 data/evaluation_reports/vector/expert_llm_judged_31_as_judge.csv \
  --judge-35 data/evaluation_reports/vector/expert_llm_judged_35_as_judge.csv \
  --output data/evaluation_reports/vector/manual_review_queue.csv
```

The queues enrich judge-disagreement cases with:

- Incident narrative
- Expected ATT&CK labels and definitions
- Retrieved ATT&CK context
- Blinded structured answers
- Deterministic Answer A/B model randomisation
- Both judges' reasoning and confidence values, hidden until a manual decision is saved

### 3. Run the review interface

Run the standalone review page:

```bash
PYTHONPATH=. uv run streamlit run app/evaluation.py --server.fileWatcherType=none
```

Alternatively, run the main app and open the **Evaluation Review** tab:

```bash
make app
```

The reviewer:

- Selects the reranked v1 or vector-only dataset.
- Views the incident narrative, expected labels, and retrieved context.
- Compares blinded Answer A and Answer B.
- Selects **Answer A**, **Answer B**, or **Tie**.
- Optionally records failure modes and review notes.
- Saves the decision before model identities and judge rationales are revealed.

Results are written to:

```text
data/evaluation_reports/reranked/manual_review_results.csv
data/evaluation_reports/vector/manual_review_results.csv
```

### 4. Summarise manual-review results

Reranked v1:

```bash
uv run python -m src.evaluation.summarize_manual_review \
  --results data/evaluation_reports/reranked/manual_review_results.csv
```

Vector-only baseline:

```bash
uv run python -m src.evaluation.summarize_manual_review \
  --results data/evaluation_reports/vector/manual_review_results.csv
```

The current reranked v1 manual review found:

| Measure | Result |
|---|---:|
| Cases reviewed | 55 |
| Gemini 3.1 wins | 21 |
| Gemini 3.5 wins | 16 |
| Ties | 18 |
| Decisive comparisons | 37 |
| 3.1 share of decisive wins | 56.8% |
| 3.5 share of decisive wins | 43.2% |

The manual-review result informed the selection of `gemini-3.1-flash-lite` as the default v1 answer-generation model in DEC-021.

---

## Run the Streamlit UI and monitoring dashboard

### 1. Pre-requisites

Ensure you have:

- Completed the environment setup.
- Installed Streamlit and plotting dependencies.
- A running database with embeddings for the Query tab.
- The reranker model available locally.
- LLM configuration in `.env` for generated answers.
- Evaluation artefacts available if you want all dashboard charts to render:
  - `data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv`
  - `data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv`
  - `data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv`
  - `data/evaluation_reports/reranked/judge_agreement_summary.csv`

If an evaluation file is missing, the affected chart displays an error rather than failing the whole app.

### 2. Run the main application

```bash
make app
# or equivalently:
PYTHONPATH=. uv run streamlit run app/home.py --server.fileWatcherType=none
```

The app opens at `http://localhost:8501`, unless `.env` configures a different `STREAMLIT_PORT`.

The main application includes:

- **Home** — project overview, data-source links, ATT&CK attribution, and system information.
- **Query** — incident narrative input, vector retrieval plus cross-encoder reranking, structured answer generation, retrieved-technique inspection, and feedback capture.
- **Dashboard** — answer-generation latency, reciprocal judge preferences, retrieval comparison, agreement rate, and collected user feedback.
- **Evaluation Review** — blinded adjudication of judge-disagreement cases for reranked and vector-only evaluation sets.

### 3. Query workflow

The Query tab:

1. Accepts a pasted incident narrative or a sample query.
2. Embeds the narrative.
3. Retrieves the top 20 vector candidates.
4. Reranks candidates locally and returns the top 5.
5. Generates a structured answer using the model specified by `MODEL_ID`.
6. Displays the answer summary, grounding note, uncertainty note, and retrieved technique descriptions.
7. Lets the user submit **Helpful** or **Not helpful** feedback.

Feedback is persisted by `src.monitoring.feedback_store.save_feedback` to:

```text
data/feedback/feedback.csv
```

Each feedback record includes the generated query ID, feedback type, configured model ID, query text, generated answer, and retrieved technique IDs.

### 4. Dashboard contents

Run the dashboard as a standalone page:

```bash
make dashboard
# or equivalently:
PYTHONPATH=. uv run streamlit run app/dashboard.py --server.fileWatcherType=none
```

The dashboard shows:

1. **Answer Generation Latency Distribution**  
   Reads latency values from `expert_llm_comparison_reranked_v1.csv`.

2. **Judge Preferences: Gemini 3.5 Flash-Lite as Judge**  
   Shows how the 3.5 judge ranked the two candidate models.

3. **Judge Preferences: Gemini 3.1 Flash-Lite as Judge**  
   Shows how the 3.1 judge ranked the two candidate models.

4. **Retrieval Method Comparison**  
   Compares MRR and Hit@3 for vector-only, vector-plus-reranking, and query-rewrite-plus-reranking.

5. **Judge Agreement Rate**  
   Shows agreement versus disagreement between the reciprocal judges.

6. **User Feedback Distribution**  
   Reads persisted `thumbs_up` and `thumbs_down` feedback from `data/feedback/feedback.csv`.

The current retrieval-comparison values are defined directly in `app/dashboard.py` from the documented DEC-018 and DEC-019 results. Update those values whenever the documented benchmark baseline changes. They are not currently loaded dynamically from retrieval benchmark CSVs.

If no feedback has been submitted, the dashboard correctly displays:

```text
No feedback collected yet. Use the main app to submit feedback!
```

This message means no rows have yet been saved; it does not mean feedback persistence is unavailable.

### 5. Dockerised Streamlit app

The repository contains `app/Dockerfile`, which builds a Streamlit image and starts:

```text
streamlit run app/home.py
```

Build the application image:

```bash
docker build -f app/Dockerfile -t cyber-threat-identifier-app .
```

Run it against a PostgreSQL service reachable from the container. Supply required database and LLM environment variables explicitly:

```bash
docker run --rm -p 8501:8501 \
  --env-file .env \
  cyber-threat-identifier-app
```

If `compose.yaml` defines an application service as well as PostgreSQL, use the repository's Compose command instead:

```bash
docker compose up --build
```

The Streamlit app needs access to PostgreSQL, a local or cached reranker model, and valid LLM credentials to fully support the Query tab.

---

## External benchmark inspection

This optional section supports feasibility work for the Security-TTP-Mapping Expert benchmark candidate. It is not part of ATT&CK ingestion.

The local inspection directory is:

```text
data/external_inspection/mitre-ttp-mapping/
```

This directory must remain ignored by Git because it may contain externally sourced threat-report text.

### Clone the candidate dataset

```bash
mkdir -p data/external_inspection

git clone https://github.com/tumeteor/mitre-ttp-mapping.git \
  data/external_inspection/mitre-ttp-mapping
```

Record the downloaded upstream revision:

```bash
git -C data/external_inspection/mitre-ttp-mapping rev-parse HEAD
```

### Build the current combined retrieval input

The current 226-case retrieval input is built from the upstream Expert development and test files:

```bash
uv run python -m src.evaluation.build_expert_retrieval_cases
```

This file supports implementation benchmarking only. Do not use it as a final held-out benchmark because it combines development- and test-derived records.

### Validate Expert labels

Validate upstream Expert labels against the local active ATT&CK corpus:

```bash
uv run python -m src.evaluation.validate_external_expert_labels
```

Expected report:

```text
data/evaluation_reports/expert_label_compatibility.csv
```

Inspect labels that are not active:

```bash
awk -F',' 'NR == 1 || $2 != "active"' \
  data/evaluation_reports/expert_label_compatibility.csv
```

---

## Rebuild from scratch

Use this only when it is safe to delete the local database volume.

```bash
make docker-down
docker compose down -v
make docker-up

uv run python -m src.database.db_init
uv run python -m src.database.db_load_techniques
uv run python -m src.database.db_build_embeddings
```

To refresh the ATT&CK corpus first:

```bash
uv run python -m src.ingestion.download_attack_data --ref <release-tag-or-commit>
uv run python -m src.ingestion.extract_attack_techniques

uv run python -m src.database.db_init
uv run python -m src.database.db_load_techniques
uv run python -m src.database.db_build_embeddings
```

After corpus, retrieval, reranker, prompt, model, or evaluation-code changes, rerun the applicable benchmarks and evaluations:

```bash
uv run python -m src.evaluation.run_expert_text_retrieval_benchmark

uv run python -m src.evaluation.run_expert_vector_retrieval_benchmark \
  --top-k 10 \
  --output data/evaluation_reports/expert_vector_retrieval_results.csv

uv run python -m src.evaluation.run_expert_hybrid_retrieval_benchmark

uv run python -m src.evaluation.run_expert_reranked_vector_retrieval_benchmark \
  --candidate-k 20 \
  --top-k 10 \
  --output data/evaluation_reports/expert_vector_reranked_retrieval_results.csv

uv run python -m src.evaluation.run_expert_query_rewrite_retrieval_benchmark \
  --candidate-k 20 \
  --top-k 10 \
  --output data/evaluation_reports/local/expert_query_rewrite_retrieval_results.csv

uv run python -m src.evaluation.run_expert_llm_comparison_reranked

uv run python -m src.evaluation.run_llm_judge_pairwise \
  --input data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv \
  --output data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv \
  --judge-model gemini-3.1-flash-lite

uv run python -m src.evaluation.run_llm_judge_pairwise \
  --input data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv \
  --output data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv \
  --judge-model gemini-3.5-flash-lite

uv run python -m src.evaluation.analyze_judge_agreement \
  --judge-31 data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv \
  --judge-35 data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv
```

Rebuild manual-review queues only when needed. Do not overwrite completed queues or results without creating a backup first:

```bash
cp data/evaluation_reports/reranked/manual_review_results.csv \
  data/evaluation_reports/reranked/manual_review_results.backup.csv
```

Rerun compatibility validation after any ATT&CK corpus refresh:

```bash
uv run python -m src.evaluation.validate_external_expert_labels
```

---

## Common issues

### `DATABASE_URL is not set`

Create `.env` in the repository root:

```bash
cp .env.example .env
```

Confirm it contains a valid `DATABASE_URL`.

### Database connection refused

Start PostgreSQL and inspect status:

```bash
make docker-up
docker compose ps
```

Inspect startup logs if PostgreSQL is not healthy:

```bash
docker compose logs postgres
```

### Input file not found

If `enterprise-attack.json` is missing:

```bash
uv run python -m src.ingestion.download_attack_data
```

If `techniques.jsonl` is missing:

```bash
uv run python -m src.ingestion.extract_attack_techniques
```

If Expert retrieval cases are missing:

```bash
uv run python -m src.evaluation.build_expert_retrieval_cases
```

### Reranker model cannot load

Confirm dependencies are installed:

```bash
uv sync
```

Run the isolated reranker smoke test:

```bash
uv run python -c "
from src.retrieval.reranker import get_reranker_model

get_reranker_model()
print('Reranker loaded successfully')
"
```

Check internet access for the initial Hugging Face download. Once the model has loaded successfully, it should be available through the local Hugging Face cache.

### Streamlit emits `torchvision` warnings

Some Streamlit file-watcher configurations inspect optional image-processing modules inside `transformers`. If `torchvision` is not installed, this can produce repeated `ModuleNotFoundError: No module named 'torchvision'` tracebacks even when the text-retrieval app itself still works.

Use the recommended Streamlit command, which disables that file watcher:

```bash
PYTHONPATH=. uv run streamlit run app/home.py --server.fileWatcherType=none
```

If the application functions correctly, these warnings do not affect retrieval, answer generation, stored evaluation results, or feedback persistence.

If you prefer to install the optional dependency:

```bash
uv pip install torchvision
```

### Query-rewriting benchmark runs slowly

The query-rewriting benchmark uses Gemini 3.1 Flash Lite with rate limiting at 15 requests/minute by default.

To disable rate limiting only if the API plan supports it:

```bash
uv run python -m src.evaluation.run_expert_query_rewrite_retrieval_benchmark \
  --candidate-k 20 \
  --top-k 10 \
  --no-rate-limit
```

If queries fail with 429 errors, keep rate limiting enabled or reduce concurrency.

### LLM API key not configured

If query rewriting, answer generation, or judging fails with authentication errors:

```bash
grep -E "LLM_API_KEY|MODEL_ID|LLM_BASE_URL" .env
```

Ensure `.env` contains valid Gemini API credentials.

### LLM judge output or agreement files missing

```bash
ls -lh data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv
ls -lh data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv
ls -lh data/evaluation_reports/reranked/judge_agreement_summary.csv
ls -lh data/evaluation_reports/reranked/judge_disagreements.csv
```

If a judge run failed with quota or rate-limit errors, rerun the same command. Checkpointing should skip completed cases.

### Manual-review output missing

```bash
ls -lh data/evaluation_reports/reranked/manual_review_queue.csv
ls -lh data/evaluation_reports/reranked/manual_review_results.csv
```

If the queue does not exist, build it with `src.evaluation.build_manual_review_queue`.

If results do not exist, open the **Evaluation Review** tab and complete the blinded review workflow.

### Streamlit dashboard charts show errors

Confirm all required files exist:

```bash
ls -lh data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv
ls -lh data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv
ls -lh data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv
ls -lh data/evaluation_reports/reranked/judge_agreement_summary.csv
```

If a chart is missing, run the corresponding benchmark or evaluation workflow.

### Dashboard shows no feedback

The message:

```text
No feedback collected yet. Use the main app to submit feedback!
```

means `data/feedback/feedback.csv` does not yet exist, is empty, or has no usable `feedback` values.

Feedback persistence is implemented. To create feedback data:

1. Open the Query tab.
2. Run an analysis.
3. Select **Helpful** or **Not helpful**.
4. Confirm that the app reports the saved feedback path.

Then verify:

```bash
ls -lh data/feedback/feedback.csv
head -n 5 data/feedback/feedback.csv
```

### External benchmark results are being used too early

If work starts to repeatedly tune on `expert_test.tsv`:

- Stop using the test split for iterative experiments.
- Return to `expert_dev.tsv` for retrieval, prompt, model, and rubric changes.
- Freeze curation and evaluation rules before running a final held-out test evaluation.

---

## Current limits

This runbook currently covers:

- ATT&CK acquisition and extraction
- Database initialisation, loading, and embeddings
- Local PostgreSQL with pgvector
- Text, vector, hybrid, and vector-plus-reranking retrieval benchmarks
- Query-rewriting retrieval benchmark with optional rate limiting
- Local cross-encoder reranker validation
- Reranked answer-generation comparison
- Reciprocal pairwise LLM-as-judge evaluation and agreement analysis
- Blinded manual review of judge-disagreement cases
- Persisted query-feedback capture
- Streamlit UI and monitoring dashboard execution
- Streamlit application Dockerfile build process
- External Expert dataset inspection
- Expert-label compatibility validation

This runbook does not yet cover:

- Final rubric-scored answer evaluation across a frozen benchmark
- Dynamic dashboard loading for the retrieval-comparison benchmark values
- Production deployment configuration, secret management, and observability
- Final held-out end-to-end external benchmark evaluation