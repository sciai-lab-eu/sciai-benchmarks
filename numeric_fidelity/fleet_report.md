# Numeric-fidelity fleet scan — all stored sciaiR reports

Date: 2026-10-10 · gate: `sciai_core.cra.numeric_verification` (deterministic, no LLM) · scanner: `maintenance/numeric_fleet_scan.py` (read-only)

## Sanity gate (meta 163, corrected LIXIPARK report)

- meta 163: 2 candidates → 2 verified / 0 skipped / **0 flagged** (expect ~0 after the 10-10 correction)

## Headline

- Reports scanned: **77**
- Candidate numeric claims: **447**
- Verified: **404** · flagged: **26** · skipped: **17**
- Fidelity over auditable claims (verified / (verified+flagged)): **94.0%**

## Fidelity by pipeline version

| pipeline version | reports | candidates | verified | flagged | skipped | fidelity % |
|---|---|---|---|---|---|---|
| 1.1.0 | 2 | 5 | 5 | 0 | 0 | 100.0 |
| 1.2.0 | 1 | 2 | 2 | 0 | 0 | 100.0 |
| 1.3.0 | 3 | 17 | 16 | 1 | 0 | 94.1 |
| 1.6.0 | 2 | 30 | 29 | 0 | 1 | 100.0 |
| 1.7.0 | 1 | 0 | 0 | 0 | 0 | 100.0 |
| 1.7.1 | 3 | 2 | 2 | 0 | 0 | 100.0 |
| 1.8.0 | 7 | 37 | 30 | 6 | 1 | 83.3 |
| legacy / unstamped | 58 | 354 | 320 | 19 | 15 | 94.4 |

## Flagged claims — worst reports first

