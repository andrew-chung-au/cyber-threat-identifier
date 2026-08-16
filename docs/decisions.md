# Decisions

This document records stable design decisions for Cyber Threat Identifier.

Each entry uses a lightweight Architecture Decision Record (ADR) format. For chronological implementation notes, experiments, and progress updates, see [`project-log.md`](project-log.md).

For corpus provenance, schema, processing rules, and data-quality notes, see [`dataset-notes.md`](dataset-notes.md). For benchmark design, metrics, and evaluation findings, see [`evaluation-notes.md`](evaluation-notes.md). For reproducible setup and commands, see [`runbook.md`](runbook.md).

## Decision index

| ID      | Decision                                         | Status            | Date       |
|---------|--------------------------------------------------|-------------------|------------|
| DEC-001 | Project scope                                    | Accepted          | 2026-07-27 |
| DEC-002 | Core corpus selection                            | Accepted          | 2026-07-27 |
| DEC-003 | Product naming and ATT&CK references             | Accepted          | 2026-07-27 |
| DEC-004 | Public repository and attribution                | Accepted; updated | 2026-08-16 |
| DEC-005 | Repository structure                             | Accepted          | 2026-07-29 |
| DEC-006 | Execution convention                             | Accepted; updated | 2026-08-16 |
| DEC-007 | Source provenance and versioning                 | Accepted          | 2026-07-29 |
| DEC-008 | Retrieval unit and chunking                      | Accepted          | 2026-07-29 |
| DEC-009 | Processed corpus schema and snapshot policy      | Accepted          | 2026-07-30 |
| DEC-010 | Database and embedding pipeline                  | Accepted          | 2026-07-29 |
| DEC-011 | Embedding baseline                               | Accepted baseline | 2026-07-30 |
| DEC-012 | Vector index strategy                            | Accepted          | 2026-07-30 |
| DEC-013 | Documentation strategy                           | Accepted          | 2026-07-30 |
| DEC-014 | External evaluation benchmark strategy           | Accepted; updated | 2026-08-16 |
| DEC-015 | Default retrieval method for v1                  | Superseded        | 2026-07-31 |
| DEC-016 | Retrieval-module refactor and shared helpers     | Accepted          | 2026-07-31 |
| DEC-017 | Answer-generation pipeline and output contract   | Accepted baseline; updated | 2026-08-16 |
| DEC-018 | Default retrieval configuration with reranking   | Accepted; updated | 2026-08-16 |
| DEC-019 | User query rewriting evaluation and decision     | Accepted          | 2026-08-13 |
| DEC-020 | Pairwise LLM-as-judge evaluation for answer generation | Accepted | 2026-08-16 |
| DEC-021 | Default answer-generation model selection        | Accepted          | 2026-08-16 |
| DEC-022 | Docker Compose execution and automated ingestion | Accepted          | 2026-08-16 |
| DEC-023 | Reviewable evaluation artefacts                  | Accepted          | 2026-08-16 |

---

## DEC-001 — Project scope

**Status:** Accepted  
**Date:** 2026-07-27

### Context

The project needs a focused, portfolio-ready security use case with a clear retrieval problem, bounded corpus, and measurable outcomes.

### Decision

Build an incident-to-technique retrieval application that maps unstructured cyber incident narratives to likely Enterprise MITRE ATT&CK techniques and sub-techniques.

Version 1 will retrieve and present relevant technique records with source-grounded evidence. It will not claim to perform incident response, establish attribution, determine incident severity, replace analyst judgement, or guarantee complete behavioural coverage.

### Alternatives considered

- ATT&CK relationship explorer.
- ATT&CK detection-gap assistant.
- Broad cyber advisory or planning assistant.
- General threat-intelligence chatbot.
- Multi-purpose SOC copilot.

### Consequences

- The scope is specific, commercially relevant, and easier to evaluate than a broad cyber assistant.
- The project has a clear input–output relationship: incident narrative in, ranked technique evidence out.
- The narrower scope supports fewer use cases than a full planning or response system.
- User-facing documentation must state that outputs are analyst-supporting suggestions rather than conclusive determinations.

---

## DEC-002 — Core corpus selection

**Status:** Accepted  
**Date:** 2026-07-27

### Context

The initial corpus must be public, reproducible, relevant to incident-to-technique mapping, and structured enough to preserve source evidence.

### Decision

Use the official Enterprise MITRE ATT&CK STIX 2.1 dataset as the initial core corpus.

Version 1 includes active Enterprise ATT&CK `attack-pattern` objects: techniques and sub-techniques. Revoked and deprecated objects are excluded.

### Alternatives considered

- General cyber-security guidance corpora.
- Unstructured threat-intelligence web content.
- Public incident reports as the primary corpus.
- Multiple cyber knowledge bases from the start.
- A broad crawl of cyber-security content.

### Consequences

- The source maps directly to adversary behaviours and technique identification.
- The STIX format provides identifiers, descriptions, tactics, platforms, URLs, and timestamps needed for retrieval and evidence display.
- Version 1 excludes potentially useful supporting objects, including procedure examples, software, groups, mitigations, detection strategies, analytics, data sources, and relationships.
- ATT&CK is not a complete incident-response or threat-intelligence corpus, so the application must not overstate its coverage.

---

## DEC-003 — Product naming and ATT&CK references

**Status:** Accepted  
**Date:** 2026-07-27

### Context

The project requires a professional product title while using a third-party knowledge base with trademark and branding requirements.

### Decision

Use **Cyber Threat Identifier** as the product title.

Use **MITRE ATT&CK®** in the first substantive documentation reference and **ATT&CK** in later references where appropriate. Do not use ATT&CK in the project, product, repository, service, company, or logo name. Do not imply MITRE sponsorship, affiliation, or endorsement.

### Alternatives considered

- Product names containing ATT&CK.
- Broader, generic cyber-assistant names.
- More creative names with less immediate clarity.
- Names focused on RAG or vector-search technology rather than the user task.

### Consequences

- The title is direct, professional, and avoids using ATT&CK as a product identity.
- The README must clearly explain the project's corpus and its relationship to MITRE ATT&CK.
- Attribution and terminology must be applied consistently throughout the repository.

---

## DEC-004 — Public repository and attribution

**Status:** Accepted; updated 2026-08-16  
**Date:** 2026-07-30

### Context

The repository is intended for portfolio use, repeatable demonstration, and public review. It uses external knowledge sources with attribution, licensing, and branding requirements.

The project also needs a practical Git policy for raw source downloads, processed corpus data, evaluation reports, and future external benchmark artefacts.

### Decision

Keep the repository publicly publishable, reproducible, source-safe, and easy to inspect.

The repository will include:

- Clear MITRE attribution and applicable copyright, licence, and terms wording.
- Source URLs, version references, download dates, and checksums.
- No secret values or credentials.
- `.env.example` rather than a committed `.env` file.
- Dependency definitions in `pyproject.toml` and `uv.lock`.
- A reproducible runbook.
- The processed ATT&CK corpus snapshot, `data/processed/techniques.jsonl`.
- The ATT&CK download provenance record, `data/source_manifest.csv`.
- Completed evaluation inputs and reports so markers can inspect reported evidence without API credentials, quota, or lengthy reruns.

