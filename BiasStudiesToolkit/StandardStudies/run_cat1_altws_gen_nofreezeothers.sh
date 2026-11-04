#!/bin/bash
set -x
# Alternative (already masked) workspace; override with ALTWS=/path/to/ws.root ./run_cat1_altws_gen_nofreezeothers.sh
ALTWS=${ALTWS:-/home/users/bdanzi/HHbbgg/CombineForBiasTests/CMSSW_14_1_0_pre4/src/HiggsAnalysis/CombinedLimit/Datacard_2016-2025_allcats_alt_ws.root}

combine "$ALTWS" -M GenerateOnly -m 125 -t 500 -s 999995 -n .gen_cat1_envelope_CHECK_truth_bern1_r0_altws_nofreezeOthers \
  --expectSignal 0 \
  --setParameters mask_cat0=1,mask_cat1=0,mask_cat2=1,mask_cat3=1,mask_cat4=1,pdfindex_hgg_cat1_13TeV=0 \
  --freezeParameters MH,pdfindex_hgg_cat1_13TeV \
  --cminDefaultMinimizerStrategy 0 --rMin -50 --rMax 50 --saveToys \
  > check_cat1_reproduce/combine_gen_cat1_envelope_CHECK_truth_bern1_r0_altws_nofreezeOthers.log 2>&1

combine "$ALTWS" -M GenerateOnly -m 125 -t 500 -s 999996 -n .gen_cat1_envelope_CHECK_truth_bern1_r1_altws_nofreezeOthers \
  --expectSignal 1 \
  --setParameters mask_cat0=1,mask_cat1=0,mask_cat2=1,mask_cat3=1,mask_cat4=1,pdfindex_hgg_cat1_13TeV=0 \
  --freezeParameters MH,pdfindex_hgg_cat1_13TeV \
  --cminDefaultMinimizerStrategy 0 --rMin -50 --rMax 50 --saveToys \
  > check_cat1_reproduce/combine_gen_cat1_envelope_CHECK_truth_bern1_r1_altws_nofreezeOthers.log 2>&1
