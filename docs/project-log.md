# Project log

This file is a chronological working journal for Cyber Threat Identifier.

It records implementation progress, discoveries, unresolved questions, and immediate next steps. It is not the source of truth for stable decisions, corpus rules, evaluation results, or setup instructions.

* For stable design decisions, see [`decisions.md`](decisions.md).
* For source provenance, schema, and processing rules, see [`dataset-notes.md`](dataset-notes.md).
* For retrieval and answer-evaluation design, experiments, and results, see [`evaluation-notes.md`](evaluation-notes.md).
* For reproducible commands and troubleshooting, see [`runbook.md`](runbook.md).

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
Proceed with Cyber Threat Identifier as an evidence-oriented, analyst-supporting incident-to-technique retrieval project. **See DEC-001, DEC-002, and DEC-003.**

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
Use a grouped, pipeline-oriented repository structure and run stages with `uv run python -m ...`. **See DEC-005 and DEC-006.**

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
Use the official Enterprise ATT&CK STIX 2.1 bundle as the initial source corpus and preserve acquisition provenance. **See DEC-007.**

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
Represent each active Enterprise technique or sub-technique as one processed JSONL record. **See DEC-008 and DEC-009.**

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
Do not chunk the initial Enterprise ATT&CK technique corpus. **See DEC-008.**

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
Use separate schema, load, and embedding stages over PostgreSQL with pgvector. **See DEC-010.**

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
Commit inspectable derived corpus and provenance artefacts; regenerate raw upstream downloads through the ingestion pipeline. **See DEC-004.**

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
Use exact cosine-distance search for the initial vector-retrieval baseline. Retain optional HNSW support for later evaluation if corpus scale, latency results, or deployment needs justify it. **See DEC-012.**

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
Maintain separate documentation responsibilities and update only the relevant document when new work is completed. **See DEC-013.**

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
Adopt the Expert subset as the leading candidate for a future curated external benchmark, subject to final answer-evaluation design and provenance review. **See DEC-014.**

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
Use **vector retrieval** as the default ATT&CK candidate-retrieval method for v1. **See DEC-015 (superseded by DEC-018).**

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
- Implemented `src/evaluation/run_expert_answer_generation.py` as a benchmark script that runs vector retrieval, calls the answer generator, records uncertainty flags, and writes JSONL/CSV outputs.
- Added a lightweight LLM client wrapper in `src/llm_client.py`.
- Ran the full ingestion, database, embedding, retrieval, and answer-generation pipeline from a clean checkout.
- Verified that existing documentation (README and runbook) still aligned with the refactored module layout and updated them where needed.

### What was learned
- Refactoring retrieval into separate modules, with shared metrics and embedding helpers, improved readability without changing behaviour at the benchmark level.
- Centralising embedding-model loading reduced repeated logs and model-initialisation time within a single process.
- The initial answer-generation path can reliably stay within the retrieved ATT&CK context and express uncertainty when expected labels are missing from the candidate set.
- A small `--limit` run is sufficient to catch most integration errors after refactor; larger runs can be reserved for post-refactor validation when everything is stable.

### Decision made
Adopt the refactored retrieval and evaluation structure as the new baseline. **See DEC-016 and DEC-017.**

### Problems or uncertainties
- The answer-generation pipeline still relies on a single configured model; model-comparison experiments and alternative prompts are future work.
- The current LLM configuration is local and subject to provider constraints; long-term deployment configuration remains unspecified.
- Per-query retrieval diagnostics (e.g. detailed hybrid vs vector case analysis) are not yet automated and will require further tooling.

### Next step
- Extend the evaluation notes with answer-generation benchmark configuration and example outputs.
- Finalise the initial human-review rubric and apply it to a small set of Expert-derived cases to validate the answer-output contract.

---

## 2026-08-12 — Local document reranking implementation and evaluation

### Stage
Retrieval refinement, document reranking, benchmark comparison, and retrieval-default selection.

### Goal
Implement a genuine second-stage document reranking pipeline over the existing vector retrieval backend; measure whether it improves ATT&CK technique ranking quality enough to justify additional local CPU latency and complexity.

### What was done
- Implemented a two-stage retrieval flow using pgvector for candidate generation and `cross-encoder/ms-marco-MiniLM-L-6-v2` for local CPU reranking.
- Confirmed the reranker successfully used the existing structured `embedding_text` field without schema migrations.
- Ran the full vector-plus-reranking benchmark over all 226 Expert-derived evaluation cases and compared it against the vector-only baseline.