The repository will not commit:

- Raw upstream ATT&CK STIX downloads.
- The local external-source inspection clone.
- Secrets, local environments, caches, Docker volumes, or runtime feedback.

The committed evaluation artefacts are derived from the Security-TTP-Mapping Expert configuration. The repository records the upstream repository, configuration, revision, licence declaration, and project filtering/evaluation treatment. The exact upstream revision used for the current artefacts is:

```text
Repository: https://github.com/tumeteor/mitre-ttp-mapping
Configuration: Expert
Revision: a16856a6438ca2b7888c5cadfba6d7c854f04a55
Licence declared by upstream: CC BY 4.0
```

This project is independent of the upstream authors and does not imply their endorsement.

### Alternatives considered

- Private exploratory notebook-style build.
- Manual local setup with undocumented steps.
- Commit all raw and processed source artefacts.
- Ignore all generated data, including the processed corpus.
- Keep every evaluation report local, requiring markers to rerun API-bound work.
- Commit an external benchmark before recording its provenance and attribution.
- Commit environment-specific configuration for convenience.

### Consequences

- Reviewers can inspect the derived ATT&CK corpus and completed evaluation evidence without running the full system.
- Raw source artefacts remain reproducible without unnecessarily duplicating upstream downloads.
- Runtime feedback remains separate from fixed offline evidence because it may contain user-entered narratives and generated answers.
- Evaluation reports must retain the documented upstream attribution and must not be described as final held-out performance when they combine development- and test-derived cases.
- The project accepts the maintenance responsibility of keeping committed report outputs aligned with documented decisions.

---

## DEC-005 — Repository structure

**Status:** Accepted  
**Date:** 2026-07-29

### Context

The project will contain distinct ingestion, database, retrieval, evaluation, generation, interface, and monitoring responsibilities. The repository must remain simple while supporting that growth.

### Decision

Use a grouped, pipeline-oriented `src/` structure:

```text
src/
├── __init__.py
├── db.py
├── llm_client.py
├── pricing.py
├── ingestion/
├── database/
├── retrieval/
├── evaluation/
├── generation/
└── monitoring/
```

Use `__init__.py` files in package directories. Place external benchmark inspection, curation, compatibility validation, retrieval evaluation, and answer evaluation modules in `src/evaluation/`.

### Alternatives considered

- A flat `src/` directory containing every module.
- A top-level `scripts/` directory plus a separate application package.
- A fully packaged distributable Python library layout.
- Notebook-first implementation.
- Placing external benchmark validation in the ingestion package.

### Consequences

- Code is easier to scan by pipeline responsibility as the project grows.
- Grouped directories require module-aware execution commands.
- External benchmark checks are kept separate from ATT&CK source ingestion.
- The project remains an application-oriented portfolio repository rather than a publishable Python package.

---

## DEC-006 — Execution convention

**Status:** Accepted; updated 2026-08-16  
**Date:** 2026-07-29

### Context

The grouped `src/` layout needs a consistent way to run modules and resolve imports reliably. The Docker image also needs to use the same locked environment as local development.

### Decision

Run project stages from the repository root using `uv run python`.

Prefer Python module execution for pipeline modules that import project packages:

```bash
uv run python -m src.ingestion.download_attack_data
```

Direct file execution is acceptable for self-contained operational scripts that do not depend on project-package imports:

```bash
uv run python src/evaluation/validate_external_expert_labels.py
```

The Docker Compose ingestion service uses the same convention inside the container:

```bash
uv run python -m src.database.db_init
```

Do not use plain system `python` for Compose ingestion stages because the project dependencies are installed in the `uv` environment.

### Alternatives considered

- Run every file directly using paths such as `python src/database/db_init.py`.
- Invoke plain system Python from the Compose ingestion service.
- Add `src/` manually to `PYTHONPATH`.
- Install the project as a package before every execution.

### Consequences

- Imports remain predictable across functional subdirectories.
- Local and containerised pipeline execution use the same dependency environment.
- Commands must be run from the repository root.
- Compose ingestion fails early when a stage fails rather than presenting partial output as a successful build.
- Self-contained validation scripts can remain simple while package-dependent pipeline stages use module execution.

---

## DEC-007 — Source provenance and versioning

**Status:** Accepted  
**Date:** 2026-07-29

### Context

The ATT&CK repository's default reference can change over time, while evaluation and portfolio evidence require a reproducible source baseline.

### Decision

Download source data from the official `mitre-attack/attack-stix-data` repository and record acquisition metadata.

The downloader records the source URL, download timestamp, repository reference, local path, SHA-256 checksum, and notes in `data/source_manifest.csv`.

The default source reference is `master`, while a `--ref` option supports a fixed release tag for reproducible baselines.

Before reporting comparable retrieval or answer-evaluation results, pin the local Enterprise ATT&CK corpus to a fixed upstream release or commit and record that release in the evaluation artefacts.

### Alternatives considered

- Download a manually exported ATT&CK file.
- Use a third-party mirror or transformed dataset.
- Use only the moving default reference.
- Commit downloaded files without recording provenance.

### Consequences

- The project has a clear acquisition and provenance trail.
- A current-data workflow and a strict-reproduction workflow are both supported.
- A fixed release must be used when reporting formally comparable retrieval and answer-evaluation results.
- Maintaining both workflows adds a small documentation burden.

---

## DEC-008 — Retrieval unit and chunking

**Status:** Accepted  
**Date:** 2026-07-29

### Context

The project needs a retrieval unit that preserves technique identity, metadata, evidence, and source provenance without adding unnecessary transformation complexity.

### Decision

Use one active Enterprise ATT&CK technique or sub-technique as one retrieval unit for version 1.

Do not apply document-style chunking to the initial technique corpus.

Each technique record produces:

- One processed JSONL record.
- One PostgreSQL row.
- One `embedding_text` field.
- One embedding vector.
- One retrieval result.

### Alternatives considered

- Fixed-size token chunks with overlap.
- Sentence-based chunks.
- Heading-aware chunks.
- One description-only embedding without technique metadata.
- One combined document containing all techniques.

### Consequences

- The retrieval unit remains source-native and easy to explain.
- Technique identity, tactics, platforms, description, and provenance remain together.
- The initial corpus is compact enough that splitting descriptions adds complexity without a clear benefit.
- Future long-form sources may require a separate chunked-document layer.

---

## DEC-009 — Processed corpus schema and snapshot policy

**Status:** Accepted  
**Date:** 2026-07-30

### Context

The raw STIX bundle is not convenient for direct inspection, validation, or database loading. The project needs a clear intermediate artefact that is reproducible and easy for portfolio reviewers to inspect.

### Decision

Write extracted technique records to:

```text
data/processed/techniques.jsonl
```

Commit the processed JSONL corpus as an inspectable derived snapshot of the current retrieval corpus.

