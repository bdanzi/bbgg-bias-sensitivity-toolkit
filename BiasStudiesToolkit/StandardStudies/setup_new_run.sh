#!/bin/bash
# Bootstrap a new Standard Bias Studies run directory for a datacard.
#
# Usage: ./setup_new_run.sh <path/to/full_datacard.txt> <run_name>
#
# Creates StandardStudies/<run_name>/ containing a copy of the canonical
# scripts and the split per-category datacards, ready for the steps in
# README.md.

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

for f in 0_split_datacard.py generate_workspaces_first.sh parser_legs_matrix.py \
         resolve_pdfindex_legs.py run_envelope_bias.sh run_full_envelope_bias.sh \
         2b_standard_bias_studies_2D_1D_tryFitDiagnostic.sh \
         2b_standard_bias_studies_2D_1D_tryFitDiagnostic_onlyplottingoption.sh \
         2b_standard_bias_studies_2D_1D_tryFitDiagnostic_vs_envelope.sh \
         plot_bias_pull_FitDiagnostics.py plot_bias_pull_FitDiagnostics_onlyrfit.py \
         analyze_envelope_choice_bias.py \
         RunBiasInSignificance.py create_table.py SummaryBiasSignificance.py; do
    cp "$SCRIPT_DIR/$f" "$RUN_DIR/$f"
done

cp "$DATACARD" "$RUN_DIR/$(basename "$DATACARD")"

cd "$RUN_DIR"
echo "=== Splitting datacard by category ==="
python3 0_split_datacard.py "$(basename "$DATACARD")"

echo ""
echo "Run directory ready: $RUN_DIR"
echo "Next steps: see $SCRIPT_DIR/README.md"