### What was learned
- The existing `embedding_text` field is suitable for cross-encoder reranking because it already combines ATT&CK ID, technique name, tactics, platforms, and cleaned description.
- The local cross-encoder successfully reranked the top 20 vector candidates on CPU without API cost or provider dependency.
- Vector-plus-reranking consistently improved every reported retrieval metric across the evaluation set, specifically yielding practical gains at the very top of the returned list (MRR, Hit@3).
- CPU reranking was the dominant contributor to end-to-end retrieval latency, though performance (approx. 1.25s median) remained acceptable for analyst-assist workflows.

### Decision made
Adopt **vector retrieval plus local cross-encoder document reranking** as the selected default retrieval configuration for version 1. **For full latency measurements, metric tables, and the formal decision rationale, see DEC-018.**

### Problems or uncertainties
- The 226-case Expert-derived set contains development- and test-derived records; it is for implementation comparison, not a frozen held-out benchmark.
- The selected reranked retrieval configuration has not yet been integrated into the answer-generation baseline.
- The Streamlit runtime path still needs a safe fallback if the reranker model cannot load.

### Next step
Implement and evaluate one constrained user-query rewriting configuration against the selected vector-plus-reranking baseline.

---

## 2026-08-13 — User query rewriting evaluation and decision

### Stage
Retrieval refinement, LLM-based query rewriting, benchmark comparison, and retrieval-default confirmation.

### Goal
Evaluate whether LLM-based user query rewriting improves retrieval quality enough to justify the additional latency and API dependency, and decide whether to adopt it as the default v1 configuration.

### What was done
- Implemented `src/retrieval/query_rewriter.py` using Gemini 3.1 Flash Lite.
- Configured prompt instructions to strictly preserve explicit behaviours, tools, and execution methods from the narrative.
- Added optional client-side rate limiting in `src/llm_client.py`.
- Ran the full query-rewrite benchmark over all 226 evaluation cases and compared it against the DEC-018 vector-plus-reranking baseline.

### What was learned
- Query rewriting improved all reported retrieval metrics over the DEC-018 baseline.
- However, query rewriting became the dominant source of retrieval latency, adding significant processing time (median ~3.1 seconds, up to 11 seconds at P95).
- The latency penalty is unacceptable for interactive analyst-assist workflows despite the measured quality improvements.

### Decision made
**Do not adopt user query rewriting as the default retrieval configuration for version 1.** Retain vector retrieval plus local cross-encoder reranking (DEC-018) as the default. **For complete evaluation metrics and latency breakdowns, see DEC-019.**

### Problems or uncertainties
- The evaluation used Gemini 3.1 Flash Lite; alternative models may have different latency and instruction-following profiles.
- Alternative prompts (e.g., heavily optimised with few-shot examples) might yield different quality-latency trade-offs.

### Next step
Proceed with Streamlit interface implementation using the vector-plus-reranking default.

---

## 2026-08-13 — Pairwise LLM-as-judge evaluation for answer generation (revised)

### Stage
Evaluation design and model comparison.

### Goal
Introduce and run a scalable, repeatable evaluation method to compare answer‑generation models (`gemini‑3.1‑flash‑lite` vs `gemini‑3.5‑flash‑lite`) on the existing 226‑case dataset, without relying solely on manual expert judgement.

### What was done
- Used the DEC-017 pipeline to produce structured answers for 226 incident narratives with both Gemini 3.1 Flash-Lite and 3.5 Flash-Lite.
- Implemented `src.evaluation.run_llm_judge_pairwise` to perform randomized A/B answer presentation.
- Required judges to compare answers on relevance, evidence grounding, uncertainty framing, and conciseness via JSON outputs.
- Ran the pairwise judge twice per case (once with 3.1 as the judge, once with 3.5).
- Implemented `src.evaluation.analyze_judge_agreement` to compute cross-judge statistics and isolate disagreement cases.

### What was learned
- The pairwise judge scripts evaluated all 226 cases successfully via checkpointing and retry/backoff mechanisms.
- Cross‑judge agreement is substantial (~75%) but not perfect, indicating evaluator uncertainty in about a quarter of the dataset.
- Both judges demonstrated a tendency to prefer `gemini‑3.1‑flash‑lite` answers.
- The 55 disagreement cases form a highly manageable pool for targeted manual human inspection.

### Decision made
**Adopt pairwise LLM‑as‑judge evaluation as the standard automated method** for comparing answer‑generation models. **See DEC-020 for the complete protocol and precise score distributions.**

