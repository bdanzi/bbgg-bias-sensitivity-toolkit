#!/bin/bash
# Bootstrap a new Likelihood Scan run directory for a datacard.
#
# Usage: ./setup_new_run.sh <path/to/full_datacard.txt> <run_name>
#
# Creates LikelihoodScan/<run_name>/ containing plot_deltaNLL.py, a copy of
# the datacard, and its text2workspace.py output (workspace.root), ready for
# the scan command printed at the end (see README.md).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -ne 2 ]; then
    echo "Usage: $0 <path/to/full_datacard.txt> <run_name>"
    exit 1
fi

DATACARD="$1"
RUN_NAME="$2"
RUN_DIR="$SCRIPT_DIR/$RUN_NAME"

if [ ! -f "$DATACARD" ]; then
    echo "[ERROR] Datacard not found: $DATACARD"
    exit 1
fi

if [ -e "$RUN_DIR" ]; then
    echo "[ERROR] $RUN_DIR already exists. Pick a different run_name or remove it first."
    exit 1
fi

mkdir -p "$RUN_DIR"
cp "$SCRIPT_DIR/plot_deltaNLL.py" "$RUN_DIR/plot_deltaNLL.py"
cp "$DATACARD" "$RUN_DIR/$(basename "$DATACARD")"

cd "$RUN_DIR"
echo "=== Building workspace ==="
text2workspace.py "$(basename "$DATACARD")" -o workspace.root -m 125

echo ""
echo "Run directory ready: $RUN_DIR"
echo "Next step (not run automatically - pick --points/--rMin/--rMax for your analysis):"
echo "  combine -M MultiDimFit workspace.root -m 125 --algo grid --points 50 --rMin -5 --rMax 5 -n .scan_r"
echo "  python3 plot_deltaNLL.py -i higgsCombine.scan_r.MultiDimFit.mH125.root"
echo "See $SCRIPT_DIR/README.md"