Each record contains, at minimum:

- `stix_id`
- `attack_id`
- `name`
- `is_subtechnique`
- `parent_attack_id`
- `tactics`
- `platforms`
- `description_raw`
- `description_clean`
- `source_url`
- `created`
- `modified`

Treat the official Enterprise ATT&CK STIX bundle as the authoritative source. Treat `techniques.jsonl` as a reproducible project-derived artefact that is regenerated when the source reference changes.

### Alternatives considered

- Load directly from STIX JSON into PostgreSQL.
- Use CSV as the primary processed representation.
- Store only embeddings and minimal metadata.
- Preserve only cleaned descriptions.
- Ignore the processed corpus and require every reviewer to regenerate it.
- Commit the full raw STIX bundle as well as the processed corpus.

### Consequences

- JSONL is easy to inspect, stream, validate, and load.
- Keeping raw and cleaned descriptions supports evidence display and retrieval quality.
- Reviewers can inspect the actual retrieval units directly in the repository.
- Corpus updates require intentional review of both `techniques.jsonl` and `source_manifest.csv`.
- Detailed schema validation and data-quality checks belong in `dataset-notes.md` and implementation tests.

---

## DEC-010 — Database and embedding pipeline

**Status:** Accepted  
**Date:** 2026-07-29

### Context

The first database loader combined schema creation, source-record loading, embedding generation, upserting, and vector-index creation. That made reruns and model comparisons harder.

### Decision

Separate database initialisation, technique loading, and embedding generation into dedicated modules.

Use PostgreSQL with pgvector. Store canonical technique fields and vectors in `techniques`, and record pipeline runs in `ingestion_runs`.

### Alternatives considered

- One combined schema, load, and embedding script.
- A vector database without PostgreSQL.
- A file-based vector index only.
- SQLite without vector-search support.
- Hosted retrieval infrastructure.

### Consequences

- Embedding models can be tested without downloading or extracting source data again.
- Structured records can be inspected and queried before vectors exist.
- PostgreSQL and pgvector must be available for local development.
- The pipeline has more stages, but each stage has a narrower responsibility.
- Database schema details and operational commands belong in the runbook and code, not this decision record.

---

## DEC-011 — Embedding baseline

**Status:** Accepted baseline  
**Date:** 2026-07-30

### Context

The project needs a local embedding model for an initial vector-retrieval baseline before comparing retrieval approaches through evaluation.

### Decision

Use `sentence-transformers/all-MiniLM-L6-v2` as the initial local embedding baseline.

Construct embedding text from the technique ID, name, tactic names, platform names, and cleaned description. Normalise vectors and use cosine-distance retrieval.

This is an accepted implementation baseline, not a final default-model selection. The final retrieval configuration will be selected only after text, vector, and hybrid approaches are evaluated against the same documented incident-narrative benchmark.

### Alternatives considered

- Description-only embeddings.
- Larger local Sentence Transformers models.
- Hosted embedding APIs.
- Sparse full-text retrieval only.
- Hybrid retrieval from the first iteration.

### Consequences

- The model is lightweight and appropriate for local development.
- Including metadata may improve context but can bias retrieval toward broad tactic or platform matches.
- The embedding pipeline can be validated before the evaluation dataset is complete.
- Later evaluation may replace this model or select text or hybrid retrieval as the default method.

---

## DEC-012 — Vector index strategy

**Status:** Accepted  
**Date:** 2026-07-30

### Context

The initial corpus contains approximately 700 technique and sub-technique records. At this scale, exact cosine-distance search is practical and provides a clear baseline for retrieval evaluation.

The project should still support an indexed vector-search path so that HNSW can be tested later as a performance optimisation.

### Decision

Use exact cosine-distance vector retrieval as the initial vector-retrieval baseline.

Support optional creation of a pgvector HNSW index using cosine-distance operations after the embedding pipeline has been validated. Do not treat HNSW creation as a required ingestion or embedding-pipeline step.

Evaluate the HNSW index only if later corpus size, latency measurements, or deployment requirements justify approximate nearest-neighbour search.

### Alternatives considered

- Create an HNSW index automatically during every embedding build.
- Exact vector search only.
- IVFFlat index.
- No database vector index support.
- External vector database.

### Consequences

- The initial retrieval baseline remains simple, deterministic, and easy to validate.
- The runbook does not require index creation for a successful corpus build.
- HNSW remains available as a later performance optimisation without changing the database schema or embedding format.
- Any later comparison must distinguish exact and approximate vector retrieval and record index settings with its evaluation results.
- The project avoids presenting an unnecessary index as evidence of production scale before it is needed.

---

## DEC-013 — Documentation strategy

**Status:** Accepted  
**Date:** 2026-07-30

### Context

The project needs to be presentation-ready while retaining an auditable record of design choices, source processing, evaluation evidence, interface behaviour, and reproducible commands.

Documentation must be split clearly enough that the README and runbook do not become long, overlapping project specifications.

### Decision

Separate public overview, decisions, working notes, dataset evidence, evaluation evidence, and operational instructions across dedicated files:

- `README.md` — concise public project overview, problem, scope, current status, architecture summary, quick start, interface overview, limitations, and attribution.
- `docs/project-log.md` — chronological progress, discoveries, temporary issues, implementation notes, and immediate next steps.
- `docs/decisions.md` — stable architectural and design decisions with alternatives and consequences.
- `docs/dataset-notes.md` — source provenance, corpus scope, schema, extraction rules, data-quality notes, and committed-versus-ignored artefact policy.
- `docs/evaluation-notes.md` — benchmark design, retrieval configurations, metrics, answer-generation experiments, human review, findings, and failure analysis.
- `docs/runbook.md` — reproducible setup, pipeline commands, verification checks, evaluation commands, manual-review workflow, interface usage, reset instructions, and common troubleshooting.

The Streamlit interface and monitoring dashboard are documented in the README and runbook. Their stable architectural implications are recorded here only when they affect project behaviour, evaluation traceability, or reproducibility.

Keep detailed rationale in the relevant evidence or decision document rather than duplicating it in the README or runbook.

### Alternatives considered

- Put all documentation in the README.
- Maintain only one running project log.
- Use the runbook as a complete project specification.
- Keep implementation notes outside the repository.
- Use notebook comments as the primary record.
- Document the interface only through screenshots or informal notes.

### Consequences

- The README remains concise and useful to portfolio reviewers.
- The runbook remains operational and can be used without reading the entire project history.
- Dataset rules and evaluation evidence have clear homes outside the runbook.
- Interface behaviour, manual review, and feedback persistence are documented where users and reviewers need them.
- Multiple files require disciplined maintenance when decisions or implementation status change.
- The repository provides a clearer and more credible evidence trail for technical reviewers.

---

## DEC-014 — External evaluation benchmark strategy

**Status:** Accepted; updated 2026-08-16  
**Date:** 2026-07-30

### Context

The project needs a credible external evaluation source for assessing whether the full system can map realistic cyber-threat narratives to relevant Enterprise ATT&CK technique candidates.

