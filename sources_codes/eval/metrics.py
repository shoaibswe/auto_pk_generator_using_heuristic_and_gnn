"""Set-based PK / FK metrics used across the eval pack."""
from __future__ import annotations
from typing import Iterable


def pk_accuracy(predicted: dict[str, list[str]], truth: dict[str, list[str]]) -> tuple[float, int, int]:
    """Fraction of tables whose predicted PK column-set matches truth.

    A predicted PK matches if (a) the table is in truth and (b) the unordered
    set of predicted columns equals the truth set.  Tables with no truth PK
    are skipped from both numerator and denominator.
    """
    correct = 0
    total = 0
    for table, gt_cols in truth.items():
        if not gt_cols:
            continue
        total += 1
        pred = predicted.get(table, [])
        if set(c.lower() for c in pred) == set(c.lower() for c in gt_cols):
            correct += 1
    if total == 0:
        return 0.0, 0, 0
    return correct / total, correct, total


def _norm_value(value):
    if isinstance(value, str):
        return value.lower()
    if isinstance(value, (list, tuple)):
        return tuple(_norm_value(v) for v in value)
    return value


def _fk_key(t: tuple) -> tuple:
    return tuple(_norm_value(v) for v in t)


def fk_prf(predicted: Iterable[tuple], truth: Iterable[tuple]) -> dict:
    P = {_fk_key(t) for t in predicted}
    T = {_fk_key(t) for t in truth}
    tp = len(P & T)
    fp = len(P - T)
    fn = len(T - P)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec, "f1": f1}
