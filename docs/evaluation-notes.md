# Evaluation notes

This document records the design, datasets, metrics, experiments, and results used to evaluate Cyber Threat Identifier.

It covers retrieval and answer generation separately where possible. Stable project-wide design choices belong in [`decisions.md`](decisions.md); source provenance and data-processing details belong in [`dataset-notes.md`](dataset-notes.md); commands for running evaluation belong in [`runbook.md`](runbook.md).

---

## Evaluation goal

Measure whether the system can retrieve and present plausible Enterprise MITRE ATT&CK technique or sub-technique candidates from incident narratives in a way that is useful, evidence-grounded, inspectable, and reproducible.

The system is intended to support analyst review. It does not confirm adversary activity, perform incident triage, assign attribution, or replace human judgement.

---

## Evaluation approach

Evaluation is divided into three layers:

1. **Retrieval evaluation** — whether relevant active ATT&CK records are returned near the top of the candidate list.
2. **Answer evaluation** — whether the generated response makes appropriately bounded claims that are supported by both the incident narrative and retrieved ATT&CK evidence.
3. **Reproducibility evaluation** — whether the same fixed corpus, model configuration, query set, and parameters reproduce comparable outputs.

Retrieval and generation should be evaluated separately because a poor answer can result from either failed retrieval or unsupported generation. Retrieval metrics commonly include recall and ranking measures, while answer evaluation focuses on relevance and faithfulness to retrieved context.

---

## Retrieval quality

### Goal

Determine whether the system retrieves expected active Enterprise ATT&CK technique records within a small candidate set.

### Current benchmark setup

The current implemented retrieval benchmark uses expert-labelled incident narratives and evaluates retrieval against pinned local Enterprise ATT&CK records.

The current retrieval benchmark input file is:

```text
data/eval/expert_retrieval_cases.csv
```

The current benchmark contains 226 evaluation cases.

The same evaluation cases are used to compare text, vector, and hybrid retrieval under the same corpus and top-k settings.

The current retrieval unit is a processed ATT&CK technique or sub-technique record, not a document chunk.

### Candidate metrics

- **Recall@k** — proportion of expected technique IDs present anywhere in the top \(k\) retrieved records.
- **Hit@k** — proportion of evaluation cases with at least one expected technique in the top \(k\) results.
- **MRR** — reciprocal rank of the first expected technique, averaged across eligible cases.
- **Per-label recall** — recall for each expected technique ID across all applicable cases.
- **Parent/sub-technique handling** — record exact-ID matches separately from parent or child matches.
- **Latency** — retrieval duration measured under the recorded local environment and corpus size.

### Reporting levels

Report retrieval metrics at:

- Top 1
- Top 3
- Top 5
- Top 10

Top 3 is the primary candidate set for the analyst-facing result. Top 5 and Top 10 are useful for diagnosing whether relevant techniques are being retrieved but ranked too low.

### Retrieval methods compared

The current implemented retrieval benchmarks compare:

- Text-only retrieval.
- Vector retrieval.
- Hybrid retrieval using Reciprocal Rank Fusion.

### Implemented benchmark commands

Run the current retrieval benchmarks with:

```bash
uv run python -m src.evaluation.run_expert_text_retrieval_benchmark
uv run python -m src.evaluation.run_expert_vector_retrieval_benchmark
uv run python -m src.evaluation.run_expert_hybrid_retrieval_benchmark
```

These commands write:

```text
data/evaluation_reports/expert_text_retrieval_results.csv
data/evaluation_reports/expert_vector_retrieval_results.csv
data/evaluation_reports/expert_hybrid_retrieval_results.csv
```

### Current findings

The current benchmark shows a strong separation between retrieval methods.

Text-only retrieval is a weak lexical baseline on this corpus. Even after loosening the text benchmark to rank candidates and filter on score greater than zero, performance remained near zero on the full 226-case run.

Vector retrieval is a much stronger single-method baseline and clearly outperforms text-only on all core ranking metrics.

Hybrid retrieval using Reciprocal Rank Fusion is **slightly stronger** than vector retrieval on this benchmark: it improves Recall@1, Recall@3, Hit@3, and MRR by small margins, while Recall@5 and Recall@10 are identical between vector and hybrid.

Current benchmark results on 226 evaluation cases:

