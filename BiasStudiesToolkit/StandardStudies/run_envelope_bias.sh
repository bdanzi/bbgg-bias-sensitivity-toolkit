#!/bin/bash
# Envelope discrete-profiling bias check on the full COMBINED workspace, with
# channel masking to isolate a single category, instead of a hand-split
# per-category datacard. One script, two fit modes:
#
#   --fit-mode envelope  (recommended / flashggFinalFit convention)
#       Toys are thrown from ONE fixed truth function per leg. The fit
#       leaves that category's pdfindex FLOATING, so combine profiles the
#       full envelope exactly as it does on real data. Loops over
#       TRUTH_FUNCTIONS x R_TRUTH_VALUES.
#
#   --fit-mode fixed  (diagnostic; matches the classic matrix in
#                      2b_standard_bias_studies_2D_1D_tryFitDiagnostic.sh)
#       Toys thrown from one truth function, fit ALSO forced onto one
#       (possibly different) function -- pdfindex frozen on both sides.
#       Loops over TRUTH_FUNCTIONS x FIT_FUNCTIONS x R_TRUTH_VALUES.
#
# In both modes, every OTHER category's pdfindex is frozen (masked channels
# don't contribute to the likelihood, so profiling their discrete index is
# both pointless and a source of minimizer instability). Note: the
# MINIMIZER_multiMin_* --X-rtd flags used by RunBiasInSignificance.py (for
# -M Significance) segfault -M FitDiagnostics when combined with
# --channel-masks (confirmed by direct reproduction on combine v10.6.0) --
# they are deliberately NOT used here.
#
# Prerequisite (once per datacard):
#   text2workspace.py Datacard_xxx.txt --channel-masks -m 125 -o Datacard_xxx.root
#
# Usage:
#   ./run_envelope_bias.sh --ws Datacard_xxx.root --cat cat2 --fit-mode envelope [--run] [--only-hgg]
#   ./run_envelope_bias.sh --ws Datacard_xxx.root --cat cat2 --fit-mode fixed    [--run] [--only-hgg]
#
# Without --run, only prints the combine commands (dry-run).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_help() {
    echo "Usage: $0 --ws <workspace.root> --cat <catN> [--fit-mode envelope|fixed] [--run] [--only-hgg] [--ntoys N] [--seed S] [--rmin X] [--rmax Y]"
    echo ""
    echo "  --ws <file>       Combined workspace built with --channel-masks (required)"
    echo "  --cat <catN>      Category to isolate via channel masking, e.g. cat2 (required)"
    echo "  --fit-mode        'envelope' (default, recommended) or 'fixed'"
    echo "  --run             Actually execute combine; otherwise dry-run (prints commands only)"
    echo "  --only-hgg        Ignore an HBB leg on this category, if present"
    echo "  --ntoys           Toys per combine call (default 1000)"
    echo "  --seed            combine -s seed (default 123456)"
    echo "  --rmin / --rmax   POI range passed to combine (default -50 / 50)"
    exit 0
}

WS=""; CAT=""; FIT_MODE="envelope"; DO_RUN=false; ONLY_HGG=false
NTOYS=1000; SEED=123456; RMIN=-50; RMAX=50

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help) show_help ;;
        --ws) WS="$2"; shift 2 ;;
        --cat) CAT="$2"; shift 2 ;;
        --fit-mode) FIT_MODE="$2"; shift 2 ;;
        --run) DO_RUN=true; shift ;;
        --only-hgg) ONLY_HGG=true; shift ;;
        --ntoys) NTOYS="$2"; shift 2 ;;
        --seed) SEED="$2"; shift 2 ;;
        --rmin) RMIN="$2"; shift 2 ;;
        --rmax) RMAX="$2"; shift 2 ;;
        *) echo "[ERROR] Unknown option: $1"; show_help ;;
    esac
done

[ -z "$WS" ] && { echo "[ERROR] --ws <workspace.root> is required"; exit 1; }
[ -z "$CAT" ] && { echo "[ERROR] --cat <catN> is required"; exit 1; }
[ ! -f "$WS" ] && { echo "[ERROR] Workspace $WS not found. Build it first with:"; echo "  text2workspace.py <datacard>.txt --channel-masks -m 125 -o $WS"; exit 1; }
if [ "$FIT_MODE" != "fixed" ] && [ "$FIT_MODE" != "envelope" ]; then
    echo "[ERROR] --fit-mode must be 'envelope' or 'fixed'"; exit 1
