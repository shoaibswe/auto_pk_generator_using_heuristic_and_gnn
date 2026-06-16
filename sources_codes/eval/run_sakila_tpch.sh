#!/usr/bin/env bash
# Run sakila + tpch sequentially and log
set +e
cd "$(dirname "$0")/../.."
for d in sakila tpch; do
  echo "=== $d ===" >> /tmp/all_runs.log
  paper_final/eval/run_one.sh $d >> /tmp/${d}_run.log 2>&1
  echo "EXIT_${d}=$?" >> /tmp/all_runs.log
done
echo "DONE" >> /tmp/all_runs.log
