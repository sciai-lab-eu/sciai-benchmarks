# Extraction benchmark 500 — FINAL report (2026-09-17)

Protocol: `Planning/20260913_extraction_quality_test_protocol.md`.
Quantitative stage: `extraction_bench500_report_20260914.md` (8/8 models, frozen
500-paper set). Qualitative stage: `qual50_20260915/` package, jk adjudication
707/707 queue items delivered 2026-09-17 (`deliverable_2026-09-17/`), rollup
`qual50_20260915/rollup_qualitative.{md,csv,json}`; independent blind third
opinion by KC-jk-dev (`third_opinion_kc.csv`).

**Status: COMPLETE. This report supersedes the 2026-09-14 provisional
recommendation.**

---

## 1. The qualitative round reverses the content-quality assumption

The quantitative stage could not distinguish "the challenger fills more
because it is better" from "because it hallucinates more". jk's adjudication
answers this: **the challengers hallucinate *less*, not more — and the
incumbent's populated content is the least accurate of the four.**

jk final scores over all 2,117 populated items (0 = wrong/hallucinated,
1 = partial, 2 = correct+grounded):

| Candidate | mean | %0 (wrong) | %2 (fully correct) | entities %2 | relationships %2 |
|---|---|---|---|---|---|
| qwen-2.5-72b (API) | **1.508** | **13.9** | **64.7** | **89.5** | 42.1 |
| deepseek-chat (reference) | 1.493 | 15.5 | 64.8 | 90.2 | **56.1** |
| mistral-small-3.2-24b | 1.456 | 15.2 | 60.8 | 79.6 | 43.5 |
| **qwen3-30b-local (incumbent)** | **1.253** | **23.3** | **48.7** | **70.0** | **29.1** |

The incumbent's quantitative strengths remain real and unmatched: 100% enum
conformance, zero junk keys, best-in-class direction agreement (87.2%). But
what it fills, it fills worst — entities 70% fully correct vs 79.6–90.2% for
challengers; relationships only 29.1% fully correct (54% partial — the
surface-form/endpoint fuzz seen quantitatively is real content weakness, not
just vocabulary difference).

**Robustness:** KC-jk-dev's blind independent scoring of the same 707 queue
items agrees with jk at **92.6%** (1 zero↔two inversion) and produces the
**identical candidate ranking** (deepseek ≈ qwen2.5-72b > mistral-small >
incumbent). The ranking is not a rater artifact.

## 2. Judge quality (protocol §5 litmus, extended)

| Scorer | agreement with jk (queue subset) | 0↔2 inversions |
|---|---|---|
| KC-jk-dev (blind third opinion) | **92.6%** | 1 |
| pre-scorer (deterministic) | 49.5% | 80 |
| LLM judge (local Qwen3-30B, litmus-passed 8/9) | 40.6% | 122 |

The litmus-passed local judge is **not reliable on contested items** (overall
agreement including consensus items: 80.2%) — its role in the package was
correctly limited to pre-filling consensus. KC-jk-dev is near-jk-level on
this rubric and is a viable pre-scorer/adjudicator-prep for future rounds.
jk's own distribution (430×2/229×1/48×0) vs KC (475/178/54): KC is slightly
more lenient.

## 3. Final decision matrix

| Candidate | validity | fill | agreement (quant.) | qualitative (jk) | efficiency | verdict |
|---|---|---|---|---|---|---|
| qwen3-30b local | 496/500, enum 100% | baseline | dir 87.2%, entF1 34.2 | **weakest (23.3% wrong)** | 237 p/h, local, free | replace as baseline |
| mistral-small-3.2-24b | 500/500, enum 84.9% | D1+7.2 D2+5.8 | dir 80.4%, entF1 39.7 | mid (15.2% wrong) | **606 p/h**; AWQ fits 24 GB | **switch candidate** |
| qwen-2.5-72b (32k ctx) | 497/500, enum 83.9% | high | dir 84.5%, entF1 40.8 | **best content (13.9% wrong)** | 297 p/h, API-only | API ceiling probe |
| deepseek-chat (reference) | 500/500, enum 87.3% | high | self-referential row | best relationships | 1,776 p/h, API | stays v4 production |

## 4. Final recommendation

1. **Switch the local v5 baseline from Qwen3-30B-A3B to Mistral-Small-3.2-24B
   (AWQ)** — contingent on a v6 pilot confirming that the two structural
   fixes below hold for it: guided enum decoding (model-independent — this is
   what made the incumbent structurally perfect, not the model itself) and
   top-level key stripping. Expected gain: content quality +~0.2 mean /
   −8pp wrong-rate, throughput 2.5× (606 vs 237 papers/h), same GPU.
2. **v6 schema requirements (unchanged, now evidence-complete):** guided
   decoding mandatory; key stripping; deprecate dead D8 fields; lift
   Mistral's D2 prompting behavior into the prompt.
3. **Do not buy hardware for quality reasons.** The quality frontier at 24 GB
   is Mistral-small-24B; the 48 GB card adds nothing the qualitative round
   justifies. The second 24 GB GPU remains a throughput/ops decision (jk
   2026-09-15: extraction dedicated GPU), not a quality one.
4. **qwen2.5-72b/deepseek stay API-only reference rows.** No API backlog
   clearance (jk, 2026-09-15 — not in a hurry).
5. **Future qualitative rounds:** use KC-jk-dev as blind pre-scorer (92.6%
   agreement) with jk adjudicating only KC-vs-pre conflicts; drop the local
   LLM judge unless a stricter litmus passes (≥9/9, no inversions).

## 5. Caveats carried forward

- Abstract stratum (150 papers) used the incumbent's own v5 rows as
  reference quantitatively — self-referential; the qualitative round is
  stratum-blind and unaffected.
- 55 of 350 frozen fulltexts were path-stub extractions (ops.chunks ingestion
  bug found 2026-09-15) — their bench rows should be scrubbed when the
  quantitative metrics are next recomputed; qualitative items drawn from them
  were adjudicated against abstracts, slightly favoring terse candidates.
- DeepSeek's reference row remains inflated by self-similarity in the
  *quantitative* agreement columns; its qualitative win (entities 90.2%,
  relationships 56.1%) is against jk's ground truth and stands.

## 6. What happens next

- jk decision: confirm the Mistral switch → v6 pilot (guided decoding + key
  stripping on Mistral-small-24B-AWQ over a 50-paper slice) → swap
  `run_v5_baseline.sh` model → re-extraction cadence decision.
- The 24-GB second GPU decision is now purely operational.
