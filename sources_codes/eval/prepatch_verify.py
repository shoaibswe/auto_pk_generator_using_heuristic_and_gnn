"""Pre-patch vs post-patch PK-selection verification (atomic only).

Generalises ``adventureworks_prepatch_diff`` to every dataset whose PK
selection is the standard ``data_quality_profile.csv``-driven pipeline.

The patch consists of two changes to the PK sort key:

  (a) the self-reference comparison lower-cases the table name, so a
      lower-cased column-base (e.g. ``address'') matches a CamelCase table
      name (e.g. ``Address''), and
  (b) the ``is_uuid_name'' feature is added as the second sort key,
      demoting columns whose name contains ``uuid'' or ``guid'' below all
      non-UUID candidates of the same arity.

For every dataset in DATASETS we reconstruct atomic-only PK selection under
both rules from the cached ``data_quality_profile.csv`` and check (i)
whether the two rules pick the same column per table, and (ii) whether each
pick matches the published ground-truth atomic PK.  Composite candidates
are not reconstructed because per-composite features are not committed.

Output committed at ``paper_final/eval/prepatch_verify.json``.

Reproducible via:
    python -m eval.prepatch_verify
"""
from __future__ import annotations
import csv
import json
import re
from pathlib import Path

from .ground_truth import parse_ddl


HERE = Path(__file__).resolve().parent.parent  # paper_final/

DATASETS = [
    "dvdrental",
    "chinook",
    "tpch",
    "adventureworks",
    "sakila",
    "northwind",
]

_TS_SUFFIX = re.compile(r"_\d{6,}$")


def _clean_table(name: str) -> str:
    n = (name or "").strip().lower()
    if n.startswith("asm__"):
        n = n[5:]
    elif n.startswith("asm_"):
        n = n[4:]
    n = _TS_SUFFIX.sub("", n)
    return n.strip("_")


def _pct(s: str) -> float:
    s = (s or "").strip()
    if not s:
        return 0.0
    return float(s.rstrip("%")) / 100.0 if s.endswith("%") else float(s)


def _atomic_candidates(profile_csv: Path) -> dict[str, list[dict]]:
    by_table: dict[str, list[dict]] = {}
    if not profile_csv.exists():
        return by_table
    with profile_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                u = _pct(row.get("Uniqueness", ""))
            except Exception:
                continue
            if u <= 0.99:
                continue
            t = _clean_table(row["Table"])
            try:
                id_score = float(row.get("IDLikeScore") or 0)
            except Exception:
                id_score = 0.0
            try:
                is_uuid = float(row.get("UUIDNameFlag") or 0)
            except Exception:
                is_uuid = 0.0
            by_table.setdefault(t, []).append({
                "col": row["Column"],
                "uniqueness": u,
                "id_score": id_score,
                "is_uuid": is_uuid,
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


def _verify_one(dataset: str) -> dict:
    profile = HERE / dataset / "data_quality_profile.csv"
    ddl = HERE / dataset / "sql_ddl.sql"
    if not ddl.exists():
        return {"dataset": dataset, "status": "no_ddl"}
    if not profile.exists():
        return {"dataset": dataset, "status": "no_profile"}

    gt_pks, _, _, _ = parse_ddl(ddl)
    gt_atomic = {
        _clean_table(t): cols[0].lower()
        for t, cols in gt_pks.items()
        if len(cols) == 1
    }

    cands = _atomic_candidates(profile)

    pre_correct = post_correct = 0
    pre_uuid = 0
    differs = []
    pre_only_match = post_only_match = 0
    for t, gt_col in gt_atomic.items():
        atomic = cands.get(t, [])
        pre = _select(atomic, t, post_patch=False)
        post = _select(atomic, t, post_patch=True)
        m_pre = (pre is not None and pre.lower() == gt_col)
        m_post = (post is not None and post.lower() == gt_col)
        if m_pre:
            pre_correct += 1
        if m_post:
            post_correct += 1
        if pre is not None and re.search(r"(uuid|guid)", pre.lower()):
            pre_uuid += 1
        if pre != post:
            differs.append({
                "table": t,
                "gt": gt_col,
                "pre": pre,
                "post": post,
                "pre_match": m_pre,
                "post_match": m_post,
            })
        if m_pre and not m_post:
            pre_only_match += 1
        if m_post and not m_pre:
            post_only_match += 1

    return {
        "dataset": dataset,
        "status": "ok",
        "atomic_gt_pks_compared": len(gt_atomic),
        "pre_patch_correct_atomic": pre_correct,
        "post_patch_correct_atomic": post_correct,
        "pre_patch_uuid_picks": pre_uuid,
        "tables_with_different_pick": len(differs),
        "post_patch_only_match": post_only_match,
        "pre_patch_only_match": pre_only_match,
        "diffs": differs,
    }


def main(argv=None):
    out = {"datasets": [_verify_one(d) for d in DATASETS]}
    summary = {
        d["dataset"]: {
            "compared": d.get("atomic_gt_pks_compared"),
            "pre": d.get("pre_patch_correct_atomic"),
            "post": d.get("post_patch_correct_atomic"),
            "differ": d.get("tables_with_different_pick"),
            "pre_uuid_picks": d.get("pre_patch_uuid_picks"),
        }
        for d in out["datasets"] if d.get("status") == "ok"
    }
    out["summary"] = summary
    out_path = HERE / "eval" / "prepatch_verify.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
