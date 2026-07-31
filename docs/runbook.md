# Runbook

## Purpose

This runbook explains how to reproduce the current Cyber Threat Identifier ingestion, database, embedding, retrieval-benchmark, and answer-generation baselines from a clean checkout.

It covers:

- Environment setup
- Local PostgreSQL with pgvector
- ATT&CK data download and extraction
- Database loading and embedding generation
- Basic verification
- Retrieval benchmark execution (text, vector, hybrid)
- Answer-generation benchmark execution
- External benchmark repository inspection
- External Expert-label compatibility validation
- Local development reset

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

Create a local environment file:

```bash
cp .env.example .env
```

The default local database connection is:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cyber_threat_identifier
```

Set any LLM-related configuration (for answer generation) in `.env` as needed (for example a model identifier and API key). Do not commit `.env`.

---

## Start the database

Start local PostgreSQL with pgvector:

```bash
docker compose up -d
```

Confirm that the database container is healthy:

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

Run each stage in order.

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

Create the project tables and enable pgvector:

```bash
uv run python -m src.database.db_init
```

### 4. Load technique records

Load processed technique records into PostgreSQL:

```bash
uv run python -m src.database.db_load_techniques
```

This stage loads canonical technique fields and prepares retrieval text. It does not generate embedding vectors.

### 5. Build embeddings

Generate vectors for loaded technique records:

```bash
uv run python -m src.database.db_build_embeddings
```

Optionally create an HNSW index for later vector-retrieval performance experiments:

```bash
uv run python -m src.database.db_build_embeddings \
  --create-hnsw-index
```

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
- No missing embedding vectors after the embedding stage completes

---

## Run retrieval benchmarks

This section reproduces the current retrieval baselines over the Expert-derived evaluation cases.

The current retrieval benchmark input file is:

```text
data/eval/expert_retrieval_cases.csv
```

The implemented retrieval benchmarks compare:

- Text-only retrieval
- Vector retrieval (default v1 backend)
- Hybrid retrieval using Reciprocal Rank Fusion

### 1. Run text retrieval benchmark

```bash
uv run python -m src.evaluation.run_expert_text_retrieval_benchmark
```

Expected output file:

```text
data/evaluation_reports/expert_text_retrieval_results.csv
```

### 2. Run vector retrieval benchmark

```bash
uv run python -m src.evaluation.run_expert_vector_retrieval_benchmark
```

Expected output file:

```text
data/evaluation_reports/expert_vector_retrieval_results.csv
```

This command loads the current embedding model and evaluates dense retrieval over the local ATT&CK corpus.

### 3. Run hybrid retrieval benchmark

```bash
uv run python -m src.evaluation.run_expert_hybrid_retrieval_benchmark
```

Expected output file:

```text
data/evaluation_reports/expert_hybrid_retrieval_results.csv
```

This command evaluates the current hybrid benchmark configuration over the same evaluation cases.

### Reference results

Current reference retrieval results on the full Expert-derived evaluation set are recorded in `docs/evaluation-notes.md`. Use those values to confirm that a local rerun is behaving as expected under the current code and corpus.

### Inspect benchmark outputs

Check that the three result files were written:

```bash
ls -lh data/evaluation_reports/expert_*_retrieval_results.csv
```

Preview the first few rows of one result file:

```bash
head -n 5 data/evaluation_reports/expert_vector_retrieval_results.csv
```

---

## Run answer-generation benchmark

This section runs the current answer-generation pipeline over Expert-derived cases using vector retrieval as the backend.

### 1. Configure the model

Ensure `.env` contains whatever configuration the LLM client needs (for example a model identifier and API key). The details depend on your chosen provider and are described in `docs/decisions.md` and `docs/evaluation-notes.md`.

You can verify configuration by running:

```bash
uv run python - <<'PY'
from src.llm_client import get_default_model, get_client

