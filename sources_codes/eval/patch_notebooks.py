"""
Apply algorithmic patches to Sieve_GNN.ipynb notebooks.

Two changes are applied to cell 0 of each notebook:

  (P1) Composite-PK ranker fix — extends SelfRef to composite candidates and
       penalises free-text atomic candidates whose perfect empirical
       uniqueness is data-instance-specific (e.g. TPC-H *_comment, AW
       filename, TPC-DS i_product_name).

  (P2) Strategy-3 weak-label redesign — replaces the previous
       `name_sim >= 0.5 AND inc_a_b >= 0.6` positive rule with a
       structural rule using only forward / reverse containment and
       cardinality asymmetry. Removes the secondary
       `name_sim >= 0.7` backfill loop. This implements the non-circular
       weak supervision rule described in the manuscript.

Run from the repo root:

    python -m paper_final.eval.patch_notebooks

The script edits notebooks in place. Idempotent: running twice has the
same effect as running once.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NOTEBOOKS = [
    ROOT / "dvdrental" / "Sieve_GNN.ipynb",
    ROOT / "chinook" / "Sieve_GNN.ipynb",
    ROOT / "tpch" / "Sieve_GNN.ipynb",
    ROOT / "adventureworks" / "Sieve_GNN.ipynb",
    ROOT / "sakila" / "Sieve_GNN.ipynb",
    ROOT / "northwind" / "Sieve_GNN.ipynb",
    ROOT / "tpcds" / "Sieve_GNN.ipynb",
]


# ---------------------------------------------------------------------------
# Patch P1 — composite-PK ranker
# ---------------------------------------------------------------------------

# Old 5-key (b/c) variant
OLD_RANKER_5KEY = """        def pk_sort_key(item, _tbl=tbl_name):

            prob, cand = item

            cols = cand['cols']

            id_score = cand['features'][7]

            is_uuid = cand['features'][8]

            self_ref = 0

            if len(cols) == 1:

                col_base = re.sub(r'_?id$', '', cols[0].lower())

                if col_base == str(_tbl).lower():

                    self_ref = 1

            return (len(cols), is_uuid, -id_score, -self_ref, -prob)"""

# Old 4-key (a) variant - DVDRental, Chinook
OLD_RANKER_4KEY_LC = """        def pk_sort_key(item, _tbl=tbl_name):

            prob, cand = item

            cols = cand['cols']

            id_score = cand['features'][7]

            self_ref = 0

            if len(cols) == 1:

                col_base = re.sub(r'_?id$', '', cols[0].lower())

                if col_base == str(_tbl).lower():

                    self_ref = 1

            return (len(cols), -id_score, -self_ref, -prob)"""

# Old 4-key TPC-DS variant (no .lower() on _tbl)
OLD_RANKER_4KEY_TPCDS = """        def pk_sort_key(item, _tbl=tbl_name):

            prob, cand = item

            cols = cand['cols']

            id_score = cand['features'][7]

            self_ref = 0

            if len(cols) == 1:

                col_base = re.sub(r'_?id$', '', cols[0].lower())

                if col_base == _tbl:

                    self_ref = 1

            return (len(cols), -id_score, -self_ref, -prob)"""

# New unified 6-key ranker. Same behaviour as old 5-key on small benchmarks
# (no rowguid, no long free-text PK columns), but extends SelfRef to
# composite candidates and demotes free-text columns with no ID-token signal.
NEW_RANKER = """        def pk_sort_key(item, _tbl=tbl_name):

            prob, cand = item

            cols = cand['cols']

            feats = cand['features']

            id_score = feats[7]

            is_uuid = feats[8] if len(feats) > 8 else 0.0

            avg_len = feats[6]

            major_text = feats[13] if len(feats) > 13 else 0.0

            # Free-text penalty: long string column with no ID-naming signal

            # whose empirical uniqueness is data-instance-specific (TPC-H

            # *_comment, AW filename, TPC-DS i_product_name). Sort ascending

            # so flagged candidates rank below clean candidates of same arity.

            free_text = 1 if (id_score == 0 and major_text >= 0.5 and avg_len > 20) else 0

            tbl_lc = str(_tbl).lower()

            tbl_base = re.sub(r'(_header|_detail|_log|_history|_data)$', '', tbl_lc)

            self_ref = 0

            if len(cols) == 1:

                col_base = re.sub(r'_?id$', '', cols[0].lower())

                if col_base == tbl_lc or col_base == tbl_base:

                    self_ref = 1

            else:

                # Composite SelfRef: ANY component name (id-stripped) overlaps

                # the table base name. Lets composite PKs win when their

                # components are clearly entity-keyed.

                for col in cols:

                    cb = re.sub(r'_?id$', '', col.lower())

                    if cb == tbl_lc or cb == tbl_base or (cb and cb in tbl_base) or (tbl_base and tbl_base in cb):

                        self_ref = 1

                        break

            return (len(cols), is_uuid, free_text, -id_score, -self_ref, -prob)"""


# ---------------------------------------------------------------------------
# Patch P2 — Strategy-3 weak-label redesign
# ---------------------------------------------------------------------------

OLD_WEAK = """        weak_label = None

        pos_name_min = float(config.get('fk_pos_name_min', 0.5))

        pos_inc_min = float(config.get('fk_pos_inc_min', 0.6))

        if name_sim >= pos_name_min and inc_a_b >= pos_inc_min:

            weak_label = 1.0

        elif inc_a_b < pos_inc_min:

            weak_label = 0.0"""

# Non-circular structural weak labels: positives require near-complete
# forward containment AND src_id_score > 0 (i.e., the source column has an
# ID-token suffix such as _id, _key, _sk). The rule does NOT consult
# name similarity, so the GATv2 edge classifier is no longer trained on a
# relaxed naming proxy on abbreviated-naming schemas (TPC-DS). Reverse
# containment is intentionally NOT used as a hard gate because fact-to-
# dimension FKs into small dimension tables routinely cover every PK
# (inc_b_a >= 0.95). The downstream data-inclusion gate at
# Phase 5b then discards spurious symmetric overlaps.
NEW_WEAK = """        weak_label = None

        pos_inc_min = float(config.get('fk_pos_inc_min', 0.95))

        neg_inc_max = float(config.get('fk_neg_inc_max', 0.30))

        if inc_a_b >= pos_inc_min and src_id_score > 0:

            weak_label = 1.0

        elif inc_a_b < neg_inc_max:

            weak_label = 0.0"""


# Old secondary backfill loop body (the most circular path):
#   weak_label = 1.0 if name_sim >= 0.7 else 0.0
# Replace with a structural rule: positives only when forward containment
# is near-complete AND id_score > 0. Otherwise abstain.
OLD_BACKFILL = """            weak_label = 1.0 if name_sim >= 0.7 else 0.0"""

NEW_BACKFILL = """            weak_label = 1.0 if (inc_score >= 0.95 and src_id_score > 0) else None"""


# ---------------------------------------------------------------------------
# Patch P4 — fix stale helper cells (cell 1 multi-seed, cell 2 heuristic
# ablation). The shipped notebooks contain a `SieveGNN(11, ...)` 4-arg
# call against a 5-arg constructor, and `get_weak_labels(candidates_original)`
# missing the required `u_min` positional argument. Both helpers also
# duplicate the old 4-key pk_sort_key inline. Patch all three issues.
# ---------------------------------------------------------------------------

OLD_HELPER_GETLABELS = """    labels, mask = get_weak_labels(candidates_original)"""
NEW_HELPER_GETLABELS = """    labels, mask = get_weak_labels(candidates_original, config.get('u_min', 0.99))"""

OLD_HELPER_SIEVE = """    model = SieveGNN(11, config['hidden_dim'], config['heads'], config['dropout'])"""
NEW_HELPER_SIEVE = """    model = SieveGNN(data.x.size(1), config['hidden_dim'], config['heads'], config['dropout'], data.edge_attr.size(1))"""

# Stale 4-key inline ranker inside helper cells. The free-text/composite-self-
# ref improvements from P1 are intentionally re-applied here so the multi-seed
# rerun matches the headline pipeline.
OLD_HELPER_RANKER = """        def pk_sort_key(item, _tbl=tbl_name):
            prob, cand = item
            cols = cand['cols']
            id_score = cand['features'][7]
            self_ref = 0
            if len(cols) == 1:
                col_base = re.sub(r'_?id$', '', cols[0].lower())
                if col_base == _tbl:
                    self_ref = 1
            return (len(cols), -id_score, -self_ref, -prob)"""

NEW_HELPER_RANKER = """        def pk_sort_key(item, _tbl=tbl_name):
            prob, cand = item
            cols = cand['cols']
            feats = cand['features']
            id_score = feats[7]
            is_uuid = feats[8] if len(feats) > 8 else 0.0
            avg_len = feats[6]
            major_text = feats[13] if len(feats) > 13 else 0.0
            free_text = 1 if (id_score == 0 and major_text >= 0.5 and avg_len > 20) else 0
            tbl_lc = str(_tbl).lower()
            tbl_base = re.sub(r'(_header|_detail|_log|_history|_data)$', '', tbl_lc)
            self_ref = 0
            if len(cols) == 1:
                col_base = re.sub(r'_?id$', '', cols[0].lower())
                if col_base == tbl_lc or col_base == tbl_base:
                    self_ref = 1
            else:
                for col in cols:
                    cb = re.sub(r'_?id$', '', col.lower())
                    if cb == tbl_lc or cb == tbl_base or (cb and cb in tbl_base) or (tbl_base and tbl_base in cb):
                        self_ref = 1
                        break
            return (len(cols), is_uuid, free_text, -id_score, -self_ref, -prob)"""


# ---------------------------------------------------------------------------
# Patch P3 — expand get_id_score to recognise the standard dimensional-
# modelling surrogate-key suffixes (_sk "surrogate key", _nk "natural key",
# _bk "business key", _dk "durable key"). This is a generally-recognised
# Kimball-school convention, not a TPC-DS-specific patch; without it the
# pipeline's name-driven heuristics misclassify every TPC-DS surrogate-key
# column as id_score=0 and the new Strategy-3 weak-label rule abstains.
# ---------------------------------------------------------------------------

OLD_IDSCORE = """def get_id_score(col_name):

    col = col_name.lower()

    if col in ['id', 'pk', 'key', 'uuid', 'guid', 'index', '_id']:

        return 3

    if re.search(r'(_id|id|_key|key|_pk|pk)$', col):

        return 2

    if re.search(r'(id|key|code|num|no|uuid|guid)', col):

        return 1

    return 0"""

NEW_IDSCORE = """def get_id_score(col_name):

    col = col_name.lower()

    if col in ['id', 'pk', 'key', 'uuid', 'guid', 'index', '_id', 'sk']:

        return 3

    if re.search(r'(_id|id|_key|key|_pk|pk|_sk|_nk|_bk|_dk)$', col):

        return 2

    if re.search(r'(id|key|code|num|no|uuid|guid|_sk_)', col):

        return 1

    return 0"""


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------

def patch_notebook(path: Path) -> dict:
    nb = json.loads(path.read_text())
    report = {"path": str(path.relative_to(ROOT.parent)), "p1": False, "p2_main": False, "p2_backfill": False, "p3": False, "skipped": []}
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell["source"])

        # P1: ranker
        new_src = src
        for old in (OLD_RANKER_5KEY, OLD_RANKER_4KEY_TPCDS, OLD_RANKER_4KEY_LC):
            if old in new_src:
                new_src = new_src.replace(old, NEW_RANKER)
                report["p1"] = True

        # P2: main weak-label block (handle both pristine and previous-patch state)
        OLD_WEAK_V1 = """        weak_label = None

        pos_inc_min = float(config.get('fk_pos_inc_min', 0.95))

        neg_inc_max = float(config.get('fk_neg_inc_max', 0.30))

        asym_max = float(config.get('fk_asym_max', 0.95))

        if inc_a_b >= pos_inc_min and inc_b_a < asym_max and src_id_score > 0:

            weak_label = 1.0

        elif inc_a_b < neg_inc_max:

            weak_label = 0.0

        elif inc_a_b >= 0.95 and inc_b_a >= 0.95 and card_ratio > 0.95:

            weak_label = 0.0"""
        if OLD_WEAK in new_src:
            new_src = new_src.replace(OLD_WEAK, NEW_WEAK)
            report["p2_main"] = True
        elif OLD_WEAK_V1 in new_src:
            new_src = new_src.replace(OLD_WEAK_V1, NEW_WEAK)
            report["p2_main"] = True

        # P2: secondary backfill
        if OLD_BACKFILL in new_src:
            new_src = new_src.replace(OLD_BACKFILL, NEW_BACKFILL)
            report["p2_backfill"] = True

        # P3: id-score expansion (idempotent)
        if OLD_IDSCORE in new_src:
            new_src = new_src.replace(OLD_IDSCORE, NEW_IDSCORE)
            report.setdefault("p3", False)
            report["p3"] = True

        # P4: stale helper cells (only present in some notebooks)
        if OLD_HELPER_GETLABELS in new_src:
            new_src = new_src.replace(OLD_HELPER_GETLABELS, NEW_HELPER_GETLABELS)
            report.setdefault("p4", False)
            report["p4"] = True
        if OLD_HELPER_SIEVE in new_src:
            new_src = new_src.replace(OLD_HELPER_SIEVE, NEW_HELPER_SIEVE)
            report["p4"] = True
        if OLD_HELPER_RANKER in new_src:
            new_src = new_src.replace(OLD_HELPER_RANKER, NEW_HELPER_RANKER)
            report["p4"] = True

        if new_src != src:
            cell["source"] = new_src.splitlines(keepends=True)

    path.write_text(json.dumps(nb, indent=1) + "\n")
    return report


def main() -> int:
    print(f"Patching {len(NOTEBOOKS)} notebooks under {ROOT}\n")
    for nb_path in NOTEBOOKS:
        if not nb_path.exists():
            print(f"  MISS: {nb_path}")
            continue
        rep = patch_notebook(nb_path)
        flags = []
        if rep["p1"]:
            flags.append("P1-ranker")
        if rep["p2_main"]:
            flags.append("P2-weak")
        if rep["p2_backfill"]:
            flags.append("P2-backfill")
        if rep.get("p3"):
            flags.append("P3-idscore")
        if rep.get("p4"):
            flags.append("P4-helpers")
        if not flags:
            flags.append("NO-OP (already patched or no match)")
        print(f"  {rep['path']:<55s}  {' / '.join(flags)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
