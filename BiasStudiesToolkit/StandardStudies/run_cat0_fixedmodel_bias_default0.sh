#!/bin/bash
# Same as run_cat0_fixedmodel_bias.sh (truth=exp1/pow1 from cat0's standard
# envelope, fit=cat0's real fixed flat0 model), but with every OTHER
# category's pdfindex set+frozen to its structural default (0) during
# generation instead of its best-fit function from data -- the "default0"
# sibling, matching the default0/bestFit comparison already done for
# dropfunc on cat1-4.
set -e

TRUTH_WS="Datacard_cat0truthstandard.root"
FIT_WS="Datacard.root"
OUTDIR="./bias_plots_cat0_fixedmodel_default0"
mkdir -p "$OUTDIR"

OTHER_SET="pdfindex_hgg_cat1_13TeV=0,pdfindex_hgg_cat2_13TeV=0,pdfindex_hgg_cat3_13TeV=0,pdfindex_hgg_cat4_13TeV=0"
OTHER_FREEZE="pdfindex_hgg_cat1_13TeV,pdfindex_hgg_cat2_13TeV,pdfindex_hgg_cat3_13TeV,pdfindex_hgg_cat4_13TeV"

declare -A IDX=( [exp1]=1 [pow1]=2 )
NTOYS=1000
SEED=123456

run_one() {
    local t_func="$1" r_truth="$2"
    local idx="${IDX[$t_func]}"
    local name="cat0_fixedmodel_default0_truth_${t_func}_r${r_truth}"

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

for t_func in exp1 pow1; do
    for r_truth in 0 2; do
        run_one "$t_func" "$r_truth" &
    done
done
wait
echo "=== done, see $OUTDIR/pull_summary.json ==="
