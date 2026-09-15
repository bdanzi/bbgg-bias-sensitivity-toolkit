#!/bin/bash
# Bootstrap a new Uncertainty Impact Study run directory for a datacard.
#
# Usage: ./setup_new_run.sh <path/to/full_datacard.txt> <run_name>
#
# Creates UncertaintyImpactStudies/<run_name>/ containing a copy of
# run_uncertainty_scan.py and the datacard, ready for the steps in README.md.
# Unlike the StandardStudies bias toolkit, this study does NOT need the
# datacard split by category: it inserts a targeted nuisance/rateParam line
# into a copy of the *full* combined card for each scan point, so every other
# category and every correlated systematic is preserved automatically.

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
cp "$SCRIPT_DIR/run_uncertainty_scan.py" "$RUN_DIR/run_uncertainty_scan.py"
cp "$DATACARD" "$RUN_DIR/$(basename "$DATACARD")"

echo "Run directory ready: $RUN_DIR"
echo "Next steps: see $SCRIPT_DIR/README.md"
