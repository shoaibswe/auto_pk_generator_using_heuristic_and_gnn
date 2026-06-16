"""Data-inclusion threshold sensitivity sweep.

For each dataset, re-score the on-disk `relationships.csv` against the
DDL-parsed ground truth at a sweep of data-inclusion thresholds.  This does
NOT re-run the pipeline; it filters the already-validated FK set by the
recorded `Inclusion_A_to_B` value, which is the data-inclusion percentage
computed during the headline run.  The output therefore answers:

    "Of the relationships the cascade actually accepted, how does the
     precision/recall/F1 trade-off shift if we tighten or relax the
     data-inclusion gate after the fact?"

It does NOT answer "what would happen if we relaxed the gate before
candidate generation" -- that would require a full re-run.

Usage:
    python -m eval.sensitivity                 # all datasets
    python -m eval.sensitivity dvdrental tpch  # selected datasets
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

from .ground_truth import parse_ddl
from .metrics import fk_prf
from .score_artefacts import (
    DATASETS,
    _read_predicted_fks_from_csv,
    _read_predicted_from_schema_json,
    _clean_table,
    _maybe_unwrap_list_column,
)
import csv

THRESHOLDS = [0.50, 0.70, 0.80, 0.90, 0.95, 0.99, 1.00]


def _load_predictions_with_inclusion(path: Path):
    """Return list of (src_t, src_col_tuple, tgt_t, tgt_col_tuple, inc_a_to_b)."""
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            src_t = row.get("Source Table") or ""
            src_c_raw = row.get("Source Col") or ""
            tgt_t = row.get("Target Table") or ""
            tgt_c = row.get("Target Col") or ""
            inc_raw = row.get("Inclusion_A_to_B") or row.get("Inclusion") or "0"
            try:
                inc = float(inc_raw)
            except ValueError:
                inc = 0.0
            src_cols = _maybe_unwrap_list_column(src_c_raw)
            tgt_cols = _maybe_unwrap_list_column(tgt_c)
            if not (src_t and tgt_t and src_cols and tgt_cols):
                continue
            if len(src_cols) != len(tgt_cols):
                continue
            rows.append((
                _clean_table(src_t),
                tuple(c.lower() for c in src_cols),
                _clean_table(tgt_t),
                tuple(c.lower() for c in tgt_cols),
                inc,
            ))
    return rows


def sweep_one(name: str, root: Path) -> dict:
    ddl = root / "sql_ddl.sql"
    if not ddl.exists():
        return {"dataset": name, "status": "missing_ddl"}

    _, _, gt_fk_unary, gt_fk_relations = parse_ddl(ddl)

    rel_csv = root / "relationships.csv"
    rows = _load_predictions_with_inclusion(rel_csv)
    if not rows:
        return {"dataset": name, "status": "no_predictions"}

    out: list[dict] = []
    for thr in THRESHOLDS:
        kept_relations = [(r[0], r[1], r[2], r[3]) for r in rows if r[4] >= thr]
        kept_components = []
        for src_t, src_cols, tgt_t, tgt_cols in kept_relations:
            for sc, tc in zip(src_cols, tgt_cols):
                kept_components.append((src_t, sc, tgt_t, tc))
        unary = fk_prf(kept_components, gt_fk_unary)
        rel = fk_prf(kept_relations, gt_fk_relations)
        out.append({
            "threshold": thr,
            "n_predicted_relations": len(kept_relations),
            "fk_unary": unary,
            "fk_all": rel,
        })
    return {"dataset": name, "status": "ok", "sweep": out}


def main(argv: list[str]) -> int:
    targets = argv if argv else list(DATASETS.keys())
    out = {}
    for name in targets:
        if name not in DATASETS:
            out[name] = {"status": "unknown_dataset"}
            continue
        out[name] = sweep_one(name, DATASETS[name])
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
