#!/usr/bin/env python3
"""Stage-1 fleet scan: numeric-fidelity audit over ALL stored sciaiR reports.

jk order 2026-10-10 ("under scrutiny"): measure how many numeric claims
(p-values / confidence intervals / effect sizes) in the stored
``reviews.meta_syntheses.report_markdown`` reports cannot be found in the
cited papers' stored text, using the deterministic gate
``sciai_core.cra.numeric_verification`` (no LLM).

READ-ONLY: this script never writes to any database.  Outputs land in
``/55a11/eval_reports/numeric_fidelity_fleet_20261010/``:

- ``fleet_scan.jsonl``  — one row per report (counts + pipeline version)
- ``flags_detail.jsonl`` — one row per flagged claim (pmid, missing tokens,
  160-char sentence excerpt, abstract-only marker)
- ``fleet_report.md``    — human summary (per-version rates, worst reports,
  methods + caveats)

Manual run:
    /55a11/sciai/.venv/bin/python /55a11/maintenance/numeric_fleet_scan.py
    /55a11/sciai/.venv/bin/python /55a11/maintenance/numeric_fleet_scan.py --meta-id 163
    /55a11/sciai/.venv/bin/python /55a11/maintenance/numeric_fleet_scan.py --limit 5
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from sciai_automation_lib import (
    LOG_DIR,
    ensure_sciai_next_on_path,
    load_dotenv_repo,
    setup_logging,
)

ensure_sciai_next_on_path()
load_dotenv_repo()

import os

os.chdir(SCRIPT_DIR.parent)  # resolve /55a11/.env for db connection

from sciai_core.cra.numeric_verification import (
    _CLUSTER_FOLLOWON_RE,
    CITATION_RE,
    extract_candidate_claims,
    load_paper_texts,
    verify_claim,
)
from sciai_core.db.connection import get_connection

LOGGER = setup_logging("numeric_fleet_scan", LOG_DIR / "numeric_fleet_scan.log")

OUT_DIR = Path("/55a11/eval_reports/numeric_fidelity_fleet_20261010")
DEFAULT_DB = "sciai"
EXCERPT_CHARS = 160


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def parse_pipeline_version(annotation: str | None) -> str | None:
    """Pipeline version from the meta annotation (JSON or legacy text)."""
    if not annotation:
        return None
    text = annotation.strip()
    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            stamp = payload.get("version_stamp")
            if isinstance(stamp, dict) and stamp.get("pipeline_version"):
                return str(stamp["pipeline_version"])
    # legacy plain text or partially broken JSON: last resort regex
    m = re.search(r'"pipeline_version"\s*:\s*"([^"]+)"', text)
    return m.group(1) if m else None


def cited_pmids_in_report(report_markdown: str) -> set[str]:
    """All PMIDs cited in the report (direct + cluster follow-ons)."""
    pmids: set[str] = set()
    for m in CITATION_RE.finditer(report_markdown or ""):
        pmids.add(m.group(1))
        end = m.end()
        while True:
            follow = _CLUSTER_FOLLOWON_RE.match(report_markdown, end)
            if not follow:
                break
            pmids.add(follow.group(1))
            end = follow.end()
    return pmids


def fetch_reports(db_name: str, meta_id: int | None, limit: int | None) -> list[dict[str, Any]]:
    sql = """
        SELECT meta_id, corpus_id, report_markdown, annotation, llm_provider, llm_model, created_at
        FROM reviews.meta_syntheses
        WHERE report_markdown IS NOT NULL AND length(report_markdown) > 100
    """
    params: list[Any] = []
    if meta_id is not None:
        sql += " AND meta_id = %s"
        params.append(meta_id)
    sql += " ORDER BY meta_id"
    if limit:
        sql += " LIMIT %s"
        params.append(limit)
    with get_connection(db_name) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def fetch_corpus_pmids(db_name: str, corpus_id: int | None) -> set[str]:
    """Corpus members with the pipeline's convention (manual exclusions out)."""
    if corpus_id is None:
        return set()
    with get_connection(db_name) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT pmid::text FROM reviews.corpus_papers
            WHERE corpus_id = %s AND NOT COALESCE(manually_excluded, FALSE)
            """,
            (corpus_id,),
        )
        return {str(r[0]) for r in cur.fetchall()}


def fetch_fulltext_map(db_name: str, pmids: list[str]) -> dict[str, bool]:
    """pmid -> has ingested fulltext (same predicate as the CRA delta stage)."""
    if not pmids:
        return {}
    with get_connection(db_name) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.pmid::text, EXISTS (
                SELECT 1 FROM ops.fulltexts f
                WHERE f.pmid = p.pmid AND f.imported = true
                  AND f.kind IN ('fulltext_pdf', 'fulltext_html')
            )
            FROM pubmed.papers p WHERE p.pmid = ANY(%s::text[])
            """,
            (pmids,),
        )
        return {str(pmid): bool(has_ft) for pmid, has_ft in cur.fetchall()}


