#!/bin/bash
# Completes run_cat0_fixedmodel_bias.sh: that script only ever tested
# truth=exp1/pow1 out of cat0's 4-function standard envelope (bern1/exp1/
# pow1/lau1), with no documented reason for skipping bern1/lau1. This runs
# the missing two truth functions, same convention (bestFit: other
# categories set+frozen to their real best-fit index), appending new
# truth_func entries into the SAME ./bias_plots_cat0_fixedmodel/pull_summary.json
# (safe: bern1/lau1 keys don't already exist there, no collision).
set -e

TRUTH_WS="Datacard_cat0truthstandard.root"
FIT_WS="Datacard.root"
OUTDIR="./bias_plots_cat0_fixedmodel"
mkdir -p "$OUTDIR"

OTHER_SET="pdfindex_hgg_cat1_13TeV=2,pdfindex_hgg_cat2_13TeV=1,pdfindex_hgg_cat3_13TeV=2,pdfindex_hgg_cat4_13TeV=4"
OTHER_FREEZE="pdfindex_hgg_cat1_13TeV,pdfindex_hgg_cat2_13TeV,pdfindex_hgg_cat3_13TeV,pdfindex_hgg_cat4_13TeV"

declare -A IDX=( [bern1]=0 [lau1]=3 )
NTOYS=1000
SEED=123456

run_one() {
    local t_func="$1" r_truth="$2"
    local idx="${IDX[$t_func]}"
    local name="cat0_fixedmodel_truth_${t_func}_r${r_truth}"

    combine "$TRUTH_WS" -M GenerateOnly -m 125 -t $NTOYS -s $SEED -n ".gen_${name}" \
        --expectSignal "${r_truth}" \
        --setParameters "pdfindex_hgg_cat0_13TeV=${idx},${OTHER_SET}" \
        --freezeParameters "MH,pdfindex_hgg_cat0_13TeV,${OTHER_FREEZE}" \
        --cminDefaultMinimizerStrategy 0 --rMin -5 --rMax 5 --saveToys \
        > "combine_gen_${name}.log" 2>&1

    combine -M FitDiagnostics "$FIT_WS" -m 125 -t $NTOYS -s $SEED -n ".fit_${name}" \
        --expectSignal "${r_truth}" \
        --toysFile "higgsCombine.gen_${name}.GenerateOnly.mH125.${SEED}.root" \
        --freezeParameters MH --cminDefaultMinimizerStrategy 0 --robustFit 1 \
        --rMin -5 --rMax 5 \
        > "combine_fit_${name}.log" 2>&1

    python3 ../plot_bias_pull_FitDiagnostics.py -i "fitDiagnostics.fit_${name}.root" \
        --r-truth "${r_truth}" --truth-func "${t_func}" --fit-func fixed_flat0 \
        --cat "${name}" -o "$OUTDIR"
}

for t_func in bern1 lau1; do
    for r_truth in 0 2; do
        run_one "$t_func" "$r_truth" &
    done
done
wait
echo "=== done, see $OUTDIR/pull_summary.json ==="
