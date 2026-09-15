#!/bin/bash
# One-off: run ONLY the bern3 truth-function leg of the cat4 envelope check,
# at the SAME settings as this run dir's original cat4 run (5000 toys,
# rMin=-50/rMax=50), to complete that run's coverage once its main loop
# (exp1/bern1/bern2/pow1/lau1/lau2, missing bern3) finishes.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="Datacard_masked.root"
CAT="cat4"
CAT_NUM="4"
FIT_MODE="envelope"
NTOYS=5000
SEED=123456
RMIN=-50
RMAX=50

eval "$(python3 "$SCRIPT_DIR/resolve_pdfindex_legs.py" "$WS" "$CAT_NUM")"

ALL_MASKS=$(python3 -c "
import ROOT
f = ROOT.TFile.Open('$WS')
w = f.Get('w')
names = sorted(v.GetName() for v in w.allVars() if v.GetName().startswith('mask_'))
print(' '.join(names))
")
MASK_SET=""
for m in $ALL_MASKS; do
    if [ "$m" == "mask_${CAT}" ]; then val=0; else val=1; fi
    MASK_SET="${MASK_SET:+$MASK_SET,}${m}=${val}"
done

OTHER_PDFINDEX=""
for p in $ALL_PDFINDEX_VARS; do
    [ "$p" != "$HGG_VAR" ] && OTHER_PDFINDEX="${OTHER_PDFINDEX:+$OTHER_PDFINDEX,}$p"
done
FREEZE_OTHERS="MH${OTHER_PDFINDEX:+,$OTHER_PDFINDEX}"

OUTDIR="./bias_plots_masked_${CAT}_${FIT_MODE}"
mkdir -p "$OUTDIR"

for r_truth in 0 2; do
    NAME="${CAT}_${FIT_MODE}_truth_bern3_fit_envelope_r${r_truth}"
    idx_gen="IDX_${HGG_VAR}_bern3"
    if [ -z "${!idx_gen}" ]; then
        echo "[ERROR] bern3 not found for $CAT -- did resolve_pdfindex_legs.py pick it up?"
        exit 1
    fi
    SET_GEN="${!idx_gen}"

    CMD_GEN="combine $WS -M GenerateOnly -m 125 -t $NTOYS -s $SEED -n .gen_${NAME} --expectSignal ${r_truth} --setParameters ${MASK_SET},${SET_GEN} --freezeParameters ${FREEZE_OTHERS},${HGG_VAR} --cminDefaultMinimizerStrategy 0 --rMin $RMIN --rMax $RMAX --saveToys"
    CMD_FIT="combine -M FitDiagnostics $WS -m 125 -t $NTOYS -s $SEED -n .fit_${NAME} --expectSignal ${r_truth} --toysFile higgsCombine.gen_${NAME}.GenerateOnly.mH125.${SEED}.root --setParameters ${MASK_SET} --freezeParameters ${FREEZE_OTHERS} --cminDefaultMinimizerStrategy 0 --robustFit 1 --rMin $RMIN --rMax $RMAX"
    CMD_PLOT="python3 $SCRIPT_DIR/plot_bias_pull_FitDiagnostics.py -i fitDiagnostics.fit_${NAME}.root --r-truth ${r_truth} --truth-func bern3 --fit-func envelope --cat ${NAME} -o $OUTDIR"

    echo "[GEN]  $CMD_GEN"
    echo "[FIT]  $CMD_FIT"
    echo "[PLOT] $CMD_PLOT"

    eval $CMD_GEN >> combine_gen_${NAME}.log 2>&1
    eval $CMD_FIT >> combine_fit_${NAME}.log 2>&1
    eval $CMD_PLOT
done
