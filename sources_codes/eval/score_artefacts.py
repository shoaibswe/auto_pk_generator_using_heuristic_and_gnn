"""Re-derive headline tables from the artefacts already in the workspace.

For each dataset we read:
  * `<dataset>/sql_ddl.sql`        -> ground-truth PKs and FKs (parsed by ground_truth.py)
  * `<dataset>/schema_final.json`  -> predicted PKs and FKs (preferred)
  * `<dataset>/relationships.csv`  -> predicted FKs (fallback)

Predicted table/column names are normalised by stripping the `asm_`/`asm__`
prefix and any trailing `_<numeric-timestamp>` suffix used in the V2 pipeline.

Both unary FK-component metrics and full FK-relation metrics are reported.

Usage:
    python -m eval.score_artefacts          # all datasets
    python -m eval.score_artefacts dvdrental tpch
"""
from __future__ import annotations
import ast
import csv
import json
import re
import sys
from pathlib import Path

from .ground_truth import parse_ddl
from .metrics import pk_accuracy, fk_prf


HERE = Path(__file__).resolve().parent.parent  # paper_final/

DATASETS = {
    "dvdrental":      HERE / "dvdrental",
    "chinook":        HERE / "chinook",
    "tpch":           HERE / "tpch",
    "tpcds":          HERE / "tpcds",
    "adventureworks": HERE / "adventureworks",
    "sakila":         HERE / "sakila",
    "northwind":      HERE / "northwind",
}


_TS_SUFFIX = re.compile(r"_\d{6,}$")


def _clean_table(name: str) -> str:
    n = (name or "").strip().lower()
    if n.startswith("asm__"):
        n = n[5:]
    elif n.startswith("asm_"):
        n = n[4:]
    n = _TS_SUFFIX.sub("", n)
    return n.strip("_")


def _maybe_unwrap_list_column(s: str) -> list[str]:
    """`['store_id']` -> ['store_id'];  `store_id` -> ['store_id']."""
    if not s:
        return []
    s = s.strip()
    if s.startswith("[") and s.endswith("]"):
        try:
            v = ast.literal_eval(s)
            if isinstance(v, (list, tuple)):
                return [str(x).strip().lower() for x in v]
        except (ValueError, SyntaxError):
            pass
    return [s.lower()]


def _read_predicted_from_schema_json(path: Path):
    pks: dict[str, list[str]] = {}
    fk_relations: list[tuple[str, tuple[str, ...], str, tuple[str, ...]]] = []
    fk_components: list[tuple[str, str, str, str]] = []
    if not path.exists():
        return pks, fk_relations, fk_components
    obj = json.loads(path.read_text(encoding="utf-8"))
    for raw_table, entries in (obj.get("tables") or {}).items():
        t = _clean_table(raw_table)
        for entry in entries or []:
            kind = entry.get("type")
            cols = [str(c).lower() for c in entry.get("columns", [])]
            if kind == "PK" and cols:
                pks[t] = cols
            elif kind == "FK":
                ref = entry.get("references", {}) or {}
                tgt_t = _clean_table(ref.get("table", ""))
                tgt_cols = ref.get("columns") or []
                if not tgt_cols and ref.get("column"):
                    tgt_cols = [ref.get("column")]
                tgt_cols = [str(c).lower() for c in tgt_cols]
                if cols and tgt_t and tgt_cols and len(cols) == len(tgt_cols):
                    fk_relations.append((t, tuple(cols), tgt_t, tuple(tgt_cols)))
                    for src_col, tgt_col in zip(cols, tgt_cols):
                        fk_components.append((t, src_col, tgt_t, tgt_col))
    return pks, fk_relations, fk_components


def _read_predicted_fks_from_csv(path: Path):
    fk_relations: list[tuple[str, tuple[str, ...], str, tuple[str, ...]]] = []
    fk_components: list[tuple[str, str, str, str]] = []
    if not path.exists():
        return fk_relations, fk_components
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            src_t = row.get("Source Table") or row.get("source_table") or row.get("src_table")
            src_c_raw = row.get("Source Col") or row.get("source_column") or row.get("src_column")
            tgt_t = row.get("Target Table") or row.get("target_table") or row.get("tgt_table")
            tgt_c = row.get("Target Col") or row.get("target_column") or row.get("tgt_column")
            if not (src_t and src_c_raw and tgt_t and tgt_c):
                continue
            src_cols = _maybe_unwrap_list_column(src_c_raw)
            tgt_cols = _maybe_unwrap_list_column(str(tgt_c))
            src_t_clean = _clean_table(src_t)
            tgt_t_clean = _clean_table(tgt_t)
            if src_cols and tgt_cols and len(src_cols) == len(tgt_cols):
                fk_relations.append((src_t_clean, tuple(src_cols), tgt_t_clean, tuple(tgt_cols)))
                for src_col, tgt_col in zip(src_cols, tgt_cols):
                    fk_components.append((src_t_clean, src_col, tgt_t_clean, tgt_col))
    return fk_relations, fk_components


def score_one(name: str, root: Path) -> dict:
    ddl = root / "sql_ddl.sql"
    rel = root / "relationships.csv"
    schema_json = root / "schema_final.json"

    result: dict = {"dataset": name, "status": "ok"}

    if not ddl.exists():
        result["status"] = "missing_ddl"
        return result

    gt_pks, gt_fk_components, gt_fk_unary, gt_fk_relations = parse_ddl(ddl)

    pred_pks, pred_fk_relations, pred_fk_components = _read_predicted_from_schema_json(schema_json)
    if not pred_fk_relations and not pred_fk_components:
        pred_fk_relations, pred_fk_components = _read_predicted_fks_from_csv(rel)

    result["fk_unary"] = fk_prf(pred_fk_components, gt_fk_unary)
    result["fk_all"] = fk_prf(pred_fk_relations, gt_fk_relations)
    if pred_pks:
        acc, c, t = pk_accuracy(pred_pks, gt_pks)
        result["pk"] = {"accuracy": acc, "correct": c, "scored": t}
    else:
        result["pk"] = {"note": "no PK predictions found in schema_final.json"}
    result["counts"] = {
        "gt_fk_components": len(gt_fk_components),
        "gt_fk_unary": len(gt_fk_unary),
        "gt_fk_relations": len(gt_fk_relations),
        "pred_fk_components": len(pred_fk_components),
        "pred_fk_relations": len(pred_fk_relations),
        "gt_pk_tables": len([t for t, cols in gt_pks.items() if cols]),
    }
    return result


def main(argv: list[str]) -> int:
    targets = argv if argv else list(DATASETS.keys())
    out = {}
    for name in targets:
        if name not in DATASETS:
            out[name] = {"status": "unknown_dataset"}
            continue
        out[name] = score_one(name, DATASETS[name])
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
