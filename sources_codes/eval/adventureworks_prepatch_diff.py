"""Pre-patch vs post-patch PK-selection diff for AdventureWorks (atomic only).

The submitted manuscript reports the AdventureWorks numbers AFTER a small
``CamelCase / UUID-aware'' patch to the PK-selection sort key in
adventureworks/Sieve_GNN.ipynb (cell 2506-2528).  The patch consists of two
changes only:

  (a) the self-reference comparison lower-cases the table name, so a
      lower-cased column-base (e.g. ``address'') matches a CamelCase table
      name (e.g. ``Address''), and

  (b) the ``is_uuid_name'' feature already computed in Phase 1 is added as
      the second sort key, demoting columns whose name contains ``uuid'' or
      ``guid'' (e.g. AdventureWorks's Microsoft-replication-artifact
      ``rowguid'' columns) below all non-UUID candidates of the same arity.

Both pre-patch and post-patch sort keys are minimality-first; the difference
matters only for atomic candidates that share arity with the published PK.

This script reconstructs the *atomic-only* PK selection under both rules from
the cached column-level profile in ``adventureworks/data_quality_profile.csv``
plus the published ground-truth DDL.  It does NOT recompute composite
candidates, because the per-composite features are not committed to disk.
This is sufficient to anchor the manuscript's claim that the dominant
pre-patch failure mode was rowguid mis-selection on atomic primary keys.

The output is a JSON committed at:
    paper_final/eval/adventureworks_prepatch_diff.json

Reproducible via:
    python -m eval.adventureworks_prepatch_diff
"""
from __future__ import annotations
import csv
import json
import re
from pathlib import Path

from .ground_truth import parse_ddl


HERE = Path(__file__).resolve().parent.parent  # paper_final/
PROFILE = HERE / "adventureworks" / "data_quality_profile.csv"
DDL = HERE / "adventureworks" / "sql_ddl.sql"
OUT = HERE / "eval" / "adventureworks_prepatch_diff.json"


def _pct(s: str) -> float:
    return float(s.rstrip("%")) / 100.0 if s.endswith("%") else float(s)


def _atomic_candidates_per_table() -> dict[str, list[dict]]:
    """Return per-table list of {col, uniqueness, id_score, is_uuid} dicts,
    filtered to columns with uniqueness > 0.99 (the headline PK threshold)."""
    by_table: dict[str, list[dict]] = {}
    with PROFILE.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                u = _pct(row["Uniqueness"])
            except Exception:
                continue
            if u <= 0.99:
                continue
            by_table.setdefault(row["Table"], []).append({
                "col": row["Column"],
                "uniqueness": u,
                "id_score": float(row["IDLikeScore"]),
                "is_uuid": float(row["UUIDNameFlag"]),
            })
    return by_table


def _self_ref(col: str, table: str, lowercase_table: bool) -> int:
    base = re.sub(r"_?id$", "", col.lower())
    tbl = table.lower() if lowercase_table else table
    return 1 if base == str(tbl) else 0


def _select(cands: list[dict], table: str, *, post_patch: bool) -> str | None:
    if not cands:
        return None
    def key(c):
        sr = _self_ref(c["col"], table, lowercase_table=post_patch)
        if post_patch:
            return (1, c["is_uuid"], -c["id_score"], -sr, 0.0)
        return (1, -c["id_score"], -sr, 0.0)
    return sorted(cands, key=key)[0]["col"]


def _norm(name: str) -> str:
    return name.lower()


def main(argv):
    gt_pks, _, _, _ = parse_ddl(DDL)
    # Map ground-truth atomic PKs by lowered table name.
    gt_atomic = {
        _norm(t): cols[0] for t, cols in gt_pks.items() if len(cols) == 1
    }

    cands = _atomic_candidates_per_table()
    # Index profile-CSV table names by lowered form to match GT.
    table_lookup: dict[str, str] = {}
    for t in cands:
        table_lookup[_norm(t)] = t

    rows = []
    pre_correct = post_correct = 0
    pre_rowguid = 0
    flips_to_id = 0
    for gt_table, gt_col in gt_atomic.items():
        prof_table = table_lookup.get(gt_table)
        if prof_table is None:
            continue
        atomic = cands[prof_table]
        pre = _select(atomic, prof_table, post_patch=False)
        post = _select(atomic, prof_table, post_patch=True)
        match_pre = (pre is not None and _norm(pre) == _norm(gt_col))
        match_post = (post is not None and _norm(post) == _norm(gt_col))
        if match_pre:
            pre_correct += 1
        if match_post:
            post_correct += 1
        if pre is not None and re.search(r"(uuid|guid)", pre.lower()):
            pre_rowguid += 1
        if (pre is not None and post is not None
                and _norm(pre) != _norm(post)
                and re.search(r"(uuid|guid)", pre.lower())
                and not re.search(r"(uuid|guid)", post.lower())):
            flips_to_id += 1
        if pre != post:
            rows.append({
                "table": prof_table,
                "ground_truth_pk": gt_col,
                "pre_patch_pick": pre,
                "post_patch_pick": post,
                "pre_match": match_pre,
                "post_match": match_post,
            })

    out = {
        "scope": (
            "Atomic-only PK reselection on AdventureWorks, comparing the "
            "pre-patch sort key (len(cols), -id_score, -self_ref) without "
            "table-name lower-casing against the post-patch sort key "
            "(len(cols), is_uuid, -id_score, -self_ref) with table-name "
            "lower-casing.  Composite candidates are not reconstructed "
            "because per-composite features are not committed to disk."
        ),
        "atomic_gt_pks_compared": len(gt_atomic),
        "pre_patch_correct_atomic":  pre_correct,
        "post_patch_correct_atomic": post_correct,
        "pre_patch_rowguid_picks": pre_rowguid,
        "flips_uuid_to_id_after_patch": flips_to_id,
        "tables_with_different_pick": rows,
    }
    OUT.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
