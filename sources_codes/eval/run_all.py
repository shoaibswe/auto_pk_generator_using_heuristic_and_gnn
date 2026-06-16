"""One-shot orchestrator: regenerate every quantitative claim in the paper.

Runs:

  1. eval.score_artefacts        -- Tables 1 & 2 from on-disk artefacts.
  2. eval.ind_baseline           -- Table 3 (IND baseline) across all datasets.
    3. eval.ind_baseline_filtered  -- ID-token and NameSim filtered IND ladder.
    4. eval.binder_baseline        -- External BINDER unary-IND baseline.
    5. eval.spider_baseline        -- External SPIDER unary-IND baseline.
    6. eval.hyfd_baseline          -- Table-wise HyFD-derived PK baseline.
    7. eval.llm_baseline (optional) -- LLM column, requires Ollama running locally.

Writes a single results.json into paper_final/eval/.

Usage:
    python -m eval.run_all                   # artefacts + internal/external baselines
    python -m eval.run_all --with-llm        # also call local Ollama

`run_all` passes an explicit seven-dataset list to BINDER and SPIDER so the
committed TPC-DS FK baselines are regenerated even though those scripts omit
TPC-DS from their workstation-safe defaults. HyFD is still run on its own
default six-dataset set because the TPC-DS table-wise FD mining run is not
part of the committed results pack.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from . import (
    binder_baseline,
    score_artefacts,
    ind_baseline,
    ind_baseline_filtered,
    spider_baseline,
    hyfd_baseline,
    sensitivity,
    error_analysis,
)


EXTERNAL_FK_DATASETS = [
    "dvdrental",
    "chinook",
    "tpch",
    "northwind",
    "sakila",
    "adventureworks",
    "tpcds",
]


def _capture(fn, argv) -> dict:
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(argv)
    try:
        return json.loads(buf.getvalue())
    except json.JSONDecodeError:
        return {"raw": buf.getvalue()}


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--with-llm", action="store_true")
    p.add_argument("--llm-model", default="llama3.1:8b-instruct-q4_K_M")
    p.add_argument("--out", default=str(Path(__file__).resolve().parent / "results.json"))
    args = p.parse_args(argv)

    out: dict = {}
    out["artefact_scoring"] = _capture(score_artefacts.main, [])
    out["ind_baseline"] = _capture(ind_baseline.main, [])
    out["ind_baseline_filtered"] = _capture(ind_baseline_filtered.main, [])
    out["binder_baseline"] = _capture(binder_baseline.main, EXTERNAL_FK_DATASETS)
    out["spider_baseline"] = _capture(spider_baseline.main, EXTERNAL_FK_DATASETS)
    out["hyfd_baseline"] = _capture(hyfd_baseline.main, [])
    out["sensitivity"] = _capture(sensitivity.main, [])
    out["error_analysis"] = _capture(error_analysis.main, [])

    if args.with_llm:
        from . import llm_baseline
        out["llm_baseline"] = _capture(llm_baseline.main, ["--model", args.llm_model])
    else:
        out["llm_baseline"] = {
            "status": "not_run",
            "reason": "Run with --with-llm and a local Ollama installation to regenerate this section.",
        }

    Path(args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"\n[run_all] wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
