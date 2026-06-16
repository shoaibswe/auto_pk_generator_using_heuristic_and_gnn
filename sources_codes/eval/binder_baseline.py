"""External BINDER baseline runner (Metanome CLI driver).

Runs HPI's BINDER inclusion-dependency algorithm (built locally from
``eval/external/metanome/metanome-algorithms``) against each dataset's
CSV files and scores the discovered unary INDs against the same
DDL-parsed unary FK ground truth used by the cascade and the in-house
IND ladder.

Intentionally minimal: this is a SoTA-comparison row, not a tunable
component of the cascade.  The output JSON is committed at
``paper_final/eval/external_binder_<dataset>.json``.

Reproducibility (one-shot):

    JAVA_HOME=$HOME/.sdkman/candidates/java/current \\
    PATH=$JAVA_HOME/bin:$PATH \\
    python -m eval.binder_baseline <dataset> [<dataset> ...]

If <dataset> is omitted, runs the small benchmarks (dvdrental, chinook,
tpch) plus the three larger schemas (adventureworks, sakila, northwind).
TPC-DS is intentionally skipped by default because the bundled CSVs are
too large for a single-process IND run on a workstation.
"""
from __future__ import annotations
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .ground_truth import parse_ddl
from .metrics import fk_prf
from .score_artefacts import _clean_table


HERE = Path(__file__).resolve().parent.parent  # paper_final/
EXT = HERE / "eval" / "external" / "metanome"
CLI_JAR = EXT / "metanome-cli.jar"
BINDER_JAR = EXT / "metanome-algorithms" / "BINDER" / "BINDERFile" / "target" / "BINDER-1.2-SNAPSHOT.jar"

# Use the FILE-input BINDER algorithm class.
BINDER_CLASS = "de.metanome.algorithms.binder.BINDERFile"

DATASETS_DEFAULT = [
    "dvdrental",
    "chinook",
    "tpch",
    "northwind",
    "sakila",
    "adventureworks",
]


def _csv_inputs(dataset: str) -> list[Path]:
    root = HERE / dataset / "data"
    if dataset == "tpcds":
        root = root / "csv"
    if not root.exists():
        return []
    return sorted(p for p in root.glob("*.csv") if p.is_file())


def _csv_table_name(p: Path) -> str:
    """Match the cascade's _clean_table normalisation on the file stem."""
    return _clean_table(p.stem)


def _detect_separator(p: Path) -> str:
    """Very small heuristic: peek at first line, pick whichever of ',' or
    ';' or '\t' produces more columns.  All bundled CSVs are comma-separated
    (the Sieve preprocessing pipeline normalises to comma), but adding the
    detection is cheap insurance."""
    with p.open("r", encoding="utf-8", errors="ignore") as f:
        line = f.readline()
    counts = {sep: line.count(sep) for sep in (",", ";", "\t", "|")}
    sep = max(counts, key=counts.get)
    return sep if counts[sep] > 0 else ","


def _run_binder(dataset: str, out_dir: Path) -> tuple[list[tuple[str, str, str, str]], dict]:
    """Run BINDER on every CSV in <dataset>/data/ and return the parsed
    unary IND list plus a small metadata dict."""
    csvs = _csv_inputs(dataset)
    if not csvs:
        return [], {"error": "no_csv_inputs"}

    sep = _detect_separator(csvs[0])
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "java", "-Xmx6g",
        "-cp", f"{CLI_JAR}:{BINDER_JAR}",
        "de.metanome.cli.App",
        "--algorithm", BINDER_CLASS,
        "--file-key", "INPUT_FILES",
        "--files", *[str(p) for p in csvs],
        "--separator", sep,
        "--header",
        "--quote", '"',
        "--escape", "\\",
        "--skip-differing-lines",
        "--output", f"file:{dataset}",
        "--algorithm-config", "DETECT_NARY:false",
    ]
    env = os.environ.copy()
    env.setdefault("JAVA_HOME", os.path.expanduser("~/.sdkman/candidates/java/current"))
    env["PATH"] = f"{env['JAVA_HOME']}/bin:{env.get('PATH','')}"

    # Metanome CLI writes output relative to the *current* working directory
    # (results/<runId>_inds).  Run inside out_dir so all artefacts land there.
    out_dir.mkdir(parents=True, exist_ok=True)
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

    # BINDER writes a result file; locate it.
    result_files = sorted(out_dir.rglob("*_inds"))
    if not result_files:
        result_files = sorted(out_dir.rglob("*.txt"))
    if not result_files:
        return [], {**meta, "error": "no_result_file"}

    # BINDER writes one JSON object per line:
    #   {"type":"InclusionDependency",
    #    "dependant":  {"columnIdentifiers":[{"tableIdentifier":"<file>.csv",
    #                                          "columnIdentifier":"<col>"}, ...]},
    #    "referenced": {"columnIdentifiers":[{...}, ...]}}
    # We restrict to unary (singleton column lists) to match the cascade's
    # unary FK scoring convention.
    inds: list[tuple[str, str, str, str]] = []
    raw = result_files[-1].read_text(encoding="utf-8", errors="ignore")
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
            # X subset X is trivially true; drop.
            n_skipped_self += 1
            continue
        inds.append((src_t, src_c, tgt_t, tgt_c))
    meta["raw_lines"] = len(raw.splitlines())
    meta["binder_inds_total"] = n_total
    meta["unary_inds_kept"] = len(inds)
    meta["self_inds_dropped"] = n_skipped_self
    meta["result_file"] = result_files[-1].name
    return inds, meta


def _score(dataset: str) -> dict:
    ddl = HERE / dataset / "sql_ddl.sql"
    if not ddl.exists():
        return {"dataset": dataset, "status": "missing_ddl"}
    if not CLI_JAR.exists() or not BINDER_JAR.exists():
        return {"dataset": dataset, "status": "binder_jar_missing",
                "expected_cli": str(CLI_JAR), "expected_binder": str(BINDER_JAR)}

    out_dir = HERE / "eval" / "external" / "binder_out" / dataset
    inds, meta = _run_binder(dataset, out_dir)

    if not inds and meta.get("exit") != 0:
        return {"dataset": dataset, "status": "binder_failed", "meta": meta}

    _, _, gt_unary, gt_relations = parse_ddl(ddl)

    # BINDER discovers INDs (subset relations).  Treat each unary IND as a
    # candidate FK; this is exactly the same convention as the in-house
    # ind_baseline.  No additional cardinality cap or naming filter is
    # applied --- this is the unfiltered SoTA-style baseline.
    unary_prf = fk_prf(inds, gt_unary)
    return {
        "dataset": dataset,
        "status": "ok",
        "meta": meta,
        "binder_unary_inds": len(inds),
        "fk_unary": unary_prf,
        "gt_unary_count": len(gt_unary),
    }


def main(argv=None):
    targets = argv or DATASETS_DEFAULT
    out = {}
    for d in targets:
        print(f"[binder] running {d} ...", file=sys.stderr, flush=True)
        out[d] = _score(d)
        # Persist incrementally so partial runs are recoverable.
        path = HERE / "eval" / f"external_binder_{d}.json"
        path.write_text(json.dumps(out[d], indent=2))
        print(f"[binder] wrote {path.name}: {out[d].get('status')}",
              file=sys.stderr, flush=True)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]) or 0)
