#!/usr/bin/env bash
set +e
cd "$(dirname "$0")/../.."
echo "=== adventureworks ===" >> /tmp/all_runs.log
paper_final/eval/run_one.sh adventureworks > /tmp/adventureworks_run.log 2>&1
echo "EXIT_aw=$?" >> /tmp/all_runs.log
echo "AW_DONE" >> /tmp/all_runs.log
