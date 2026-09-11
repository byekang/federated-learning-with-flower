#!/usr/bin/env bash
# Stop all Flower processes started by this project.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for PIDFILE in "$ROOT"/logs/*.pid; do
    [[ -e "$PIDFILE" ]] || continue
    PID="$(cat "$PIDFILE")"
    NAME="$(basename "$PIDFILE" .pid)"
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" && echo "stopped $NAME (pid $PID)"
    else
        echo "$NAME (pid $PID) not running"
    fi
    rm -f "$PIDFILE"
done

# safety net for orphaned flower processes started by this user
pkill -u "$USER" -f "flower-superlink|flower-supernode|flower-superexec" 2>/dev/null \
    && echo "killed orphaned flower processes"
exit 0
