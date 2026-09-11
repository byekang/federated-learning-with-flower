#!/usr/bin/env bash
# Start N Flower SuperNodes (clients) on ports 9094..(9093+N).
# Each SuperNode gets its partition id via --node-config.
# Usage: start_supernodes.sh [NUM_NODES]   (default 10)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/flower_env.sh"
NUM_NODES="${1:-10}"
TS="$(date -u +%Y%m%dT%H%M%S)"
mkdir -p "$ROOT/logs"

FAILED=0
for i in $(seq 0 $((NUM_NODES - 1))); do
    PIDFILE="$ROOT/logs/supernode_$i.pid"
    if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "SuperNode $i already running (pid $(cat "$PIDFILE"))"
        continue
    fi
    LOG="$ROOT/logs/supernode_${i}_${TS}.log"
    nohup "$BIN/flower-supernode" --insecure \
        --superlink 127.0.0.1:9092 \
        --host 127.0.0.1 --port "$((9094 + i))" \
        --node-config "partition-id=$i num-partitions=$NUM_NODES" \
        > "$LOG" 2>&1 &
    echo $! > "$PIDFILE"
    echo "SuperNode $i started: pid $(cat "$PIDFILE"), port $((9094 + i)), log $LOG"
done

sleep 2
for i in $(seq 0 $((NUM_NODES - 1))); do
    PIDFILE="$ROOT/logs/supernode_$i.pid"
    if [[ -f "$PIDFILE" ]] && ! kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "ERROR: SuperNode $i died right after start. Last log lines:" >&2
        tail -5 "$(ls -t "$ROOT/logs/supernode_${i}_"*.log | head -1)" >&2
        FAILED=1
    fi
done
exit $FAILED
