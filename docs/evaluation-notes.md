# Evaluation notes

This document records the design, datasets, metrics, experiments, and results used to evaluate Cyber Threat Identifier.

It covers retrieval and answer generation separately where possible. Stable project-wide design choices belong in [`decisions.md`](decisions.md); source provenance and data-processing details belong in [`dataset-notes.md`](dataset-notes.md); commands for running evaluation belong in [`runbook.md`](runbook.md).

---

## Evaluation goal

Measure whether the system can retrieve and present plausible Enterprise MITRE ATT&CK technique or sub-technique candidates from incident narratives in a way that is useful, evidence-grounded, inspectable, and reproducible.

The system is intended to support analyst review. It does not confirm adversary activity, perform incident triage, assign attribution, or replace human judgement.

The current evaluation evidence supports internal model and retrieval configuration choices; it does not establish general cyber-security retrieval performance or production readiness.

---

## Evaluation approach

Evaluation is divided into three layers:

1. **Retrieval evaluation** — whether relevant active ATT&CK records are returned near the top of the candidate list.
2. **Answer evaluation** — whether the generated response makes appropriately bounded claims that are supported by both the incident narrative and retrieved ATT&CK evidence.
3. **Reproducibility evaluation** — whether the same corpus, model configuration, query set, and parameters reproduce comparable outputs.

Retrieval and generation are evaluated separately because poor end-to-end answers can result from retrieval failures, unsupported generation, or both.

---

## Retrieval quality

### Goal

Determine whether the system retrieves expected active Enterprise ATT&CK technique records within a small ranked candidate set.

### Current benchmark setup

The current implemented retrieval benchmark uses Expert-derived incident narratives and active Enterprise ATT&CK technique and sub-technique records.

The derived 226-case benchmark input is not committed. Upstream source details, split policy, and provenance requirements are documented in [`docs/dataset-notes.md`](docs/dataset-notes.md). Reviewers can obtain the upstream Expert dataset from the documented Security-TTP-Mapping source and exact revision, then follow the evaluation workflow to recreate or extend the benchmark.

The current benchmark contains 226 cases assembled from the upstream Expert development and test splits. It is an **implementation-comparison set**, not a frozen held-out benchmark. It mixes development- and test-derived cases and is used to compare retrieval configurations under the same corpus and case set.

The retrieval unit is one processed ATT&CK technique or sub-technique record. The corpus is not chunked.

All compared methods use the same local ATT&CK corpus, case set, expected-label format, and ranking metrics.

### Retrieval metrics

Metrics are computed by `src/evaluation/metrics.py`.

- **Recall@k** — proportion of expected technique IDs present in the top \(k\) retrieved records.
- **Hit@k** — proportion of cases with at least one expected technique ID in the top \(k\) retrieved records.
- **MRR** — reciprocal rank of the first expected technique ID, averaged across cases.
- **Latency** — measured duration for retrieval stages where timing is implemented.

Metrics are reported at Top 1, Top 3, Top 5, and Top 10.

Top 3 is a useful primary quality view because analyst and answer-generation workflows generally inspect only a small candidate set. Top 5 and Top 10 support diagnostic analysis of candidates that are retrieved but ranked too low.

### Retrieval methods compared

The implemented retrieval methods are:

- **Text** — PostgreSQL full-text retrieval over ATT&CK `embedding_text`.
- **Vector** — pgvector cosine-similarity retrieval using normalised `sentence-transformers/all-MiniLM-L6-v2` embeddings.
- **Hybrid** — Reciprocal Rank Fusion over text and vector ranked candidate lists.
- **Vector + reranking** — top 20 vector candidates reordered by a local cross-encoder.
- **Query rewrite + vector + reranking** — LLM-rewritten queries followed by vector retrieval and reranking.