| meta | corpus | version | flags | excerpt (pmids; missing tokens) |
|---|---|---|---|---|
| 130 | 154 | legacy | 5 | PMIDs 32285645; missing 0.03: “In a larger 5-year cohort of 423 patients, baseline apathy specifically predicted decline in executive function (β = −0.12, p = 0.03) (PMID: 32285645).”<br>PMIDs 32285645; missing 0.02: “In the 5-year cohort of 423 patients, baseline hallucinations predicted global cognitive decline (β = −0.15, p = 0.02) (PMID: 32285645).”<br>PMIDs 29936131; missing 0.33: “In the PRECODE-1 study of 351 de novo patients, RBD was included in a predictive model but did not show independent statistical significance (OR=1.45, p=0.33) (…”<br>PMIDs 29936131; missing 0.003, 0.13: “In 351 de novo patients, subjective cognitive complaints tripled the odds of early cognitive decline (OR=3.13, 95% CI: 1.47–6.69, p=0.003), with a post-hoc anal…”<br>PMIDs 32925096; missing 0.01: “A cross-sectional study of 100 PD patients found only moderate agreement between patient and clinician impressions of cognitive impairment (kappa=0.45, p<0.001)…” |
| 136 | 150 | legacy | 4 | PMIDs 33103730; missing 0.041, 0.021, 0.012, 1.444: “(PMID: 33103730) **PMID 32334107** found that the GLP1R rs3765467 GG genotype was significantly associated with increased PD risk (OR=1.444, p=0.041) in a Chine…”<br>PMIDs 38677445; missing 0.39, 0.73, 0.54 *(abstract-only flag)*: “(PMID: 38677445) # Epidemiological Evidence PMID 39260107 found that among 86,229 type 2 diabetes patients, GLP-1 agonist treatment was associated with reduced…”<br>PMIDs 39182542, 39919774; missing 0.002 *(abstract-only flag)*: “(PMID: 39182542) ## Clinical Trial Evidence A phase 3 trial demonstrated that GLP-1 receptor agonists significantly slowed motor decline in Parkinson's disease…”<br>PMIDs 40727970; missing -4.8, 2.4, -1.2, 0.51: “## Negative and Null Findings Exenatide once weekly showed no significant difference from placebo in multiple system atrophy patients at 48 weeks (mean differen…” |
| 133 | 155 | legacy | 3 | PMIDs 29936131; missing 0.003: “In a prospective cohort of 351 de novo PD patients, such complaints increased odds of early cognitive decline nearly threefold (OR=3.13, 95% CI 1.47–6.69, p=0.0…”<br>PMIDs 33610074; missing 0.012 *(abstract-only flag)*: “Objective polysomnography data in 49 PD patients confirmed that RBD diagnosis and tonic excessive REM muscle tone significantly predicted greater cognitive decl…”<br>PMIDs 29936131; missing 0.13: “However, in another predictive model, RBD did not reach statistical significance as an independent predictor (OR=1.45, p=0.13) (PMID: 29936131).” |
| 162 | 176 | 1.8.0 | 3 | PMIDs 38598572; missing -1.71, 1.63, 0.96: “The adjusted between-group difference in MDS-UPDRS part III scores at 12 months was −0.04 points (95% CI, −1.71 to 1.63; P=0.96), a point estimate that is essen…”<br>PMIDs 38598572; missing -2.92, -0.12, -1.52, 0.03: “At 6 months, the adjusted between-group difference was −1.52 points (95% CI, −2.92 to −0.12; P=0.03), favoring lixisenatide and reaching nominal statistical sig…”<br>PMIDs 38598572; missing 0.96: “However, by 12 months, this difference had attenuated to −0.04 points and was no longer significant (P=0.96) (PMID: 38598572).” |
| 158 | 170 | 1.8.0 | 2 | PMIDs 23840473; missing 0.55, 0.97: “This beverage-specific effect was corroborated by the NIH-AARP prospective cohort (n=306,997), which identified a significant inverse association for beer consu…”<br>PMIDs 36442208; missing 0.92 *(abstract-only flag)*: “A meta-analysis of 52 studies reported that ever drinkers had a 16% lower PD risk compared to never drinkers (OR 0.84, 95% CI: 0.76–0.92), with a negative dose-…” |
| 90 | 135 | legacy | 1 | PMIDs 32919961; missing 1.05, 1.88, 1.41: “- **Prospective cohort evidence**: A study of 1,113 farmers and spouses found pesticide use associated with incident PD (adjusted OR 1.41, 95% CI: 1.05–1.88) (P…” |
| 99 | 142 | legacy | 1 | PMIDs 27193358, 28554406, 38261451; missing .001 *(abstract-only flag)*: “### 3.2 Technology Integration: Promise Versus Evidence Gap | Aspect | Established Finding | Unresolved Tension | |:---|:---|:---| | Recognition | Sensors and d…” |
| 134 | 150 | legacy | 1 | PMIDs 38598572, 39864104; missing -1.71, 1.63, -2.92, -0.12, -1.52, 0.96, 0.03: “Lixisenatide in early PD (n=156) missed its 12-month primary endpoint (adjusted difference -0.04 points; 95% CI, -1.71 to 1.63; P=0.96), with only a secondary 6…” |
| 135 | 150 | legacy | 1 | PMIDs 38598572; missing -2.92, -0.12, -1.52, 0.03: “However, a secondary analysis at 6 months showed a small benefit (adjusted difference: -1.52 points; 95% CI -2.92 to -0.12; P=0.03) (PMID: 38598572).” |
| 137 | 150 | legacy | 1 | PMIDs 38598572; missing 0.96, 0.03: “The lixisenatide phase 2 trial was technically negative for its primary endpoint at 12 months (p=0.96), though a secondary analysis at 6 months showed a small b…” |
| 139 | 112 | legacy | 1 | PMIDs 28704778, 33945559; missing 0.003: “Similar benefits were observed in a prospective cohort of 120 advanced PD patients, with UPDRS Part III scores improving by 4.2 points (p = 0.003) and OFF time…” |
| 141 | 144 | legacy | 1 | PMIDs 19698841; missing .14 *(abstract-only flag)*: “**Tumor Characteristics and Outcomes** In 509 patients who underwent esophagectomy, adenocarcinoma of the distal esophagus and gastroesophageal junction showed…” |
| 149 | 130 | 1.3.0 | 1 | PMIDs 22491195; missing 0.02 *(abstract-only flag)*: “## Related Movement Disorders (Non-PD) In autosomal dominant cerebellar ataxia and spastic paraplegia, disease progression varied by mutation type: SCA1, SCA2,…” |
| 160 | 172 | 1.8.0 | 1 | PMIDs 17565222; missing 0.3 *(abstract-only flag)*: “Levodopa-treated patients had significantly lower serum folate (p = 0.3) and B12 (p = 0.3) than controls; notably, adding a COMT inhibitor *further reduced* B12…” |

## Methods

- Every `reviews.meta_syntheses` row with non-empty `report_markdown` (>100 chars) was scanned.
- Corpus membership: `reviews.corpus_papers` with `NOT COALESCE(manually_excluded, FALSE)` (the pipeline's convention). Rows without a resolvable corpus fall back to the report's own citation set (marked `report citations (fallback)` in the JSONL).
- Candidate claims: report sentences citing ≥1 corpus PMID that contain a p-value or a confidence interval (`extract_candidate_claims`). Tokens verified: CI bounds, p-values, headline effect/OR/HR/RR values (`verify_claim`) against the stored text (abstract + `ops.chunks` fulltext, 400k-char cap, `load_paper_texts`).
- Verdicts: `verified` (all tokens found in at least one cited paper), `numeric_not_in_source` (≥1 token absent → flag), `skipped` (no tokens, unsettlable inequality-only claims, or no stored text — never a flag).
- Pipeline version parsed from `annotation.version_stamp.pipeline_version` (JSON first, regex fallback for legacy/plain-text annotations).

## Caveats

- **Abstract-only flags**: a flag on a paper WITHOUT an ingested fulltext means the number was checked against the abstract alone — many legitimate results numerics live only in the full text. These are marked `abstract_only: true` in `flags_detail.jsonl` and *(abstract-only flag)* above; read them as 'unverifiable from stored text', not as fabrication evidence. Fulltext-backed flags are the hard findings.
- Multi-citation sentences attribute loosely by design (a token is verified if it appears in ANY cited corpus paper) — precision over recall: real flags can hide when a sister citation carries the same number.
- Stored fulltexts include the legacy path-stub class (2026-09-15 ops.chunks bug): a paper counted as fulltext-backed may effectively have little real text.
- `skipped` is dominated by papers with no stored text and by inequality-only p-claims (p<0.05 without an exact source value); skips are excluded from the fidelity rate.
- The gate checks number PRESENCE, not correctness of context, direction, or estimand (that is the citation-QA / resolver layer).