| Method | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Hit@3 | Hit@10 | MRR |
|---|---:|---:|---:|---:|---:|---:|---:|
| Text   | 0.0088 | 0.0133 | 0.0133 | 0.0133 | 0.0133 | 0.0133 | 0.0111 |
| Vector | 0.1098 | 0.1940 | 0.2710 | 0.3551 | 0.3540 | 0.5619 | 0.3134 |
| Hybrid | 0.1120 | 0.2029 | 0.2710 | 0.3551 | 0.3628 | 0.5619 | 0.3151 |

The hybrid uplift over vector is real but marginal at the current corpus size and query mix, and hybrid adds extra implementation and compute complexity. For v1, the project therefore treats **vector retrieval** as the default backend for ATT&CK candidate retrieval, with text and hybrid retained as evaluated baselines and debugging tools that can be reconsidered as defaults if future lexical improvements or corpus changes increase hybrid’s advantage.

### Interpretation notes

These retrieval results should be treated as corpus-specific and benchmark-specific. They compare first-stage retrieval methods over the current active-technique ATT&CK corpus and the current Expert-derived evaluation set.

The current results do not imply that lexical retrieval is unimportant in general. They indicate that, for this corpus and query set, the present text baseline is much weaker than dense retrieval and does not yet contribute enough high-value candidates to justify hybrid as the default, even though it is slightly stronger than vector on this specific benchmark.

---

## Answer quality

### Goal

Determine whether the generated answer is concise, useful for analyst review, and grounded in the supplied incident narrative and retrieved ATT&CK records.

### Expected answer behaviour

A good answer should:

- Identify one primary candidate and, when warranted, a small number of alternative technique or sub-technique candidates.
- Use ATT&CK IDs and names exactly as represented in the retrieved local corpus.
- Explain the observable narrative behaviour supporting each candidate.
- Distinguish explicit narrative evidence from model inference.
- Refer only to retrieved ATT&CK records as ATT&CK evidence.
- State uncertainty when the narrative is incomplete or the candidate set is ambiguous.
- Remain concise enough for practical analyst review.

### Unacceptable answer behaviour

A failed answer includes one or more of the following:

- Names an ATT&CK technique not included in the retrieved candidate records.
- States a technical fact not supported by the narrative or retrieved ATT&CK evidence.
- Invents malware capabilities, tooling, actor identity, campaign attribution, impact, or incident severity.
- Presents a likely candidate as confirmed activity.
- Provides broad remediation, detection, or incident-response advice not requested by the user.
- Treats a parent technique and sub-technique as independent evidence when one is simply a hierarchy relationship.
- Produces verbose generic cyber-security explanation without tying it to the observed behaviour.

### Initial human-review rubric

Score each category as `0`, `1`, or `2`.

| Category | 0 | 1 | 2 |
|---|---|---|---|
| Candidate validity | Candidate IDs are unsupported or not retrieved | At least one plausible candidate, but notable mismatch or omission | Primary candidate is plausible and supported by narrative behaviour |
| Retrieval grounding | Claims are not tied to retrieved records | Some claims are grounded but support is incomplete | Technique claims and rationale are supported by retrieved records |
| Narrative grounding | Invents or distorts narrative facts | Mostly aligned but contains a minor unsupported inference | Uses only stated narrative evidence and clearly labelled inference |
| Uncertainty handling | Overconfident confirmation language | Mixed confidence language | Clearly frames outputs as candidate techniques for analyst review |
| Analyst usefulness | Unclear, generic, or excessively verbose | Understandable but incomplete or poorly prioritised | Concise, structured, and actionable for review |

Maximum score: 10.

Record a short reviewer rationale for every score of `0` or `1` so recurring failure patterns can be analysed.

### Current answer-evaluation status

Retrieval benchmarking is implemented and running.

Answer-generation evaluation design is defined, but full answer-generation benchmarking and scored human-review runs are still pending.

---

## External benchmark candidate

### Source

The leading candidate external benchmark is the **Expert** subset of the public Security-TTP-Mapping repository:

```text
Repository: https://github.com/tumeteor/mitre-ttp-mapping
Configuration: Expert
Files: expert_train.tsv, expert_dev.tsv, expert_test.tsv
Fields: text1, labels
```

