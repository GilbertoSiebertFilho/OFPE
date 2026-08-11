#!/usr/bin/env bash
# =============================================================================
#  OFPE Field Data Platform - start here (macOS / Linux).
#
#  ./start.sh sets everything up the first time and just starts the app every
#  time after that. Everything it installs goes into a .venv folder next to
#  this script, so it cannot break any other Python on the machine.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

echo
echo "  OFPE Field Data Platform"
echo "  ------------------------"
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "  python3 was not found."
    echo
    echo "  macOS:  brew install python"
    echo "  Ubuntu: sudo apt install python3 python3-venv"
    echo
    exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "  First run. Creating a private Python environment..."
    python3 -m venv .venv
    echo "  Installing the packages it needs. This takes a minute or two,"
    echo "  once, and only the first time."
    echo
    .venv/bin/python -m pip install --upgrade pip --quiet
    .venv/bin/python -m pip install -r requirements.txt --quiet
    echo "  Setup finished."
    echo
fi

echo "  Starting. Your browser will open in a moment."
echo "  Leave this window open while you use the app."
echo
exec .venv/bin/python run.py --open
