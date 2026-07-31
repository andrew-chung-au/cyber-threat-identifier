# Project log

This file is a chronological working journal for Cyber Threat Identifier.

It records implementation progress, discoveries, unresolved questions, and immediate next steps. It is not the source of truth for stable decisions, corpus rules, evaluation results, or setup instructions.

For stable design decisions, see [`decisions.md`](decisions.md).  
For source provenance, schema, and processing rules, see [`dataset-notes.md`](dataset-notes.md).  
For retrieval and answer-evaluation design, experiments, and results, see [`evaluation-notes.md`](evaluation-notes.md).  
For reproducible commands and troubleshooting, see [`runbook.md`](runbook.md).

---

## 2026-07-27 — Project framing and documentation setup

### Stage

Topic selection, scope definition, naming, corpus selection, and documentation setup.

### Goal

Define a portfolio-ready project direction and create a clear documentation structure before implementation begins.

### What was done

- Explored several possible projects in the security and threat-analysis space.
- Rejected ideas that were too broad, difficult to evaluate, weakly reproducible, or potentially fragile from a licensing and branding perspective.
- Chose a retrieval project that maps incident narratives to likely Enterprise MITRE ATT&CK techniques.
- Selected **Cyber Threat Identifier** as the product name.
- Confirmed that MITRE ATT&CK would be used descriptively as the source knowledge base, not in the product name.
- Created the initial documentation plan covering the README, project log, decisions register, dataset notes, evaluation notes, and runbook.

### What was learned

- A narrow incident-to-technique task is easier to explain and evaluate than a general cyber copilot.
- Enterprise ATT&CK provides a structured, recognisable foundation for technique retrieval.
- Documentation needs separate homes for public overview, decisions, data evidence, experiments, and operational instructions.

### Decision made

Proceed with Cyber Threat Identifier as an evidence-oriented, analyst-supporting incident-to-technique retrieval project.

### Problems or uncertainties

- The retrieval unit, chunking approach, database design, and evaluation benchmark were not yet finalised.
- The project still needed a clear implementation sequence from source acquisition through retrieval evaluation.

### Next step

Define the repository structure, source-acquisition approach, and minimum ingestion pipeline.

---

## 2026-07-29 — Repository and pipeline structure

### Stage

Project structure and implementation planning.

### Goal

Choose a simple repository layout that supports ingestion, database loading, retrieval, evaluation, a future interface, and later monitoring.

### What was done

- Compared a flat `src/` directory with a grouped structure organised by pipeline responsibility.
- Chose a grouped `src/` layout for ingestion, database operations, retrieval, evaluation, generation, and monitoring.
- Kept shared helpers, including database configuration and LLM utilities, at the root of `src/`.
- Chose Python module execution from the repository root as the standard way to run pipeline stages.

### What was learned

- A grouped structure makes the pipeline easier to scan as the project grows.
- The repository should prioritise readable application and pipeline code rather than a fully packaged library design.
- Module execution provides more predictable imports across subdirectories.

### Decision made

Use a grouped, pipeline-oriented repository structure and run stages with `uv run python -m ...`.

### Problems or uncertainties

- Streamlit and monitoring are intentionally deferred until a retrieval and answer baseline is working.
- A Makefile was considered useful but deferred until core commands have been validated.

### Next step

Implement reproducible source acquisition for the Enterprise ATT&CK STIX data.

---

## 2026-07-29 — Source acquisition design

### Stage

Dataset selection and ingestion.

### Goal

Create a reproducible way to download and record the Enterprise MITRE ATT&CK dataset used by the project.

### What was done

- Selected the official MITRE ATT&CK STIX data repository as the source.
- Defined `src/ingestion/download_attack_data.py`.
- Configured the downloader to retrieve the STIX collection index and Enterprise bundle.
- Added SHA-256 checksums and an append-only download manifest.
- Added a `--ref` option to support both the current default reference and fixed release tags.
- Chose `data/raw/attack/` as the local raw-download location.
- Chose `data/source_manifest.csv` as the provenance record.

### What was learned

- A moving upstream reference supports current-data refreshes but does not provide a fixed experimental baseline.
- Recording the source URL, reference, timestamp, local path, and SHA-256 checksum creates a useful provenance trail.
- A fixed release tag should be used before reporting formally comparable retrieval evaluation results.

### Decision made

Use the official Enterprise ATT&CK STIX 2.1 bundle as the initial source corpus and preserve acquisition provenance.

### Problems or uncertainties

- The initial pinned release for formal evaluation has not yet been chosen.
- Additional ATT&CK object types and external security sources remain intentionally out of scope for version 1.

