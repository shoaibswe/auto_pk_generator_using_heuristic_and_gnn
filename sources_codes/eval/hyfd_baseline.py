"""External HyFD baseline runner (Metanome CLI driver).

HyFD is a single-relation functional-dependency miner, so unlike BINDER and
SPIDER it cannot be run once across a multi-table schema to emit FK candidates.
This runner instead executes HyFD once per CSV table, reconstructs minimal
superkeys from the emitted FD set, chooses a deterministic representative key
per table, and scores the resulting PK map against the same DDL-parsed PK
ground truth used by the cascade.

The output JSON is committed at ``paper_final/eval/external_hyfd_<dataset>.json``.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from .binder_baseline import _csv_inputs, _detect_separator
from .ground_truth import parse_ddl
from .metrics import pk_accuracy
from .score_artefacts import _clean_table


HERE = Path(__file__).resolve().parent.parent  # paper_final/
EXT = HERE / "eval" / "external" / "metanome"
CLI_JAR = EXT / "metanome-cli.jar"
HYFD_JAR = EXT / "metanome-algorithms" / "HyFD" / "target" / "HyFD-1.2-SNAPSHOT.jar"

HYFD_CLASS = "de.metanome.algorithms.hyfd.HyFD"

DATASETS_DEFAULT = [
    "dvdrental",
    "chinook",
    "tpch",
    "northwind",
    "sakila",
    "adventureworks",
]


def _read_header(path: Path, sep: str) -> list[str]:
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f, delimiter=sep)
        try:
            row = next(reader)
        except StopIteration:
            return []
    return [str(col).strip().lower() for col in row if str(col).strip()]


def _parse_fd_file(path: Path) -> tuple[list[tuple[tuple[str, ...], str]], dict]:
    fds: list[tuple[tuple[str, ...], str]] = []
    raw = path.read_text(encoding="utf-8", errors="ignore")
    total = 0
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "FunctionalDependency":
            continue
        total += 1
        lhs = obj.get("determinant", {}).get("columnIdentifiers") or []
        rhs = obj.get("dependant", {}).get("columnIdentifier")
        lhs_cols = tuple(sorted((item.get("columnIdentifier") or "").lower() for item in lhs if item.get("columnIdentifier")))
        rhs_col = (rhs or "").lower()
        if rhs_col:
            fds.append((lhs_cols, rhs_col))
    return fds, {"raw_lines": len(raw.splitlines()), "fds_total": total, "result_file": path.name}


def _closure(seed: tuple[str, ...], fds: list[tuple[tuple[str, ...], str]]) -> set[str]:
    closed = set(seed)
    changed = True
    while changed:
        changed = False
        for lhs, rhs in fds:
            if set(lhs).issubset(closed) and rhs not in closed:
                closed.add(rhs)
                changed = True
    return closed


def _minimalize(key: tuple[str, ...], universe: set[str], fds: list[tuple[tuple[str, ...], str]]) -> set[tuple[str, ...]]:
    frontier = [tuple(sorted(key))]
    minimal: set[tuple[str, ...]] = set()
    seen = set(frontier)
    while frontier:
        current = frontier.pop()
        reducible = False
        for idx in range(len(current)):
            smaller = current[:idx] + current[idx + 1 :]
            if not smaller:
                continue
            if smaller in seen:
                continue
            seen.add(smaller)
            if _closure(smaller, fds) == universe:
                frontier.append(smaller)
                reducible = True
        if not reducible:
            minimal.add(current)
    return minimal


def _predict_key(columns: list[str], fds: list[tuple[tuple[str, ...], str]]) -> tuple[list[str] | None, dict]:
    universe = set(columns)
    if not columns:
        return None, {"status": "empty_table"}
    if len(columns) == 1:
        return [columns[0]], {"status": "singleton_table", "candidate_keys": [[columns[0]]], "n_fds": len(fds)}

    lhs_candidates = {lhs for lhs, _rhs in fds if lhs}
    superkeys = [lhs for lhs in lhs_candidates if _closure(lhs, fds) == universe]
    minimal: set[tuple[str, ...]] = set()
    for key in superkeys:
        minimal |= _minimalize(key, universe, fds)

    if not minimal:
        return None, {"status": "no_superkey", "n_fds": len(fds), "n_lhs_candidates": len(lhs_candidates)}

    chosen = min(minimal, key=lambda cols: (len(cols), list(cols)))
    return list(chosen), {
        "status": "ok",
        "n_fds": len(fds),
        "n_lhs_candidates": len(lhs_candidates),
        "n_superkeys": len(superkeys),
        "candidate_keys": [list(cols) for cols in sorted(minimal, key=lambda cols: (len(cols), list(cols)))],
    }


def _run_hyfd_table(csv_path: Path, out_dir: Path) -> tuple[list[tuple[tuple[str, ...], str]], dict]:
    sep = _detect_separator(csv_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "java", "-Xmx6g",
        "-cp", f"{CLI_JAR}:{HYFD_JAR}",
        "de.metanome.cli.App",
        "--algorithm", HYFD_CLASS,
        "--file-key", "INPUT_GENERATOR",
        "--files", str(csv_path),
        "--separator", sep,
        "--header",
        "--quote", '"',
        "--escape", "\\",
        "--skip-differing-lines",
        "--output", f"file:{csv_path.stem}",
    ]
    env = os.environ.copy()
    env.setdefault("JAVA_HOME", os.path.expanduser("~/.sdkman/candidates/java/current"))
    env["PATH"] = f"{env['JAVA_HOME']}/bin:{env.get('PATH','')}"

    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(out_dir))
    elapsed = time.time() - t0

    meta = {
        "separator": sep,
        "elapsed_sec": round(elapsed, 2),
        "exit": proc.returncode,
        "stderr_tail": proc.stderr.strip().splitlines()[-5:] if proc.stderr else [],
        "stdout_tail": proc.stdout.strip().splitlines()[-5:] if proc.stdout else [],
    }
    if proc.returncode != 0:
        return [], meta

    result_files = sorted(out_dir.rglob("*_fds"))
    if not result_files:
        result_files = sorted(out_dir.rglob("*.txt"))
    if not result_files:
        return [], {**meta, "error": "no_result_file"}

    fds, parse_meta = _parse_fd_file(result_files[-1])
    return fds, {**meta, **parse_meta}


def _score(dataset: str) -> dict:
    ddl = HERE / dataset / "sql_ddl.sql"
    if not ddl.exists():
        return {"dataset": dataset, "status": "missing_ddl"}
    if not CLI_JAR.exists() or not HYFD_JAR.exists():
        return {
            "dataset": dataset,
            "status": "hyfd_jar_missing",
            "expected_cli": str(CLI_JAR),
            "expected_hyfd": str(HYFD_JAR),
        }

    gt_pks, _fk_components, _gt_unary, _gt_relations = parse_ddl(ddl)
    csvs = _csv_inputs(dataset)
    if not csvs:
        return {"dataset": dataset, "status": "no_csv_inputs"}

    predicted: dict[str, list[str]] = {}
    per_table: dict[str, dict] = {}
    for csv_path in csvs:
        table = _clean_table(csv_path.stem)
        out_dir = HERE / "eval" / "external" / "hyfd_out" / dataset / table
        fds, meta = _run_hyfd_table(csv_path, out_dir)
        if meta.get("exit") != 0:
            per_table[table] = {"status": "hyfd_failed", "meta": meta}
            continue
        cols = _read_header(csv_path, meta["separator"])
        key, key_meta = _predict_key(cols, fds)
        if key:
            predicted[table] = key
        per_table[table] = {"meta": meta, **key_meta, "predicted_key": key}

    acc, correct, scored = pk_accuracy(predicted, gt_pks)
    return {
        "dataset": dataset,
        "status": "ok",
        "pk": {"accuracy": acc, "correct": correct, "scored": scored},
        "predicted_tables": len(predicted),
        "tables_with_ground_truth": len([t for t, cols in gt_pks.items() if cols]),
        "per_table": per_table,
    }


def main(argv=None):
    targets = argv or DATASETS_DEFAULT
    out = {}
    for d in targets:
        print(f"[hyfd] running {d} ...", file=sys.stderr, flush=True)
        out[d] = _score(d)
        path = HERE / "eval" / f"external_hyfd_{d}.json"
        path.write_text(json.dumps(out[d], indent=2))
        print(f"[hyfd] wrote {path.name}: {out[d].get('status')}", file=sys.stderr, flush=True)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]) or 0)