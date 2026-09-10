#!/usr/bin/env bash
# Submit the FL run to the local deployment.
# Usage: run_experiment.sh <logreg|mlp> [num_rounds] [min_nodes] [partitions_dir] [results_name]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL="${1:?usage: run_experiment.sh <logreg|mlp> [num_rounds] [min_nodes] [partitions_dir] [results_name]}"
ROUNDS="${2:-10}"
MIN_NODES="${3:-10}"
PARTS="${4:-partitions}"
NAME="${5:-$MODEL}"
TS="$(date -u +%Y%m%dT%H%M%S)"
mkdir -p "$ROOT/logs"
LOG="$ROOT/logs/run_${NAME}_${TS}.log"

# Ensure the Flower CLI knows how to reach the local SuperLink (Exec API).
CFG="$HOME/.flwr/config.toml"
if ! grep -q "\[superlink.local-deployment\]" "$CFG" 2>/dev/null; then
    mkdir -p "$HOME/.flwr"
    printf '\n[superlink.local-deployment]\naddress = "127.0.0.1:9093"\ninsecure = true\n' >> "$CFG"
    echo "added local-deployment connection to $CFG"
fi

cd "$ROOT"
"$ROOT/.venv/bin/flwr" run . local-deployment --stream --run-config \
    "model-type=\"$MODEL\" num-server-rounds=$ROUNDS min-nodes=$MIN_NODES partitions-dir=\"$PARTS\" data-dir=\"$ROOT/data\" results-dir=\"$ROOT/results/$NAME\"" \
    2>&1 | tee "$LOG"
echo "run log: $LOG"
