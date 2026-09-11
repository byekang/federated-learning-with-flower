#!/usr/bin/env bash
# Start the Flower SuperLink (server): Fleet API :9092, Exec API :9093.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/flower_env.sh"
TS="$(date -u +%Y%m%dT%H%M%S)"
mkdir -p "$ROOT/logs"
LOG="$ROOT/logs/superlink_${TS}.log"

if [[ -f "$ROOT/logs/superlink.pid" ]] && kill -0 "$(cat "$ROOT/logs/superlink.pid")" 2>/dev/null; then
    echo "SuperLink already running (pid $(cat "$ROOT/logs/superlink.pid"))"
    exit 0
fi

# run apps in the current environment (system packages) instead of per-run uv envs
nohup "$BIN/flower-superlink" --insecure \
    --disable-runtime-dependency-installation > "$LOG" 2>&1 &
echo $! > "$ROOT/logs/superlink.pid"

sleep 2
if ! kill -0 "$(cat "$ROOT/logs/superlink.pid")" 2>/dev/null; then
    echo "ERROR: SuperLink failed to start. Last log lines:" >&2
    tail -5 "$LOG" >&2
    exit 1
fi
echo "SuperLink started: pid $(cat "$ROOT/logs/superlink.pid"), log $LOG"
