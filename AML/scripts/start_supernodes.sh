#!/usr/bin/env bash
# Start N Flower SuperNodes (clients) on ports 9094..(9093+N).
# Each SuperNode gets its partition id via --node-config.
# Usage: start_supernodes.sh [NUM_NODES]   (default 10)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NUM_NODES="${1:-10}"
export PATH="$ROOT/.venv/bin:$PATH"
TS="$(date -u +%Y%m%dT%H%M%S)"
mkdir -p "$ROOT/logs"

for i in $(seq 0 $((NUM_NODES - 1))); do
    PIDFILE="$ROOT/logs/supernode_$i.pid"
    if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "SuperNode $i already running (pid $(cat "$PIDFILE"))"
        continue
    fi
    LOG="$ROOT/logs/supernode_${i}_${TS}.log"
    nohup "$ROOT/.venv/bin/flower-supernode" --insecure \
        --superlink 127.0.0.1:9092 \
        --host 127.0.0.1 --port "$((9094 + i))" \
        --node-config "partition-id=$i num-partitions=$NUM_NODES" \
        > "$LOG" 2>&1 &
    echo $! > "$PIDFILE"
    echo "SuperNode $i started: pid $(cat "$PIDFILE"), port $((9094 + i)), log $LOG"
done
