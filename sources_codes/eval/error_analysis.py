"""Per-dataset FK error analysis.

For each dataset, compare the cascade's accepted FK set against the
DDL-parsed ground truth and emit the explicit TP / FP / FN sets.

Usage:
    python -m eval.error_analysis                 # all datasets
    python -m eval.error_analysis dvdrental tpch  # selected datasets
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

from .ground_truth import parse_ddl
from .score_artefacts import (
    DATASETS,
    _read_predicted_fks_from_csv,
    _read_predicted_from_schema_json,
)


def _norm_relation(t):
    return (
        str(t[0]).lower(),
        tuple(str(c).lower() for c in t[1]),
        str(t[2]).lower(),
        tuple(str(c).lower() for c in t[3]),
    )


def _norm_component(t):
    return tuple(str(x).lower() for x in t)


def analyse_one(name: str, root: Path) -> dict:
    ddl = root / "sql_ddl.sql"
    if not ddl.exists():
        return {"dataset": name, "status": "missing_ddl"}
    _, _, gt_fk_unary, gt_fk_relations = parse_ddl(ddl)

    rel_csv = root / "relationships.csv"
    schema_json = root / "schema_final.json"
    pred_pks, pred_fk_relations, pred_fk_components = _read_predicted_from_schema_json(schema_json)
    if not pred_fk_relations and not pred_fk_components:
        pred_fk_relations, pred_fk_components = _read_predicted_fks_from_csv(rel_csv)

    P_unary = {_norm_component(t) for t in pred_fk_components}
    T_unary = {_norm_component(t) for t in gt_fk_unary}
    P_rel = {_norm_relation(t) for t in pred_fk_relations}
    T_rel = {_norm_relation(t) for t in gt_fk_relations}

    def _fmt_unary(s):
        return sorted([{"src_table": a, "src_col": b, "tgt_table": c, "tgt_col": d} for (a, b, c, d) in s], key=lambda x: (x["src_table"], x["src_col"]))

    def _fmt_rel(s):
        return sorted([{"src_table": a, "src_cols": list(b), "tgt_table": c, "tgt_cols": list(d)} for (a, b, c, d) in s], key=lambda x: (x["src_table"], x["src_cols"]))

    return {
        "dataset": name,
        "status": "ok",
        "unary": {
            "tp": _fmt_unary(P_unary & T_unary),
            "fp": _fmt_unary(P_unary - T_unary),
            "fn": _fmt_unary(T_unary - P_unary),
        },
        "relation_level": {
            "tp": _fmt_rel(P_rel & T_rel),
            "fp": _fmt_rel(P_rel - T_rel),
            "fn": _fmt_rel(T_rel - P_rel),
        },
    }


def main(argv: list[str]) -> int:
    targets = argv if argv else list(DATASETS.keys())
    out = {}
    for name in targets:
        if name not in DATASETS:
            out[name] = {"status": "unknown_dataset"}
            continue
        out[name] = analyse_one(name, DATASETS[name])
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
