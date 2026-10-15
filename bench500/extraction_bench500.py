#!/usr/bin/env python3
"""Extraction-quality benchmark — 500-paper battery (protocol v1, 2026-09-13).

Implements Planning/20260913_extraction_quality_test_protocol.md:

  freeze   Build the frozen stratified 500-paper list
           -> eval_reports/extraction_benchmark500_20260914.json
  run      Run one candidate model over the frozen list into
           reviews.extractions_bench (migration 021; NEVER extractions_v2,
           so benchmark rows cannot leak into the KG). Resumable: existing
           (run_id, paper_id) rows are skipped.
  status   Progress/yield per run_id.

Candidates our 24GB RTX PRO 4000 cannot serve go through OpenRouter
(provider "openrouter"); the incumbent Qwen3-30B-A3B runs on local vLLM in
the GPU-window tail; DeepSeek-chat runs as the external reference row.

Run:
  PYTHONPATH=/55a11/sciai_next /55a11/sciai/.venv/bin/python \
      /55a11/maintenance/extraction_bench500.py freeze
  PYTHONPATH=/55a11/sciai_next /55a11/sciai/.venv/bin/python \
      /55a11/maintenance/extraction_bench500.py run \
      --run-id bench500-20260914-deepseek --provider deepseek --model deepseek-chat \
      --concurrency 4
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from sciai_automation_lib import (  # noqa: E402
    LockFile,
    get_dsn,
    load_dotenv_repo,
    setup_logging,
)

load_dotenv_repo()

LOGGER = setup_logging(
    "extraction_bench500",
    Path("/55a11/logs/extraction_bench500.log"),
)

FROZEN_PATH = Path("/55a11/eval_reports/extraction_benchmark500_20260914.json")
SCHEMA_NAME = "universal_pd_v5"
BENCH_DATE = "2026-09-14"

N_FULLTEXT = 350
N_ABSTRACT = 150
MIN_LONG_FULLTEXT = 25          # papers above LONG_CHARS in the fulltext stratum
LONG_CHARS = 30_000             # context-pressure stratum threshold (chars)
TYPE_GROUPS = [
    "clinical_trial", "observational_human", "animal_study",
    "laboratory", "computational", "reviews",
]
REVIEW_SUBTYPES = {"narrative_review", "systematic_review", "meta_analysis", "scoping_review"}
ERA_BINS = [("<=2000", None, 2000), ("2001-2015", 2001, 2015), ("2016-2026", 2016, None)]


# ---------------------------------------------------------------------------
# freeze
# ---------------------------------------------------------------------------
def type_group(paper_types) -> Optional[str]:
    """Primary stratum label from a v4/v5 paper_type array."""
    if not paper_types:
        return None
    first = paper_types[0]
    if first in REVIEW_SUBTYPES:
        return "reviews"
    if first in TYPE_GROUPS:
        return first
    return None  # 'other' and friends are out of scope for the battery


def era_bin(year: Optional[int]) -> str:
    y = year or 0
    for label, lo, hi in ERA_BINS:
        if (lo is None or y >= lo) and (hi is None or y <= hi):
            return label
    return "2016-2026"


def _fetch_pool(conn, reference_schema: str, require_fulltext: bool) -> List[dict]:
    """Candidate pool: successful reference extractions + era + type + length.

    Deterministic pseudo-random order via md5 (reproducible without seed
    management). Fulltext length = concatenated ops.chunks length (the same
    content the runner sees).
    """
    ft_join = "JOIN ops.fulltexts f ON f.pmid = p.pmid AND f.imported = true"
    ft_anti = "LEFT JOIN ops.fulltexts f ON f.pmid = p.pmid AND f.imported = true"
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT e.paper_id, p.pmid, p.year,
               e.extracted_data->'paper_type' AS paper_types,
               e.extracted_from,
               COALESCE(cl.n_chars, 0) AS n_chars
        FROM reviews.extractions_v2 e
        JOIN pubmed.papers p ON p.paper_id = e.paper_id
        {ft_join if require_fulltext else ft_anti}
        LEFT JOIN LATERAL (
            SELECT sum(length(c.text)) AS n_chars
            FROM ops.chunks c WHERE c.paper_id = e.paper_id
        ) cl ON TRUE
        WHERE e.schema_name = %s AND e.success = TRUE
          AND (%s OR f.pmid IS NULL)
        ORDER BY md5(e.paper_id::text || ':bench500')
        """,
        (reference_schema, require_fulltext),
    )
    rows = []
    for paper_id, pmid, year, paper_types, extracted_from, n_chars in cur.fetchall():
        tg = type_group(paper_types or [])
        if tg is None:
            continue
        rows.append({
            "paper_id": paper_id,
            "pmid": pmid,
            "year": year,
            "type_group": tg,
            "era": era_bin(year),
            "n_chars": n_chars or 0,
        })
    cur.close()
    return rows