print("MODEL_ID:", get_default_model())
client = get_client()
print("Client initialised:", type(client).__name__)
PY
```

### 2. Run answer generation

Run the answer-generation benchmark over the Expert-derived cases:

```bash
uv run python -m src.evaluation.run_expert_answer_generation
```

To limit the run during development:

```bash
uv run python -m src.evaluation.run_expert_answer_generation --limit 10 --top-k 5
```

Expected output files:

```text
data/evaluation_reports/expert_answer_generation_v1.jsonl
data/evaluation_reports/expert_answer_generation_v1.csv
```

Each record includes:

- Evaluation case metadata (IDs, split, index)
- Expected ATT&CK IDs
- Retrieved ATT&CK IDs
- Primary and alternative candidate IDs
- Supporting IDs and grounded summary
- Uncertainty note and `review_required` flag
- Prompt version and model metadata
- Token counts (if available)

### Inspect answer outputs

Preview the first few records:

```bash
head -n 3 data/evaluation_reports/expert_answer_generation_v1.jsonl
```

Or inspect the CSV in a notebook or spreadsheet for human review.

---

## External benchmark inspection

This section is optional. It supports feasibility work for the external Expert benchmark candidate and does not form part of the ATT&CK ingestion pipeline.

The external upstream dataset is stored locally under:

```text
data/external_inspection/mitre-ttp-mapping/
```

This directory should remain ignored by Git:

```gitignore
# Raw upstream downloads: regenerated by the ingestion pipeline
data/raw/attack/*.json

# External datasets downloaded only for feasibility inspection
data/external_inspection/
```

### Clone the candidate dataset

Create the inspection directory and clone the upstream repository:

```bash
mkdir -p data/external_inspection

git clone https://github.com/tumeteor/mitre-ttp-mapping.git \
  data/external_inspection/mitre-ttp-mapping
```

Record the exact downloaded upstream revision:

```bash
git -C data/external_inspection/mitre-ttp-mapping rev-parse HEAD
```

The Expert split files should be present at:

```text
data/external_inspection/mitre-ttp-mapping/datasets/expert/
├── expert_train.tsv
├── expert_dev.tsv
└── expert_test.tsv
```

### Validate Expert labels

Validate external Expert labels against the local active Enterprise ATT&CK corpus:

```bash
uv run python -m src.evaluation.validate_external_expert_labels
```

The script expects:

```text
data/external_inspection/mitre-ttp-mapping/datasets/expert/
data/raw/attack/enterprise-attack.json
```

It writes a compatibility report to:

```text
data/evaluation_reports/expert_label_compatibility.csv
```

Inspect labels that are not active in the local ATT&CK corpus:

```bash
awk -F',' 'NR == 1 || $2 != "active"' \
  data/evaluation_reports/expert_label_compatibility.csv
```

This report contains ATT&CK IDs, status, technique names, and split membership. It does not copy threat-report narrative text and may be retained as a project evaluation artefact.

---

## Rebuild from scratch

Use this only for early local development when it is safe to delete the local database.

```bash
docker compose down -v
docker compose up -d

uv run python -m src.database.db_init
uv run python -m src.database.db_load_techniques
uv run python -m src.database.db_build_embeddings
```

This rebuild uses the existing processed corpus.

To also refresh the ATT&CK source corpus, run the download and extraction stages before rebuilding the database:

```bash
uv run python -m src.ingestion.download_attack_data --ref <release-tag-or-commit>
uv run python -m src.ingestion.extract_attack_techniques

uv run python -m src.database.db_init
uv run python -m src.database.db_load_techniques
uv run python -m src.database.db_build_embeddings
```

To rerun retrieval benchmarks after a corpus or retrieval-code change:

```bash
uv run python -m src.evaluation.run_expert_text_retrieval_benchmark
uv run python -m src.evaluation.run_expert_vector_retrieval_benchmark
uv run python -m src.evaluation.run_expert_hybrid_retrieval_benchmark
```

To rerun external label compatibility after a corpus refresh:

```bash
uv run python -m src.evaluation.validate_external_expert_labels
```

To rerun answer generation after prompt or model changes:

```bash
uv run python -m src.evaluation.run_expert_answer_generation
```

---

## Common issues

### `DATABASE_URL is not set`

Create `.env` in the repository root:

```bash
cp .env.example .env
```

Then confirm it contains a valid `DATABASE_URL`.

### Database connection refused

Start PostgreSQL and check its status:

```bash
docker compose up -d
docker compose ps
```

View database logs if the service is not healthy:

```bash
docker compose logs postgres
```

### Input file not found

If `enterprise-attack.json` is missing, rerun the ATT&CK download stage:

```bash
uv run python -m src.ingestion.download_attack_data
```

If `techniques.jsonl` is missing, rerun extraction:

```bash
uv run python -m src.ingestion.extract_attack_techniques
```

If retrieval benchmark input cases are missing, confirm this file exists:

```bash
ls -lh data/eval/expert_retrieval_cases.csv
```

If Expert TSV files are missing during external compatibility validation, clone the external inspection dataset:

```bash
git clone https://github.com/tumeteor/mitre-ttp-mapping.git \
  data/external_inspection/mitre-ttp-mapping
```

### pgvector extension unavailable

Confirm that the Compose PostgreSQL service is running, then recreate the local database:

```bash
docker compose down -v
docker compose up -d

uv run python -m src.database.db_init
```

### Embedding model download warning

If you see a warning about unauthenticated requests while loading the embedding model, the benchmark can still complete successfully. To reduce rate-limit risk and improve download reliability, configure a local token for the embedding provider, or ensure the model is cached on disk.

### Retrieval benchmark output missing

Confirm that the benchmark command completed successfully, then check the output path:

```bash
ls -lh data/evaluation_reports/expert_text_retrieval_results.csv
ls -lh data/evaluation_reports/expert_vector_retrieval_results.csv
ls -lh data/evaluation_reports/expert_hybrid_retrieval_results.csv
```

### Answer-generation output missing

Confirm that the answer-generation command completed successfully, then check:

```bash
ls -lh data/evaluation_reports/expert_answer_generation_v1.csv
ls -lh data/evaluation_reports/expert_answer_generation_v1.jsonl
```

If they are missing, check `.env` for model configuration and rerun with a small `--limit`.

### External benchmark results are being used too early

If benchmark work starts to drift into repeated test-set tuning:

- Stop using `expert_test.tsv` for iterative experiments.
- Move tuning and rubric design back to `expert_dev.tsv`.
- Reconfirm that held-out test rows are only used after benchmark rules are frozen.

---

## Current limits

This runbook currently covers:

- ATT&CK acquisition and extraction
- Database initialisation and record loading
- Embedding generation
- Basic database verification
- Retrieval benchmark execution
- Answer-generation benchmark execution
- External repository inspection
- External Expert-label compatibility validation

This runbook does not yet cover:

- Human-review workflow commands
- Streamlit interface startup
- Monitoring and observability
- Final held-out end-to-end evaluation execution

Those steps should be added once their corresponding modules, rules, and outputs are implemented and validated.