### Next step

Extract active Enterprise techniques and sub-techniques from the downloaded STIX bundle.

---

## 2026-07-29 — Technique extraction and retrieval-unit design

### Stage

Ingestion and corpus design.

### Goal

Transform the Enterprise ATT&CK STIX bundle into clean, retrieval-ready technique records.

### What was done

- Defined `src/ingestion/extract_attack_techniques.py`.
- Limited the initial corpus to active Enterprise `attack-pattern` objects.
- Excluded revoked and deprecated records.
- Extracted technique identity, sub-technique status, tactics, platforms, descriptions, source URLs, and timestamps.
- Preserved raw descriptions for evidence and produced cleaned descriptions for retrieval preparation.
- Removed inline citation markers from cleaned descriptions.
- Resolved duplicate ATT&CK IDs using the newest source modification timestamp.
- Chose `data/processed/techniques.jsonl` as the processed corpus output.

### What was learned

- ATT&CK technique records provide the identity and metadata required for an evidence-oriented retrieval result.
- Maintaining raw and cleaned descriptions supports both transparent evidence display and cleaner retrieval text.
- The processed corpus provides a practical inspection point between STIX extraction and database loading.

### Decision made

Represent each active Enterprise technique or sub-technique as one processed JSONL record.

### Problems or uncertainties

- Parent-technique enrichment remains limited to the current extracted fields.
- Procedure examples, software, groups, mitigations, relationships, and detection content remain outside the initial corpus.

### Next step

Measure record size and decide whether document-style chunking is necessary.

---

## 2026-07-29 — Chunking assessment

### Stage

Corpus design and retrieval preparation.

### Goal

Determine whether technique records should be split into smaller chunks before database loading and embedding.

### What was done

- Measured description length and record size across the active Enterprise technique corpus.
- Evaluated whether one technique record is already an appropriate retrieval unit.
- Defined an embedding-text structure that combines technique identity, metadata, and cleaned description.
- Removed planned document-style chunking from the initial pipeline.

### What was learned

- The technique records are compact enough to retain as complete source-native retrieval units.
- The median cleaned description was approximately 151 words; the average was approximately 168 words.
- The 95th percentile was approximately 312 words, and the largest record was approximately 555 words.
- Chunking would add complexity and could separate technique identity and metadata from its evidence text.

### Decision made

Do not chunk the initial Enterprise ATT&CK technique corpus.

### Problems or uncertainties

- A future project expansion using long-form reports, procedure examples, or advisory documents may need a separate chunked-document layer.
- The no-chunking decision must be revisited if corpus composition changes substantially.

### Next step

Create the PostgreSQL schema and separate source-record loading from embedding generation.

---

## 2026-07-29 — Database and embedding pipeline split

### Stage

Database design and embedding preparation.

### Goal

Create a reproducible PostgreSQL and pgvector pipeline that keeps source-record loading independent from embedding generation.

### What was done

- Reviewed the initial combined database-loading approach.
- Split schema initialisation, JSONL loading, and embedding generation into separate modules.
- Defined canonical technique storage and pipeline-run audit records.
- Selected PostgreSQL with pgvector for structured records and vector storage.
- Selected `sentence-transformers/all-MiniLM-L6-v2` as the initial local embedding baseline.
- Chose normalised embeddings and exact cosine-distance retrieval.

### What was learned

- Separating loading from embedding generation supports reruns, debugging, and later model comparisons.
- Structured records remain inspectable before embeddings are present.
- A refreshed technique record needs embedding regeneration when its embedding text changes.

### Decision made

Use separate schema, load, and embedding stages over PostgreSQL with pgvector.

### Problems or uncertainties

- The Compose configuration, dependencies, and full pipeline still need validation from a clean local checkout.
- Text retrieval, hybrid retrieval, and the evaluation benchmark are not implemented at this stage.
- The baseline embedding model requires measurement rather than assumption.

### Next step

Make the environment runnable, validate the database connection, and run the complete pipeline from a clean state.

---

## 2026-07-30 — Reproducibility and repository artefacts

### Stage

Reproducibility, source control, and documentation alignment.

### Goal

Clarify which data artefacts belong in the public repository and which should be regenerated locally.

### What was done

- Reviewed the role of raw STIX downloads, processed records, provenance manifests, and future evaluation data.
- Decided to commit the processed corpus snapshot and download manifest.
- Decided to exclude raw downloaded STIX files from Git because they are reproducible upstream artefacts.
- Confirmed that future curated evaluation data should be version controlled only where its provenance and redistribution terms permit this.
- Updated the documentation plan to keep the processed-corpus policy in dataset notes and the operational commands in the runbook.