### Problems or uncertainties
- LLM judges are not ground truth and inherently exhibit bias; manual review of disagreement cases is still outstanding.
- The 226-case dataset is an internal implementation-comparison set, not a fully frozen, held-out benchmark.

### Next step
Implement the Streamlit interface and integrate the judge outputs and agreement metrics into the monitoring dashboard.

---

## 2026-08-13 — Streamlit UI implementation and monitoring dashboard

### Stage
Interface implementation, monitoring, and integration with evaluation outputs.

### Goal
Provide an interactive Streamlit interface for security practitioners to map incident narratives to ATT&CK techniques, inspect retrieved evidence, submit feedback, and review evaluation metrics.

### What was done
- Implemented `app/home.py` as the main Streamlit entry point with four tabs: Home, Query, Dashboard, and Evaluation Review.
- Built the Query interface (`app/query.py`) to execute incident-narrative input through the vector-plus-reranking retrieval path.
- Added feedback persistence via `src.monitoring.feedback_store.save_feedback`.
- Built the Dashboard (`app/dashboard.py`) to display generation latency, judge preferences, retrieval comparisons, and user feedback distributions.
- Implemented the manual-review workflow (`app/evaluation.py`) for adjudicating disagreement cases.
- Added `app/Dockerfile` to build a standalone Streamlit application image.

### What was learned
- The dashboard successfully integrates offline evaluation artefacts, allowing reviewers to observe metrics without initiating API-heavy runs.
- Presenting both reciprocal judges in the dashboard is necessary for a transparent pairwise evaluation display.
- Feedback persistence is functional, and the dashboard correctly identifies when no feedback exists as a clean starting state.

### Decision made
- Adopt the four-tab Streamlit application as the primary v1 interface.
- Use vector retrieval plus local cross-encoder reranking for the Query workflow.
- Use the Evaluation Review tab as the standard interface for manual adjudication.

### Problems or uncertainties
- The retrieval-comparison chart currently references documented DEC-018 and DEC-019 values directly in the application code rather than dynamically parsing benchmark CSVs.
- Feedback volume is virtually zero at launch and cannot yet be treated as a representative quality signal.

### Next step
Complete the reranked answer-generation comparison, reciprocal judge evaluation, and blinded manual review, then update the decisions register with the final evidence.

---

## 2026-08-16 — Reranked answer-generation evaluation and manual review

### Stage
Answer-generation evaluation, reciprocal LLM judging, manual adjudication, and monitoring integration.

### Goal
Compare Gemini 3.1 Flash-Lite and Gemini 3.5 Flash-Lite under the selected v1 retrieval pipeline, review all judge-disagreement cases, and use the results to select the default answer-generation model.

### What was done
- Ran `src.evaluation.run_expert_llm_comparison_reranked` using the top 5 reranked ATT&CK records as answer context.
- Generated structured answers for both models across all 226 evaluation cases.
- Conducted reciprocal pairwise LLM judging with randomized A/B presentation.
- Used `app/evaluation.py` to manually review all 55 reranked judge-disagreement cases blind to model identity.

### What was learned
- The manual review determined that Gemini 3.1 Flash-Lite secured the majority of decisive comparisons over Gemini 3.5 Flash-Lite.
- However, nearly a third of manually reviewed cases resulted in a tie, indicating substantial practical overlap between the models.
- The review identified shared pipeline issues, such as incomplete retrieved context and narrative-label mismatches, which affected both models equally.

### Decision made
Select `gemini-3.1-flash-lite` as the default v1 answer-generation model. **See DEC-021 for the detailed human adjudication metrics and failure mode analysis.**

### Problems or uncertainties
- The 226-case set remains an implementation-comparison set, not a frozen held-out benchmark.
- The high tie rate confirms the choice is a measured preference rather than an indication of universal superiority.

### Next step
Synchronise README, runbook, evaluation notes, dataset notes, project log, UI model information, dashboard labels, and decision records with the completed results.

---

## 2026-08-16 — Documentation and UI alignment after model selection

### Stage
Documentation, interface, evaluation-artefact, and reproducibility alignment.

### Goal
Ensure that the repository documentation and Streamlit interface describe the implemented v1 system rather than the earlier assumption that Gemini 3.5 Flash-Lite would be the default or preferred model.

