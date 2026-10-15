# sciai-benchmarks

**How sciai-lab measures its own extraction quality.** Every model or schema
that enters the production pipeline is benchmarked first; the harnesses and
reports are public so the numbers can be checked.

## Contents

- `bench500/` — the extraction-model benchmark: a frozen 500-paper set
  (350 full-text + 150 abstract-only), the runner, and the final report
  (8 models compared; structural validity, content correctness, direction
  agreement; expert adjudication of 2,117 items).
- `adversarial/` — the expert-labeled adversarial case set (known-truth cases
  incl. polarity traps, sign conventions, entity-split tripwires) used as a
  release gate.
- `numeric_fidelity/` — deterministic verification that every number in a
  generated report appears in its cited source (fleet scan over all stored
  reports).

## Why

Literature-extraction quality is usually asserted, not measured. These
benchmarks are how we decide which model runs in production, and how we catch
regressions when anything changes. The reports include the failures.