### What was learned

- A processed corpus snapshot improves portfolio review because the actual retrieval records can be inspected without requiring a database or initial source download.
- Keeping raw upstream downloads out of Git avoids unnecessary duplication while retaining reproducibility through references and checksums.
- Documentation needs strict boundaries to avoid the README, runbook, decisions register, and dataset notes repeating the same material.

### Decision made

Commit inspectable derived corpus and provenance artefacts; regenerate raw upstream downloads through the ingestion pipeline.

### Problems or uncertainties

- The repository still needs a final `.gitignore` review after the current generated files are inspected.
- The exact wording required when distributing ATT&CK-derived corpus content must remain aligned with current MITRE terms.

### Next step

Finalise environment configuration, run the pipeline from a clean checkout, and inspect the resulting processed corpus and database records.

---

## 2026-07-30 — HNSW index scope refinement

### Stage

Vector retrieval preparation and performance strategy.

### Goal

Decide whether HNSW indexing belongs in the required baseline pipeline for the initial corpus.

### What was done

- Reconsidered automatic HNSW-index creation in light of the small initial corpus.
- Distinguished exact cosine-distance search, which is appropriate for baseline correctness checks, from approximate nearest-neighbour indexing, which is a performance optimisation.
- Updated the intended runbook and README approach so that HNSW creation is optional rather than a required embedding-build step.

### What was learned

- The initial corpus has approximately 700 technique and sub-technique records, so exact cosine-distance search is practical for baseline retrieval evaluation.
- HNSW is useful to support later performance testing, but it should not be treated as necessary evidence of production readiness.
- Any later comparison should record whether results use exact or approximate search and include relevant index settings.

### Decision made

Use exact cosine-distance search for the initial vector-retrieval baseline. Retain optional HNSW support for later evaluation if corpus scale, latency results, or deployment needs justify it.

### Problems or uncertainties

- At this stage, retrieval implementation and latency measurements did not yet exist; later work added text, vector, and hybrid retrieval benchmarks over the Expert-derived cases.
- Index performance and recall trade-offs cannot be assessed until a reviewed evaluation benchmark exists.

### Next step

Validate the source-to-vector pipeline, then create a small reviewed evaluation dataset before selecting a retrieval approach.

---

## 2026-07-30 — Documentation responsibility split

### Stage

Documentation alignment.

### Goal

Prevent the project documentation from becoming repetitive while preserving both public clarity and technical traceability.

### What was done

- Reviewed overlap between the README, runbook, decisions register, dataset notes, evaluation notes, and project log.
- Shortened the intended role of the runbook to reproducible setup, commands, verification, resets, and common issues.
- Kept public project framing, scope, status, and limitations in the README.
- Assigned corpus provenance, schema, extraction details, and data-artifact policy to dataset notes.
- Assigned retrieval experiments, benchmark design, metrics, and failure analysis to evaluation notes.
- Retained the project log as a chronological record of working progress and next steps.

### What was learned

- A runbook is more useful when it is operational rather than a full technical specification.
- A concise README is stronger for portfolio reviewers than a document that repeats implementation and troubleshooting detail.
- Decision records should state stable choices and consequences, not duplicate stage-by-stage working history.

### Decision made

Maintain separate documentation responsibilities and update only the relevant document when new work is completed.

### Problems or uncertainties

- Documentation can still drift if implementation changes are not reflected in the correct file.
- The next implementation stages will need consistent updates across the project log, evaluation notes, and README status.

### Next step

Complete clean-checkout validation of the current pipeline and record the actual results in a new project-log entry.

---

## 2026-07-30 — External answer-evaluation dataset feasibility check

### Stage

Evaluation planning and external benchmark feasibility.

### Goal

Determine whether a public dataset of authentic cyber-threat narratives with existing ATT&CK labels could support later end-to-end evaluation of the full system.

### What was done

- Identified the Expert subset in the public `tumeteor/mitre-ttp-mapping` repository as a candidate external evaluation source.
- Downloaded the upstream repository into `data/external_inspection/mitre-ttp-mapping/` for local feasibility inspection.
- Kept `data/external_inspection/` ignored by Git so upstream source files are not accidentally committed during evaluation planning.
- Inspected the Expert split structure: `expert_train.tsv`, `expert_dev.tsv`, and `expert_test.tsv`.
- Confirmed that the files contain a threat-report text field (`text1`) and a list-like ATT&CK label field (`labels`).
- Reviewed the held-out Expert test split, which contains 157 annotated threat-report passages.
- Confirmed that the test split contains no explicit ATT&CK technique IDs and no explicit ATT&CK or MITRE wording in the narrative text.
- Confirmed that the Expert test records do not exactly overlap with the repository's procedure-example split.
- Added `src/evaluation/validate_external_expert_labels.py`.
- Validated all unique Expert labels across the train, development, and test splits against the local active Enterprise ATT&CK corpus.
- Wrote the compatibility report to `data/evaluation_reports/expert_label_compatibility.csv`.

