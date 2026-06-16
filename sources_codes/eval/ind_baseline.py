"""Brute-force unary inclusion-dependency baseline.

For every cross-table column pair (src, tgt) compute |unique(src) - unique(tgt)|
and accept the pair as a candidate FK if:

  * unique(src) is non-empty,
  * |unique(src) \\ unique(tgt)| / |unique(src)| <= (1 - containment_threshold),
  * |unique(src)| <= cardinality_cap_ratio * |unique(tgt)|.

Then score the resulting set against ground truth parsed from the dataset's
sql_ddl.sql.

Usage:
    python -m eval.ind_baseline dvdrental tpch chinook tpcds
    python -m eval.ind_baseline                       # default: all four

Notes:
    * This is intentionally naive; it is the closest data-only baseline already
      present in the executed TPC-H notebook (see Section Results in the paper).
    * Memory-light: each column is loaded once, kept as a Python set, dropped
      after all cross-comparisons against later columns are done.
"""
from __future__ import annotations
import csv
import json
import sys
from pathlib import Path

from .ground_truth import parse_ddl
from .metrics import fk_prf


HERE = Path(__file__).resolve().parent.parent

DATASETS = {
    "dvdrental":      HERE / "dvdrental",
    "chinook":        HERE / "chinook",
    "tpch":           HERE / "tpch",
    "tpcds":          HERE / "tpcds",
    "adventureworks": HERE / "adventureworks",
    "sakila":         HERE / "sakila",
    "northwind":      HERE / "northwind",
}

CONTAINMENT_THRESHOLD = 0.95
CARDINALITY_CAP_RATIO = 1.05


def _data_dir(root: Path) -> Path:
    # data is shipped under <dataset>/data; tpcds uses data/csv
    if (root / "data" / "csv").exists():
        return root / "data" / "csv"
    return root / "data"


def _csv_files(root: Path) -> list[Path]:
    d = _data_dir(root)
    return sorted([p for p in d.glob("*.csv") if p.is_file()])


def _table_name_from_filename(p: Path) -> str:
    name = p.stem.lower()
    # strip common prefixes used in the workspace (asm_*) and trailing timestamp suffixes
    if name.startswith("asm__"):
        name = name[5:]
    elif name.startswith("asm_"):
        name = name[4:]
    # drop trailing _<digits> timestamp suffix
    parts = name.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) >= 6:
        name = parts[0]
    return name.strip("_")


def _load_columns(csv_path: Path) -> dict[str, set[str]]:
    cols: dict[str, list[str]] = {}
    with csv_path.open(encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return {}
        header = [h.strip().lower() for h in header]
        for h in header:
            cols[h] = []
        for row in reader:
            for h, v in zip(header, row):
                if v != "" and v is not None:
                    cols[h].append(v)
    return {h: set(vs) for h, vs in cols.items() if vs}


def discover_inds(root: Path) -> list[tuple[str, str, str, str]]:
    files = _csv_files(root)
    tables: dict[str, dict[str, set[str]]] = {}
    for fp in files:
        t = _table_name_from_filename(fp)
        tables[t] = _load_columns(fp)

    out: list[tuple[str, str, str, str]] = []
    table_names = list(tables.keys())
    for i, t_src in enumerate(table_names):
        for c_src, v_src in tables[t_src].items():
            n_src = len(v_src)
            if n_src == 0:
                continue
            for j, t_tgt in enumerate(table_names):
                if t_tgt == t_src:
                    continue
                for c_tgt, v_tgt in tables[t_tgt].items():
                    n_tgt = len(v_tgt)
                    if n_tgt == 0:
                        continue
                    if n_src > CARDINALITY_CAP_RATIO * n_tgt:
                        continue
                    missing = len(v_src - v_tgt)
                    contain = 1.0 - (missing / n_src)
                    if contain >= CONTAINMENT_THRESHOLD:
                        out.append((t_src, c_src, t_tgt, c_tgt))
    return out


def _as_unary_relations(edges: list[tuple[str, str, str, str]]) -> list[tuple[str, tuple[str, ...], str, tuple[str, ...]]]:
    return [(src_t, (src_c,), tgt_t, (tgt_c,)) for src_t, src_c, tgt_t, tgt_c in edges]


def main(argv: list[str]) -> int:
    targets = argv if argv else list(DATASETS.keys())
    results: dict = {}
    for name in targets:
        if name not in DATASETS:
            results[name] = {"status": "unknown_dataset"}
            continue
        root = DATASETS[name]
        ddl = root / "sql_ddl.sql"
        if not ddl.exists():
            results[name] = {"status": "missing_ddl"}
            continue
        _, gt_fk_components, gt_fk_unary, gt_fk_relations = parse_ddl(ddl)
        pred = discover_inds(root)
        results[name] = {
            "status": "ok",
            "ind_baseline_unary": fk_prf(pred, gt_fk_unary),
            "ind_baseline_all": fk_prf(_as_unary_relations(pred), gt_fk_relations),
            "predicted_count": len(pred),
            "gt_unary_count": len(gt_fk_unary),
            "gt_component_total": len(gt_fk_components),
            "gt_relation_total": len(gt_fk_relations),
        }
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