### What was done
- Set default model configuration `MODEL_ID=gemini-3.1-flash-lite`.
- Updated `app/query.py` and `app/home.py` to read the configured model without hard-coded fallbacks, and accurately display the vector-plus-reranking architecture.
- Updated `app/dashboard.py` to explicitly display both reciprocal judge preference charts.
- Re-documented the four Streamlit tabs and explicit feedback persistence rules.

### What was learned
- A comprehensive repository scan was necessary to locate and correct stale statements drafted before the final evaluation workflows concluded.
- The interface documentation must clearly distinguish between the selected runtime answer model, the models evaluated, and the models used as reciprocal judges.

### Decision made
Use `gemini-3.1-flash-lite` as the documented and configured default v1 answer-generation model. Treat the dashboard's hard-coded retrieval values as explicit benchmark constants until dynamic loading is implemented.

### Problems or uncertainties
- The feedback store is file-based and local; it is not suited for concurrent production scaling.
- The final external benchmark remains subject to unresolved third-party narrative redistribution rules.

### Next step
Run a final consistency check for obsolete baseline statements.

---

## 2026-08-16 — Docker Compose validation and submission-readiness hardening

### Stage
Containerization, ingestion automation, reproducibility, dashboard polish, and final documentation alignment.

### Goal
Validate that the complete v1 application stack can be rebuilt from an empty local Docker state, with PostgreSQL, pgvector, Streamlit, source ingestion, database loading, and embedding generation all executed through Docker Compose.

### What was done
- Pinned the Docker image's `uv` tool version and configured it to execute the locked virtual environment.
- Updated `compose.yaml` to define `postgres`, `streamlit`, and an on-demand `ingest` profile.
- Configured the `ingest` profile to run the entire data extraction, pgvector schema initialization, data loading, and embedding pipeline synchronously.
- Conducted a destructive clean-state validation (`docker compose down -v`, followed by `make up` and `make ingest`).
- Renumbered and polished the dashboard charts sequentially.

### What was learned
- `uv sync` installs project dependencies into the project virtual environment, so utility services in Compose must use `uv run python` rather than system `python`.
- A Streamlit container can appear healthy via HTTP checks while a lazily imported Query workflow still lacks a fully initialized database dependency.
- The persistent Hugging Face cache volume successfully mitigates redundant model downloads on subsequent container runs.

### Decision made
Treat Docker Compose as the canonical local execution path for the v1 application stack. Retain the `ingest` service as an explicit one-off profile rather than implementing a complex external orchestrator. **See DEC-022 and DEC-023.**

### Problems or uncertainties
- The current default ingest configuration points to the moving ATT&CK `master` branch. Formal benchmarks should pivot to a fixed release tag.

### Next step
Deploy the application to AWS EC2 for reviewer access.

---

## 2026-08-17 — EC2 demo deployment and public sample-query cleanup

### Stage
Deployment, interface validation, data-governance cleanup, and documentation alignment.

### Goal
Deploy the v1 application to an AWS EC2 instance for a time-limited demonstration, validate the end-to-end Docker Compose path, and remove the public application's dependency on private expert-evaluation artefacts.

### What was done
- Provisioned an Ubuntu 24.04 `t3.medium` EC2 instance, installed Docker Compose, and deployed the stack.
- Validated the on-demand `ingest` profile within the cloud environment.
- Identified and replaced the Query page's dependency on local private expert CSVs with a public `data/sample_queries.json` file consisting of synthetic or source-informed sample narratives.
- Purged restricted expert-evaluation files from the staged public branch and updated `.gitignore` rules.

### What was learned
- Executing `docker compose up -d` boots PostgreSQL and Streamlit but does not initialize the pgvector application schema—the ingestion profile *must* be run for new volumes.
- Publicly accessible demonstration interfaces must not silently link to local evaluation artefacts, as it violates external data redistribution policies.
- EC2 root filesystem utilization spiked during model caching, warranting close monitoring prior to further benchmark execution.

### Decision made
Use AWS EC2 and Docker Compose as the temporary demonstration deployment path. Separate public demonstration samples from restricted/local expert-evaluation data. **See DEC-024, DEC-025, and DEC-026.**

### Problems or uncertainties
- The deployment is strictly a temporary demonstration environment; TLS, managed secrets, production-grade authentication, and high availability are explicitly out of scope.
- The exposed Streamlit port (`8501`) should be locked down to the demonstrator's IP via AWS Security Groups.

### Next step
Commit the documentation updates, verify the sample-query path on the live instance, rotate any exposed API keys used during setup, and prepare to terminate the environment post-demonstration.

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