### What was learned

- The Expert subset is a substantially better candidate for full-system evaluation than synthetic narratives because it contains authentic threat-report language with existing technique and sub-technique labels.
- The Expert test split is small but practical for a portfolio benchmark: its passages are generally short enough for a bounded analyst-facing answer, while still containing realistic multi-label behaviour descriptions.
- Across all Expert splits, 281 of 290 unique labels are active in the current local Enterprise ATT&CK corpus; three are deprecated and six are revoked.
- None of the 290 labels are absent from the current local Enterprise ATT&CK corpus.
- Only four of the 157 held-out Expert test records contain one or more non-active labels.
- The four affected test rows are upstream indices `12`, `17`, `32`, and `130`.
- The external dataset is technically compatible with the current corpus without downgrading the application to an older ATT&CK release.
- The repository README declares CC BY 4.0, but the original third-party threat-report provenance is not itemised in the Expert subset documentation; redistribution of copied narrative text therefore needs a separate final review before a curated benchmark is committed publicly.

### Decision made

Adopt the Expert subset as the leading candidate for a future curated external benchmark, subject to final answer-evaluation design and provenance review.

For the future benchmark, a record will be ineligible if any upstream expected ATT&CK technique or sub-technique ID is not active in the project's pinned Enterprise ATT&CK corpus. The upstream TSV files will remain unchanged.

### Problems or uncertainties

- The Expert labels are multi-label and unordered, so they do not provide a verified single primary technique for each narrative.
- The final answer contract, evaluation rubric, and curation rules have not yet been designed.
- The external test split must remain held out and must not be repeatedly used to choose retrieval settings, prompts, or models.
- The precise ATT&CK release used for the Expert subset labels has not been explicitly confirmed in the repository documentation.
- The licensing and provenance position for redistributing selected third-party report passages needs to be resolved before committing copied narrative text to the public repository.

### Next step

Implement and validate the full answer-generation path, then use `expert_dev.tsv` to define the answer contract, curation rules, and answer-evaluation rubric before applying those frozen rules to the held-out Expert test split.

---

## 2026-07-31 — Retrieval benchmarks and default choice

### Stage

Retrieval implementation and evaluation.

### Goal

Implement text, vector, and hybrid retrieval benchmarks over the current ATT&CK corpus; compare their performance on Expert-derived cases; and choose a sensible default retrieval method for v1.

### What was done

- Implemented `src.evaluation.run_expert_text_retrieval_benchmark` over the active Enterprise ATT&CK technique corpus.
- Implemented `src.evaluation.run_expert_vector_retrieval_benchmark` using normalised embeddings from `sentence-transformers/all-MiniLM-L6-v2` and exact cosine-distance search.
- Implemented `src.evaluation.run_expert_hybrid_retrieval_benchmark` using Reciprocal Rank Fusion over text and vector ranked lists.
- Ran all three retrieval benchmarks over `data/eval/expert_retrieval_cases.csv` (226 cases).
- Recorded per-method metrics and saved CSV outputs in `data/evaluation_reports/expert_text_retrieval_results.csv`, `expert_vector_retrieval_results.csv`, and `expert_hybrid_retrieval_results.csv`.
- Updated `docs/evaluation-notes.md` to describe the benchmark setup, metrics, and current retrieval findings.
- Updated `README.md` to reflect that retrieval baselines and benchmarks are implemented and to state that vector retrieval is the current default backend.

### What was learned

- Text-only retrieval is a very weak lexical baseline on this corpus: Hit@k and MRR remain close to zero even after loosening score filtering.
- Vector retrieval is much stronger than text and clearly improves Recall@k, Hit@k, and MRR across the 226-case Expert-derived benchmark.
- Hybrid retrieval using RRF is slightly stronger than vector-only on some ranking metrics (e.g. Recall@1, Recall@3, Hit@3, MRR), while Recall@5 and Recall@10 remain identical.
- The hybrid uplift over vector is real but small at the current corpus size and query mix; the extra implementation and compute complexity does not yet justify making hybrid the default.
- These results support treating vector retrieval as the default v1 backend, with text and hybrid retained as evaluated baselines and debugging tools.

### Decision made

Use **vector retrieval** as the default ATT&CK candidate-retrieval method for v1.

