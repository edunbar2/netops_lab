#!/usr/bin/env bash
set -u

SOURCE="${BASH_SOURCE[0]:-$0}"
APP_DIR="$(cd -- "$(dirname -- "$SOURCE")" && pwd -P)"
cd "$APP_DIR" || { read -r -p "Press Enter to close..."; exit 1; }

if [[ -x "$APP_DIR/.venv/bin/python" ]]; then
  PYTHON="$APP_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON="$(command -v python)"
else
  echo "Python was not found. Install Python 3.10+ from python.org or with Homebrew: brew install python"
  echo "Then run: python3 install.py"
  read -r -p "Press Enter to close..."
  exit 1
fi

if [[ ! -f "$APP_DIR/gns3_ccnp_lab_gui_qt.py" ]]; then
  echo "Could not find gns3_ccnp_lab_gui_qt.py in: $APP_DIR"
  read -r -p "Press Enter to close..."
  exit 1
fi

"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10 or newer is required/recommended for this application.")
try:
    import PySide6  # noqa: F401
except Exception as exc:
    raise SystemExit(
        "PySide6 is not available for this Python environment.\n"
        "Run: python3 -m pip install -r requirements.txt\n"
        f"Details: {exc}"
    )
PY
CHECK_RC=$?
if [[ $CHECK_RC -ne 0 ]]; then
  read -r -p "Press Enter to close..."
  exit $CHECK_RC
fi

"$PYTHON" "$APP_DIR/gns3_ccnp_lab_gui_qt.py" "$@"
APP_RC=$?
if [[ $APP_RC -ne 0 ]]; then
  echo
  echo "NetOps Labs exited with an error."
  read -r -p "Press Enter to close..."
fi
exit $APP_RC
