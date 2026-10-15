# Adversarial benchmark v1 — seeding notes (2026-10-10)

Spec: `Planning/20261010_adversarial_benchmark_spec.md` §2. All ground truth was
taken from the live DB on 2026-10-10 (pubmed.papers abstracts, kg.assertions,
kg.entity_synonyms, reviews.corpus_papers) — nothing from memory. 37 cases
(spec: 30–50). Per category:

| Category | Cases | Spec range |
|---|---|---|
| exact_pmid | 8 | 6–8 |
| synonyms | 7 | 6–8 |
| primary_vs_review | 7 | 6–8 |
| null_vs_negative | 5 | 4–6 |
| other_disease_traps | 5 | 4–6 |
| notices | 5 | 4–6 |

## exact_pmid (AB-EP01…08)

Seeded: LIXIPARK 38598572 (mandated), cinpanemab SPARK 35921450, isradipine
STEADY-PD III 32227247, inosine SURE-PD3 34519802, prasinezumab PASADENA
35921451, ambroxol AiM-PD 31930374, SPARX exercise 29228079, EARLYSTIM DBS
23406026. Subfield spread: GLP-1, immunotherapy ×2, calcium channel, metabolic,
GBA pathway, exercise, DBS.

Verified: every number in the expected verdicts quoted from the stored abstract
(full abstract text read, not just the results sentence) — incl. LIXIPARK's
3.08 / CI 0.86–5.30 / P=0.007 (the corrected values), SPARK's per-dose
changes and P values, PASADENA's 80% CIs, AiM-PD's CSF numbers + open-label
design, EARLYSTIM's PDQ-39 7.8 vs 0.2 / 8.0 / P=0.002. All 8 papers exist in
pubmed.papers with RCT pub_types and hold 8–10 kg.assertions each.

Not verified / caveats:
- Assertion *content* of these papers was counted, not audited line by line
  (the cases test the answer layer; abstract numbers are the yardstick).
- EARLYSTIM has three NEJM letters (23697520-22) sharing the title — noted in
  gold_notes; a retrieval that returns a letter instead of the trial should
  fail the case.

## synonyms (AB-SY01…07)

Seeded: levodopa/L-DOPA (D007980), Sinemet (C009265), alpha-synuclein split
(D051844 vs P37840 — KNOWN-FAIL tripwire), LID merged family
(CLU:levodopa-induced-dyskinesia), H&Y consolidated (SELF:hoehn and yahr
stage), LRRK2 gene/protein split (HGNC:18618 vs Q5S007 — known-split), and
"dardarin" false-absence trap (→ Q5S007).

Verified: synonym registrations read from kg.entity_synonyms for every family;
assertion/paper counts recomputed (D007980: 14,485/9,245; D051844:
14,838/5,281; P37840: 26,115/12,011; LID: 2,475/909; H&Y: 3,056/2,794;
HGNC:18618: 4,901/2,681; Q5S007: 2,679/784; C009265: 415/296). The
levodopa→LID edge is 486 positive / 1 negative; the single negative is a
genuine hemiparkinsonian-monkey negation, not a sign deviation (context read).

Not verified / caveats:
- The two KNOWN-SPLIT cases (SY03, SY06) are expected to FAIL until the
  code-preserving merge lands — they are regression tripwires, and the expert
  should ratify them as such rather than "fix" the expectation.
- The treats sign convention (negative = benefit) underlies SY01's expected
  verdict; the convention itself is asserted from the 2026-09-24 fix plus
  3 sample contexts read, not re-audited over all 3,174 rows.

## primary_vs_review (AB-PV01…07)

Seeded: the GLP-1/PD trial-vs-review mix from corpus 150 — the four PD RCTs
(28781108, 38598572, 38101901, 39919773), the post-hoc non-motor analysis
29843254 (pub_type trap: tagged Randomized Controlled Trial while being a
post-hoc reuse), the network meta-analysis 40189519 (the meta-152 HR=0.72
fabrication target), and the independent-evidence counting case.

Verified: corpus 150's pub_type composition recomputed from the DB (6
RCT-tagged = 4 PD trials + MSA trial 40727970 + post-hoc 29843254; ~90
Review-tagged). All trial numbers re-verified from abstracts. 40189519's
abstract states verbatim that GLP-1 RAs showed NO significant preventive
effect and only dapagliflozin was significant (OR 0.28, CI 0.09–0.93).

Not verified / caveats:
- "~90 reviews" is a pub_type count (Review-tagged rows in corpus 150);
  individual reviews were not read.
