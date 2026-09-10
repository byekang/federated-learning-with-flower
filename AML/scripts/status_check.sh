#!/usr/bin/env bash
# Status check for the FL AML demo: process liveness, listening ports,
# experiment progress (latest round in metrics JSON), recent log lines.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Process liveness ==="
for PIDFILE in "$ROOT"/logs/*.pid; do
    [[ -e "$PIDFILE" ]] || { echo "no pid files"; break; }
    PID="$(cat "$PIDFILE")"
    NAME="$(basename "$PIDFILE" .pid)"
    if kill -0 "$PID" 2>/dev/null; then
        echo "ALIVE  $NAME (pid $PID)"
    else
        echo "DEAD   $NAME (pid $PID)"
    fi
done

echo
echo "=== Listening ports (9092-9103) ==="
ss -tln 2>/dev/null | awk '$4 ~ /:(909[2-9]|910[0-3])$/ {print "  " $4}' | sort -u

echo
echo "=== Experiment progress ==="
for MODEL in logreg mlp; do
    AGG="$ROOT/results/$MODEL/aggregated_metrics.json"
    LOC="$ROOT/results/$MODEL/local_metrics.json"
    if [[ -f "$AGG" ]]; then
        "$ROOT/.venv/bin/python" - "$MODEL" "$AGG" "$LOC" <<'EOF'
import json, sys
model, agg_path, loc_path = sys.argv[1:4]
agg = json.load(open(agg_path))
last = agg[-1]
n_local = 0
try:
    n_local = len(json.load(open(loc_path)))
except FileNotFoundError:
    pass
print(f"{model}: aggregated points={len(agg)} local entries={n_local} "
      f"latest round={last['round']} precision={last['precision']:.4f} "
      f"recall={last['recall']:.4f} f1={last['f1']:.4f}")
EOF
    else
        echo "$MODEL: no results yet"
    fi
done

echo
echo "=== Recent log lines ==="
for LOG in $(ls -t "$ROOT"/logs/*.log 2>/dev/null | head -3); do
    echo "--- $(basename "$LOG")"
    tail -3 "$LOG"
done
