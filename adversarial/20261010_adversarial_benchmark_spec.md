# Adversarial retrieval & answer benchmark — spec v1 (2026-10-10)

**Origin:** Luca Pisano's platform audit (2026-10-09/10), priority P1:
"Benchmark 30–50 expert-labeled PD cases across search, extraction,
synthesis, KG Ask, graph contests, synonyms and corrections. Score recall,
numeric fidelity, source attribution and false absence claims." Method
authorship: Luca. Build + automation: KC. Expert labeling: jk / Thomas /
Luca (any one or split — the load is ~3–4 hours total, see §4).

**Purpose.** bench500 measured extraction quality against source text. This
benchmark measures the *user-facing answer layer* — the failure surface the
audit actually exposed (a primary trial missed at retrieval then claimed
absent; an Expression of Concern cited as trial evidence; sign deviations
presented as controversy). It runs on every release as a regression
scorecard, and its results are publishable as the platform's
self-measurement evidence.

## 1. Scope

Four surfaces, exercised end-to-end against the live system:

1. **KG Ask** (the audit's finding 4) — retrieval coverage + answer wording.
2. **Corpus search/screening** — keyword/semantic retrieval + pubtype
   filters, as exposed in the corpus builder.
3. **Contested-claims view** — does a case's known claim appear contested
   only when genuinely bidirectional (post deviation-guard)?
4. **Small CRA** — one per run over a fixed micro-corpus (5–8 papers with
   known contents), checked for numeric fidelity and absence phrasing.

## 2. The case set (30–50 cases)

Six categories, each seeded from cases where the ground truth is in our own
data — several taken directly from the audit:

| Category | n | Construction | Pass criterion (auto-scorable parts) |
|---|---|---|---|
| Exact-PMID | 6–8 | questions naming a specific PMID whose correct answer we hold (incl. LIXIPARK 38598572) | seeded paper in retrieved set; answer quotes the source-verified numbers |
| Synonyms | 6–8 | spelling/abbreviation families adjudicated in Sept–Oct (L-DOPA/levodopa/Sinemet; α-synuclein/alpha-synuclein; LID variants) | both spellings reach the same canonical evidence |
| Primary vs review | 6–8 | topics with known primary-trial vs review mixes (GLP-1 trials) | primary studies named as such; reviews never counted as independent evidence |
| Null vs negative | 4–6 | genuine null trials (NLY01 38101901; Exenatide-PD3) | "no effect found", never "negative effect"; statistical-null vs effect-direction kept apart |
| Other-disease traps | 4–6 | cases whose retrieval surface includes non-PD models (stroke model 35805109; MSA trial 40727970) | not presented as PD evidence |
| Notices | 4–6 | questions touching Exenatide-PD3 (EoC 42330995) and a retracted paper | notice never contributes trial evidence; status shown beside the affected trial |

Case file (JSONL): `case_id, category, question, must_find_pmids[],
forbidden_claims[], expected_verdict (free text), gold_notes, seed_source`.
Frozen like bench500: the case set + a recorded graph-state hash
(assertions count + kg.edge_summaries count) so later runs can detect case
rot when the graph grows underneath.

## 3. Harness

Same shape as `maintenance/extraction_bench500.py` (freeze / run / status),
quarantined outputs under `eval_reports/adversarial_benchmark_<date>/`:

- **freeze**: write cases.jsonl + graph-state hash.
- **run**: execute each case against the live surfaces (KG Ask via
  `kg/answer_engine.py`; search via the corpus-builder retrieval path;
  contested via `trackb_queries.contested_claims`; one CRA via the worker
  on the fixed micro-corpus). Metered LLM wrapper (the bench's pattern);
  expected cost ~$1–2 per full run.
- **score**: deterministic scorers first — (a) must-find PMIDs present in
  retrieved set; (b) every numeric claim in the answer passes the
  numeric-fidelity gate (cra/numeric_verification.py, v1.9.0); (c) absence
  claims phrased scoped ("not among the N retrieved") — regex on the
  mandated patterns; (d) forbidden claims absent. The residual
  answer-quality judgment goes to the expert.

## 4. Expert labeling protocol (the human bottleneck, minimized)

Two passes, both in the HTML adjudication form (`maintenance/
review_form_html.py`, the tool used for the canonicalization rounds):

1. **Case ratification** (~1–2 min/case): KC pre-fills expected answers
   from the data; the expert accepts/corrects each case. Catches cases
   whose "known truth" is itself wrong before they become the yardstick.
2. **Answer adjudication** (~2–3 min/flagged case): the auto-scorer
   pre-judges; the expert reviews only flagged or uncertain answers.

Any of jk/Thomas/Luca can hold either pass; splitting is fine. Luca's time
is optional — the method is credited to him.

## 5. Acceptance thresholds (feed the Stage-3 product gate)

- Seeded-PMID recall: 100% when the PMID is named in the question.
- False graph-wide absence claims: 0.
- Numeric-fidelity: every numeric claim source-verified or flagged
  pre-release; unresolved `numeric_not_in_source` on clinical-trial papers
  blocks release.
- Contested flags on the seeded deviation traps: 0 false contests.
- Scorecard per release: `eval_reports/adversarial_benchmark_<date>/scorecard.md`
  with per-category rates, comparable across pipeline versions.

## 6. Calendar & cost

- Day 1–3: case set seeded from data + harness built (KC, background).
- Day 4–7: expert case ratification (form in the tailnet share).
- Week 2: first full run + adjudication + scorecard v1 → Stage-3 decision.
- Cost: ~$1–2 API per run; no GPU.

## 7. Risks / honest limits

- **Case rot**: the graph grows weekly; the graph-state hash + must-find
  PMIDs make rot detectable, cases get a re-ratification each quarter.
- **Label noise**: single-expert labels per case (mitigate: KC pre-fill +
  spot double-labeling of 10% by a second expert).
- **Coverage**: 50 cases cannot prove correctness; they catch regressions
  on the failure classes we have SEEN. New audit findings become new cases
  — the set grows with every incident.