- 29843254's numbers (PDQ-39 emotional well-being 5.7, P=0.047; NMSS −1.7,
  P=0.071) come from the stored abstract tail; the full abstract was only
  partially stored in the output I read (rightmost 700 chars) — the two
  quoted values are verbatim from that excerpt.

## null_vs_negative (AB-NN01…05)

Seeded: NLY01 38101901 and Exenatide-PD3 39919773 (mandated), plus isradipine
32227247, inosine 34519802, and the two anti-α-synuclein antibodies
(35921450 + 35921451) as one thematic case.

Verified: null statistics from abstracts (NLY01 −0.39/p=0.77 and
+0.36/p=0.79; Exenatide-PD3 0.92/CI −1.56–3.39/p=0.47; isradipine −0.27/
P=0.85; inosine 1.26/P=.18 futility stop). KG state checked: NLY01 and
Exenatide-PD3 both store treats→PD as 'negative' with null-result contexts
("no improvement was found" / "no significant effect was found") — the
sign-convention trap is documented in gold_notes.

Not verified / caveats:
- The KG's stored 'negative' sign on genuine nulls is a *known convention
  collision* (treats: negative = benefit by convention; here the context is a
  null). The cases demand context-driven wording; whether the current answer
  layer can do that is exactly what they measure. The expert should not
  "correct" the expected verdict into the stored-sign reading.

## other_disease_traps (AB-OD01…05)

Seeded: MSA exenatide trial 40727970 (positive there: −7.4 UMSARS,
p=0.0003 — mandated), stroke/AD-models review 35805109 (mandated),
liraglutide Alzheimer's phase 2b 41326666 (null primary, nominally positive
secondary), essential-tremor DBS 37187082, and the UMSARS-vs-MDS-UPDRS
scale/disease mismatch framing of 40727970.

Verified: 40727970 abstract (MSA, 50 participants, UMSARS outcome); its KG
treats edge is correctly disease-scoped to D019578 (MSA). 35805109's 9
assertions read individually — oxidative-stress claim is stroke-model, the
amyloid/tau claims are AD-model. 41326666 abstract tail read (primary P=0.14
null; ADAS-Exec 0.15 unadjusted P=0.01). 37187082's assertions target
D014202 (Tremor), not PD.

Not verified / caveats:
- 41326666's abstract was read from the tail excerpt (rightmost 900 chars);
  the null-primary + nominal-secondary structure is from that excerpt.
- 40727970 sits INSIDE corpus 150 (GLP-1/PD corpus) — the trap is realistic,
  but it also means a "corpus-pure" retrieval will surface it legitimately;
  the pass criterion is disease labeling, not exclusion.

## notices (AB-NT01…05)

Seeded: EoC 42330995 on Exenatide-PD3 (mandated), retracted Exendin-4 rodent
paper 22774922 (a member of corpus 150), retracted zonisamide meta-analysis
36132085 (with retraction notice 38229985), retracted STN-DBS gait letter
39390222, retracted STN-volume clinical trial 33708991.

Verified: all five are pub_type-tagged (Expression of Concern / Retracted
Publication) and all five hold ZERO kg.assertions after the 2026-10-10 purge
(queried individually). 42330995 has an empty abstract (typical for notices).
Non-retracted zonisamide alternatives confirmed (RCT 38376645; canonical
D000078305 with 732 assertions).

Not verified / caveats:
- Whether 39919773's own 9 clinical_trial assertions should also be
  quarantined (they currently remain) is a pending jk decision (labeled-reuse
  vs quarantine); NT01 only demands the EoC never be cited as evidence and
  that the status be surfaced — it deliberately does not prejudge the trial
  paper's own rows.
- The zonisamide case's positive half (what the correct answer *should* say)
  is not number-pinned; only the exclusion of the retracted meta-analysis is
  scored.

## Global caveats

- All 29 PMIDs referenced anywhere in the case set were verified present in
  pubmed.papers (programmatic check in the build script; none missing).
- Graph state at freeze: kg.assertions = 1,094,362; kg.edge_summaries =
  770,465; pubmed.papers = 359,345 (graph_state.json + cases sha256).
- Case rot: the KG grows weekly; synonym/canonical counts in gold_notes will
  drift — that is expected and is what graph_state.json + quarterly
  re-ratification are for.
- Single-seeder labels (KC); expert ratification pass via cases_review.html
  is the correction step per spec §4.