### Implemented benchmark commands

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
```

The reranking benchmark fails if the local reranker cannot load. It does not silently fall back to vector-only retrieval, preventing invalid reranking results from being reported.

### Text, vector, and hybrid findings

Text-only retrieval is a weak lexical baseline on this corpus. Even after loosening score filtering, performance remained near zero on the full 226-case run.

Vector retrieval is substantially stronger than text-only retrieval across all core ranking metrics.

Hybrid retrieval using Reciprocal Rank Fusion is slightly stronger than vector-only retrieval on some metrics, including Recall@1, Recall@3, Hit@3, and MRR. Recall@5 and Recall@10 are identical between the earlier vector and hybrid benchmark runs.

| Method | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Hit@3 | Hit@10 | MRR |
|---|---:|---:|---:|---:|---:|---:|---:|
| Text | 0.0088 | 0.0133 | 0.0133 | 0.0133 | 0.0133 | 0.0133 | 0.0111 |
| Vector | 0.1098 | 0.1940 | 0.2710 | 0.3551 | 0.3540 | 0.5619 | 0.3134 |
| Hybrid | 0.1120 | 0.2029 | 0.2710 | 0.3551 | 0.3628 | 0.5619 | 0.3151 |

The hybrid uplift is real but small. Before document reranking was implemented, vector was selected as the simpler v1 default because hybrid's marginal gain did not justify its added lexical retrieval and fusion complexity.

### Document reranking experiment

A two-stage local reranking configuration was implemented and benchmarked on 2026-08-12.

The pipeline is:

```text
Incident narrative
  → Query embedding with all-MiniLM-L6-v2
  → pgvector cosine-similarity retrieval of top 20 ATT&CK records
  → Cross-encoder scoring of narrative and structured ATT&CK record pairs
  → Return top 10 reranked candidates for benchmark evaluation
```

Configuration:

| Setting | Value |
|---|---|
| First-stage retrieval | Vector retrieval with pgvector cosine similarity |
| Query embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Candidate pool | Top 20 vector candidates |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Reranker execution | Local CPU |
| Reranker document text | Existing structured ATT&CK `embedding_text` |
| Benchmark output depth | Top 10 |
| Production/UI target depth | Top 5 initially |
| Benchmark cases | 226 Expert-derived cases |

The reranker receives the existing `embedding_text` field, which contains the ATT&CK ID, technique name, tactics, platforms, and cleaned ATT&CK description. No additional chunking or database schema migration was required.

### Vector versus reranking results

| Metric | Vector | Vector + cross-encoder reranking | Absolute change |
|---|---:|---:|---:|
| Recall@1 | 0.1098 | 0.1462 | +0.0364 |
| Recall@3 | 0.1940 | 0.2526 | +0.0586 |
| Recall@5 | 0.2710 | 0.3104 | +0.0394 |
| Recall@10 | 0.3551 | 0.3866 | +0.0315 |
| Hit@3 | 0.3540 | 0.4159 | +0.0619 |
| Hit@10 | 0.5619 | 0.5973 | +0.0354 |
| MRR | 0.3134 | 0.3578 | +0.0444 |

Vector-plus-reranking improves every reported ranking metric over vector-only retrieval on the current 226-case evaluation set.

The largest practical gains occur near the top of the ranked list:

- MRR increased from 0.3134 to 0.3578.
- Hit@3 increased from 0.3540 to 0.4159.
- Recall@3 increased from 0.1940 to 0.2526.

These results indicate that reranking improves the order of candidates already found by vector retrieval.

### Reranking latency

The reranking benchmark records query embedding, vector search, reranking, and total retrieval timing.

| Timing metric | Result |
|---|---:|
| Median total retrieval time | 1,254.79 ms |
| P95 total retrieval time | 1,451.74 ms |
| Median reranking time | 1,223.29 ms |
| P95 reranking time | 1,414.23 ms |

CPU reranking is the dominant contributor to end-to-end retrieval latency.

Vector-only latency was not separately instrumented in the current vector benchmark. The reported reranking timings therefore establish the latency of the selected two-stage configuration, but do not yet provide a complete like-for-like vector-only latency comparison.

### Query rewriting experiment

A query-rewriting configuration was implemented and benchmarked on 2026-08-13.

The pipeline is:

```text
Incident narrative
  → LLM query rewriting with gemini-3.1-flash-lite
  → Query embedding with all-MiniLM-L6-v2
  → pgvector cosine-similarity retrieval of top 20 ATT&CK records
  → Cross-encoder scoring of rewritten query and structured ATT&CK record pairs
  → Return top 10 reranked candidates for benchmark evaluation
