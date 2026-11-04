#!/usr/bin/env python3
import ROOT
import sys
import os
import argparse
import numpy as np
import json

ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(110)
#ROOT.gStyle.SetOptStat("mr")
ROOT.gStyle.SetOptFit(111)

parser = argparse.ArgumentParser(description='Plot Pull from FitDiagnostics Matrix')
parser.add_argument('-i', '--input', required=True, help='Input fitDiagnostics file')
parser.add_argument('--r-truth', type=float, required=True, help='Injected r value')
parser.add_argument('--truth-func', required=True, help='Truth function name')
parser.add_argument('--fit-func', required=True, help='Fit function name')
parser.add_argument('--cat', required=True, help='Category descriptor')
parser.add_argument('-o', '--outdir', default='./bias_plots', help='Output directory')
parser.add_argument('--r-min', type=float, default=None, help='rMin used in the fit, to drop toys pinned at the boundary')
parser.add_argument('--r-max', type=float, default=None, help='rMax used in the fit, to drop toys pinned at the boundary')
parser.add_argument('--boundary-eps', type=float, default=1e-3, help='How close to rMin/rMax counts as pinned-at-boundary')
args = parser.parse_args()

os.makedirs(args.outdir, exist_ok=True)

if not os.path.exists(args.input):
    print(f"[ERROR] Input file {args.input} missing.")
    sys.exit(1)

f = ROOT.TFile.Open(args.input)
t = f.Get("tree_fit_sb")
if not t:
    print(f"[ERROR] tree_fit_sb missing in {args.input}")
    sys.exit(1)

title = f"Pull: r_{{in}}={args.r_truth}, Truth={args.truth_func.upper()}, Fit={args.fit_func.upper()} ({args.cat})"
hist_pull = ROOT.TH1F("h", title, 40, -5, 5)
hist_pull.GetXaxis().SetTitle("(r_{fit} - r_{in}) / #sigma_{fit}")
hist_pull.GetYaxis().SetTitle("Entries / 0.25")

# Error branch logic handling asymmetric errors from FitDiagnostics tree.
# This used to be gated behind `if "2" in args.cat or "3" in args.cat or "4"
# in args.cat`, which was really just checking whether those digits happened
# to appear ANYWHERE in the --cat descriptor string (category name, function
# name, or r value), not the actual category number. Whenever none of
# '2'/'3'/'4' appeared (e.g. cat1, truth=exp1, r=0), `plotting` stayed empty,
# `todraw` became the invalid expression ">>h", and every toy in that
# combination silently produced an empty/zero pull histogram (n_toys=0,
# mean=0, sigma=0) even though the underlying fit results were perfectly fine.
#
# Standard (established) convention: use the symmetric average when the
# asymmetric errors differ by more than a factor of 3 (extreme asymmetry -
# averaging is more robust there), otherwise pick the error on the side
# r_fit actually moved towards relative to r_in. Applied uniformly to every
# category - a per-category override was tried and reverted; the real
# handle for categories with more pathological toys (e.g. cat1) is the
# boundary-pinned-toy cut below, not switching the error formula.
r_in = args.r_truth
plotting = f"(r-{r_in})/((rLoErr/rHiErr>3.0 || rHiErr/rLoErr>3.0) ? (rLoErr+rHiErr)/2 : (r>{r_in} ? rLoErr : rHiErr))"
print(plotting)

todraw = f"{plotting}>>h"
base_cut = "(fit_status==0 || fit_status==300) && rLoErr > 0.05 && rHiErr > 0.05"

# Drop toys "pathological beyond recovery": the fit pinned at rMin/rMax.
# These can still report a finite, even large, error on the *other* side
# (so the rLoErr/rHiErr>0.05 cut above doesn't necessarily catch them), but
# the fit itself never found a real minimum - the pull from such a toy is
# meaningless, not just noisy. Only applied when the caller tells us what
# rMin/rMax were actually used (varies per study/script).
if args.r_min is not None:
    base_cut += f" && abs(r-({args.r_min}))>{args.boundary_eps}"
if args.r_max is not None:
    base_cut += f" && abs(r-({args.r_max}))>{args.boundary_eps}"

t.Draw(todraw, base_cut, "goff")

canv = ROOT.TCanvas("c", "c", 800, 600)
hist_pull.Draw("E")

maxX = 5.0
fg = ROOT.TF1("fg", "gaus", -maxX, maxX)
fg.SetLineColor(2)
fg.SetLineWidth(2)

# A single Gaussian fit over the full (-5,5) range is easily dragged off by a
# handful of outlier/boundary toys in the tails, giving a huge chi2/ndf and a
# mean/sigma that don't describe the bulk of the distribution. Standard fix:
# seed with a wide fit, then iteratively refit restricted to the core
# (+-core_width sigma around the current estimate) until it converges, so the
# reported mean/sigma reflect the bulk of the toys rather than the tails.
#
# This adaptive window converges to a different [lo, hi] per r_truth (r0 vs
# r2 have different toy spreads), which makes the two plots for the same
# truth/fit combo look inconsistent side by side even though nothing is
# wrong. To keep every injected-r variant visually consistent with its r=0
# baseline, r=0 computes the window as before and caches it; any other r
# reuses that cached window instead of re-deriving its own.
import re
core_range_cache_path = os.path.join(args.outdir, ".core_range_cache.json")
core_range_key = re.sub(r'_r-?\d+$', '', args.cat) + f"|{args.truth_func}|{args.fit_func}"
try:
    with open(core_range_cache_path) as _fh:
        core_range_cache = json.load(_fh)
