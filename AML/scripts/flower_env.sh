# Locate the Python environment where Flower is installed.
# Sourced by the other scripts; expects $ROOT to be set.
# Resolution order: .venv inside this project -> the currently activated
# virtualenv -> the PATH. Sets $BIN to the directory holding the flower-*
# executables and puts it on PATH (flower-superlink spawns flower-superexec
# from PATH).
if [[ -x "$ROOT/.venv/bin/flower-superlink" ]]; then
    BIN="$ROOT/.venv/bin"
elif [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/flower-superlink" ]]; then
    BIN="$VIRTUAL_ENV/bin"
elif command -v flower-superlink >/dev/null 2>&1; then
    BIN="$(cd "$(dirname "$(command -v flower-superlink)")" && pwd)"
else
    echo "ERROR: Flower is not installed anywhere these scripts can find it." >&2
    echo "Create the virtualenv INSIDE this folder (see README Quickstart):" >&2
    echo "  cd $ROOT" >&2
    echo "  python3 -m venv --system-site-packages .venv" >&2
    echo "  .venv/bin/pip install \"flwr==1.36.0\" pyarrow" >&2
    echo "Or activate the virtualenv where you installed flwr, then re-run." >&2
    exit 1
fi
export PATH="$BIN:$PATH"
