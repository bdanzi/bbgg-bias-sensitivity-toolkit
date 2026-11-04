#!/bin/bash
set -e
CAT=$1
R=$2
declare -A MASKS
for c in 0 1 2 3 4; do
    if [ "$c" -eq "$CAT" ]; then MASKS[$c]=0; else MASKS[$c]=1; fi
done
MASKSTR="mask_cat0=${MASKS[0]},mask_cat1=${MASKS[1]},mask_cat2=${MASKS[2]},mask_cat3=${MASKS[3]},mask_cat4=${MASKS[4]}"
FREEZE="MH"
for c in 0 1 2 3 4; do
    if [ "$c" -ne "$CAT" ]; then FREEZE="${FREEZE},pdfindex_hgg_cat${c}_13TeV"; fi
done

combine ws_truth_combined_masked.root -M GenerateOnly --toysFrequentist -t 1000 -s 123456 -n ".percat_cat${CAT}_truth_r${R}" \
    --expectSignal ${R} --setParameters ${MASKSTR} --saveToys -m 125 --rMin -10 --rMax 10 --cminDefaultMinimizerStrategy 0

combine -M FitDiagnostics ws_fit_combined_masked.root -m 125 -t 1000 -s 123456 -n ".percat_cat${CAT}_fit_r${R}" \
    --toysFile "higgsCombine.percat_cat${CAT}_truth_r${R}.GenerateOnly.mH125.123456.root" \
    --setParameters ${MASKSTR} --freezeParameters ${FREEZE} \
    --cminDefaultMinimizerStrategy 0 --toysFrequentist --robustFit 1 --rMin -10 --rMax 10

python3 plot_bias_pull_FitDiagnostics.py -i "fitDiagnostics.percat_cat${CAT}_fit_r${R}.root" --r-truth ${R} --truth-func GGJetsDDQCDTTGG --fit-func envelope --cat "cat${CAT}_percat" -o ./bias_plots_percat
