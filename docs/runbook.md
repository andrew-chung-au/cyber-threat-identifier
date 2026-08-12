# Runbook


## Purpose


This runbook explains how to reproduce the current Cyber Threat Identifier ingestion, database, embedding, retrieval-benchmark, document-reranking, and answer-generation baselines from a clean checkout.


It covers:


- Environment setup
- Local PostgreSQL with pgvector
- ATT&CK data download and extraction
- Database loading and embedding generation
- Basic verification
- Retrieval benchmark execution: text, vector, hybrid, and vector-plus-reranking
- Local cross-encoder reranker setup and verification
- Answer-generation benchmark execution
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


The current reranking benchmark is designed for local CPU execution. A GPU and ONNX runtime are not required for the current assessed implementation.


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


Set any LLM-related configuration required for answer generation in `.env`. Do not commit `.env`.


---


## Start the database


Start local PostgreSQL with pgvector:


```bash
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


Run this smoke test before running the reranking benchmark:


```bash
uv run python -c "
from src.retrieval.reranker import get_reranker_model

get_reranker_model()
print('Reranker loaded successfully')
"
```


On the first run, Hugging Face downloads the model into the local cache.


A warning about unauthenticated Hugging Face Hub requests does not prevent the model from loading. The warning can be ignored if the download completes successfully. Configure an `HF_TOKEN` only if rate limits or download reliability become a problem.


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


### Reference results


Reference results for the current 226-case benchmark are recorded in [`evaluation-notes.md`](evaluation-notes.md).


The currently selected retrieval configuration is vector retrieval plus local cross-encoder reranking. It improved all reported metrics over vector-only retrieval in the current benchmark.


Do not describe these results as final held-out performance because the current benchmark contains development- and test-derived cases.


### Inspect benchmark outputs


```bash
ls -lh data/evaluation_reports/expert_*_retrieval_results.csv
```


Preview vector-plus-reranking diagnostic fields:


```bash
uv run python -c "
import pandas as pd

df = pd.read_csv(
    'data/evaluation_reports/expert_vector_reranked_retrieval_results.csv'
)

print(
    df[
        [
            'eval_id',
            'expected_attack_ids',
            'vector_candidate_attack_ids',
            'retrieved_attack_ids',
            'original_vector_ranks',
            'reranked_ranks',
            'reranker_scores',
            'mrr',
            'total_retrieval_ms',
        ]
    ].head(5).to_string(index=False)
)
"
```


---


## Run answer-generation benchmark


The current answer-generation pipeline is implemented over Expert-derived cases.


At the current implementation stage, verify which retrieval backend is used by the answer-generation runner before claiming that answer generation uses reranked context. The original answer-generation baseline was implemented using vector retrieval.


### 1. Configure the model


Ensure `.env` contains the required LLM configuration.


Verify the LLM client configuration:


```bash
uv run python - <<'PY'
from src.llm_client import get_default_model, get_client

print("MODEL_ID:", get_default_model())
client = get_client()
print("Client initialised:", type(client).__name__)
PY
```


### 2. Run answer generation


Run all available Expert-derived cases:


```bash
uv run python -m src.evaluation.run_expert_answer_generation
```


Run a smaller development smoke test:


```bash
uv run python -m src.evaluation.run_expert_answer_generation \
  --limit 10 \
  --top-k 5
```


Expected output files:


```text
data/evaluation_reports/expert_answer_generation_v1.jsonl
data/evaluation_reports/expert_answer_generation_v1.csv
```


Each record includes evaluation metadata, expected and retrieved ATT&CK IDs, selected candidates, supporting IDs, answer summary, uncertainty information, review-required status, and model/prompt metadata.


Inspect the first few generated records:


```bash
head -n 3 data/evaluation_reports/expert_answer_generation_v1.jsonl
```


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


Expected Expert split files:


```text
data/external_inspection/mitre-ttp-mapping/datasets/expert/
├── expert_train.tsv
├── expert_dev.tsv
└── expert_test.tsv
```


### Build the current combined retrieval input


The current 226-case retrieval input is built from the upstream Expert development and test files:


```bash
uv run python -m src.evaluation.build_expert_retrieval_cases
```


This file supports implementation benchmarking only. Do not use it as a final held-out benchmark because it combines development and test-derived records.


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


The report contains label compatibility information and should not reproduce external threat-report narrative text.


---


## Rebuild from scratch


Use this only when it is safe to delete the local database volume.


```bash
docker compose down -v
docker compose up -d

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


After corpus, embedding-model, retrieval-code, or reranker-code changes, rerun the applicable benchmarks:


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
docker compose up -d
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


Do not report reranking benchmark results if the benchmark falls back to vector-only retrieval. The current benchmark is intentionally configured to fail instead.


### Hugging Face unauthenticated-request warning


A warning about unauthenticated Hugging Face Hub requests is non-fatal if model download and loading complete successfully.


If downloads fail because of rate limits, configure an `HF_TOKEN` locally or retry after the model cache is available. Never commit a token to `.env.example`, source code, or Git history.


### Retrieval benchmark output missing


```bash
ls -lh data/evaluation_reports/expert_text_retrieval_results.csv
ls -lh data/evaluation_reports/expert_vector_retrieval_results.csv
ls -lh data/evaluation_reports/expert_hybrid_retrieval_results.csv
ls -lh data/evaluation_reports/expert_vector_reranked_retrieval_results.csv
```


### Answer-generation output missing


```bash
ls -lh data/evaluation_reports/expert_answer_generation_v1.csv
ls -lh data/evaluation_reports/expert_answer_generation_v1.jsonl
```


Check `.env` for LLM configuration and rerun with a small `--limit`.


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
- Local cross-encoder reranker validation
- Answer-generation baseline execution
- External Expert dataset inspection
- Expert-label compatibility validation


This runbook does not yet cover:


- Query rewriting execution
- Final answer-rubric scoring workflow
- LLM model-comparison evaluation
- Streamlit interface startup
- User-feedback collection
- Monitoring dashboard execution
- Full application Docker Compose configuration
- Final held-out end-to-end external benchmark evaluation