def _proportional_allocation(pool: List[dict], total: int) -> Dict[tuple, int]:
    """Largest-remainder proportional allocation over (type_group, era)."""
    counts = Counter((r["type_group"], r["era"]) for r in pool)
    n_pool = sum(counts.values())
    raw = {k: v * total / n_pool for k, v in counts.items()}
    alloc = {k: int(v) for k, v in raw.items()}
    remainder = total - sum(alloc.values())
    for key in sorted(raw, key=lambda k: raw[k] - alloc[k], reverse=True):
        if remainder <= 0:
            break
        alloc[key] += 1
        remainder -= 1
    return alloc


def _sample_pool(pool: List[dict], total: int, min_long: int = 0) -> List[dict]:
    alloc = _proportional_allocation(pool, total)
    by_stratum: Dict[tuple, List[dict]] = defaultdict(list)
    for row in pool:
        by_stratum[(row["type_group"], row["era"])].append(row)

    picked: List[dict] = []
    picked_ids = set()
    for stratum, quota in alloc.items():
        rows = by_stratum[stratum][:quota]
        picked.extend(rows)
        picked_ids.update(r["paper_id"] for r in rows)

    # Context-pressure guarantee: swap in long papers if the proportional
    # draw fell short (replace from the same type_group where possible).
    if min_long > 0:
        n_long = sum(1 for r in picked if r["n_chars"] > LONG_CHARS)
        if n_long < min_long:
            long_candidates = [r for r in pool if r["n_chars"] > LONG_CHARS and r["paper_id"] not in picked_ids]
            for cand in long_candidates[: min_long - n_long]:
                swap_idx = next(
                    (i for i, r in enumerate(picked)
                     if r["n_chars"] <= LONG_CHARS and r["type_group"] == cand["type_group"]),
                    next((i for i, r in enumerate(picked) if r["n_chars"] <= LONG_CHARS), None),
                )
                if swap_idx is None:
                    break
                picked_ids.discard(picked[swap_idx]["paper_id"])
                picked[swap_idx] = cand
                picked_ids.add(cand["paper_id"])
    return picked


