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
| DEC-004 | Public repository and attribution                | Accepted          | 2026-07-30 |
| DEC-005 | Repository structure                             | Accepted          | 2026-07-29 |
| DEC-006 | Execution convention                             | Accepted          | 2026-07-29 |
| DEC-007 | Source provenance and versioning                 | Accepted          | 2026-07-29 |
| DEC-008 | Retrieval unit and chunking                      | Accepted          | 2026-07-29 |
| DEC-009 | Processed corpus schema and snapshot policy      | Accepted          | 2026-07-30 |
| DEC-010 | Database and embedding pipeline                  | Accepted          | 2026-07-29 |
| DEC-011 | Embedding baseline                               | Accepted baseline | 2026-07-30 |
| DEC-012 | Vector index strategy                            | Accepted          | 2026-07-30 |
| DEC-013 | Documentation strategy                           | Accepted          | 2026-07-30 |
| DEC-014 | External evaluation benchmark strategy           | Accepted          | 2026-07-30 |
| DEC-015 | Default retrieval method for v1                  | Accepted          | 2026-07-31 |
| DEC-016 | Retrieval-module refactor and shared helpers     | Accepted          | 2026-07-31 |
| DEC-017 | Answer-generation pipeline and output contract   | Accepted baseline | 2026-07-31 |

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
- The README must clearly explain the project’s corpus and its relationship to MITRE ATT&CK.
- Attribution and terminology must be applied consistently throughout the repository.

---

## DEC-004 — Public repository and attribution

**Status:** Accepted  
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
- Lightweight evaluation reports that do not reproduce upstream narrative text, including label-compatibility reports.
- Evaluation code, frozen benchmark-selection rules, upstream source references, and upstream row identifiers.

The repository will not commit:

- Raw upstream ATT&CK STIX downloads.
- External datasets downloaded for feasibility inspection.
- Full copied third-party threat-report passages from an external benchmark unless their redistribution and attribution position is explicitly resolved.

Raw ATT&CK files are regenerated through the documented download stage and verified using recorded source references and checksums. External feasibility downloads remain under `data/external_inspection/` and are ignored by Git.

### Alternatives considered

- Private exploratory notebook-style build.
- Manual local setup with undocumented steps.
- Commit all raw and processed source artefacts.
- Ignore all generated data, including the processed corpus.
- Commit an external benchmark before resolving its provenance and redistribution position.
- Mixed-source corpus with uncertain reuse or attribution requirements.
- Commit environment-specific configuration for convenience.

### Consequences

- The project is safer to share publicly and easier for reviewers to reproduce.
- Reviewers can inspect the derived ATT&CK retrieval corpus without first downloading the upstream STIX bundle.
- The processed corpus and manifest must be reviewed before intentional updates are committed.
- Raw source artefacts remain reproducible without unnecessarily duplicating upstream files.
- External evaluation can be documented and reproduced from source revision and row IDs without prematurely republishing threat-report text.
- Reproducibility, attribution, and provenance add maintenance and documentation work.

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

Use `__init__.py` files in package directories.

Place external benchmark inspection, curation, compatibility validation, retrieval evaluation, and answer evaluation modules in `src/evaluation/`.

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

**Status:** Accepted  
**Date:** 2026-07-29

### Context

The grouped `src/` layout needs a consistent way to run modules and resolve imports reliably.

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

### Alternatives considered

- Run every file directly using paths such as `python src/database/db_init.py`.
- Add `src/` manually to `PYTHONPATH`.
- Install the project as a package before every execution.

### Consequences

- Imports remain predictable across functional subdirectories.
- The runbook can use a consistent `uv run python` command style.
- Commands must be run from the repository root.
- Self-contained validation scripts can remain simple while package-dependent pipeline stages use module execution.

---

## DEC-007 — Source provenance and versioning

**Status:** Accepted  
**Date:** 2026-07-29

### Context

The ATT&CK repository’s default reference can change over time, while evaluation and portfolio evidence require a reproducible source baseline.

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

The project needs to be presentation-ready while retaining an auditable record of design choices, source processing, evaluation evidence, and reproducible commands.

Documentation must be split clearly enough that the README and runbook do not become long, overlapping project specifications.

### Decision

Separate public overview, decisions, working notes, dataset evidence, evaluation evidence, and operational instructions across dedicated files:

