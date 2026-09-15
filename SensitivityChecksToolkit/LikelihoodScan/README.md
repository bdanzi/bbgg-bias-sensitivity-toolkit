# Likelihood Scan

**Question:** what does the 1D profile likelihood (`2 x deltaNLL`) look like
as a function of the signal strength `r`? Is the minimum well-constrained,
and where do the 1-sigma/2-sigma crossings fall?

This is a thin, generalized wrapper around the standard combine
`MultiDimFit --algo grid` recipe plus a plotting script - it's not a batch
scan like `UncertaintyImpactStudies`, so there's no `--run`/dry-run gate:
`setup_new_run.sh` only builds the workspace (cheap); you choose and launch
the actual scan yourself since its cost depends entirely on `--points`.

## Step-by-step (new datacard, 1D or 2D)

```bash
# 0. Bootstrap a run directory (builds workspace.root via text2workspace.py)
./setup_new_run.sh /path/to/Datacard_newAnalysis.txt myRunName
cd myRunName

# 1. Run the scan (pick --points / --rMin / --rMax for your analysis;
#    50 points is a reasonable starting resolution):
combine -M MultiDimFit workspace.root -m 125 --algo grid --points 50 \
    --rMin -5 --rMax 5 -n .scan_r

# 2. Plot it:
python3 plot_deltaNLL.py -i higgsCombine.scan_r.MultiDimFit.mH125.root
#    -> scan_r_plot.pdf / .png, with 1-sigma/2-sigma reference lines at
#       2*deltaNLL = 1 / 4.
```

`--poi` (default `r`) lets you plot a scan over a different parameter (e.g.
`--poi r_hgg` for a per-leg POI); pass the same `--points`/`-P <poi>` choice
you used when launching the scan so the branch name matches.