def stage_freeze() -> None:
    import psycopg

    conn = psycopg.connect(get_dsn())

    LOGGER.info("Fetching fulltext pool (reference: universal_pd_v4)…")
    ft_pool = _fetch_pool(conn, "universal_pd_v4", require_fulltext=True)
    LOGGER.info("Fulltext pool: %d papers", len(ft_pool))

    # Abstract-only stratum: no v4 exists for papers without fulltext (v4 is
    # fulltext-only). Reference for these 150 is the incumbent's v5 abstract
    # extraction; agreement metrics on this stratum must be read with that
    # caveat (documented in the frozen list).
    LOGGER.info("Fetching abstract-only pool (reference: universal_pd_v5 abstract rows)…")
    abs_pool = _fetch_pool(conn, "universal_pd_v5", require_fulltext=False)
    LOGGER.info("Abstract-only pool: %d papers", len(abs_pool))

    conn.close()

    picked_ft = _sample_pool(ft_pool, N_FULLTEXT, min_long=MIN_LONG_FULLTEXT)
    picked_abs = _sample_pool(abs_pool, N_ABSTRACT)

    rows = []
    for r in picked_ft:
        rows.append({
            "paper_id": r["paper_id"],
            "pmid": r["pmid"],
            "stratum": {
                "tier": "fulltext",
                "era": r["era"],
                "paper_type": r["type_group"],
                "long": r["n_chars"] > LONG_CHARS,
            },
            "n_chars": r["n_chars"],
            "reference_schema": "universal_pd_v4",
        })
    for r in picked_abs:
        rows.append({
            "paper_id": r["paper_id"],
            "pmid": r["pmid"],
            "stratum": {
                "tier": "abstract_only",
                "era": r["era"],
                "paper_type": r["type_group"],
                "long": False,
            },
            "n_chars": 0,
            "reference_schema": "universal_pd_v5",
        })

    doc = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": "Planning/20260913_extraction_quality_test_protocol.md",
        "schema_under_test": SCHEMA_NAME,
        "seed": "md5(paper_id || ':bench500') — deterministic, reproducible",
        "deviations": [
            "Abstract-only stratum reference is universal_pd_v5 (incumbent) because "
            "v4 is fulltext-only; agreement metrics on the abstract_only tier are "
            "self-referential for the incumbent and must be read accordingly.",
            "Papers typed 'other' are excluded from the pool (protocol lists six groups).",
        ],
        "n": len(rows),
        "stratum_summary": {
            "by_tier": dict(Counter(r["stratum"]["tier"] for r in rows)),
            "by_type": dict(Counter(r["stratum"]["paper_type"] for r in rows)),
            "by_era": dict(Counter(r["stratum"]["era"] for r in rows)),
            "long_fulltext": sum(1 for r in rows if r["stratum"]["long"]),
        },
        "papers": rows,
    }
    FROZEN_PATH.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    LOGGER.info("Frozen list written to %s: %d papers", FROZEN_PATH, len(rows))
    LOGGER.info("Strata: %s", json.dumps(doc["stratum_summary"], indent=1))


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------
def _bench_store(cur, run_id: str, provider: str, model: str, paper: dict,
                 result: dict, extracted_from: Optional[str]) -> None:
    cur.execute(
        """
        INSERT INTO reviews.extractions_bench
            (run_id, candidate_model, llm_provider, paper_id, pmid, schema_name,
             stratum, extracted_data, success, error_message, raw_response,
             elapsed_ms, prompt_tokens, extracted_from)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (run_id, paper_id, schema_name) DO NOTHING
        """,
        (
            run_id, model, provider, paper["paper_id"], paper.get("pmid"),
            SCHEMA_NAME, json.dumps(paper["stratum"]),
            json.dumps(result.get("data")) if result.get("data") else None,
            result.get("success", False), result.get("error"),
            (result.get("raw_response") or "")[:2000],
            result.get("elapsed_ms", 0), result.get("prompt_tokens"),
            extracted_from,
        ),
    )


