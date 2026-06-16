"""LLM-based PK/FK extraction baseline using a local Ollama server.

Sends the dataset's `sql_ddl.sql` to a local Ollama model with a strict JSON
output contract, then scores the parsed PK/FK set against ground truth.

Default model: `llama3.1:8b-instruct-q4_K_M` -- override with --model.
The script never sends raw row data; only the DDL text is sent.

Usage:
    ollama serve &
    ollama pull llama3.1:8b-instruct-q4_K_M
    python -m eval.llm_baseline                          # all datasets
    python -m eval.llm_baseline --model qwen2.5:7b dvdrental
"""
from __future__ import annotations
import argparse
import json
import sys
import textwrap
import urllib.request
from pathlib import Path

from .ground_truth import parse_ddl
from .metrics import pk_accuracy, fk_prf


HERE = Path(__file__).resolve().parent.parent
DATASETS = {
    "dvdrental": HERE / "dvdrental",
    "chinook":   HERE / "chinook",
    "tpch":      HERE / "tpch",
    "tpcds":     HERE / "tpcds",
}

OLLAMA_URL = "http://localhost:11434/api/generate"

PROMPT = textwrap.dedent("""\
    You are a database schema analyser.  Given the SQL DDL below, identify:
      1. the primary key columns of each table,
      2. all foreign-key relationships.

    Output strictly valid JSON with this shape, no commentary, no markdown:

    {
      "primary_keys": { "<table>": ["<col>", ...], ... },
      "foreign_keys": [
                { "src_table": "...", "src_columns": ["...", "..."],
                    "tgt_table": "...", "tgt_columns": ["...", "..."] },
        ...
      ]
    }

    DDL:
    ```sql
    {ddl}
    ```
    """)


def call_ollama(model: str, ddl_text: str, timeout: int = 600) -> str:
    body = json.dumps({
        "model": model,
        "prompt": PROMPT.replace("{ddl}", ddl_text),
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.0},
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("response", "")


def parse_llm_response(s: str) -> tuple[
    dict[str, list[str]],
    list[tuple[str, tuple[str, ...], str, tuple[str, ...]]],
    list[tuple[str, str, str, str]],
]:
    obj = json.loads(s)
    pks_raw = obj.get("primary_keys", {}) or {}
    fks_raw = obj.get("foreign_keys", []) or []
    pks = {str(t).lower(): [str(c).lower() for c in cols] for t, cols in pks_raw.items()}
    fk_relations = []
    fk_components = []
    for fk in fks_raw:
        try:
            src_cols = fk.get("src_columns") or []
            tgt_cols = fk.get("tgt_columns") or []
            if not src_cols and fk.get("src_column"):
                src_cols = [fk["src_column"]]
            if not tgt_cols and fk.get("tgt_column"):
                tgt_cols = [fk["tgt_column"]]
            src_table = str(fk["src_table"]).lower()
            tgt_table = str(fk["tgt_table"]).lower()
            src_cols = tuple(str(c).lower() for c in src_cols)
            tgt_cols = tuple(str(c).lower() for c in tgt_cols)
            if not src_cols or not tgt_cols or len(src_cols) != len(tgt_cols):
                continue
            fk_relations.append((src_table, src_cols, tgt_table, tgt_cols))
            for src_col, tgt_col in zip(src_cols, tgt_cols):
                fk_components.append((src_table, src_col, tgt_table, tgt_col))
        except (KeyError, TypeError):
            continue
    return pks, fk_relations, fk_components


def score_one(name: str, root: Path, model: str) -> dict:
    ddl = root / "sql_ddl.sql"
    if not ddl.exists():
        return {"status": "missing_ddl"}
    ddl_text = ddl.read_text(encoding="utf-8", errors="ignore")
    try:
        raw = call_ollama(model, ddl_text)
    except Exception as exc:  # noqa: BLE001
        return {"status": "ollama_error", "error": str(exc)}
    try:
        pred_pks, pred_fk_relations, pred_fk_components = parse_llm_response(raw)
    except Exception as exc:  # noqa: BLE001
        return {"status": "parse_error", "error": str(exc), "raw": raw[:500]}
    gt_pks, gt_fk_components, gt_fk_unary, gt_fk_relations = parse_ddl(ddl)
    pk_acc, c, t = pk_accuracy(pred_pks, gt_pks)
    return {
        "status": "ok",
        "model": model,
        "pk": {"accuracy": pk_acc, "correct": c, "scored": t},
        "fk_unary": fk_prf(pred_fk_components, gt_fk_unary),
        "fk_all": fk_prf(pred_fk_relations, gt_fk_relations),
        "counts": {
            "pred_fk_components": len(pred_fk_components),
            "pred_fk_relations": len(pred_fk_relations),
            "gt_fk_unary": len(gt_fk_unary),
            "gt_fk_components": len(gt_fk_components),
            "gt_fk_relations": len(gt_fk_relations),
        },
    }


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="llama3.1:8b-instruct-q4_K_M")
    p.add_argument("datasets", nargs="*")
    args = p.parse_args(argv)

    targets = args.datasets if args.datasets else list(DATASETS.keys())
    out = {}
    for name in targets:
        if name not in DATASETS:
            out[name] = {"status": "unknown_dataset"}
            continue
        out[name] = score_one(name, DATASETS[name], args.model)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