```

Configuration:

| Setting | Value |
|---|---|
| Query-rewrite model | `gemini-3.1-flash-lite` |
| Query-rewrite prompt | v1 (behaviour-focused, detail-preserving) |
| Rate limiting | 15 requests/minute (default enabled) |
| First-stage retrieval | Vector retrieval with pgvector cosine similarity |
| Query embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Candidate pool | Top 20 vector candidates |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Reranker execution | Local CPU |
| Reranker document text | Existing structured ATT&CK `embedding_text` |
| Benchmark output depth | Top 10 |
| Benchmark cases | 226 Expert-derived cases |

The query rewriter receives the full incident narrative and returns a concise ATT&CK-oriented retrieval query. Prompt instructions direct the model to preserve only behaviours, tools, execution methods, file artefacts, credentials, targets, operating-system details, and network actions explicitly stated in the narrative.

### Vector + rerank versus query rewrite + vector + rerank results

| Metric | Vector + rerank (DEC-018) | Query rewrite + vector + rerank | Absolute change |
|---|---:|---:|---:|
| Recall@1 | 0.1462 | 0.1495 | +0.0033 |
| Recall@3 | 0.2526 | 0.2966 | +0.0440 |
| Recall@5 | 0.3104 | 0.3507 | +0.0403 |
| Recall@10 | 0.3866 | 0.4581 | +0.0715 |
| Hit@3 | 0.4159 | 0.4690 | +0.0531 |
| Hit@10 | 0.5973 | 0.6726 | +0.0753 |
| MRR | 0.3578 | 0.3940 | +0.0362 |

Query rewriting improves all reported ranking metrics over the DEC-018 vector-plus-reranking baseline.

The improvements are most pronounced at deeper cutoffs:

- Recall@10 increased from 0.3866 to 0.4581.
- Hit@10 increased from 0.5973 to 0.6726.
- MRR increased from 0.3578 to 0.3940.

These results indicate that query rewriting helps retrieve additional relevant candidates that were absent from the top 20 vector pool, while also improving the ordering of candidates within the reranked set.

### Query rewriting latency

The query-rewrite benchmark records query rewriting, embedding, vector search, reranking, and total retrieval timing.

| Timing metric | Result |
|---|---:|
| Median total retrieval time | 4,362.28 ms |
| P95 total retrieval time | 12,202.92 ms |
| Median query-rewrite time | 3,183.88 ms |
| P95 query-rewrite time | 10,954.94 ms |

Query rewriting is the dominant contributor to end-to-end retrieval latency, adding approximately 3.1 seconds median latency and up to 11 seconds at P95 compared to the DEC-018 baseline.

Rate limiting at 15 requests/minute worked as expected, with 226 queries completing in approximately 15 minutes of wall-clock time.

### Retrieval decision

Vector retrieval plus local cross-encoder reranking is the selected v1 retrieval configuration.

The selection is based on consistent improvement across Recall@1/3/5/10, Hit@3/10, and MRR relative to vector-only retrieval, combined with acceptable latency for interactive analyst-assist workflows. In the final synced local CPU benchmark run, median total retrieval latency was 1,254.79 ms, p95 total latency was 1,451.74 ms, median reranking time was 1,223.29 ms, and p95 reranking time was 1,414.23 ms.

Query rewriting improved all reported metrics but introduced unacceptable latency (~3.1s median, ~11s P95) for interactive use. It is documented as an evaluated best-practice component (DEC-019) and retained for future re-evaluation under conditions such as lower-latency LLM endpoints, improved prompts, or hybrid retrieval strategies.

Retain text-only, vector-only, hybrid retrieval, and query-rewrite retrieval as implemented baselines and diagnostic tools.

The selected default is documented in DEC-018. It supersedes DEC-015 only for the default v1 retrieval configuration. The query-rewriting evaluation and decision are documented in DEC-019.

### Interpretation and limitations

The results are corpus-specific and benchmark-specific. They do not establish general cyber-security retrieval performance or production readiness.

The current 226-case file contains development- and test-derived cases. It should not be described as a frozen held-out final benchmark.

The reranker cannot recover techniques that are absent from the first-stage top 20 vector candidates. It improves ordering only within the vector candidate pool.

Query rewriting can recover candidates outside the original vector pool by changing the query embedding, but at significant latency cost.

The selected reranker is a compact general-domain MS MARCO cross-encoder. It is an evaluated baseline, not evidence that this is the optimal model for ATT&CK retrieval.

The query-rewriting model (Gemini 3.1 Flash Lite) is an evaluated baseline; alternative models or prompts may yield different quality-latency trade-offs.

ONNX optimisation, GPU execution, reranker-model comparison, candidate-pool-depth tuning, and query-rewrite prompt optimisation are deferred. They are future performance experiments, not required for the current assessed implementation.

---

## Answer quality

### Goal

Determine whether generated answers are concise, useful for analyst review, and grounded in the supplied incident narrative and retrieved ATT&CK records.

### Expected answer behaviour

A good answer should:

- Identify one primary candidate when evidence supports one, and provide a small number of alternatives where warranted.
- Use ATT&CK IDs and names exactly as represented in the retrieved local corpus.
- Explain observable narrative behaviour supporting each candidate.
- Distinguish stated narrative evidence from model inference.
- Refer only to retrieved ATT&CK records as ATT&CK evidence.
- State uncertainty when evidence is incomplete or candidates are ambiguous.
- Remain concise enough for practical analyst review.

### Unacceptable answer behaviour

A failed answer includes one or more of the following:

- Names an ATT&CK technique not included in the retrieved candidate records.
- States technical facts unsupported by the narrative or retrieved ATT&CK evidence.
- Invents malware capabilities, tooling, actor identity, campaign attribution, impact, or incident severity.
- Presents a likely candidate as confirmed activity.
- Treats parent and sub-technique labels as independent evidence when they are only hierarchy-related.
- Produces generic cyber-security explanation without tying it to observed behaviour.

### Initial human-review rubric

Score each category as `0`, `1`, or `2`.

| Category | 0 | 1 | 2 |
|---|---|---|---|
| Candidate validity | Candidate IDs are unsupported or not retrieved | At least one plausible candidate, but notable mismatch or omission | Primary candidate is plausible and supported by narrative behaviour |
| Retrieval grounding | Claims are not tied to retrieved records | Some claims are grounded but support is incomplete | Technique claims and rationale are supported by retrieved records |
| Narrative grounding | Invents or distorts narrative facts | Mostly aligned but contains a minor unsupported inference | Uses only stated narrative evidence and clearly labels inference |
| Uncertainty handling | Overconfident confirmation language | Mixed confidence language | Clearly frames outputs as candidates for analyst review |
| Analyst usefulness | Unclear, generic, or excessively verbose | Understandable but incomplete or poorly prioritised | Concise, structured, and useful for review |

Maximum score: 10.

Record a short reviewer rationale for scores of `0` or `1` so that recurring failure patterns can be analysed.

### Current answer-evaluation status

The answer-generation pipeline is implemented for Expert-derived cases and writes structured outputs to:

```text
data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv
```

Each record includes, at minimum:

- Evaluation case metadata.
- Expected and retrieved ATT&CK IDs.
- Primary, alternative, and supporting ATT&CK IDs.
- Answer summary, retrieval grounding note, and uncertainty note.
- Review-required flag.
- Prompt version, LLM model, and token metadata when available.

Current outputs are suitable for qualitative inspection, checking that generated IDs remain within retrieved context, and designing the final answer-evaluation workflow.

The pairwise LLM-as-judge comparison between `gemini-3.1-flash-lite` and `gemini-3.5-flash-lite` is complete, with judge outputs and agreement metrics integrated into the Streamlit monitoring dashboard (`app/dashboard.py`). All 55 reranked judge-disagreement cases have been manually reviewed blind to model identity and informed the selection of `gemini-3.1-flash-lite` as the v1 default answer-generation model (DEC-021).

A full rubric-scored human evaluation over a frozen held-out external benchmark remains future work. That evaluation will use curation rules frozen on `expert_dev.tsv` and applied to the held-out `expert_test.tsv` split, not the current 226-case implementation-comparison set.

---

## Pairwise LLM-as-judge answer comparison

### Goal

Compare answer-generation models on the 226-case expert-derived set using an automated, repeatable method that works over the DEC‑017 structured outputs, while quantifying how often different LLM judges agree.

### Dataset

- **Source:** Expert-derived incident narratives used for retrieval evaluation.
- **Cases:** 226.
- **Inputs per case:**
  - Incident narrative (`query_text`).
  - Structured answer outputs from:
    - `gemini-3.1-flash-lite`
    - `gemini-3.5-flash-lite`
  - Fields used in judging include `answer_summary` and `retrieved_attack_ids`.

### Judge setup

Implemented in `src/evaluation/run_llm_judge_pairwise.py`:

- For each case:
  - Randomly assign the two model outputs to "Answer A" and "Answer B" (A/B randomisation to reduce position bias).
  - Build a judge prompt that shows:
    - The narrative.
    - Answer A summary and retrieved IDs.
    - Answer B summary and retrieved IDs.
  - Ask the judge to compare along:
    1. Technique relevance.
    2. Evidence grounding in the narrative.
    3. Uncertainty framing.
    4. Actionability for an analyst.
    5. Conciseness.
  - Require step-by-step reasoning, then a JSON verdict:
    - `reasoning`
    - `winner`: `"A"` or `"B"`.
    - `confidence`: `"low"`, `"medium"`, or `"high"`.

- Judges:
  - Run the pairwise judge twice per case:
    - Once with `gemini-3.1-flash-lite` as judge.
    - Once with `gemini-3.5-flash-lite` as judge.
  - Use `src.llm_client.generate_text_answer` for judge calls, which embeds retry and exponential backoff on rate-limit and transient errors.

- Implementation details:
  - Legacy `RateLimiter` references were removed; rate limiting is now handled within `llm_client`.
  - Checkpointing is enabled: partial results are written after each case so runs can resume after quota resets.

### Commands

Judge runs:

```bash
uv run python -m src.evaluation.run_llm_judge_pairwise \
  --input data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv \
  --judge-model gemini-3.1-flash-lite \
  --output data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv

