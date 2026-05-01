#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  python3 ./gns3_ccnp_lab_generator.py "$@"
else
  echo "python3 was not found. Install Python 3 from python.org or with Homebrew: brew install python"
  exit 1
fi