fi

CAT_NUM="${CAT#cat}"
TRUTH_FUNCTIONS=("exp1" "bern1" "bern2" "bern3" "pow1" "lau1" "lau2")
FIT_FUNCTIONS=("exp1" "bern1" "bern2" "bern3" "pow1" "lau1" "lau2")
R_TRUTH_VALUES=(0 2)

echo "=== Resolving pdfindex legs and function map for $CAT (mode: $FIT_MODE) ==="
eval "$(python3 "$SCRIPT_DIR/resolve_pdfindex_legs.py" "$WS" "$CAT_NUM")"

HAS_HGG=false; HAS_HBB=false
[ -n "$HGG_VAR" ] && HAS_HGG=true
if [ -n "$HBB_VAR" ] && [ "$ONLY_HGG" = false ]; then HAS_HBB=true; fi

if [ "$HAS_HGG" = false ] && [ "$HAS_HBB" = false ]; then
    echo "[ERROR] No pdfindex variable found for $CAT in $WS."
    echo "        Check --channel-masks was used and that $CAT is a real bin name."
    exit 1
fi

TARGET_LIST=""
[ "$HAS_HGG" = true ] && TARGET_LIST="$HGG_VAR"
[ "$HAS_HBB" = true ] && TARGET_LIST="${TARGET_LIST:+$TARGET_LIST }$HBB_VAR"
TARGET_LIST_CSV="$(echo "$TARGET_LIST" | tr ' ' ',')"