uv run python -m src.evaluation.run_llm_judge_pairwise \
  --input data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv \
  --judge-model gemini-3.5-flash-lite \
  --output data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv
```

Agreement analysis:

```bash
uv run python -m src.evaluation.analyze_judge_agreement \
  --judge-31 data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv \
  --judge-35 data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv
```

### Judge outputs

Per-judge runs produce:

- `data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv`
- `data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv`

Each row includes:

- `eval_id`
- `judge_model`
- `winner` (mapped back to `gemini-3.1-flash-lite` or `gemini-3.5-flash-lite`)
- `reasoning`
- `confidence`
- Token-usage metadata where available.

Agreement analysis produces:

- `data/evaluation_reports/reranked/judge_agreement_summary.csv` — aggregate counts, rates, and per-judge preference distributions.
- `data/evaluation_reports/reranked/judge_disagreements.csv` — the subset of cases where 3.1 and 3.5 disagree as judges.

### Reranked evaluation results (v1)

The authoritative v1 evaluation uses vector retrieval plus local cross-encoder reranking for answer generation.

On the 226-case reranked run:

- **Total cases:** 226
- **Agreement between judges:** 171 / 226 (**75.66%**)
- **Disagreement:** 55 / 226 (**24.34%**)

Judge preferences:

- **3.1-as-judge:**
  - Prefers 3.1 outputs: 153 (67.70%)
  - Prefers 3.5 outputs: 73 (32.30%)

- **3.5-as-judge:**
  - Prefers 3.1 outputs: 142 (62.83%)
  - Prefers 3.5 outputs: 84 (37.17%)

These metrics indicate that:

- LLM judges agree on the better answer in roughly three-quarters of cases.
- Both judges show a consistent tendency to prefer `gemini-3.1-flash-lite` answers on this dataset.

The judge outputs and agreement metrics are visualised in the Streamlit monitoring dashboard (`app/dashboard.py`), which includes charts for:
- Judge agreement rate.
- Judge preferences for each judge model.

### Manual review of disagreements

All 55 reranked disagreement cases were manually reviewed blind to model identity using the Streamlit Evaluation Review workflow.

Manual review results:

- **Reviewed cases:** 55
- **3.1 wins:** 21 (38.2% of all; 56.8% of decisive)
- **3.5 wins:** 16 (29.1% of all; 43.2% of decisive)
- **Ties:** 18 (32.7%)
- **Decisive comparisons:** 37
- **Judge 3.1 agreement with human:** 18 / 37 (48.6%)
- **Judge 3.5 agreement with human:** 19 / 37 (51.4%)

Frequently observed failure modes:

- Inadequate uncertainty handling: 21 cases
- Weak grounding in narrative: 20 cases
- Incorrect technique mapping: 14 cases
- Unsupported or hallucinated technique: 13 cases

The review also identified shared pipeline and dataset-quality issues, including incomplete retrieved context and expected labels that did not always match the narrative. These findings are retained as regression and data-quality candidates; they do not negate the relative model-selection comparison.

A separate vector-only baseline review of 57 judge-disagreement cases also favoured 3.1 (34 vs 14 decisive wins), but was not used for model selection because it does not match the deployed v1 architecture.

The final model-selection decision is documented in DEC-021.

### Interpretation and limitations

- LLM judges are not ground truth; they provide a scalable comparative signal. Cross-judge agreement (~75%) helps quantify reliability but does not eliminate judge bias.
- Both judges favour `gemini-3.1-flash-lite` on this dataset, but without manual review the preference magnitudes should be treated as advisory rather than definitive.
- The 226-case set is an internal expert-derived implementation-comparison set, not a frozen held-out external benchmark.
- Free-tier API limits introduce slow, long-running judge jobs; checkpointing mitigates this but further runs may need adjusted limits or scheduling.
- The manual review covered all 55 reranked disagreements; the 32.7% tie rate indicates substantial practical overlap between the models.

---

## Streamlit monitoring dashboard

### Goal

Provide an interactive interface for:
- Inspecting evaluation metrics and latency distributions.
- Visualising judge preferences and agreement rates.
- Supporting future manual review of disagreement cases.

### Dashboard contents

Implemented in `app/dashboard.py`, the monitoring dashboard currently includes charts for:

1. **Answer-generation latency distribution**
   - Histogram of `latency_seconds` from `expert_llm_comparison_reranked_v1.csv`.
   - Shows median and distribution of answer-generation times across models.

2. **Judge preferences: Gemini 3.5 Flash-Lite as judge**
   - Bar chart of winner counts from `expert_llm_judged_reranked_35_as_judge.csv`.
   - Shows how often 3.5-as-judge prefers 3.1 vs 3.5 outputs.

3. **Judge preferences: Gemini 3.1 Flash-Lite as judge**
   - Bar chart of winner counts from `expert_llm_judged_reranked_31_as_judge.csv`.
   - Shows how often 3.1-as-judge prefers 3.1 vs 3.5 outputs.

4. **Retrieval method comparison**
   - Grouped bar chart of MRR and Hit@3 for:
     - Vector only.
     - Vector + rerank.
     - Query rewrite + vector + rerank.
   - Currently uses hard-coded metrics from DEC-018 and DEC-019; future work can read dynamically from benchmark CSVs.

5. **Judge agreement rate**
   - Pie chart from `judge_agreement_summary.csv`.
   - Shows proportion of cases where 3.1-as-judge and 3.5-as-judge agree vs disagree.

6. **User feedback distribution**
   - Bar chart of thumbs-up vs thumbs-down counts from `data/feedback/feedback.csv`.
   - Displays "No feedback collected yet" if the file is missing or empty.

### Data sources

The dashboard reads from:

- `data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv`
- `data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv`
- `data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv`
- `data/evaluation_reports/reranked/judge_agreement_summary.csv`
- `data/feedback/feedback.csv` (optional)

If a file is missing, the corresponding chart shows an error message or info notice rather than failing the entire dashboard.

### Usage

Run the dashboard via:

```bash
make dashboard
# or
PYTHONPATH=. uv run streamlit run app/dashboard.py --server.fileWatcherType=none
```

The dashboard is also accessible as a tab in the main Streamlit app (`app/home.py`).

### Limitations and future work

- The retrieval-comparison chart currently uses hard-coded metrics; future versions can read dynamically from benchmark CSVs.
- Additional views (e.g. per-case inspection, retrieval diagnostics, disagreement-case browser) can be added as new dashboard pages or tabs.
- Feedback volume is currently limited and should not be treated as a representative measure of answer quality.

---

## External benchmark candidate

### Source

The leading external benchmark candidate is the Expert configuration of Security-TTP-Mapping:

```text
Repository: https://github.com/tumeteor/mitre-ttp-mapping
Configuration: Expert
Files: expert_train.tsv, expert_dev.tsv, expert_test.tsv
Fields: text1, labels
```

The upstream repository remains local and ignored during feasibility work. Raw narratives must not be committed publicly unless redistribution, provenance, and attribution treatment are explicitly resolved.

The exact upstream revision used for the current committed evaluation artefacts is:

```text
Revision: a16856a6438ca2b7888c5cadfba6d7c854f04a55
Licence declared by upstream: CC BY 4.0
```

### Split policy

| Upstream split | Purpose | Use rule |
|---|---|---|
| `expert_train.tsv` | Optional exploratory analysis | Do not use for final evaluation |
| `expert_dev.tsv` | Finalise retrieval settings, curation rules, prompts, answer schema, and rubric | May be used repeatedly during development |
| `expert_test.tsv` | Held-out external evaluation | Do not use to tune retrieval, prompt, model, or curation thresholds |

The Expert test split contains 157 upstream records. It must remain held out until the retrieval configuration, answer contract, curation rules, and review rubric are frozen.

### Label compatibility

A final curated benchmark record is eligible only if every upstream expected ATT&CK ID is active in the project's pinned local Enterprise ATT&CK corpus.

The compatibility script is:

```text
src/evaluation/validate_external_expert_labels.py
```

The current report is:

```text
data/evaluation_reports/expert_label_compatibility.csv
```

Initial validation across Expert train, development, and test splits found:

| Status | Unique label count |
|---|---:|
| Active | 281 |
| Deprecated | 3 |
| Revoked | 6 |
| Absent | 0 |
| Total | 290 |

Four held-out test records contain one or more non-active labels: upstream indices `12`, `17`, `32`, and `130`.

Before additional curation, 153 of 157 Expert test records are compatible with the current active ATT&CK corpus.

Do not automatically remap deprecated or revoked labels. Keep the upstream TSV files unchanged and preserve original label lists, split, row index, and source revision.

### Future curation rules

Final curation rules must be selected using only `expert_dev.tsv`, then frozen and applied mechanically to `expert_test.tsv`.

Potential eligibility rules include:

- Every expected ATT&CK ID is active in the pinned corpus.
- The narrative contains observable technical behaviour.
- The narrative is not primarily vendor boilerplate, campaign history, actor biography, or IOC-only material.
- The narrative does not reveal ATT&CK IDs or explicit mapping language.
- Text-length and label-count thresholds are selected on development data before test use.
- Every inclusion or exclusion receives a recorded reason.

The upstream labels are unordered and multi-label. Do not invent a primary ground-truth label. Preserve upstream labels as a set and use any future reviewed primary label only as a separately documented human-created field.

---

## Evaluation records

### Retrieval record

Store one retrieval result per evaluation case and configuration.

```json
{
  "run_id": "retrieval-2026-08-12-001",
  "eval_id": "external-expert-test-001",
  "corpus_version": "<processed corpus hash or source revision>",
  "attack_release": "<pinned ATT&CK release>",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "retrieval_method": "vector_reranked",
  "candidate_k": 20,
  "top_k": 10,
  "reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
  "retrieved_attack_ids": ["T1105", "T1041", "T1119"],
  "original_vector_ranks":,[1][2][8]
  "reranker_scores": [4.1, 3.7, 3.2],
  "embedding_ms": 0,
  "vector_search_ms": 0,
  "reranking_ms": 0,
  "total_retrieval_ms": 0
}
```

### Answer record

Store one generated-answer record per evaluation case and generation configuration.

```json
{
  "run_id": "answer-2026-08-12-001",
  "eval_id": "external-expert-test-001",
  "retrieval_run_id": "retrieval-2026-08-12-001",
  "llm_model": "<model identifier>",
  "prompt_version": "<prompt version>",
  "generation_parameters": {
    "temperature": 0
  },
  "retrieved_attack_ids": ["T1105", "T1041", "T1119"],
  "primary_attack_id": "T1105",
  "alternative_attack_ids": ["T1041"],
  "supporting_attack_ids": ["T1105", "T1041"],
  "answer_summary": "<generated structured summary>",
  "retrieval_grounding_note": "<how retrieved records support the mapping>",
  "uncertainty_note": "<explicit uncertainty or ambiguity>",
  "review_required": true,
  "human_scores": {
    "candidate_validity": 0,
    "retrieval_grounding": 0,
    "narrative_grounding": 0,
    "uncertainty_handling": 0,
    "analyst_usefulness": 0
  },
  "review_notes": ""
}
```

### Current artefacts

Current retrieval result files include:

- `expert_text_retrieval_results.csv`
- `expert_vector_retrieval_results.csv`
- `expert_hybrid_retrieval_results.csv`
- `expert_vector_reranked_retrieval_results.csv`
- `expert_query_rewrite_retrieval_results.csv` (local, contains external narratives)

Current answer-generation and judge files include:

- `expert_answer_generation_v1.jsonl`
- `expert_answer_generation_v1.csv`
- `expert_llm_judged_31_as_judge.csv`
- `expert_llm_judged_35_as_judge.csv`
- `judge_agreement_summary.csv`
- `judge_disagreements.csv`

Reranked evaluation artefacts (v1):

- `data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv`
- `data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv`
- `data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv`
- `data/evaluation_reports/reranked/judge_agreement_summary.csv`
- `data/evaluation_reports/reranked/judge_disagreements.csv`
- `data/evaluation_reports/reranked/manual_review_results.csv`

These artefacts are committed for marker inspection under DEC-023. They allow the evaluation evidence and dashboard charts to be inspected without rerunning API-bound jobs.

Do not commit reports containing external narrative text unless redistribution permissions have been reviewed. Public artefacts should prefer aggregate metrics, source references, case identifiers or hashes where appropriate, and derived diagnostics that do not reproduce upstream narratives.

---

## Experiment log template

## YYYY-MM-DD — Short experiment title

### Objective

What is being tested?

### Evaluation layer

Retrieval / answer generation / end-to-end / reproducibility.

### Dataset

- Dataset or benchmark name:
- Split:
- Number of eligible cases:
- Excluded cases and reasons:
- ATT&CK corpus release:
- Corpus version or hash:

### Setup

- Retrieval method:
- Candidate pool:
- Returned top-k:
- Search type:
- Embedding model:
- Reranker model:
- Query-rewrite configuration:
- Fusion method:
- LLM model:
- Prompt version:
- Generation parameters:

### Metrics

- Recall@1:
- Recall@3:
- Recall@5:
- Recall@10:
- Hit@3:
- Hit@10:
- MRR:
- Median total retrieval latency:
- P95 total retrieval latency:
- Mean answer-rubric score:
- Grounding failures:
- Unsupported-claim failures:

### Result summary

- What improved?
- What regressed?
- What stayed unclear?

### Decision or follow-up

State whether this is an experiment-specific observation or a stable decision requiring an update to `decisions.md`.

---

## Early evaluation principles

- Prefer grounded evidence over polished wording.
- Evaluate retrieval separately from generation whenever possible.
- Keep simple baselines for comparison.
- Record case-level failures, not only aggregate results.
- Treat plausible but unsupported outputs as failures.
- Preserve the upstream external dataset unchanged.
- Use development data for selection; use held-out test data only after choices are frozen.
- Record corpus version, source revision, embedding model, reranker model, prompt version, candidate pool, top-k, and generation settings for reported experiments.
- Do not report repeatedly tuned development results as general system performance.
- Treat the current 226-case set as an implementation-comparison set, not as a frozen held-out benchmark.
- The public Query interface uses `data/sample_queries.json` for demonstration narratives; it does not load narratives from restricted expert evaluation files.
- The EC2 deployment requires an explicit ingestion step (`docker compose --profile ingest up --build`) before the application database is ready for query use.