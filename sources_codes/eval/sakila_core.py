"""Score Sakila on the deduplicated 22-FK *core* set.

The published Sakila DDL declares 40 unary FK constraints, but 18 of those
are duplicates introduced by PostgreSQL inheritance from the
``payment_p2007_*`` partition tables.  Those partition tables ship empty in
the official jOOQ dump, so the cascade cannot recover their copies of the
``payment.<col> -> <other>.<col>`` constraints.  Reporting only against the
inflated 40-constraint set produces a ceiling of recall = 0.50 that is a
property of the dump, not of the cascade.

This script scores the same predicted FK set produced by the headline
pipeline against the deduplicated 22-FK *core* set (all FKs whose source
table is not ``payment_p2007_*``); see Table tab:verified_summary,
second Sakila row.

Output committed at ``paper_final/eval/sakila_core_results.json``.

Usage:
    python -m eval.sakila_core
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

from .ground_truth import parse_ddl
from .metrics import fk_prf
from .score_artefacts import (
    _read_predicted_from_schema_json,
    _read_predicted_fks_from_csv,
)


HERE = Path(__file__).resolve().parent.parent  # paper_final/
SAKILA = HERE / "sakila"


def _is_partition(src_table: str) -> bool:
    return src_table.lower().startswith("payment_p2007")


def main() -> int:
    ddl = SAKILA / "sql_ddl.sql"
    schema_json = SAKILA / "schema_final.json"
    rel = SAKILA / "relationships.csv"

    if not ddl.exists():
        print(json.dumps({"status": "missing_ddl"}, indent=2))
        return 1

    _, _, gt_fk_unary, gt_fk_relations = parse_ddl(ddl)

    # Core: drop FKs whose source table is a payment_p2007_* partition.
    core_unary = [t for t in gt_fk_unary if not _is_partition(t[0])]
    core_relations = [t for t in gt_fk_relations if not _is_partition(t[0])]

    _, pred_relations, pred_components = _read_predicted_from_schema_json(schema_json)
    if not pred_relations and not pred_components:
        pred_relations, pred_components = _read_predicted_fks_from_csv(rel)

    # Mirror what the pipeline outputs: do not penalise the cascade for
    # not predicting the partition-table copies.
    pred_components_core = [t for t in pred_components if not _is_partition(t[0])]
    pred_relations_core = [t for t in pred_relations if not _is_partition(t[0])]

    result = {
        "sakila_core": {
            "status": "ok",
            "ground_truth_full_unary": len(gt_fk_unary),
            "ground_truth_core_unary": len(core_unary),
            "partition_fks_dropped": len(gt_fk_unary) - len(core_unary),
            "fk_unary_core": fk_prf(pred_components_core, core_unary),
            "fk_all_core": fk_prf(pred_relations_core, core_relations),
        }
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