# --- Channel masks: unmask the target category, mask everything else ---
ALL_MASKS=$(python3 -c "
import ROOT
f = ROOT.TFile.Open('$WS')
w = f.Get('w')
names = sorted(v.GetName() for v in w.allVars() if v.GetName().startswith('mask_'))
print(' '.join(names))
")
if [ -z "$ALL_MASKS" ]; then
    echo "[ERROR] No mask_* parameters found in $WS. Was it built with --channel-masks?"
    exit 1
fi
MASK_SET=""
for m in $ALL_MASKS; do
    if [ "$m" == "mask_${CAT}" ]; then val=0; else val=1; fi
    MASK_SET="${MASK_SET:+$MASK_SET,}${m}=${val}"
done
echo "Channel masks: $MASK_SET"

# --- Freeze every OTHER category's pdfindex (irrelevant once masked, but
#     otherwise pointlessly profiled and a source of minimizer instability) ---
OTHER_PDFINDEX=""
for p in $ALL_PDFINDEX_VARS; do
    keep=true
    for t in $TARGET_LIST; do [ "$p" == "$t" ] && keep=false; done
    [ "$keep" = true ] && OTHER_PDFINDEX="${OTHER_PDFINDEX:+$OTHER_PDFINDEX,}$p"
done
FREEZE_OTHERS="MH${OTHER_PDFINDEX:+,$OTHER_PDFINDEX}"
FREEZE_GEN="${FREEZE_OTHERS}${TARGET_LIST_CSV:+,$TARGET_LIST_CSV}"
if [ "$FIT_MODE" == "fixed" ]; then
    FREEZE_FIT="$FREEZE_GEN"
else
    FREEZE_FIT="$FREEZE_OTHERS"
fi

# NOTE: the MINIMIZER_multiMin_* --X-rtd flags used by RunBiasInSignificance.py
# (for -M Significance) segfault combine v10.6.0's -M FitDiagnostics when
# combined with --channel-masks -- confirmed by direct reproduction. Freezing
# every other category's pdfindex (done above via FREEZE_OTHERS) is what
# actually matters for FitDiagnostics; no extra --X-rtd flags are used here.
STABILITY_FLAGS=""

echo ""
if [ "$DO_RUN" = false ]; then
    echo "DRY-RUN MODE: only printing commands. Add --run to execute."
fi

OUTDIR="./bias_plots_masked_${CAT}_${FIT_MODE}"

for t_func in "${TRUTH_FUNCTIONS[@]}"; do
    if [ "$FIT_MODE" == "envelope" ]; then
        FIT_LOOP=("envelope")
    else
        FIT_LOOP=("${FIT_FUNCTIONS[@]}")
    fi

    for f_func in "${FIT_LOOP[@]}"; do
        if [ "$FIT_MODE" == "fixed" ] && [ "$t_func" == "$f_func" ]; then continue; fi

        for r_truth in "${R_TRUTH_VALUES[@]}"; do
            SET_GEN=""; SET_FIT=""
            SKIP=false

            if [ "$HAS_HGG" = true ]; then
                idx_gen="IDX_${HGG_VAR}_${t_func}"
                [ -z "${!idx_gen}" ] && SKIP=true
                SET_GEN="${!idx_gen}"
                if [ "$FIT_MODE" == "fixed" ]; then
                    idx_fit="IDX_${HGG_VAR}_${f_func}"
                    [ -z "${!idx_fit}" ] && SKIP=true
                    SET_FIT="${!idx_fit}"
                fi
            fi
            if [ "$HAS_HBB" = true ]; then
                idx_gen_b="IDX_${HBB_VAR}_${t_func}"
                [ -z "${!idx_gen_b}" ] && SKIP=true
                SET_GEN="${SET_GEN:+$SET_GEN,}${!idx_gen_b}"
                if [ "$FIT_MODE" == "fixed" ]; then
                    idx_fit_b="IDX_${HBB_VAR}_${f_func}"
                    [ -z "${!idx_fit_b}" ] && SKIP=true
                    SET_FIT="${SET_FIT:+$SET_FIT,}${!idx_fit_b}"
                fi
            fi
            [ "$SKIP" = true ] && continue

            NAME="${CAT}_${FIT_MODE}_truth_${t_func}_fit_${f_func}_r${r_truth}"
            echo "-------------------------------------------------------------------------"
            echo "   [$FIT_MODE] $CAT | Truth [${t_func^^}] vs Fit [${f_func^^}] | r=${r_truth}"
            echo "-------------------------------------------------------------------------"

            CMD_GEN="combine $WS -M GenerateOnly -m 125 -t $NTOYS -s $SEED -n .gen_${NAME} --expectSignal ${r_truth} --setParameters ${MASK_SET},${SET_GEN} --freezeParameters ${FREEZE_GEN} --cminDefaultMinimizerStrategy 0 --rMin $RMIN --rMax $RMAX --saveToys"
            CMD_FIT="combine -M FitDiagnostics $WS -m 125 -t $NTOYS -s $SEED -n .fit_${NAME} --expectSignal ${r_truth} --toysFile higgsCombine.gen_${NAME}.GenerateOnly.mH125.${SEED}.root --setParameters ${MASK_SET}${SET_FIT:+,${SET_FIT}} --freezeParameters ${FREEZE_FIT} --cminDefaultMinimizerStrategy 0 --robustFit 1 --rMin $RMIN --rMax $RMAX $STABILITY_FLAGS"
            CMD_PLOT="python3 $SCRIPT_DIR/plot_bias_pull_FitDiagnostics.py -i fitDiagnostics.fit_${NAME}.root --r-truth ${r_truth} --truth-func ${t_func} --fit-func ${f_func} --cat ${NAME} -o $OUTDIR"

            echo "  [GEN]  $CMD_GEN"
            echo "  [FIT]  $CMD_FIT"
            echo "  [PLOT] $CMD_PLOT"

            if [ "$DO_RUN" = true ]; then
                eval $CMD_GEN > combine_gen_${NAME}.log 2>&1
                if [ $? -ne 0 ]; then echo "[ERROR] Generation failed for ${NAME}. See combine_gen_${NAME}.log"; continue; fi
                eval $CMD_FIT > combine_fit_${NAME}.log 2>&1
                if [ $? -eq 0 ]; then
                    mkdir -p "$OUTDIR"
                    eval $CMD_PLOT
                else
                    echo "[ERROR] Fit failed for ${NAME}. See combine_fit_${NAME}.log"
                fi
            fi
        done
    done
done