Retain **text retrieval** and **hybrid retrieval (vector + text, RRF)** as implemented baselines and diagnostic tools. Hybrid can be reconsidered as the default later if improvements to the lexical channel or corpus characteristics increase its advantage enough to justify the extra complexity.

### Problems or uncertainties

- Hybrid’s marginal advantage suggests the lexical channel does contribute occasionally valuable hits; further per-query analysis is needed to understand when and why.
- The current benchmark is retrieval-only; full end-to-end evaluation including answer generation and human review is still pending.
- Latency and resource-usage comparisons between vector and hybrid retrieval have not yet been measured under realistic interface conditions.

### Next step

Design and implement the candidate-answer generation path, then use the Expert development split to define the answer contract, curation rules, and human-review rubric before applying frozen rules to the held-out Expert test split.

---

## 2026-07-31 — Retrieval and generation refactor validation

### Stage

Refactoring and pipeline validation.

### Goal

Refactor retrieval and evaluation code into clearer modules, introduce shared helpers and answer-generation support, and confirm that the end-to-end pipeline still reproduces the existing benchmarks.

### What was done

- Introduced dedicated modules under `src/retrieval/` for text, vector, and hybrid retrieval, with shared dataclasses for retrieved candidates.
- Added a shared embedding-model helper to centralise loading of `sentence-transformers/all-MiniLM-L6-v2` and avoid redundant initialisation within a single process.
- Added `src/evaluation/metrics.py` to centralise retrieval-metric computation for text, vector, and hybrid runs.
- Implemented `src/generation/schemas.py`, `src/generation/prompts.py`, and `src/generation/answer_generator.py` to define the structured answer-output schema and prompt scaffolding.
- Implemented `src/evaluation/run_expert_answer_generation.py` as a benchmark script that:
  - runs vector retrieval over Expert-derived cases,
  - calls the answer generator to select primary and alternative techniques,
  - records uncertainty and review-required flags,
  - and writes JSONL and CSV outputs to `data/evaluation_reports/`.
- Added a lightweight LLM client wrapper in `src/llm_client.py` to handle model ID configuration and client construction.
- Ran the full ingestion, database, embedding, retrieval, and answer-generation pipeline from a clean checkout:
  - confirmed that text, vector, and hybrid retrieval benchmarks still reproduced the expected ordering of methods and similar metric ranges,
  - confirmed that answer-generation outputs were grounded in retrieved ATT&CK IDs and respected the uncertainty framing.
- Verified that existing documentation (README and runbook) still aligned with the refactored module layout and updated them where needed.

### What was learned

- Refactoring retrieval into separate modules, with shared metrics and embedding helpers, improved readability without changing behaviour at the benchmark level.
- Centralising embedding-model loading reduced repeated logs and model-initialisation time within a single process.
- The initial answer-generation path can reliably stay within the retrieved ATT&CK context and express uncertainty when expected labels are missing from the candidate set.
- A small `--limit` run is sufficient to catch most integration errors after refactor; larger runs can be reserved for post-refactor validation when everything is stable.

### Decision made

Adopt the refactored retrieval and evaluation structure as the new baseline:

- Keep text, vector, and hybrid retrieval in separate modules with shared schemas and metrics.
- Use the shared embedding-model helper for all embedding-based evaluations.
- Use the new answer-generation pipeline as the basis for future rubric-based human evaluation.

### Problems or uncertainties

- The answer-generation pipeline still relies on a single configured model; model-comparison experiments and alternative prompts are future work.
- The current LLM configuration is local and subject to provider constraints; long-term deployment configuration remains unspecified.
- Per-query retrieval diagnostics (e.g. detailed hybrid vs vector case analysis) are not yet automated and will require further tooling.

### Next step

- Extend the evaluation notes with:
  - a description of the answer-generation benchmark configuration,
  - example answer outputs and failure patterns,
  - and a mapping between retrieval failures and answer failures.
- Finalise the initial human-review rubric and apply it to a small set of Expert-derived cases to validate the answer-output contract.

---

## Template for future entries

## YYYY-MM-DD — Short stage title

### Stage

Ingestion / corpus design / database / retrieval / generation / evaluation / interface / monitoring / documentation.

### Goal

What is the target outcome for this stage?

### What was done

- Action completed.
- Action completed.
- Action completed.

### What was learned

- Insight or changed understanding.
- Constraint discovered.
- Clarification gained.

### Decision made

State the decision made during this stage, or write `No new stable decision` and link to an existing decision if applicable.

### Problems or uncertainties

- Issue or unresolved question.
- Risk or ambiguity.

### Next step

State the next single concrete action.