- `README.md` — concise public project overview, problem, scope, current status, architecture summary, quick start, limitations, and attribution.
- `docs/project-log.md` — chronological progress, discoveries, temporary issues, and immediate next steps.
- `docs/decisions.md` — stable architectural and design decisions with alternatives and consequences.
- `docs/dataset-notes.md` — source provenance, corpus scope, schema, extraction rules, data-quality notes, and committed-versus-ignored artefact policy.
- `docs/evaluation-notes.md` — benchmark design, retrieval configurations, metrics, findings, and failure analysis.
- `docs/runbook.md` — concise reproducible setup, pipeline commands, verification checks, reset instructions, and common troubleshooting.

Keep detailed rationale in the relevant evidence or decision document rather than duplicating it in the README or runbook.

### Alternatives considered

- Put all documentation in the README.
- Maintain only one running project log.
- Use the runbook as a complete project specification.
- Keep implementation notes outside the repository.
- Use notebook comments as the primary record.

### Consequences

- The README remains concise and useful to portfolio reviewers.
- The runbook stays operational and can be used without reading the entire project history.
- Dataset rules and evaluation evidence have clear homes outside the runbook.
- Multiple files require disciplined maintenance when decisions or implementation status change.
- The repository provides a clearer and more credible evidence trail for technical reviewers.

---

## DEC-014 — External evaluation benchmark strategy

**Status:** Accepted  
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

---

## DEC-015 — Default retrieval method for v1

**Status:** Accepted  
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
- Future retrieval work can focus on improving the lexical channel and fusion configuration; if those changes materially increase hybrid’s advantage, the default can be updated in a new decision record.

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

**Status:** Accepted baseline  
**Date:** 2026-07-31

### Context

Retrieval benchmarks established that vector retrieval is a strong default candidate backend, with hybrid providing a marginal uplift for some metrics. To support the project’s goal of analyst-facing outputs, the system also needs a candidate-answer layer that:

- is grounded in retrieved ATT&CK records,
- clearly expresses uncertainty,
- and produces structured outputs suitable for human review and scoring.

At this stage, answer-generation design and evaluation are still evolving, so the initial pipeline must be treated as a baseline rather than a final contract.

### Decision

Introduce a structured answer-generation pipeline with a clear output contract:

- Retrieval:
  - Use vector retrieval (v1 default) to fetch top-k ATT&CK technique candidates for each incident narrative.
  - Record the retrieved ATT&CK IDs and any metadata needed for grounding.
- Generation:
  - Use an LLM client (configured via environment) to generate a structured answer that includes:
    - `primary_attack_id` — the main candidate technique ID selected from the retrieved list.
    - `alternative_attack_ids` — a small set of additional candidate technique IDs from the retrieved list.
    - `supporting_attack_ids` — IDs for which evidence is explicitly discussed.
    - `answer_summary` — a concise, analyst-readable explanation of the candidates and their rationale.
    - `retrieval_grounding_note` — a short explanation of how retrieved ATT&CK descriptions support the mapping.
    - `uncertainty_note` — explicit mention of ambiguity, missing expected labels, or incomplete evidence.
    - `review_required` — a boolean flag indicating whether a human should review the answer before using it.
    - `prompt_version` and `llm_model` metadata.
- Output:
  - Store one record per evaluation case in:
    - `data/evaluation_reports/expert_answer_generation_v1.jsonl`
    - `data/evaluation_reports/expert_answer_generation_v1.csv`
  - Use this structured output as the basis for human-review rubrics and failure analysis.

Treat this pipeline and schema as an accepted baseline: it is suitable for early answer evaluation and rubric design, but model choice, prompt wording, and some field details may change as evaluation results accumulate.

### Alternatives considered

- Generate free-form narrative answers without a structured schema.
- Embed ATT&CK IDs directly in natural language without separate fields.
- Combine retrieval and generation into a single monolithic script.
- Delay any answer-generation implementation until retrieval work and external benchmark curation are fully complete.

### Consequences

- The answer layer remains explicitly grounded in retrieved ATT&CK records and cannot introduce arbitrary new IDs outside the retrieved candidate set without being flagged.
- The structured contract allows for systematic human review and scoring across dimensions such as candidate validity, retrieval grounding, narrative grounding, uncertainty handling, and analyst usefulness.
- The pipeline enables separation of retrieval failures (missing or mis-ranked candidates) from generation failures (poor reasoning over available evidence).
- Future work can iterate on prompts, model selection, and rubric design while preserving the same high-level output contract, or evolve the contract in new decision records when needed.