A manually authored internal benchmark remains useful for early pipeline checks, but it is not sufficient for final performance claims because project-authored narratives and expected labels can introduce author bias.

The `tumeteor/mitre-ttp-mapping` repository contains an Expert dataset configuration with pre-split threat-report narratives and externally supplied ATT&CK technique or sub-technique labels. The downloaded upstream source is stored locally under `data/external_inspection/mitre-ttp-mapping/` for feasibility inspection.

Compatibility validation against the current local active Enterprise ATT&CK corpus found:

- 290 unique labels across all Expert train, development, and test splits.
- 281 active labels.
- 3 deprecated labels.
- 6 revoked labels.
- 0 absent labels.
- 4 held-out test rows containing one or more non-active labels.
- 153 of 157 held-out test rows containing only active labels before later curation.

The exact upstream revision used for the current committed evaluation artefacts is:

```text
Repository: https://github.com/tumeteor/mitre-ttp-mapping
Configuration: Expert
Revision: a16856a6438ca2b7888c5cadfba6d7c854f04a55
Licence declared by upstream: CC BY 4.0
```

### Decision

Adopt the Security-TTP-Mapping **Expert** configuration as the leading candidate external benchmark for future end-to-end retrieval and answer evaluation.

Use the upstream splits as follows:

- `expert_train.tsv` — optional exploratory analysis only.
- `expert_dev.tsv` — develop and freeze answer format, curation rules, retrieval settings, prompt configuration, and scoring rubric.
- `expert_test.tsv` — held-out final external evaluation only.

A record is eligible for the eventual curated benchmark only when every upstream expected ATT&CK ID is active in the project's pinned local Enterprise ATT&CK corpus.

Do not automatically remap deprecated or revoked upstream labels to newer ATT&CK IDs. Exclude affected records instead.

Do not edit the upstream TSV files. Preserve the original source revision, upstream split, row index, and complete original label list for every future retained benchmark case.

Keep the external repository in `data/external_inspection/` and ignored by Git during feasibility and development. Do not commit copied threat-report narrative text to the public repository until redistribution, attribution, and provenance treatment is explicitly resolved.

The committed evaluation inputs and reports are review artefacts derived from this source. They are not the retrieval corpus and are not presented as a frozen held-out final benchmark.

### Alternatives considered

- Use only a manually authored internal benchmark.
- Use raw Expert test data without filtering for label compatibility.
- Downgrade the application corpus to an older ATT&CK release to preserve every upstream label.
- Automatically remap revoked or deprecated upstream labels to newer ATT&CK IDs.
- Use the larger CTI-HAL dataset as the primary external benchmark.
- Commit a curated copy of threat-report text immediately.

### Consequences

- The project gains a realistic, externally labelled source for later end-to-end evaluation.
- Development choices can be made using the development split while preserving a held-out test split for final reporting.
- The current active ATT&CK corpus can remain in use without being downgraded to preserve a small number of outdated labels.
- Final external evaluation begins with at most 153 compatibility-clean test records before text-length, label-count, and narrative-quality curation.
- Multi-label, unordered upstream labels require set-based retrieval metrics and careful answer-review design.
- The project must not invent a primary label for an upstream multi-label narrative without separate human review and explicit metadata.
- External benchmark provenance and redistribution constraints may require storing only selection metadata, source references, row indices, and aggregate evaluation results in the public repository.
- Final benchmark rules must be frozen on `expert_dev.tsv` before they are applied to the held-out test split.
- Reviewers can inspect completed evaluation reports without rerunning API-bound jobs.

---

## DEC-015 — Default retrieval method for v1

**Status:** Superseded by DEC-018  
**Date:** 2026-07-31

### Context

Text, vector, and hybrid retrieval baselines have now been implemented over the active Enterprise ATT&CK technique corpus and evaluated against the same Expert-derived incident-narrative benchmark.

On the current 226-case retrieval benchmark, text-only retrieval is a very weak lexical baseline. Vector retrieval clearly outperforms text on all core ranking metrics. Hybrid retrieval using Reciprocal Rank Fusion is slightly stronger than vector-only on some ranking metrics (e.g. Recall@1, Recall@3, Hit@3, MRR) while Recall@5 and Recall@10 are identical.

Hybrid offers a small uplift over vector at the current corpus size and query mix, but it adds additional implementation and compute complexity.

### Decision

Use **vector retrieval** as the default ATT&CK candidate-retrieval method for version 1.

Retain **text retrieval** and **hybrid retrieval (vector + text, RRF)** as implemented, benchmarked baselines and diagnostic tools. Hybrid can be reconsidered and promoted to the default retrieval method later if improvements to the lexical channel or corpus characteristics increase its advantage enough to justify the extra complexity and resource cost.

### Alternatives considered

- Use hybrid retrieval as the v1 default because it is numerically slightly stronger than vector-only on the current benchmark.
- Use text-only retrieval as the default.
- Delay choosing a default until answer-generation evaluation is complete.

### Consequences

- The default v1 retrieval method is simple, relatively cheap to run, and clearly stronger than text-only on the current benchmark.
- Hybrid remains available for diagnostics and future promotion; it is not removed despite its current marginal advantage.
- The documentation must explain that hybrid is slightly stronger on the measured retrieval metrics, but that vector is chosen as the default for v1 because the uplift is small and does not yet justify the added complexity.
- Future retrieval work can focus on improving the lexical channel and fusion configuration; if those changes materially increase hybrid's advantage, the default can be updated in a new decision record.
- This decision is superseded by DEC-018 for the default v1 retrieval configuration, which adds local cross-encoder reranking to vector retrieval.

---

## DEC-016 — Retrieval-module refactor and shared helpers

**Status:** Accepted  
**Date:** 2026-07-31

### Context

The initial retrieval implementation evolved incrementally and combined multiple concerns (SQL, scoring, metrics, and fusion) inside a small number of files. As retrieval benchmarks and answer-generation support were added, it became harder to reason about and reuse retrieval logic across evaluation scripts.

Repeated embedding-model initialisation in different scripts also added unnecessary overhead and noisy logging.

### Decision

Refactor retrieval and evaluation code into clearer modules with shared helpers:

- Keep text, vector, and hybrid retrieval implementations under `src/retrieval/`:
  - `text.py` — lexical retrieval over the `techniques` table.
  - `vector.py` — dense retrieval using pgvector.
  - `hybrid.py` — Reciprocal Rank Fusion over text and vector candidate lists.
- Define shared dataclasses (or equivalent types) for retrieved candidates, so all retrieval methods return consistent structures.
- Add a shared embedding-model helper (for example in `src/retrieval/embedding_model.py`) that:
  - loads `sentence-transformers/all-MiniLM-L6-v2` (or another configured model),
  - can be reused across multiple benchmark scripts within a process,
  - and hides model-name details behind a small function interface.
- Centralise retrieval metric computation in `src/evaluation/metrics.py`, used by:
  - text, vector, and hybrid retrieval benchmark scripts,
  - answer-generation evaluation where retrieval metrics are needed.

### Alternatives considered

