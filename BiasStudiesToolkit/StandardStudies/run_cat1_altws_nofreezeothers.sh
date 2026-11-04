#!/bin/bash
set -x
# Alternative (already masked) workspace; override with ALTWS=/path/to/ws.root ./run_cat1_altws_nofreezeothers.sh
ALTWS=${ALTWS:-/home/users/bdanzi/HHbbgg/CombineForBiasTests/CMSSW_14_1_0_pre4/src/HiggsAnalysis/CombinedLimit/Datacard_2016-2025_allcats_alt_ws.root}

combine -M FitDiagnostics "$ALTWS" -m 125 -t 500 -s 999995 -n .fit_cat1_envelope_CHECK_truth_bern1_r0_altws_nofreezeOthers \
  --expectSignal 0 \
  --toysFile higgsCombine.gen_cat1_envelope_CHECK_truth_bern1_r0_altws.GenerateOnly.mH125.999995.root \
  --setParameters mask_cat0=1,mask_cat1=0,mask_cat2=1,mask_cat3=1,mask_cat4=1 \
  --freezeParameters MH \
  --cminDefaultMinimizerStrategy 0 --robustFit 1 --rMin -50 --rMax 50 \
  > check_cat1_reproduce/combine_fit_cat1_envelope_CHECK_truth_bern1_r0_altws_nofreezeOthers.log 2>&1

python3 plot_bias_pull_FitDiagnostics.py -i fitDiagnostics.fit_cat1_envelope_CHECK_truth_bern1_r0_altws_nofreezeOthers.root \
  --r-truth 0 --truth-func bern1 --fit-func envelope --cat cat1_envelope_CHECK_truth_bern1_r0_altws_nofreezeOthers \
  -o ./check_cat1_reproduce

combine -M FitDiagnostics "$ALTWS" -m 125 -t 500 -s 999996 -n .fit_cat1_envelope_CHECK_truth_bern1_r1_altws_nofreezeOthers \
  --expectSignal 1 \
  --toysFile higgsCombine.gen_cat1_envelope_CHECK_truth_bern1_r1_altws.GenerateOnly.mH125.999996.root \
  --setParameters mask_cat0=1,mask_cat1=0,mask_cat2=1,mask_cat3=1,mask_cat4=1 \
  --freezeParameters MH \
  --cminDefaultMinimizerStrategy 0 --robustFit 1 --rMin -50 --rMax 50 \
  > check_cat1_reproduce/combine_fit_cat1_envelope_CHECK_truth_bern1_r1_altws_nofreezeOthers.log 2>&1

python3 plot_bias_pull_FitDiagnostics.py -i fitDiagnostics.fit_cat1_envelope_CHECK_truth_bern1_r1_altws_nofreezeOthers.root \
  --r-truth 1 --truth-func bern1 --fit-func envelope --cat cat1_envelope_CHECK_truth_bern1_r1_altws_nofreezeOthers \
  -o ./check_cat1_reproduce