def stage_run(args) -> None:
    import psycopg

    if not FROZEN_PATH.exists():
        LOGGER.error("Frozen list missing (%s); run `freeze` first", FROZEN_PATH)
        sys.exit(1)
    papers = json.loads(FROZEN_PATH.read_text(encoding="utf-8"))["papers"]
    if args.only_papers:
        # Restrict to a subsample (e.g. the qual50 selection.json for the v6
        # pilot): a JSON file with a top-level "papers" list carrying paper_id.
        sel = json.loads(Path(args.only_papers).read_text(encoding="utf-8"))
        wanted = {p["paper_id"] for p in sel["papers"]}
        papers = [p for p in papers if p["paper_id"] in wanted]
        LOGGER.info("subsample %s: %d of the frozen 500", args.only_papers, len(papers))
    if args.limit:
        papers = papers[: args.limit]

    from sciai_core.extraction.runner import ExtractionRunner

    conn = psycopg.connect(get_dsn())
    with conn.cursor() as cur:
        cur.execute(
            "SELECT paper_id FROM reviews.extractions_bench WHERE run_id = %s AND schema_name = %s",
            (args.run_id, SCHEMA_NAME),
        )
        done = {r[0] for r in cur.fetchall()}
    todo = [p for p in papers if p["paper_id"] not in done]
    LOGGER.info(
        "run_id=%s provider=%s model=%s: %d papers (%d already done, skipped)",
        args.run_id, args.provider, args.model, len(todo), len(done),
    )
    if not todo:
        conn.close()
        return

    runner = ExtractionRunner(
        db_connection=lambda: psycopg.connect(get_dsn()),
        default_provider=args.provider,
        default_model=args.model,
    )

    lock = LockFile(f"bench500-{args.run_id}")
    if not lock.acquire():
        LOGGER.error("Another process holds the lock for run %s; aborting", args.run_id)
        sys.exit(1)

    counters: Counter = Counter()
    store_lock = threading.Lock()
    try:
        def _one(paper: dict) -> None:
            result = runner.extract_single_paper(
                paper_id=paper["paper_id"],
                schema_name=SCHEMA_NAME,
                provider=args.provider,
                model=args.model,
                dry_run=True,  # never extractions_v2; we store to the bench table
            )
            _content, extracted_from = runner._get_paper_content(paper["paper_id"], paper.get("pmid", ""))
            with store_lock, conn.cursor() as cur:
                _bench_store(cur, args.run_id, args.provider, args.model,
                             paper, result, extracted_from)
                conn.commit()
                counters["success" if result.get("success") else "failed"] += 1
                done_total = counters["success"] + counters["failed"]
                if done_total % 25 == 0:
                    LOGGER.info("progress: %d/%d (ok=%d fail=%d)",
                                done_total, len(todo), counters["success"], counters["failed"])

        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            list(pool.map(_one, todo))
    finally:
        lock.release()
        conn.close()

    LOGGER.info("Run %s finished: %s", args.run_id, dict(counters))


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------
def stage_status() -> None:
    import psycopg

    conn = psycopg.connect(get_dsn())
    with conn.cursor() as cur:
        cur.execute("""
            SELECT run_id, candidate_model, llm_provider,
                   count(*) AS n,
                   count(*) FILTER (WHERE success) AS ok,
                   round(avg(elapsed_ms)) AS avg_ms,
                   sum(prompt_tokens) AS prompt_tokens
            FROM reviews.extractions_bench
            GROUP BY 1, 2, 3 ORDER BY 1
        """)
        rows = cur.fetchall()
    conn.close()
    if not rows:
        print("No benchmark rows yet.")
        return
    print(f"{'run_id':44} {'model':40} {'prov':10} {'n':>4} {'ok':>4} {'avg_ms':>7} {'tokens':>10}")
    for run_id, model, provider, n, ok, avg_ms, tokens in rows:
        print(f"{run_id:44} {model:40} {provider:10} {n:>4} {ok:>4} {avg_ms or 0:>7} {tokens or 0:>10}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("freeze")
    run_p = sub.add_parser("run")
    run_p.add_argument("--run-id", required=True)
    run_p.add_argument("--provider", required=True,
                       choices=["vllm", "openrouter", "deepseek", "openai", "kimi"])
    run_p.add_argument("--model", required=True)
    run_p.add_argument("--concurrency", type=int, default=1)
    run_p.add_argument("--limit", type=int, default=None, help="First N papers (smoke tests)")
    run_p.add_argument("--only-papers", default=None,
                       help="JSON file with a papers list (qual50 selection.json) to subsample the frozen 500")
    sub.add_parser("status")
    args = parser.parse_args()

    if args.cmd == "freeze":
        stage_freeze()
    elif args.cmd == "run":
        stage_run(args)
    else:
        stage_status()


if __name__ == "__main__":
    main()