- Keep all retrieval code in a single module.
- Initialise the embedding model directly in each benchmark script.
- Implement retrieval logic inline in each evaluation script without shared helpers.
- Move immediately to a separate microservice for retrieval instead of refactoring modules.

### Consequences

- Retrieval logic is easier to understand and reuse across benchmarks and future components (such as an interface).
- Embedding-model initialisation is centralised, reducing duplication and making it easier to change the default model later.
- Benchmark scripts become thinner, focusing on orchestration and I/O rather than retrieval implementation details.
- The new structure adds a small amount of upfront complexity but simplifies future changes to retrieval and metrics.

---

## DEC-017 — Answer-generation pipeline and output contract

**Status:** Accepted baseline; updated 2026-08-16  
**Date:** 2026-07-31

### Context

Retrieval benchmarks established that vector retrieval was a strong baseline and that local cross-encoder reranking improved the ordering of retrieved ATT&CK candidates.

The project also needs a candidate-answer layer that:

- is grounded in retrieved ATT&CK records;
- clearly expresses uncertainty;
- produces structured outputs suitable for human review and scoring;
- allows retrieval failures to be distinguished from answer-generation failures;
- records enough metadata to reproduce model comparisons.

### Decision

Use a structured answer-generation pipeline with a stable high-level output contract.

The current v1 answer-generation flow is:

```text
Incident narrative
  → Vector retrieval of top 20 ATT&CK candidates
  → Local cross-encoder reranking
  → Top 5 reranked ATT&CK records for answer context
  → Structured answer generation
  → Analyst-facing answer and retrieved-evidence display
```

#### Retrieval

The current v1 answer-generation and analyst-facing retrieval configuration uses:

- `sentence-transformers/all-MiniLM-L6-v2` for query embeddings;
- PostgreSQL with pgvector cosine-similarity retrieval;
- a first-stage candidate pool of 20 ATT&CK records;
- `cross-encoder/ms-marco-MiniLM-L-6-v2` for local CPU reranking;
- the top 5 reranked records as the initial answer-generation context.

The vector-only answer-generation implementation remains available as a historical and diagnostic baseline, but it is not the current v1 runtime configuration.

Record the retrieved ATT&CK IDs and retrieval metadata needed for grounding and evaluation.

#### Generation

Use an LLM client configured through the environment to produce a structured answer containing:

- `primary_attack_id` — the main candidate technique ID selected from the retrieved list.
- `alternative_attack_ids` — a small set of additional candidate technique IDs from the retrieved list.
- `supporting_attack_ids` — IDs for which evidence is explicitly discussed.
- `answer_summary` — a concise, analyst-readable explanation of the candidates and their rationale.
- `retrieval_grounding_note` — a short explanation of how retrieved ATT&CK descriptions support the mapping.
- `uncertainty_note` — explicit mention of ambiguity, missing expected labels, or incomplete evidence.
- `review_required` — a boolean flag indicating whether a human should review the answer before use.
- `prompt_version` and `llm_model` metadata.
- Available latency and token-usage metadata.

The selected v1 default model is recorded separately in DEC-021. The answer-generation comparison evaluates both:

- `gemini-3.1-flash-lite`;
- `gemini-3.5-flash-lite`.

#### Output

The original vector-only baseline outputs are stored in:

```text
data/evaluation_reports/expert_answer_generation_v1.jsonl
data/evaluation_reports/expert_answer_generation_v1.csv
```

The current reranked v1 model-comparison output is stored in:

```text
data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv
```

Use structured outputs as the basis for:

- pairwise LLM-as-judge comparison;
- manual review of judge disagreements;
- rubric-based answer evaluation;
- failure analysis;
- analyst-facing evidence display.

Treat the output contract as a stable high-level baseline. Prompt wording, model choice, and non-essential metadata may evolve through later decision records.

### Alternatives considered

- Generate free-form narrative answers without a structured schema.
- Embed ATT&CK IDs directly in natural language without separate fields.
- Combine retrieval and generation into a single monolithic script.
- Continue using vector-only retrieval for the deployed answer-generation path.
- Delay answer-generation implementation until retrieval work and external benchmark curation were fully complete.

### Consequences

- The answer layer remains explicitly grounded in retrieved ATT&CK records.
- The structured contract allows systematic human review and scoring across candidate validity, retrieval grounding, narrative grounding, uncertainty handling, and analyst usefulness.
- The pipeline enables separation of retrieval failures from generation failures.
- Reranked context is now used in the current answer-generation comparison and analyst-facing Query workflow.
- The original vector-only outputs remain useful for historical comparison but must not be described as the current deployed v1 answer-generation configuration.
- The answer-generation model is selected separately from the retrieval configuration so the two decisions can be evaluated independently.
- Future changes to retrieval depth, answer schema, prompt contract, or model family require a new comparison and may require a new decision record.

---

## DEC-018 — Default retrieval configuration with reranking

**Status:** Accepted; updated 2026-08-16  
**Date:** 2026-08-12  
**Supersedes:** DEC-015 for the default v1 retrieval configuration

### Context

DEC-015 selected vector retrieval as the v1 default after comparing text, vector, and hybrid retrieval. At that time, hybrid retrieval produced only a marginal improvement over vector retrieval and did not justify the additional complexity.

A local second-stage document-reranking experiment was implemented and evaluated using:

- first-stage semantic retrieval with `sentence-transformers/all-MiniLM-L6-v2`;
- PostgreSQL with pgvector cosine-distance search over active Enterprise ATT&CK technique and sub-technique records;
- retrieval of the top 20 vector candidates;
- a local CPU cross-encoder reranker, `cross-encoder/ms-marco-MiniLM-L-6-v2`;
- existing structured ATT&CK `embedding_text` as the reranker document text;
- top 10 reranked records for retrieval benchmark compatibility;
- top 5 reranked records for the current analyst-facing Query workflow and answer-generation comparison.

The vector-only and vector-plus-reranking configurations were evaluated against the same 226-case Expert-derived retrieval set.

### Results

| Metric | Vector | Vector + cross-encoder reranking | Absolute change |
|--------|--------|----------------------------------|-----------------|
| Recall@1 | 0.1098 | 0.1462 | +0.0364 |
| Recall@3 | 0.1940 | 0.2526 | +0.0586 |
| Recall@5 | 0.2710 | 0.3104 | +0.0394 |
| Recall@10 | 0.3551 | 0.3866 | +0.0315 |
| Hit@3 | 0.3540 | 0.4159 | +0.0619 |
| Hit@10 | 0.5619 | 0.5973 | +0.0354 |
| MRR | 0.3134 | 0.3578 | +0.0444 |

The reranked configuration improved every reported retrieval metric.

The final synced local CPU reranking benchmark measured:

- Median total retrieval time: 1,254.79 ms.
- P95 total retrieval time: 1,451.74 ms.
- Median reranking time: 1,223.29 ms.
- P95 reranking time: 1,414.23 ms.

A second benchmark run after `uv lock` and `uv sync` reproduced the same retrieval-quality metrics, confirming that the selected configuration remained stable under the final locked dependency state.

