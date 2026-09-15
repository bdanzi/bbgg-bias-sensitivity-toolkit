# Sculpting Bias Studies

**Question:** the analytic background model per category (a `RooMultiPdf`
envelope of smooth functions, fit to data) is a *model*. The real non-resonant
background (GGJets/TTGG/DDQCDGJets) has whatever shape it actually has in MC.
If we generate toys from the **true MC-template shape** (a `RooHistPdf` built
directly from simulated events) and fit them with the **analytic envelope
datacard**, does the analytic model sculpt the true shape and pull the fitted
signal strength `r` away from its injected value?

This mirrors the reference workflow: build a `RooHistPdf` from MC
(`GGjetsWS.py`-style), generate toys from that truth ("MCALL"/"GGJets" card),
and fit with the real ("PDFALL"/analytic) card.

## Prerequisites specific to this study

The truth-workspace builders read analysis-specific inputs that you must edit
for a new analysis before running:

- `GGJets_improved.py` / `MCALLWS_revisited.py`: the `ak.from_parquet(...)`
  path to the merged scored-events ntuple, and the per-SR selection cuts
  (`is_ggHH_sig_score`, `is_nonRes_bkg_score`, `dijet_mass`/`mass` windows,
  etc.) that define SR1/SR2/SR3 for the new analysis.
- `MCALLWS_revisited.py` additionally clones signal-like analytic PDFs
  (TTH/VH/GG2H/VBF) out of a packaged background workspace
  `CMS-HGG_multipdf_packaged_cat<N>.root` — copy the one produced by your
  FinalFit background-fit step into the run directory before running it.
- **Which categories are GGJets/non-resonant-dominated** (and therefore
  candidates for this study) and their SR label (`SR1`, `SR2`, ...) is a
  physics choice for the new analysis — decide this before step 4.

## Step-by-step (new datacard, 1D or 2D)

```bash
# 0. Bootstrap a run directory (splits the datacard by category automatically)
./setup_new_run.sh /path/to/Datacard_newAnalysis.txt myRunName
cd myRunName

# 1. Build the analytic (envelope) workspace per category, and print the
#    RooMultiPdf -> function index map for each (needed to sanity-check step 4/5).
./generate_workspaces_first.sh

# 2. Edit GGJets_improved.py / MCALLWS_revisited.py for this analysis
#    (parquet path + SR cut definitions), then build the truth workspaces
#    for each GGJets-dominated SR, for the dimensionality of this datacard:
python3 GGJets_improved.py --dim 1D        # or --dim 2D
python3 MCALLWS_revisited.py --dim 1D      # or --dim 2D
#    -> nominal_pdfs/GGjetsWS_<SR>_<dim>.root, nominal_pdfs/MCALLWS_<SR>_<dim>.root

# 3. For each GGJets-dominated category catN with truth label SR<k>, build the
#    hybrid datacard whose data/bkg shape is the truth RooHistPdf:
python3 make_ggjets_datacard.py datacard_cat2.txt SR1 1D
#    -> datacard_cat2_GGJets.txt

# 4. Turn both cards into workspaces: the hybrid one is the *generation*
#    ("truth") workspace, the original one is the *fit* ("analytic") workspace.
text2workspace.py datacard_cat2_GGJets.txt -o ws_truth_cat2.root -m 125
text2workspace.py datacard_cat2.txt        -o ws_fit_cat2.root   -m 125

# 5. Generate toys from the truth workspace, at whatever injected signal
#    strength(s) you want to scan, e.g. r=0 and r=6.5:
combine ws_truth_cat2.root -M GenerateOnly --toysFrequentist -t 1000 \
    --expectSignal 0 --saveToys -m 125 -n cat2FromTruth.r0
combine ws_truth_cat2.root -M GenerateOnly --toysFrequentist -t 1000 \
    --expectSignal 6.5 --saveToys -m 125 -n cat2FromTruth.r6.5

# 6. Fit those toys with the real analytic (fit) workspace:
combine -M FitDiagnostics ws_fit_cat2.root -m 125 \
    --toysFile higgsCombinecat2FromTruth.r0.GenerateOnly.mH125.123456.root \
    --rMin -10 --rMax 10 -t 1000 --cminDefaultMinimizerStrategy 0 \
    --toysFrequentist --robustFit 1 -n cat2FromTruth.r0

# 8. Plot the pull:
python3 plot_bias_pull_FitDiagnostics.py -i higgsCombinecat2FromTruth.r0.MultiDimFit.mH125.123456.root \
    --r-truth 0 --truth-func GGJetsMC --fit-func envelope --cat cat2 -o ./bias_plots
```

Repeat steps 3-8 for every GGJets-dominated category/SR and for every
injected-`r` value you want to scan (typically `r=0` for a pure-background
closure and a non-zero `r` matching the expected signal yield). `plot_bias_pull.py`
fits a Gaussian to `Pull = (r_truth - r_fit) / sigma_fit`: a mean significantly
away from 0 indicates the analytic envelope is sculpting the true background
shape and biasing `r`.
