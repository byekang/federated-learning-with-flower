#!/usr/bin/env bash
# Start the Flower SuperLink (server): Fleet API :9092, Exec API :9093.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$ROOT/.venv/bin:$PATH"   # superlink spawns flower-superexec from PATH
TS="$(date -u +%Y%m%dT%H%M%S)"
mkdir -p "$ROOT/logs"
LOG="$ROOT/logs/superlink_${TS}.log"

if [[ -f "$ROOT/logs/superlink.pid" ]] && kill -0 "$(cat "$ROOT/logs/superlink.pid")" 2>/dev/null; then
    echo "SuperLink already running (pid $(cat "$ROOT/logs/superlink.pid"))"
    exit 0
fi

# run apps in the current venv (system packages) instead of per-run uv envs
nohup "$ROOT/.venv/bin/flower-superlink" --insecure \
    --disable-runtime-dependency-installation > "$LOG" 2>&1 &
echo $! > "$ROOT/logs/superlink.pid"
echo "SuperLink started: pid $(cat "$ROOT/logs/superlink.pid"), log $LOG"
