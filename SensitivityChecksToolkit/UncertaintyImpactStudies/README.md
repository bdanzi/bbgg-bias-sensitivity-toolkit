# Uncertainty Impact Studies

**Question:** for a given background/single-Higgs process, how much does the
expected upper limit (or expected significance) degrade as we inflate its
acceptance uncertainty (lnN) or scan its normalization (rate), per category
and across all categories combined? Which (process, category) pairs matter
most for the analysis's sensitivity?

Unlike a hand-split per-category datacard, this works directly on the
**full combined datacard**: each scan point is a copy of the full card with
one extra `accUnc_<scope>_<process> lnN ...` (mode `lnN`) or
`rateScale_<scope>_<process> rateParam <scope> <process> 1 [0,5]` (mode
`rate`) line that only touches the targeted (category, process) column (or,
in the `GLOBAL` scope, that process across every category) - every other
category and every correlated systematic is preserved exactly as in the real
fit.

## Why the process list is auto-discovered, not hardcoded

The original `UncertaintiesStudy*.py` scripts hardcoded
`BKG_PROCESSES = ["ggh_mass", "tth_mass", "vbf_mass", "vh_mass", "bkg_mass"]`,
the exact process names of one specific analysis's datacard. A different
datacard (different production-mode naming, a run2/run3 split, etc.) would
silently match nothing. `run_uncertainty_scan.py` instead reads the
datacard's own `process <name1> <name2> ...` line and takes every unique
process name **not containing `"HH"`** (i.e. every non-signal process,
since this analysis's HH signal processes are always named with an `HH`
substring, e.g. `ggHH_...`, `qqHH_...`) - this covers `bkg_mass` plus every
single-Higgs background, however many run-period variants the analysis has,
without editing the script. Use `--processes` to override if needed.

## Step-by-step (new datacard, 1D or 2D)

```bash
# 0. Bootstrap a run directory (no datacard splitting needed for this study)
./setup_new_run.sh /path/to/Datacard_newAnalysis.txt myRunName
cd myRunName

# 1. Dry-run first: prints the auto-discovered categories/processes and the
#    planned combine-call count (does not execute combine).
python3 run_uncertainty_scan.py Datacard_newAnalysis.txt

# 2. Actually run the lnN-vs-expected-limit scan (the default mode/metric):
python3 run_uncertainty_scan.py Datacard_newAnalysis.txt --run

# 3. Same scan, but for expected significance instead of expected limit:
python3 run_uncertainty_scan.py Datacard_newAnalysis.txt --metric significance --run

# 4. Rate-scale scan instead of an lnN nuisance (bkg_mass is automatically
#    excluded - scanning the rate of a data-driven RooMultiPdf envelope,
#    rather than a normalized template process, isn't physically meaningful):
python3 run_uncertainty_scan.py Datacard_newAnalysis.txt --mode rate --run

# Only care about the all-categories ("GLOBAL") scan, skip the per-category loop:
python3 run_uncertainty_scan.py Datacard_newAnalysis.txt --only-global --run

# Restrict to specific categories/processes, or override the scan range:
python3 run_uncertainty_scan.py Datacard_newAnalysis.txt \
    --categories cat1 cat2 --processes ggH_run2_13TeV_hgg ttH_run2_13TeV_hgg \
    --scan-min 1.0 --scan-max 1.5 --scan-n 6 --run
```

Each combine call is a single Asimov fit (`-t -1`, no toys), so it's fast
per-point - but the full category x process x scan-point matrix can still be
a few hundred combine calls for a 5-category, ~9-process analysis. Always
check the dry-run's printed "Planned combine calls" count before adding
`--run`.

Outputs land in `--outdir` (default: the run directory itself, for the
generated `card_<scope>_<process>_<i>.txt` and `higgsCombine_*.root` files)
and `--plotdir` (default: `./sensitivity_plots/`, for `impact_<cat>_<mode>_<metric>.png`,
`heatmap_impact_<mode>_<metric>.png`, and `impact_GLOBAL_<mode>_<metric>.png`).
The GLOBAL scan also prints a ranking of processes by fractional change in
the metric from the nominal to the last scan point.
