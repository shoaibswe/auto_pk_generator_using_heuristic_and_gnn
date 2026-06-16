#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
source ../.venv/bin/activate
DATASET="${1:-tpcds}"
cd "$DATASET"
echo "[run] starting $DATASET at $(date)"
papermill Sieve_GNN.ipynb Sieve_GNN_executed.ipynb --log-output --kernel python3
echo "[run] finished $DATASET at $(date)"