### Decision

Use **vector retrieval plus local cross-encoder document reranking** as the selected default retrieval configuration for version 1.

The default v1 retrieval flow is:

```text
Incident narrative
  → Query embedding with all-MiniLM-L6-v2
  → pgvector cosine-similarity retrieval of top 20 ATT&CK records
  → Local CPU cross-encoder reranking with cross-encoder/ms-marco-MiniLM-L-6-v2
  → Ranked ATT&CK candidates
```

Use the following depths:

- Retrieval evaluation: retrieve 20 vector candidates and return 10 reranked candidates, preserving comparison with Recall@10 and Hit@10.
- Analyst-facing Query workflow: retrieve 20 vector candidates and return the top 5 reranked records.
- Current reranked answer-generation comparison: retrieve 20 vector candidates and use the top 5 reranked records as answer-generation context.

Retain the following retrieval methods as implemented baselines and diagnostic modes:

- Text-only retrieval.
- Vector-only retrieval.
- Hybrid text-plus-vector retrieval using Reciprocal Rank Fusion.
- Vector retrieval plus local cross-encoder reranking.
- Query rewrite plus vector retrieval and reranking.

Keep vector-only retrieval available as a fallback option for future interface or runtime handling if the reranker cannot load. The evaluation benchmark must fail rather than silently fall back to vector-only retrieval, so benchmark outputs cannot be misrepresented as reranked results.

### Alternatives considered

- Retain vector-only retrieval as the v1 default because it has lower latency and less implementation complexity.
- Use hybrid text-plus-vector retrieval as the default because it was marginally stronger than vector-only retrieval in the earlier comparison.
- Use a larger local reranker model.
- Use a hosted reranking API.
- Use an ONNX-optimised reranker implementation before selecting a default.
- Defer reranking until after answer-generation evaluation was complete.

### Consequences

- The selected default improves all reported retrieval metrics over vector-only retrieval on the current Expert-derived evaluation set.
- The strongest observed improvement is in ordering quality: MRR increased from 0.3134 to 0.3578, while Hit@3 increased from 0.3540 to 0.4159.
- The selected reranked configuration is now integrated into the analyst-facing Query workflow and the reranked answer-generation comparison.
- In the final synced local CPU benchmark run, reranking produced 1,254.79 ms median total retrieval latency and 1,451.74 ms p95 total latency.
- The Streamlit interface should provide visible progress while retrieval and reranking are running.
- The interface exposes retrieved ATT&CK evidence and the selected retrieval path so analysts can inspect the basis of the ranking.
- The current result is based on the existing 226-case Expert-derived evaluation set, which includes development- and test-derived records and is not yet a frozen held-out benchmark.
- This decision does not replace DEC-014. Final external benchmark claims must still use curation rules frozen on the Expert development split before evaluation on the held-out Expert test split.
- ONNX optimisation is deferred. It may be evaluated later as a deployment or performance optimisation, but it is not required to establish the current result.
- Future changes to candidate-pool depth, returned top-k, cross-encoder model, CPU/GPU execution, ONNX runtime, or fallback behaviour require a new benchmark comparison and a new decision record if they alter the selected default configuration.

---

## DEC-019 — User query rewriting evaluation and decision

**Status:** Accepted  
**Date:** 2026-08-13

### Context

Following DEC-018, which established vector retrieval plus local cross-encoder reranking as the default v1 configuration, an additional retrieval enhancement was evaluated: LLM-based user query rewriting.

The hypothesis was that rewriting verbose incident narratives into concise, ATT&CK-oriented retrieval queries might improve semantic matching by:

- Removing report-writing filler and campaign background.
- Focusing on behaviours, tools, execution methods, and IOCs.
- Producing queries that better align with ATT&CK technique description embeddings.

A query-rewriting pipeline was implemented and evaluated:

- Query rewriting with Gemini 3.1 Flash Lite (`gemini-3.1-flash-lite`) via OpenAI-compatible API.
- Prompt instructions directing the model to preserve only behaviours, tools, execution methods, file artefacts, credentials, targets, operating-system details, and network actions explicitly stated in the narrative.
- Rate limiting at 15 requests/minute to respect the Gemini free tier.
- First-stage semantic retrieval with `sentence-transformers/all-MiniLM-L6-v2` and pgvector.
- Local CPU cross-encoder reranking with `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- Retrieval of 20 vector candidates, reranking, and return of top 10 candidates.

The `rewritten_vector_reranked` configuration was evaluated against the same 226-case Expert-derived retrieval set used for DEC-018.

Results were:

| Metric | Vector + rerank (DEC-018) | Query rewrite + vector + rerank | Absolute change |
|--------|---------------------------|---------------------------------|-----------------|
| Recall@1 | 0.1462 | 0.1495 | +0.0033 |
| Recall@3 | 0.2526 | 0.2966 | +0.0440 |
| Recall@5 | 0.3104 | 0.3507 | +0.0403 |
| Recall@10 | 0.3866 | 0.4581 | +0.0715 |
| Hit@3 | 0.4159 | 0.4690 | +0.0531 |
| Hit@10 | 0.5973 | 0.6726 | +0.0753 |
| MRR | 0.3578 | 0.3940 | +0.0362 |

Query rewriting improved all reported retrieval metrics over the DEC-018 baseline.

The benchmark measured the following latency characteristics:

- Median total retrieval time: 4,362.28 ms.
- P95 total retrieval time: 12,202.92 ms.
- Median query-rewrite time: 3,183.88 ms.
- P95 query-rewrite time: 10,954.94 ms.

Query rewriting is therefore the dominant source of retrieval latency in the evaluated pipeline, adding approximately 3.1 seconds median latency and up to 11 seconds at P95 compared to the DEC-018 baseline.

### Decision

**Do not adopt user query rewriting as the default retrieval configuration for version 1.**

Retain **vector retrieval plus local cross-encoder reranking** (DEC-018) as the default v1 configuration.

Document query rewriting as an evaluated retrieval enhancement that improved metrics but introduced unacceptable latency for the initial analyst-assist workflow. Keep the implementation available for future re-evaluation under the following conditions:

- Access to lower-latency LLM endpoints (e.g., paid-tier Gemini with higher RPM limits, or self-hosted models).
- Prompt-engineering improvements that reduce rewrite latency while preserving quality.
- Embedding models fine-tuned for ATT&CK-specific query-document matching that may reduce reliance on query rewriting.
- Hybrid approaches that combine raw narrative retrieval with rewritten-query retrieval.

The query-rewriting implementation remains in the codebase:

- `src/retrieval/query_rewriter.py` — LLM-based query rewriting with caching.
- `src/retrieval/rewritten_reranked_vector.py` — End-to-end rewritten query retrieval with reranking.
- `src/evaluation/run_expert_query_rewrite_retrieval_benchmark.py` — Benchmark script for evaluation.

Rate limiting is implemented in `src/llm_client.py` with an optional `RateLimiter` class that can be enabled for batch tasks and disabled for interactive use.

### Alternatives considered

- Adopt query rewriting as the default despite the latency penalty, prioritising retrieval quality over response time.
- Use query rewriting only for offline analysis or batch evaluation, not for interactive use.
- Implement hybrid retrieval combining candidates from both raw narratives and rewritten queries.
- Defer query-rewriting evaluation until after the v1 interface is deployed.
- Use a different LLM (e.g., Gemini 2.5 Flash, Gemini 2.5 Pro) with different latency and instruction-following characteristics.

### Consequences

- The default v1 retrieval configuration remains vector plus reranking with median latency ~1.3 seconds, acceptable for interactive analyst-assist workflows.
- Query rewriting is documented as an evaluated best-practice component, satisfying the "user query rewriting" best-practice criterion (evaluated, even if not deployed).
- The implementation is available for future optimisation or re-evaluation if latency constraints are relaxed or LLM endpoints improve.
- The project retains all three best-practice points: hybrid search (evaluated), document reranking (deployed), and user query rewriting (evaluated).
- Future work can explore prompt engineering (few-shot examples, detail preservation), alternative embedding models, or hybrid retrieval strategies to close the gap between retrieval quality and latency.
- The decision preserves the option to revisit query rewriting in a future decision record if conditions change (e.g., paid-tier LLM access, improved prompts, or different latency requirements).

---

## DEC-020 — Pairwise LLM-as-judge evaluation for answer generation

**Status:** Accepted  
**Date:** 2026-08-16  
**Supersedes:** The answer-model comparison and manual-review plan previously described in the earlier DEC-020 draft.

### Context

DEC-017 established a structured answer-generation contract for mapping incident narratives to Enterprise MITRE ATT&CK techniques.

DEC-018 selected vector retrieval plus local cross-encoder reranking as the deployed v1 retrieval configuration. The current answer-generation comparison therefore needed to use the same retrieval path rather than the earlier vector-only baseline.

The project needed a scalable, repeatable method to compare:

- `gemini-3.1-flash-lite`;
- `gemini-3.5-flash-lite`.

The evaluation needed to assess answer quality beyond retrieval accuracy, including:

- technique relevance;
- grounding in the incident narrative;
- use of retrieved ATT&CK evidence;
- uncertainty handling;
- analyst usefulness;
- conciseness.

### Decision

Use reciprocal pairwise LLM-as-judge evaluation on the 226-case Expert-derived dataset under the selected v1 retrieval pipeline:

```text
Incident narrative
  → Vector retrieval: top 20 candidates
  → Local cross-encoder reranking
  → Top 5 reranked ATT&CK records
  → Structured answer generation by each candidate model
  → Pairwise LLM judging
