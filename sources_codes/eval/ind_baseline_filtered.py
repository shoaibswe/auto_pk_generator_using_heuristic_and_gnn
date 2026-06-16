"""Stronger IND baselines: data-inclusion + lightweight post-filters.

This script extends `eval/ind_baseline.py` with two additional baselines that
use the *same* unfiltered unary-IND candidate set but apply increasingly
realistic post-filters.  The point is to probe how much of \\methodname{}'s
precision lift comes from the data-validation gate, the naming filter, and
the combination, before any graph-attention component is involved.

Three baselines:
  1. ``ind_only``    -- the existing unfiltered unary IND baseline
                       (data-inclusion >= 0.95, cardinality cap 1.05x).
  2. ``ind_idscore`` -- ind_only filtered to source columns whose name has
                       an ID-token signal (id, key, code, num, no, _id,
                       _key, ...).  This is the cheapest realistic filter a
                       practitioner would apply to BINDER/SPIDER output.
  3. ``ind_idscore_namesim`` -- ind_idscore additionally filtered to
                       (src_col, tgt_table) pairs whose name similarity
                       (singular/plural-aware) is >= 0.5.  This is the same
                       NameSim signal \\methodname{} uses in Strategy 1, applied
                       on top of an unfiltered IND tool's output.

Reproducible via:
    python -m eval.ind_baseline_filtered            # all four datasets
    python -m eval.ind_baseline_filtered tpch       # one dataset
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

from .ground_truth import parse_ddl
from .metrics import fk_prf
from .ind_baseline import (
    DATASETS, CARDINALITY_CAP_RATIO, CONTAINMENT_THRESHOLD,
    discover_inds, _as_unary_relations,
)


# ---- naming heuristics: identical in spirit to those in the headline cascade ----

ID_TOKENS_EXACT = {"id", "pk", "key", "uuid", "guid", "index"}
ID_TOKENS_SUFFIX = ("_id", "id", "_key", "key", "_pk", "pk")
ID_TOKENS_INFIX = ("id", "key", "code", "num", "no")
KEY_LIKE_SUFFIXES = ("_id", "_key", "_code", "_no", "_num")


def id_score(col: str) -> int:
    c = col.lower()
    if c in ID_TOKENS_EXACT or c == "_id":
        return 3
    for s in ID_TOKENS_SUFFIX:
        if c.endswith(s) and c != s:
            return 2
    for inf in ID_TOKENS_INFIX:
        if inf in c:
            return 1
    return 0


def _strip_keylike_suffix(col: str) -> str:
    c = col.lower()
    for s in KEY_LIKE_SUFFIXES:
        if c.endswith(s) and len(c) > len(s):
            return c[: -len(s)]
    return c


def _strip_short_prefix(col: str) -> str:
    """Strip a leading 1-2 char prefix followed by underscore (TPC-H l_, ps_, ...)."""
    m = re.match(r"^[a-z]{1,2}_(.+)$", col.lower())
    return m.group(1) if m else col.lower()


def _name_sim(src_col: str, tgt_table: str) -> float:
    base = _strip_keylike_suffix(src_col)
    base = _strip_short_prefix(base)
    tgt = tgt_table.lower()
    tgt_short = _strip_short_prefix(tgt)
    if base == tgt or base == tgt_short:
        return 1.0
    # singular/plural agreement
    if base + "s" == tgt or base == tgt + "s":
        return 0.9
    if base + "s" == tgt_short or base == tgt_short + "s":
        return 0.9
    if base in tgt or tgt in base:
        return 0.7
    if base in tgt_short or tgt_short in base:
        return 0.7
    return 0.0


def _filter_by_idscore(edges):
    return [e for e in edges if id_score(e[1]) > 0]


def _filter_by_namesim(edges, threshold: float):
    return [e for e in edges if _name_sim(e[1], e[2]) >= threshold]


def _exclude_self_pk(edges, pks: dict[str, list[str]]):
    """Skip src cols that are the *sole* PK of their own table -- this matches
    the Strategy-1 'no circular references' rule in the cascade."""
    out = []
    for src_t, src_c, tgt_t, tgt_c in edges:
        spk = pks.get(src_t, [])
        if len(spk) == 1 and spk[0].lower() == src_c.lower():
            continue
        out.append((src_t, src_c, tgt_t, tgt_c))
    return out


def main(argv):
    targets = argv if argv else list(DATASETS.keys())
    results = {}
    for name in targets:
        if name not in DATASETS:
            results[name] = {"status": "unknown_dataset"}
            continue
        root = DATASETS[name]
        ddl = root / "sql_ddl.sql"
        if not ddl.exists():
            results[name] = {"status": "missing_ddl"}
            continue
        pks, fk_components, fk_unary, fk_relations = parse_ddl(ddl)

        ind_all = discover_inds(root)
        ind_id = _filter_by_idscore(ind_all)
        ind_id_excl = _exclude_self_pk(ind_id, pks)
        ind_id_name = _filter_by_namesim(ind_id_excl, 0.5)
        ind_id_name07 = _filter_by_namesim(ind_id_excl, 0.7)

        results[name] = {
            "status": "ok",
            "gt_unary_count": len(fk_unary),
            "gt_relation_count": len(fk_relations),
            "ind_only": {
                "n": len(ind_all),
                "unary": fk_prf(ind_all, fk_unary),
                "all":   fk_prf(_as_unary_relations(ind_all), fk_relations),
            },
            "ind_idscore": {
                "n": len(ind_id),
                "unary": fk_prf(ind_id, fk_unary),
                "all":   fk_prf(_as_unary_relations(ind_id), fk_relations),
            },
            "ind_idscore_namesim_0_5": {
                "n": len(ind_id_name),
                "unary": fk_prf(ind_id_name, fk_unary),
                "all":   fk_prf(_as_unary_relations(ind_id_name), fk_relations),
            },
            "ind_idscore_namesim_0_7": {
                "n": len(ind_id_name07),
                "unary": fk_prf(ind_id_name07, fk_unary),
                "all":   fk_prf(_as_unary_relations(ind_id_name07), fk_relations),
            },
        }
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