# ---------------------------------------------------------------------------
# per-report scan
# ---------------------------------------------------------------------------

def scan_report(db_name: str, row: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    meta_id = int(row["meta_id"])
    corpus_id = row["corpus_id"]
    report = row["report_markdown"]
    version = parse_pipeline_version(row.get("annotation"))

    corpus_pmids = fetch_corpus_pmids(db_name, corpus_id)
    corpus_source = "reviews.corpus_papers"
    if not corpus_pmids:
        # legacy row without a resolvable corpus: audit against the report's
        # own citation set (foreign-citation filter degenerates to "all").
        corpus_pmids = cited_pmids_in_report(report)
        corpus_source = "report citations (fallback)"

    claims = extract_candidate_claims(report, corpus_pmids)
    claim_pmids = sorted({p for c in claims for p in c.pmids if p in corpus_pmids})
    paper_texts = load_paper_texts(db_name, claim_pmids)
    fulltext_map = fetch_fulltext_map(db_name, claim_pmids)

    n_verified = n_skipped = 0
    flags: list[dict[str, Any]] = []
    for claim in claims:
        verdict = verify_claim(claim, paper_texts, corpus_pmids)
        if verdict["verdict"] == "verified":
            n_verified += 1
        elif verdict["verdict"] == "skipped":
            n_skipped += 1
        else:
            # sentence splitting is [.!?]-based, so markdown headers/tables can
            # glue multi-line runs into one "sentence" — collapse whitespace for
            # the excerpt so the report table stays one row per claim
            sentence = re.sub(r"\s+", " ", claim.sentence).strip()
            excerpt = sentence if len(sentence) <= EXCERPT_CHARS else sentence[:EXCERPT_CHARS].rstrip() + "…"
            claim_cited = [p for p in verdict["pmids"] if p in corpus_pmids]
            abstract_only = bool(claim_cited) and all(not fulltext_map.get(p, False) for p in claim_cited)
            flags.append({
                "meta_id": meta_id,
                "corpus_id": corpus_id,
                "pipeline_version": version,
                "pmids": claim_cited,
                "missing_tokens": [t.strip() for t in verdict["missing"]],
                "abstract_only": abstract_only,
                "excerpt": excerpt,
            })

    summary = {
        "meta_id": meta_id,
        "corpus_id": corpus_id,
        "pipeline_version": version,
        "llm": f"{row.get('llm_provider')}/{row.get('llm_model')}",
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "corpus_size": len(corpus_pmids),
        "corpus_source": corpus_source,
        "n_candidates": len(claims),
        "n_verified": n_verified,
        "n_skipped": n_skipped,
        "n_flagged": len(flags),
    }
    return summary, flags


# ---------------------------------------------------------------------------
# report rendering
# ---------------------------------------------------------------------------

def render_fleet_report(
    summaries: list[dict[str, Any]],
    flags: list[dict[str, Any]],
    sanity: dict[str, Any] | None,
) -> str:
    total = len(summaries)
    cand = sum(s["n_candidates"] for s in summaries)
    ver = sum(s["n_verified"] for s in summaries)
    skip = sum(s["n_skipped"] for s in summaries)
    flag = sum(s["n_flagged"] for s in summaries)
    audited = ver + flag
    fidelity = (100.0 * ver / audited) if audited else 100.0

    lines: list[str] = []
    lines.append("# Numeric-fidelity fleet scan — all stored sciaiR reports")
    lines.append("")
    lines.append("Date: 2026-10-10 · gate: `sciai_core.cra.numeric_verification` (deterministic, no LLM) · "
                 "scanner: `maintenance/numeric_fleet_scan.py` (read-only)")
    lines.append("")
    if sanity:
        lines.append("## Sanity gate (meta 163, corrected LIXIPARK report)")
        lines.append("")
        lines.append(
            f"- meta {sanity['meta_id']}: {sanity['n_candidates']} candidates → "
            f"{sanity['n_verified']} verified / {sanity['n_skipped']} skipped / "
            f"**{sanity['n_flagged']} flagged** (expect ~0 after the 10-10 correction)"
        )
        lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append(f"- Reports scanned: **{total}**")
    lines.append(f"- Candidate numeric claims: **{cand}**")
    lines.append(f"- Verified: **{ver}** · flagged: **{flag}** · skipped: **{skip}**")
    lines.append(f"- Fidelity over auditable claims (verified / (verified+flagged)): **{fidelity:.1f}%**")
    lines.append("")

    # per-version table
    lines.append("## Fidelity by pipeline version")
    lines.append("")
    lines.append("| pipeline version | reports | candidates | verified | flagged | skipped | fidelity % |")
    lines.append("|---|---|---|---|---|---|---|")
    by_version: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in summaries:
        by_version[s["pipeline_version"] or "legacy / unstamped"].append(s)
    for version in sorted(by_version, key=lambda v: (v == "legacy / unstamped", v)):
        rows = by_version[version]
        v_ver = sum(r["n_verified"] for r in rows)
        v_flag = sum(r["n_flagged"] for r in rows)
        v_skip = sum(r["n_skipped"] for r in rows)
        v_cand = sum(r["n_candidates"] for r in rows)
        v_aud = v_ver + v_flag
        v_fid = (100.0 * v_ver / v_aud) if v_aud else 100.0
        lines.append(f"| {version} | {len(rows)} | {v_cand} | {v_ver} | {v_flag} | {v_skip} | {v_fid:.1f} |")
    lines.append("")

    # worst reports
    lines.append("## Flagged claims — worst reports first")
    lines.append("")
    worst = sorted((s for s in summaries if s["n_flagged"]), key=lambda s: -s["n_flagged"])
    if not worst:
        lines.append("No flagged claims anywhere in the fleet.")
        lines.append("")
    else:
        lines.append("| meta | corpus | version | flags | excerpt (pmids; missing tokens) |")
        lines.append("|---|---|---|---|---|")
        flags_by_meta: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for f in flags:
            flags_by_meta[f["meta_id"]].append(f)
        for s in worst:
            cells = []
            for f in flags_by_meta[s["meta_id"]]:
                marker = " *(abstract-only flag)*" if f["abstract_only"] else ""
                cells.append(
                    f"PMIDs {', '.join(f['pmids'])}; missing {', '.join(f['missing_tokens'])}"
                    f"{marker}: “{f['excerpt']}”"
                )
            lines.append(
                f"| {s['meta_id']} | {s['corpus_id']} | {s['pipeline_version'] or 'legacy'} | "
                f"{s['n_flagged']} | " + "<br>".join(cells) + " |"
            )
        lines.append("")

    lines.append("## Methods")
    lines.append("")
    lines.append("- Every `reviews.meta_syntheses` row with non-empty `report_markdown` (>100 chars) was scanned.")
    lines.append("- Corpus membership: `reviews.corpus_papers` with `NOT COALESCE(manually_excluded, FALSE)` "
                 "(the pipeline's convention). Rows without a resolvable corpus fall back to the report's own "
                 "citation set (marked `report citations (fallback)` in the JSONL).")
    lines.append("- Candidate claims: report sentences citing ≥1 corpus PMID that contain a p-value or a "
                 "confidence interval (`extract_candidate_claims`). Tokens verified: CI bounds, p-values, "
                 "headline effect/OR/HR/RR values (`verify_claim`) against the stored text "
                 "(abstract + `ops.chunks` fulltext, 400k-char cap, `load_paper_texts`).")
    lines.append("- Verdicts: `verified` (all tokens found in at least one cited paper), "
                 "`numeric_not_in_source` (≥1 token absent → flag), `skipped` (no tokens, unsettlable "
                 "inequality-only claims, or no stored text — never a flag).")
    lines.append("- Pipeline version parsed from `annotation.version_stamp.pipeline_version` "
                 "(JSON first, regex fallback for legacy/plain-text annotations).")
    lines.append("")
    lines.append("## Caveats")
    lines.append("")
    lines.append("- **Abstract-only flags**: a flag on a paper WITHOUT an ingested fulltext means the number "
                 "was checked against the abstract alone — many legitimate results numerics live only in the "
                 "full text. These are marked `abstract_only: true` in `flags_detail.jsonl` and "
                 "*(abstract-only flag)* above; read them as 'unverifiable from stored text', not as "
                 "fabrication evidence. Fulltext-backed flags are the hard findings.")
    lines.append("- Multi-citation sentences attribute loosely by design (a token is verified if it appears in "
                 "ANY cited corpus paper) — precision over recall: real flags can hide when a sister citation "
                 "carries the same number.")
    lines.append("- Stored fulltexts include the legacy path-stub class (2026-09-15 ops.chunks bug): a paper "
                 "counted as fulltext-backed may effectively have little real text.")
    lines.append("- `skipped` is dominated by papers with no stored text and by inequality-only p-claims "
                 "(p<0.05 without an exact source value); skips are excluded from the fidelity rate.")
    lines.append("- The gate checks number PRESENCE, not correctness of context, direction, or estimand "
                 "(that is the citation-QA / resolver layer).")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB, help="database name (default: sciai)")
    parser.add_argument("--limit", type=int, default=None, help="debug: scan at most N reports")
    parser.add_argument("--meta-id", type=int, default=None, help="debug: scan only this meta_id")
    parser.add_argument("--out-dir", default=str(OUT_DIR), help="output directory")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    LOGGER.info("numeric fleet scan start (db=%s, meta_id=%s, limit=%s)", args.db, args.meta_id, args.limit)
    rows = fetch_reports(args.db, args.meta_id, args.limit)
    LOGGER.info("reports to scan: %d", len(rows))

    summaries: list[dict[str, Any]] = []
    all_flags: list[dict[str, Any]] = []
    for row in rows:
        meta_id = row["meta_id"]
        try:
            summary, flags = scan_report(args.db, row)
        except Exception:
            LOGGER.exception("meta %s: scan failed", meta_id)
            summaries.append({
                "meta_id": meta_id, "corpus_id": row.get("corpus_id"),
                "pipeline_version": None, "error": "scan failed (see log)",
            })
            continue
        summaries.append(summary)
        all_flags.extend(flags)
        LOGGER.info(
            "meta %s (corpus %s, v%s): %d candidates = %d verified / %d skipped / %d flagged",
            meta_id, summary["corpus_id"], summary["pipeline_version"] or "?",
            summary["n_candidates"], summary["n_verified"], summary["n_skipped"], summary["n_flagged"],
        )

    scan_path = out_dir / "fleet_scan.jsonl"
    flags_path = out_dir / "flags_detail.jsonl"
    report_path = out_dir / "fleet_report.md"

    with scan_path.open("w") as fh:
        for s in summaries:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    with flags_path.open("w") as fh:
        for f in all_flags:
            fh.write(json.dumps(f, ensure_ascii=False) + "\n")

    sanity = next((s for s in summaries if s["meta_id"] == 163), None)
    report_path.write_text(render_fleet_report(summaries, all_flags, sanity))

    total_flag = sum(s.get("n_flagged", 0) for s in summaries)
    LOGGER.info(
        "done: %d reports, %d flagged claims; outputs in %s", len(summaries), total_flag, out_dir
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
