"""Per-dataset PK accuracy split by atomic vs composite ground-truth keys.

Reads `<dataset>/sql_ddl.sql` for ground truth and `<dataset>/schema_final.json`
for predictions, using the same parsers and table-name normalisation as
`eval/score_artefacts.py`.  Output is the per-dataset breakdown reported in
Table~\\ref{tab:pk_atomic_composite} of the paper.

Usage:
    python -m eval.pk_breakdown            # all datasets
    python -m eval.pk_breakdown dvdrental  # one dataset
"""
from __future__ import annotations
import json
import sys

from .ground_truth import parse_ddl
from .score_artefacts import DATASETS, _read_predicted_from_schema_json


def breakdown_one(name, root) -> dict:
    ddl = root / "sql_ddl.sql"
    if not ddl.exists():
        return {"status": "missing_ddl"}
    gt_pks, _, _, _ = parse_ddl(ddl)
    pred_pks, _, _ = _read_predicted_from_schema_json(root / "schema_final.json")
    a_total = a_corr = c_total = c_corr = 0
    for t, gt in gt_pks.items():
        if not gt:
            continue
        is_comp = len(gt) > 1
        match = (set(c.lower() for c in pred_pks.get(t, [])) ==
                 set(c.lower() for c in gt))
        if is_comp:
            c_total += 1
            if match:
                c_corr += 1
        else:
            a_total += 1
            if match:
                a_corr += 1
    return {
        "atomic":    {"correct": a_corr, "total": a_total},
        "composite": {"correct": c_corr, "total": c_total},
        "overall":   {"correct": a_corr + c_corr, "total": a_total + c_total},
    }


def main(argv):
    targets = argv if argv else list(DATASETS.keys())
    out = {}
    for name in targets:
        if name not in DATASETS:
            out[name] = {"status": "unknown_dataset"}
            continue
        out[name] = breakdown_one(name, DATASETS[name])
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