```

For each case, generate one structured answer using each candidate model.

Store the reranked answer-generation comparison in:

```text
data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv
```

The comparison records, where available:

- `eval_id`;
- model identifier;
- incident narrative;
- expected ATT&CK IDs;
- retrieved ATT&CK IDs;
- retrieval configuration;
- retrieval latency metadata;
- primary, alternative, and supporting ATT&CK IDs;
- answer summary;
- retrieval-grounding note;
- uncertainty note;
- review-required flag;
- token metadata;
- generation latency metadata.

### Pairwise judge protocol

For each `eval_id`:

- Randomly assign the two generated answers to Answer A and Answer B.
- Ask a judge to compare technique relevance, narrative grounding, uncertainty framing, analyst actionability, and conciseness.
- Require JSON containing `reasoning`, `winner`, and `confidence`.
- Map the selected A/B answer back to the underlying model identifier.
- Run the protocol twice:
  - `gemini-3.1-flash-lite` as judge;
  - `gemini-3.5-flash-lite` as judge.
- Use checkpointing and retry/backoff so interrupted or rate-limited runs can resume.

Store the final judge outputs in:

```text
data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv
data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv
```

Persist the aggregated agreement and disagreement artefacts in:

```text
data/evaluation_reports/reranked/judge_agreement_summary.csv
data/evaluation_reports/reranked/judge_disagreements.csv
```

### Results

The reciprocal pairwise evaluation completed for all 226 cases.

| Measure | Result |
|---------|--------|
| Cases evaluated | 226 |
| Cross-judge agreement | 171 / 226 |
| Cross-judge agreement rate | 75.66% |
| Cross-judge disagreements | 55 / 226 |
| Cross-judge disagreement rate | 24.34% |
| 3.1-as-judge preferred 3.1 output | 153 / 226 (67.70%) |
| 3.1-as-judge preferred 3.5 output | 73 / 226 (32.30%) |
| 3.5-as-judge preferred 3.1 output | 142 / 226 (62.83%) |
| 3.5-as-judge preferred 3.5 output | 84 / 226 (37.17%) |

### Human adjudication

Automated judge disagreement was treated as evaluator uncertainty rather than as a final model-selection result.

All 55 reranked disagreement cases were manually reviewed blind to model identity using `app/evaluation.py` through the Streamlit Evaluation Review workflow.

The reviewer saw:

- the incident narrative;
- expected ATT&CK labels and definitions;
- retrieved ATT&CK context;
- both structured answers labelled only as Answer A and Answer B;
- optional failure-mode tags;
- optional review notes.

The reviewer selected one of:

- Answer A;
- Answer B;
- Tie.

The selected answer was mapped back to its model identifier after submission.

Model identities and both judge rationales were revealed only after the manual decision was saved.

Completed results are stored in:

```text
data/evaluation_reports/reranked/manual_review_results.csv
```

DEC-021 records the final human-adjudicated model-selection decision.

### Alternatives considered

- Use one LLM judge only.
- Use human evaluation for all 226 cases.
- Evaluate retrieval only and omit answer-level evaluation.
- Use independent rubric scoring instead of pairwise comparison.
- Select a model using automated judge preferences without human adjudication.
- Use the earlier vector-only answer-generation comparison as the authoritative v1 evidence.

### Consequences

- The project has a reproducible answer-level evaluation workflow aligned with the deployed v1 retrieval architecture.
- Reciprocal judging exposes judge disagreement and reduces reliance on a single evaluator.
- Full manual adjudication of disagreement cases provides a human evidence layer for model selection.
- The final answer-generation model choice is documented separately in DEC-021.
- The earlier vector-only evaluation artefacts are retained for diagnostic comparison but are not used to choose the deployed v1 model.
- The Streamlit dashboard displays both judge preference distributions and cross-judge agreement.
- The Evaluation Review tab provides an auditable interface for blinded comparison, failure-mode tagging, and review notes.
- The 226-case evaluation remains an internal implementation-comparison set rather than a frozen held-out external benchmark.

---

## DEC-021 — Default answer-generation model selection

**Status:** Accepted  
**Date:** 2026-08-16  
**Supersedes:** The deferred model-selection state described in the earlier DEC-020 draft.

### Context

DEC-020 compared `gemini-3.1-flash-lite` and `gemini-3.5-flash-lite` on 226 Expert-derived cases using reciprocal pairwise LLM judging under the selected v1 retrieval pipeline:

```text
vector retrieval
  → local cross-encoder reranking
  → top 5 answer-generation context
