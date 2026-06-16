"""External SPIDER baseline runner (Metanome CLI driver).

Runs HPI's SPIDER inclusion-dependency algorithm (built locally from
``eval/external/metanome/metanome-algorithms``) against each dataset's
CSV files and scores the discovered unary INDs against the same
DDL-parsed unary FK ground truth used by the cascade and the in-house
IND ladder.

The output JSON is committed at ``paper_final/eval/external_spider_<dataset>.json``.

Reproducibility (one-shot):

    JAVA_HOME=$HOME/.sdkman/candidates/java/current \
    PATH=$JAVA_HOME/bin:$PATH \
    python -m eval.spider_baseline <dataset> [<dataset> ...]

If <dataset> is omitted, runs the small benchmarks (dvdrental, chinook,
tpch) plus the three larger schemas (adventureworks, sakila, northwind).
TPC-DS is intentionally skipped by default because the bundled CSVs are
too large for a single-process IND run on a workstation.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from .binder_baseline import _csv_inputs, _detect_separator, _run_binder
from .ground_truth import parse_ddl
from .metrics import fk_prf
from .score_artefacts import _clean_table


HERE = Path(__file__).resolve().parent.parent  # paper_final/
EXT = HERE / "eval" / "external" / "metanome"
CLI_JAR = EXT / "metanome-cli.jar"
SPIDER_JAR = EXT / "metanome-algorithms" / "SPIDER" / "SPIDERFile" / "target" / "SPIDER-1.2-SNAPSHOT.jar"

SPIDER_CLASS = "de.metanome.algorithms.spider.SPIDERFile"

DATASETS_DEFAULT = [
    "dvdrental",
    "chinook",
    "tpch",
    "northwind",
    "sakila",
    "adventureworks",
]


def _parse_ind_file(path: Path) -> tuple[list[tuple[str, str, str, str]], dict]:
    inds: list[tuple[str, str, str, str]] = []
    raw = path.read_text(encoding="utf-8", errors="ignore")
    n_total = 0
    n_skipped_self = 0
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        n_total += 1
        dep = obj.get("dependant", {}).get("columnIdentifiers") or []
        ref = obj.get("referenced", {}).get("columnIdentifiers") or []
        if len(dep) != 1 or len(ref) != 1:
            continue
        src_t = _clean_table(Path(dep[0].get("tableIdentifier", "")).stem)
        tgt_t = _clean_table(Path(ref[0].get("tableIdentifier", "")).stem)
        src_c = (dep[0].get("columnIdentifier") or "").lower()
        tgt_c = (ref[0].get("columnIdentifier") or "").lower()
        if not (src_t and tgt_t and src_c and tgt_c):
            continue
        if src_t == tgt_t and src_c == tgt_c:
            n_skipped_self += 1
            continue
        inds.append((src_t, src_c, tgt_t, tgt_c))
    meta = {
        "raw_lines": len(raw.splitlines()),
        "inds_total": n_total,
        "unary_inds_kept": len(inds),
        "self_inds_dropped": n_skipped_self,
        "result_file": path.name,
    }
    return inds, meta


def _run_spider(dataset: str, out_dir: Path) -> tuple[list[tuple[str, str, str, str]], dict]:
    csvs = _csv_inputs(dataset)
    if not csvs:
        return [], {"error": "no_csv_inputs"}

    sep = _detect_separator(csvs[0])
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "java", "-Xmx6g",
        "-cp", f"{CLI_JAR}:{SPIDER_JAR}",
        "de.metanome.cli.App",
        "--algorithm", SPIDER_CLASS,
        "--file-key", "INPUT_FILES",
        "--files", *[str(p) for p in csvs],
        "--separator", sep,
        "--header",
        "--quote", '"',
        "--escape", "\\",
        "--skip-differing-lines",
        "--output", f"file:{dataset}",
    ]
    env = os.environ.copy()
    env.setdefault("JAVA_HOME", os.path.expanduser("~/.sdkman/candidates/java/current"))
    env["PATH"] = f"{env['JAVA_HOME']}/bin:{env.get('PATH','')}"

    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(out_dir))
    elapsed = time.time() - t0

    meta = {
        "n_csv": len(csvs),
        "separator": sep,
        "elapsed_sec": round(elapsed, 2),
        "exit": proc.returncode,
        "stderr_tail": proc.stderr.strip().splitlines()[-5:] if proc.stderr else [],
        "stdout_tail": proc.stdout.strip().splitlines()[-5:] if proc.stdout else [],
    }
    if proc.returncode != 0:
        return [], meta

    result_files = sorted(out_dir.rglob("*_inds"))
    if not result_files:
        result_files = sorted(out_dir.rglob("*.txt"))
    if not result_files:
        return [], {**meta, "error": "no_result_file"}

    inds, parse_meta = _parse_ind_file(result_files[-1])
    return inds, {**meta, **parse_meta}


def _score(dataset: str) -> dict:
    ddl = HERE / dataset / "sql_ddl.sql"
    if not ddl.exists():
        return {"dataset": dataset, "status": "missing_ddl"}
    if not CLI_JAR.exists() or not SPIDER_JAR.exists():
        return {
            "dataset": dataset,
            "status": "spider_jar_missing",
            "expected_cli": str(CLI_JAR),
            "expected_spider": str(SPIDER_JAR),
        }

    out_dir = HERE / "eval" / "external" / "spider_out" / dataset
    inds, meta = _run_spider(dataset, out_dir)

    if not inds and meta.get("exit") != 0:
        return {"dataset": dataset, "status": "spider_failed", "meta": meta}

    _, _, gt_unary, _ = parse_ddl(ddl)
    unary_prf = fk_prf(inds, gt_unary)
    return {
        "dataset": dataset,
        "status": "ok",
        "meta": meta,
        "spider_unary_inds": len(inds),
        "fk_unary": unary_prf,
        "gt_unary_count": len(gt_unary),
    }


def main(argv=None):
    targets = argv or DATASETS_DEFAULT
    out = {}
    for d in targets:
        print(f"[spider] running {d} ...", file=sys.stderr, flush=True)
        out[d] = _score(d)
        path = HERE / "eval" / f"external_spider_{d}.json"
        path.write_text(json.dumps(out[d], indent=2))
        print(f"[spider] wrote {path.name}: {out[d].get('status')}", file=sys.stderr, flush=True)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]) or 0)