except (FileNotFoundError, json.JSONDecodeError):
    core_range_cache = {}

core_width = 2.0
if r_in == 0 or core_range_key not in core_range_cache:
    hist_pull.Fit(fg, "LRQ0", "", -maxX, maxX)
    mean_est, sigma_est = fg.GetParameter(1), fg.GetParameter(2)
    for _ in range(5):
        if sigma_est <= 0:
            break
        lo, hi = mean_est - core_width * sigma_est, mean_est + core_width * sigma_est
        hist_pull.Fit(fg, "LRQ0", "", lo, hi)
        new_mean, new_sigma = fg.GetParameter(1), fg.GetParameter(2)
        if abs(new_mean - mean_est) < 1e-3 and abs(new_sigma - sigma_est) < 1e-3:
            mean_est, sigma_est = new_mean, new_sigma
            break
        mean_est, sigma_est = new_mean, new_sigma
    lo, hi = mean_est - core_width * sigma_est, mean_est + core_width * sigma_est
    if r_in == 0:
        core_range_cache[core_range_key] = [lo, hi]
        with open(core_range_cache_path, "w") as _fh:
            json.dump(core_range_cache, _fh)
else:
    # Reuse the r=0 study's converged core-fit window for this same combo.
    lo, hi = core_range_cache[core_range_key]

# Final fit over the (shared) core range, so the stat box shows a meaningful
# chi2/ndf computed only over the region the Gaussian actually describes.
# Drawn with "0" (no auto-draw of the core-range-only curve) - TF1.SetRange()
# on a TF1 already added to the histogram's function list does NOT
# retroactively widen what gets painted (verified: the curve was being
# hard-clipped exactly at the core-fit boundary, not just fading out
# mathematically), so instead draw a separate clone spanning the full window
# with the same fitted parameters.
hist_pull.Fit(fg, "LR0", "", lo, hi)
fg_full = fg.Clone("fg_full")
fg_full.SetRange(-maxX, maxX)
fg_full.SetLineColor(2)
fg_full.SetLineWidth(2)
fg_full.Draw("same")
print(f"--> Core-fit range used: [{lo:.2f}, {hi:.2f}], chi2/ndf = {fg.GetChisquare():.1f}/{fg.GetNDF()}")

outname = f"{args.outdir}/pull_{args.cat}_truth_{args.truth_func}_fit_{args.fit_func}_r{int(r_in)}.png"
canv.SaveAs(outname)
print(f"--> Saved pull plot: {outname}")

# ==========================================
# Save cumulative JSON summary
# ==========================================
# ==========================================
# Save cumulative JSON summary
# ==========================================
# Extract basic metrics from the histogram
mean_pull = hist_pull.GetMean()
rms_pull = hist_pull.GetRMS()
n_toys = int(hist_pull.GetEntries())

# 1. Compute Median using ROOT Quantiles
probs = np.array([0.5], dtype=float)
quantiles = np.array([0.0], dtype=float)
hist_pull.GetQuantiles(1, quantiles, probs)
median_pull = quantiles[0]

# 2. Compute the Standard Error of the Median
# We extract the parameters from the Gaussian fit performed earlier in your script
fit_mean = float(fg.GetParameter(1))
fit_sigma = float(fg.GetParameter(2))

if n_toys > 0 and fit_sigma > 0:
    # Standard error of the median formula for an approximately Gaussian distribution:
    # sigma_median = sqrt(pi/2) * (sigma_fit / sqrt(N))
    error_median_pull = np.sqrt(np.pi / 2.0) * (fit_sigma / np.sqrt(n_toys))
else:
    error_median_pull = 0.0

summary_json = os.path.join(args.outdir, "pull_summary.json")

record = {
    "category": args.cat,
    "truth_func": args.truth_func,
    "fit_func": args.fit_func,
    "r_truth": float(args.r_truth),
    "n_toys": n_toys,
    "mean_pull": float(mean_pull),
    "median_pull": float(median_pull),
    "error_median_pull": float(error_median_pull), # Added error on the median
    "rms_pull": float(rms_pull),
    "fit_mean": fit_mean,
    "fit_sigma": fit_sigma
}

if os.path.exists(summary_json):
    try:
        with open(summary_json, "r") as fin:
            data = json.load(fin)
            if not isinstance(data, list):
                data = []
    except Exception:
        data = []
else:
    data = []

# Append the new record
data.append(record)

# Rewrite the updated JSON file
with open(summary_json, "w") as fout:
    json.dump(data, fout, indent=4)

print(f"--> Updated JSON summary: {summary_json}")

# Cleanly close the ROOT file at the very end
f.Close()
