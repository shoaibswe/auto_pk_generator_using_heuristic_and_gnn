"""Multi-seed wrapper: re-execute each dataset's Sieve_GNN.ipynb with a sweep of
random seeds and collect the printed metrics into a single JSON.

Implementation note: the existing notebooks set `SEED = 42` at the top of
the training cell.  This wrapper uses `papermill` to inject `SEED` as a
notebook parameter; the cell tagged `parameters` in each notebook (or the
first code cell if no tag is present) is overwritten with the seed.

Usage:
    pip install papermill
    python -m eval.multi_seed --seeds 13 17 42 123 2024
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
NOTEBOOKS = {
    "dvdrental": HERE / "dvdrental" / "Sieve_GNN.ipynb",
    "chinook":   HERE / "chinook"   / "Sieve_GNN.ipynb",
    "tpch":      HERE / "tpch"      / "Sieve_GNN.ipynb",
}

_METRIC_RE = re.compile(
    r"PK=(\d+)/(\d+)\s+FK P=([0-9.]+)\s+R=([0-9.]+)\s+F1=([0-9.]+)",
    re.IGNORECASE,
)


def _extract_metrics_from_notebook(nb_path: Path) -> dict:
    try:
        obj = json.loads(nb_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"status": "parse_error", "error": str(exc)}

    matches: list[tuple[int, int, float, float, float]] = []
    for cell in obj.get("cells", []):
        for out in cell.get("outputs", []):
            texts = []
            if "text" in out:
                texts.append("".join(out.get("text", [])))
            if "data" in out and "text/plain" in out["data"]:
                plain = out["data"]["text/plain"]
                texts.append("".join(plain) if isinstance(plain, list) else str(plain))
            for text in texts:
                for m in _METRIC_RE.finditer(text):
                    matches.append((
                        int(m.group(1)),
                        int(m.group(2)),
                        float(m.group(3)),
                        float(m.group(4)),
                        float(m.group(5)),
                    ))
    if not matches:
        return {"status": "metrics_missing"}

    pk_correct, pk_total, fk_precision, fk_recall, fk_f1 = matches[-1]
    return {
        "status": "ok",
        "pk_correct": pk_correct,
        "pk_total": pk_total,
        "pk_accuracy": pk_correct / pk_total if pk_total else 0.0,
        "fk_precision": fk_precision,
        "fk_recall": fk_recall,
        "fk_f1": fk_f1,
    }


def _mean_std(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "mean": None, "std": None}
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return {"n": len(values), "mean": mean, "std": var ** 0.5}


def _split_seed_and_dataset_args(argv: list[str]) -> list[str]:
    """Allow `--seeds 13 dvdrental` by stopping seed collection at first non-int."""
    if "--seeds" not in argv:
        return argv

    index = argv.index("--seeds")
    rewritten = argv[: index + 1]
    tail = argv[index + 1 :]
    seed_args: list[str] = []
    dataset_args: list[str] = []
    parsing_seeds = True

    for token in tail:
        if parsing_seeds:
            try:
                int(token)
            except ValueError:
                parsing_seeds = False
                dataset_args.append(token)
            else:
                seed_args.append(token)
        else:
            dataset_args.append(token)

    if dataset_args:
        return rewritten + seed_args + ["--"] + dataset_args
    return rewritten + seed_args


def _prepare_seeded_notebook(src_nb: Path, dst_nb: Path, seed: int) -> None:
    obj = json.loads(src_nb.read_text(encoding="utf-8"))
    for cell in obj.get("cells", []):
        source = cell.get("source", [])
        if not isinstance(source, list):
            continue
        updated = []
        changed = False
        for line in source:
            if re.match(r"\s*NUM_SEEDS\s*=", line):
                updated.append("NUM_SEEDS = 1\n")
                changed = True
            elif re.match(r"\s*SEEDS\s*=", line):
                updated.append(f"SEEDS = [{seed}]\n")
                changed = True
            elif "labels, mask = get_weak_labels(candidates_original)" in line:
                updated.append("    labels, mask = get_weak_labels(candidates_original, config['u_min'], config.get('manual_pk_labels'))\n")
                changed = True
            elif "labels, mask = get_weak_labels(all_candidates)" in line:
                updated.append("    labels, mask = get_weak_labels(all_candidates, CONFIG['u_min'], CONFIG.get('manual_pk_labels'))\n")
                changed = True
            elif "model = SieveGNN(11, config['hidden_dim'], config['heads'], config['dropout'])" in line:
                updated.append("    model = SieveGNN(data.x.size(1), config['hidden_dim'], config['heads'], config['dropout'], edge_dim=data.edge_attr.size(1))\n")
                changed = True
            elif "model = SieveGNN(11, CONFIG['hidden_dim'], CONFIG['heads'], CONFIG['dropout'])" in line:
                updated.append("    model = SieveGNN(data.x.size(1), CONFIG['hidden_dim'], CONFIG['heads'], CONFIG['dropout'], edge_dim=data.edge_attr.size(1))\n")
                changed = True
            elif "criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([3.0]))" in line:
                updated.append("    criterion = nn.NLLLoss()\n")
                changed = True
            elif "loss = criterion(out[mask].squeeze(), labels[mask])" in line:
                updated.append("        loss = criterion(out[mask], labels[mask])\n")
                changed = True
            elif "probs = torch.sigmoid(model(data)).squeeze().numpy()" in line:
                updated.append("        probs = torch.exp(model(data))[:, 1].numpy()\n")
                changed = True
            else:
                updated.append(line)
        if changed:
            cell["source"] = updated
    dst_nb.write_text(json.dumps(obj), encoding="utf-8")


def run_one(name: str, nb_path: Path, seed: int, out_dir: Path) -> dict:
    try:
        import papermill as pm  # type: ignore
    except ImportError:
        return {"status": "papermill_missing", "hint": "pip install papermill"}
    out_dir.mkdir(parents=True, exist_ok=True)
    seeded_nb = out_dir / f"{name}_seed{seed}_input.ipynb"
    out_nb = out_dir / f"{name}_seed{seed}.ipynb"
    try:
        _prepare_seeded_notebook(nb_path, seeded_nb, seed)
        pm.execute_notebook(
            str(seeded_nb), str(out_nb),
            kernel_name="python3",
            cwd=str(nb_path.parent),
        )
        metrics = _extract_metrics_from_notebook(out_nb)
        return {"status": "ok", "out_nb": str(out_nb), "metrics": metrics}
    except Exception as exc:  # noqa: BLE001
        if out_nb.exists():
            metrics = _extract_metrics_from_notebook(out_nb)
            if metrics.get("status") == "ok":
                return {
                    "status": "partial_ok",
                    "out_nb": str(out_nb),
                    "metrics": metrics,
                    "error": str(exc),
                }
        return {"status": "execution_error", "error": str(exc)}


def main(argv: list[str]) -> int:
    argv = _split_seed_and_dataset_args(argv)
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, nargs="+", default=[13, 17, 42, 123, 2024])
    p.add_argument("--out", default=str(HERE / "eval" / "multi_seed_runs"))
    p.add_argument("datasets", nargs="*")
    args = p.parse_args(argv)

    targets = args.datasets if args.datasets else list(NOTEBOOKS.keys())
    results: dict = {}
    out_dir = Path(args.out)
    for name in targets:
        if name not in NOTEBOOKS:
            results[name] = {"status": "unknown_dataset"}
            continue
        results.setdefault(name, {})
        metric_rows: list[dict] = []
        for seed in args.seeds:
            one = run_one(name, NOTEBOOKS[name], seed, out_dir / name)
            results[name][str(seed)] = one
            if one.get("status") in {"ok", "partial_ok"} and one.get("metrics", {}).get("status") == "ok":
                metric_rows.append(one["metrics"])
        if metric_rows:
            results[name]["summary"] = {
                "pk_accuracy": _mean_std([m["pk_accuracy"] for m in metric_rows]),
                "fk_precision": _mean_std([m["fk_precision"] for m in metric_rows]),
                "fk_recall": _mean_std([m["fk_recall"] for m in metric_rows]),
                "fk_f1": _mean_std([m["fk_f1"] for m in metric_rows]),
            }
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