```

The two judges agreed on 171 of 226 cases (75.66%) and disagreed on 55 cases (24.34%).

Because disagreement indicates evaluator uncertainty, all 55 reranked disagreement cases were manually reviewed blind to model identity.

The review assessed:

- technique relevance and correctness;
- grounding in the incident narrative;
- appropriate use of retrieved ATT&CK context;
- uncertainty handling and `review_required` behaviour;
- analyst usefulness and clarity.

### Manual-review results

| Measure | Result |
|---------|--------|
| Cases reviewed | 55 |
| Gemini 3.1 wins | 21 (38.2% of all cases) |
| Gemini 3.5 wins | 16 (29.1% of all cases) |
| Ties | 18 (32.7% of all cases) |
| Decisive comparisons | 37 |
| 3.1 share of decisive wins | 21 / 37 (56.8%) |
| 3.5 share of decisive wins | 16 / 37 (43.2%) |
| 3.1-as-judge agreement with human | 18 / 37 (48.6%) |
| 3.5-as-judge agreement with human | 19 / 37 (51.4%) |

The most frequent manually tagged failure modes were:

- inadequate uncertainty handling: 21 cases;
- weak grounding in the narrative: 20 cases;
- incorrect technique mapping: 14 cases;
- unsupported or hallucinated technique: 13 cases.

The review also identified shared pipeline and dataset-quality issues, including incomplete retrieved context and expected labels that did not always match the narrative.

These shared issues are retained as regression and data-quality candidates. They do not negate the relative model-selection comparison.

### Decision

Select `gemini-3.1-flash-lite` as the default v1 answer-generation model.

### Rationale

Gemini 3.1 Flash-Lite won 21 of 37 decisive blind human comparisons (56.8%), exceeding the predefined threshold of at least 55% of decisive wins and a minimum three-case margin.

It led Gemini 3.5 Flash-Lite by five decisive cases.

The 32.7% tie rate indicates substantial practical overlap between the models. Therefore, this is a measured v1 choice rather than a claim that 3.1 is universally superior.

The selected model should remain subject to regression evaluation as prompts, retrieval settings, corpus versions, or deployment conditions change.

A separate vector-only baseline review covered 57 judge-disagreement cases and also favoured 3.1:

- 34 wins for 3.1;
- 14 wins for 3.5;
- 9 ties.

This result is supporting diagnostic evidence only. It was not combined with the reranked result because the vector-only pipeline does not match the deployed v1 architecture.

### Consequences

- Set the default `MODEL_ID` to `gemini-3.1-flash-lite` in `.env.example` and runtime configuration.
- Display the configured model in the Streamlit system information.
- Use `gemini-3.1-flash-lite` in the current analyst-facing Query workflow unless overridden intentionally through environment configuration.
- Retain `gemini-3.5-flash-lite` as an evaluated alternative.
- Retain vector-only and reranked evaluation artefacts as reproducible baselines.
- Retain the manual-review results and failure-mode tags for regression and data-quality analysis.
- Add manually identified shared failures, empty-context cases, and misleading-label cases to a future regression or gold-standard dataset.
- Re-run answer-generation and manual-review evaluation before changing the default retrieval configuration, generation prompt, answer schema, or default answer model.
- Treat feedback persisted by the Streamlit application as a future evaluation signal, not as a replacement for controlled benchmark or human-review evidence.

---

## DEC-022 — Docker Compose execution and automated ingestion

**Status:** Accepted  
**Date:** 2026-08-16

### Context

The rubric requires a reproducible containerised application and an automated ingestion workflow. The project already had separate Python modules for downloading, extracting, database initialisation, loading, and embedding generation.

A first Compose attempt exposed two implementation issues: the image needed to use the locked `uv` environment, and the ingestion service needed to invoke `uv run python` rather than plain system Python.

### Decision

Use Docker Compose as the canonical local execution path for the v1 stack:

- `postgres` runs PostgreSQL with pgvector.
- `streamlit` runs the analyst-facing application.
- `ingest` is an on-demand Compose profile that executes the complete pipeline.

The ingestion profile runs:

```text
Download ATT&CK source
  → Extract active techniques
  → Initialise PostgreSQL schema
  → Load and upsert processed records
  → Generate embeddings
```

The ingestion service uses the locked project environment through `uv run python`, fails fast on errors, mounts project data for generated corpus/provenance files, and persists the Hugging Face model cache in a named volume.

Canonical commands are:

```bash
make up
make ingest
make down
```

### Validation

A destructive clean-state validation completed successfully:

```bash
docker compose down -v
make up
make ingest
```

The run produced 697 active technique/sub-technique records. Database verification returned:

```text
total_techniques | embedded_techniques | missing_embeddings
-----------------+---------------------+------------------
697              | 697                 | 0
```

The application container also queried PostgreSQL successfully and returned:

```text
Technique count: 697
```

### Alternatives considered

- Run PostgreSQL in Compose but execute ingestion only on the host.
- Add Prefect or another workflow orchestrator solely for rubric presentation.
- Combine all ingestion logic into one monolithic script.
- Use plain system Python in the ingestion container.

### Consequences

- A marker can run the application and complete ingestion through Docker Compose without host Python dependencies.
- The existing modular Python scripts are sufficient as the automated ingestion implementation; no additional orchestrator is required for v1.
- The first clean run requires network access for ATT&CK and Hugging Face downloads and may take several minutes.
- The named model-cache volume reduces repeat-run time.
- The current Compose path is validated locally but remains intended for reproducible local demonstration rather than production deployment.

---

## DEC-023 — Reviewable evaluation artefacts

**Status:** Accepted  
**Date:** 2026-08-16

### Context

Evaluation runs include API-bound answer generation and LLM-as-judge calls that may require credentials, quota, and substantial time. A marker should be able to inspect the evidence supporting the reported results without rerunning those jobs.

### Decision

Commit the current evaluation inputs and completed evaluation reports required to inspect the v1 evidence and render the dashboard. Keep raw source downloads, the external inspection clone, secrets, caches, Docker volumes, and runtime feedback ignored.

The committed reports must be accompanied by:

- upstream repository and configuration;
- exact source revision;
- licence declaration and attribution;
- clear statement that the 226-case set combines development- and test-derived records;
- clear statement that the results are implementation-comparison evidence, not final held-out performance.

The current external evaluation source is:

```text
Repository: https://github.com/tumeteor/mitre-ttp-mapping
Configuration: Expert
Revision: a16856a6438ca2b7888c5cadfba6d7c854f04a55
Licence declared by upstream: CC BY 4.0
```

### Consequences

- Markers can inspect retrieval, answer-generation, judge, agreement, and manual-review evidence without API credentials or quota.
- The dashboard can render completed offline evaluation charts immediately after the repository is cloned.
- Runtime feedback remains an honest empty state until a real user submits feedback.
- Any future change to the source revision, corpus, evaluation set, or reported metrics must update the relevant evidence and documentation together.