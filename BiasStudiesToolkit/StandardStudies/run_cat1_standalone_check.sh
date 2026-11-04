#!/bin/bash
set -x
WS=workspace_multipdf_cat1.root

# r=0, seed 999994
combine "$WS" -M GenerateOnly -m 125 -t 500 -s 999994 -n .gen_cat1_standalone_truth_bern1_r0 \
  --expectSignal 0 \
  --setParameters pdfindex_hgg_cat1_13TeV=0 \
  --freezeParameters MH,pdfindex_hgg_cat1_13TeV \
  --cminDefaultMinimizerStrategy 0 --rMin -50 --rMax 50 --saveToys \
  > check_cat1_standalone/combine_gen_cat1_standalone_truth_bern1_r0.log 2>&1

combine -M FitDiagnostics "$WS" -m 125 -t 500 -s 999994 -n .fit_cat1_standalone_truth_bern1_r0 \
  --expectSignal 0 \
  --toysFile higgsCombine.gen_cat1_standalone_truth_bern1_r0.GenerateOnly.mH125.999994.root \
  --freezeParameters MH \
  --cminDefaultMinimizerStrategy 0 --robustFit 1 --rMin -50 --rMax 50 \
  > check_cat1_standalone/combine_fit_cat1_standalone_truth_bern1_r0.log 2>&1

python3 plot_bias_pull_FitDiagnostics.py -i fitDiagnostics.fit_cat1_standalone_truth_bern1_r0.root \
  --r-truth 0 --truth-func bern1 --fit-func envelope --cat cat1_standalone_truth_bern1_r0 \
  -o ./check_cat1_standalone

# r=1, seed 999993
combine "$WS" -M GenerateOnly -m 125 -t 500 -s 999993 -n .gen_cat1_standalone_truth_bern1_r1 \
  --expectSignal 1 \
  --setParameters pdfindex_hgg_cat1_13TeV=0 \
  --freezeParameters MH,pdfindex_hgg_cat1_13TeV \
  --cminDefaultMinimizerStrategy 0 --rMin -50 --rMax 50 --saveToys \
  > check_cat1_standalone/combine_gen_cat1_standalone_truth_bern1_r1.log 2>&1

combine -M FitDiagnostics "$WS" -m 125 -t 500 -s 999993 -n .fit_cat1_standalone_truth_bern1_r1 \
  --expectSignal 1 \
  --toysFile higgsCombine.gen_cat1_standalone_truth_bern1_r1.GenerateOnly.mH125.999993.root \
  --freezeParameters MH \
  --cminDefaultMinimizerStrategy 0 --robustFit 1 --rMin -50 --rMax 50 \
  > check_cat1_standalone/combine_fit_cat1_standalone_truth_bern1_r1.log 2>&1

python3 plot_bias_pull_FitDiagnostics.py -i fitDiagnostics.fit_cat1_standalone_truth_bern1_r1.root \
  --r-truth 1 --truth-func bern1 --fit-func envelope --cat cat1_standalone_truth_bern1_r1 \
  -o ./check_cat1_standalone