The source describes Expert examples as selected threat-report paragraphs annotated by security experts. The repository README declares a Creative Commons CC BY 4.0 licence for the project, but individual original threat-report sources and their redistribution terms are not itemised. The full upstream repository therefore remains local and ignored during feasibility work.

### Split policy

| Upstream split | Purpose | Use rule |
|---|---|---|
| `expert_train.tsv` | Optional exploratory analysis only | Do not use for final evaluation |
| `expert_dev.tsv` | Finalise curation rules, answer format, prompts, and rubric | May be used repeatedly during development |
| `expert_test.tsv` | Held-out external evaluation | Do not use to tune retrieval, prompt, model, or curation thresholds |

The test split contains 157 upstream records. It must remain held out until the retrieval configuration, answer contract, curation rules, and human-review rubric are frozen.

### Technical suitability

Initial local inspection found that the Expert test data contains short threat-report passages paired with multi-label ATT&CK technique or sub-technique IDs.

The test split is suitable for later full-system evaluation because:

- It contains externally supplied labels rather than project-authored expected answers.
- The narrative text did not contain explicit ATT&CK IDs.
- The narrative text did not contain explicit MITRE or ATT&CK mapping phrases.
- No exact or substring overlap was found between Expert test narratives and the repository's procedure-example split.
- The records contain realistic multi-label ambiguity, which is useful for evaluating candidate ranking and cautious answer generation.

The dataset is not yet a final benchmark. It requires frozen compatibility and curation rules before use.

---

## Label compatibility

### Corpus compatibility rule

A benchmark record is eligible only when **every upstream expected ATT&CK ID is active in the project's pinned local Enterprise ATT&CK corpus**.

Records containing a deprecated, revoked, or absent expected label are excluded from the curated benchmark. The original upstream TSV files must never be edited.

### Validation artefact

Label compatibility is validated by:

```text
src/evaluation/validate_external_expert_labels.py
```

The script compares Expert labels against local Enterprise ATT&CK `attack-pattern` objects and classifies each label as:

- `active`
- `deprecated`
- `revoked`
- `absent`

The output report is:

```text
data/evaluation_reports/expert_label_compatibility.csv
```

### Initial validation result

The initial compatibility check across all Expert train, development, and test splits found:

| Status | Unique label count |
|---|---:|
| Active    | 281 |
| Deprecated| 3   |
| Revoked   | 6   |
| Absent    | 0   |
| Total     | 290 |

The initial compatibility check identified four held-out Expert test records containing one or more non-active expected labels:

```text
12
17
32
130
```

Therefore, before additional curation, 153 of 157 test records are compatible with the current active Enterprise ATT&CK corpus.

No automatic remapping of revoked or deprecated labels will be performed. A newer ATT&CK identifier may represent a changed hierarchy or a more specific interpretation than the original external annotation; replacing labels would introduce project-authored ground truth.

---

## Future benchmark curation

### Purpose

Create a small, high-signal, externally labelled benchmark for end-to-end evaluation after retrieval and answer-generation design is stable.

### Proposed eligibility rules

A candidate Expert record should be retained only if it:

- Comes from the appropriate upstream split for its intended use.
- Contains only active expected ATT&CK IDs in the pinned local corpus.
- Contains observable technical behaviour in the narrative.
- Has sufficient context for a bounded analyst-facing explanation.
- Is not primarily vendor boilerplate, campaign history, actor biography, or an IOC-only statement.
- Does not reveal ATT&CK IDs or explicit mapping language in the narrative text.
- Meets frozen text-length and label-count rules established using `expert_dev.tsv`.

### Proposed initial thresholds

These thresholds are starting points only and must be validated on the development split before they are applied to the held-out test split:

- Normalised narrative length: 30 to 200 words
- Expected active label count: 1 to 4
- No non-active expected labels
- Manual content-type review: behavioural narrative required

### Required benchmark metadata

Each retained case should preserve provenance and selection decisions. Do not create this final benchmark file until redistribution/provenance treatment is settled.

