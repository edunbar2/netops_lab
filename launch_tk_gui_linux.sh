#!/usr/bin/env bash
set -u

SOURCE="${BASH_SOURCE[0]:-$0}"
APP_DIR="$(cd -- "$(dirname -- "$SOURCE")" && pwd -P)"
cd "$APP_DIR" || exit 1

if [[ -x "$APP_DIR/.venv/bin/python" ]]; then
  PYTHON="$APP_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON="$(command -v python)"
else
  echo "Python was not found. Install Python 3.10+ and run: python3 install.py --legacy-tk"
  exit 1
fi

if [[ ! -f "$APP_DIR/gns3_ccnp_lab_gui.py" ]]; then
  echo "Could not find gns3_ccnp_lab_gui.py in: $APP_DIR"
  exit 1
fi

"$PYTHON" "$APP_DIR/gns3_ccnp_lab_gui.py" "$@"
APP_RC=$?
if [[ $APP_RC -ne 0 ]]; then
  echo
  echo "Legacy Tk GUI exited with an error. Install/update dependencies with:"
  echo "python3 -m pip install -r requirements-tk-legacy.txt"
fi
exit $APP_RC
