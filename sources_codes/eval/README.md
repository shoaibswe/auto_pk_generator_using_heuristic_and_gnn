# Reproducibility Pack — Sieve-GNN paper

This directory bundles the scripts used to regenerate the DDL-grounded non-LLM
results reported in `paper_final/main.tex`.  All scripts are pure-Python
(stdlib + optional `papermill` for multi-seed); no notebook re-execution is
required for the headline artefact, internal IND ladder, or external baseline
numbers.

## Layout

```
eval/
  ground_truth.py     # SQL DDL parser → (PKs, FK components, FK relations)
  metrics.py          # set-based PK accuracy, FK precision/recall/F1
  score_artefacts.py  # DDL-grounded scoring from on-disk artefacts
  ind_baseline.py     # Brute-force unary IND baseline + relation-level view
  ind_baseline_filtered.py
  binder_baseline.py  # External BINDER runner via Metanome CLI
  spider_baseline.py  # External SPIDER runner via Metanome CLI
  hyfd_baseline.py    # Table-wise HyFD-derived PK baseline
  llm_baseline.py     # Ollama-based LLM extractor baseline
  multi_seed.py       # Multi-seed wrapper around the existing notebooks
  run_all.py          # One-shot orchestrator → results.json
  README.md           # this file
```

## Quick start

From `paper_final/` (one level up from this directory):

```bash
# DDL-grounded artefact scoring + internal/external baselines
python -m eval.run_all

# Add the LLM baseline section.  Requires a local Ollama install:
ollama serve &
ollama pull gemma3:12b
python -m eval.run_all --with-llm
```

A single `eval/results.json` is written, with sub-keys `artefact_scoring`,
`ind_baseline`, `ind_baseline_filtered`, `binder_baseline`,
`spider_baseline`, `hyfd_baseline`, and `llm_baseline`.  `run_all.py`
passes an explicit seven-dataset list to BINDER and SPIDER, so the committed
TPC-DS external FK rows are regenerated even though those baseline scripts
skip TPC-DS in their default standalone mode.  When `--with-llm` is not
used, the LLM section is recorded as `not_run` rather than silently omitted.

## Individual scripts

```bash
# Just the DDL-grounded artefact scorer
python -m eval.score_artefacts                       # all four datasets
python -m eval.score_artefacts dvdrental tpch        # subset

# Just Table 3 (IND baseline)
python -m eval.ind_baseline                          # all four datasets

# Internal filtered IND ladder
python -m eval.ind_baseline_filtered

# External baselines
python -m eval.binder_baseline
python -m eval.spider_baseline
python -m eval.hyfd_baseline
python -m eval.binder_baseline tpcds                 # warehouse-scale FK run
python -m eval.spider_baseline tpcds                 # warehouse-scale FK run

# LLM baseline (default model gemma3:12b)
python -m eval.llm_baseline --model qwen2.5:7b

# Multi-seed re-execution of training notebooks (requires papermill)
pip install papermill
python -m eval.multi_seed --seeds 13 17 42 123 2024
```

## What each script reads

| Script              | Reads from                                                        |
| ------------------- | ----------------------------------------------------------------- |
| `score_artefacts`   | `<dataset>/sql_ddl.sql`, `<dataset>/schema_final.json`, `<dataset>/relationships.csv` |
| `ind_baseline`      | `<dataset>/sql_ddl.sql`, `<dataset>/data/*.csv`                   |
| `ind_baseline_filtered` | `<dataset>/sql_ddl.sql`, `<dataset>/data/*.csv`              |
| `binder_baseline`   | `<dataset>/sql_ddl.sql`, `<dataset>/data/*.csv`, Metanome jars    |
| `spider_baseline`   | `<dataset>/sql_ddl.sql`, `<dataset>/data/*.csv`, Metanome jars    |
| `hyfd_baseline`     | `<dataset>/sql_ddl.sql`, `<dataset>/data/*.csv`, Metanome jars    |
| `llm_baseline`      | `<dataset>/sql_ddl.sql` only — no row data is sent over the wire |
| `multi_seed`        | `<dataset>/Sieve_GNN.ipynb` (re-executed via papermill)          |

## Notes

* `score_artefacts.py` reads PK predictions from `schema_final.json` and FK
  predictions from `relationships.csv`.  It now reports both unary FK metrics
  and full-FK-relation metrics; the relation-level numbers only differ from the
  unary projection when a dataset contains composite foreign keys.
* `ind_baseline.py` uses the same containment threshold (0.95) and
  cardinality cap (1.05×) as the data-inclusion gate inside the main
  pipeline, so it is the closest data-only ablation already present in
  the executed TPC-H notebook.
* `binder_baseline.py` and `spider_baseline.py` run the published Metanome
  algorithms as unfiltered unary-IND baselines.  By default `spider_baseline`
  skips TPC-DS because that warehouse-scale run is slower on a workstation;
  invoke it explicitly for TPC-DS when needed.  `run_all.py` already does
  this for both BINDER and SPIDER.
* `hyfd_baseline.py` is not an FK baseline.  It mines functional dependencies
  one table at a time, reconstructs minimal superkeys, and scores one
  deterministic PK prediction per table.  The TPC-DS HyFD run is not part of
  the one-shot workflow because the table-wise FD mining job is too expensive
  for the committed artefact pack.
* `llm_baseline.py` only sends the DDL text to the local Ollama server; it
  never sends raw row data.
* `multi_seed.py` rewrites temporary notebook copies before execution so it can
  inject seeds into the current notebook layout and recover printed metrics even
  if later non-critical notebook cells fail.