```json
{
  "case_id": "external-expert-test-001",
  "dataset_name": "Security-TTP-Mapping",
  "dataset_configuration": "Expert",
  "upstream_repository": "https://github.com/tumeteor/mitre-ttp-mapping",
  "upstream_revision": "<git commit hash>",
  "upstream_split": "test",
  "upstream_row_index": 0,
  "narrative": "<original narrative if redistribution is permitted>",
  "upstream_expected_attack_ids": ["T1105", "T1113"],
  "local_attack_release": "<pinned ATT&CK release>",
  "word_count": 0,
  "label_count": 0,
  "selection_status": "included",
  "selection_reason": "All labels active; behavioural narrative; passes frozen rules"
}
```

### Primary-label policy

The upstream labels are unordered and do not provide a verified primary technique.

Do not add a `primary_attack_id` field merely for convenience. If a focused primary-candidate benchmark is later needed, create a separate explicitly human-reviewed field:

```json
{
  "reviewed_primary_attack_id": "T1105",
  "reviewed_primary_label_rationale": "..."
}
```

The original upstream label list must always remain preserved separately as `upstream_expected_attack_ids`.

---

## Evaluation records

### Retrieval result record

Store one retrieval record per evaluation case and retrieval configuration:

```json
{
  "run_id": "retrieval-2026-07-30-001",
  "eval_id": "external-expert-test-001",
  "corpus_version": "<processed corpus hash or source revision>",
  "attack_release": "<pinned ATT&CK release>",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "retrieval_method": "vector",
  "search_type": "exact_cosine",
  "top_k": 5,
  "expected_attack_ids": ["T1105", "T1113"],
  "retrieved_attack_ids": ["T1105", "T1041", "T1119", "T1059", "T1083"],
  "retrieval_latency_ms": 0
}
```

### Answer result record

Store one generated-answer record per evaluation case and generation configuration:

```json
{
  "run_id": "answer-2026-07-30-001",
  "eval_id": "external-expert-test-001",
  "retrieval_run_id": "retrieval-2026-07-30-001",
  "llm_model": "<model identifier>",
  "prompt_version": "<prompt version>",
  "generation_parameters": {
    "temperature": 0
  },
  "retrieved_attack_ids": ["T1105", "T1041", "T1119"],
  "answer": "<generated answer>",
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

### Current retrieval artefacts

The current implemented retrieval benchmark produces method-specific result files in:

```text
data/evaluation_reports/
```

Current retrieval artefacts include:

- `expert_text_retrieval_results.csv`
- `expert_vector_retrieval_results.csv`
- `expert_hybrid_retrieval_results.csv`

---

## Initial benchmark plan

A small internal benchmark remains useful for early debugging and tightly controlled checks, but the current implemented retrieval benchmark is:

```text
data/eval/expert_retrieval_cases.csv
```

If a separate internal benchmark is maintained, store it in:

```text
data/eval_questions.csv
```

Suggested columns:

- `eval_id`
- `incident_narrative`
- `expected_techniques`
- `expected_tactics`
- `notes`
- `source_type`
- `difficulty`

The initial internal benchmark should contain approximately 10 to 25 reviewed narratives. It is intended for basic pipeline checks and early retrieval debugging, not for final performance claims.

The external Expert development split should later replace internal examples as the main source for selecting curation rules and answer-evaluation design. The external Expert test split is reserved for the final held-out evaluation.

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
- Search type: exact cosine / HNSW / text / hybrid
- Embedding model:
- Embedding text version:
- Fusion method:
- Chunking strategy:
- Top-k:
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
- Mean answer-rubric score:
- Grounding failures:
- Unsupported-claim failures:
- Median retrieval latency:

### Result summary

- What improved?
- What regressed?
- What stayed unclear?

### Example failure cases

- Evaluation case:
- Expected IDs:
- Retrieved IDs:
- Generated answer issue:
- Likely cause:
- Proposed response:

### Decision or follow-up

What should change next? State whether this is an experiment-specific observation or a stable design decision that must also be added to `decisions.md`.

---

## Early evaluation principles

- Prefer grounded evidence over polished wording.
- Evaluate retrieval separately from generation whenever possible.
- Keep a simple baseline for comparison.
- Record failure cases, not only aggregate results or successful examples.
- Treat plausible but unsupported outputs as failures.
- Preserve the upstream external dataset unchanged.
- Use development data for choices; use held-out test data only after choices are frozen.
- Record corpus version, source revision, embedding model, prompt version, top-k, and generation settings for every reported result.
- Do not report a result as general system performance if it was repeatedly used to tune the system.