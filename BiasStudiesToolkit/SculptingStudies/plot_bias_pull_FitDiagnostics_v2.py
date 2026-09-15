#!/usr/bin/env python3
"""Improved pull plotter for sculpting-bias FitDiagnostics toys.

Same inputs/outputs as plot_bias_pull_FitDiagnostics.py (reads tree_fit_sb from
a FitDiagnostics ROOT file, writes one PNG), but fixes two problems seen in
practice with the original script:

1. It silently fit a Gaussian to whatever survived the rLoErr/rHiErr>0.05 cut,
   even when that left a handful of entries out of 1000 (e.g. cat1: 3/1000
   toys have a usable MINOS error - the rest have rLoErr==0, i.e. the error
   scan simply failed to converge). Fitting a Gaussian to ~3 points is
   meaningless and looks deceptively like a real result. This version reports
   the survival fraction on the plot and refuses to fit+claim a pull mean/sigma
   below a configurable efficiency floor - it draws the raw (valid-error) toy
   count instead and stamps the plot as too-low-statistics/unreliable.
2. The Gaussian fit used blind ROOT default initial parameters over a fixed
   +/-5 range regardless of the actual spread of the data, which is fragile
   for categories whose pull distribution is not centered/scaled anywhere near
   O(1) (e.g. very background-poor categories). This version seeds the fit
   from the histogram's own mean/RMS and fits over a data-driven range.
"""
import ROOT
import sys
import os
import argparse
import numpy as np

ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptFit(0)

parser = argparse.ArgumentParser(description="Plot Pull from a FitDiagnostics toy tree (robust version)")
parser.add_argument("-i", "--input", required=True, help="Input fitDiagnostics file")
parser.add_argument("--r-truth", type=float, required=True, help="Injected r value")
parser.add_argument("--truth-func", required=True, help="Truth function name")
parser.add_argument("--fit-func", required=True, help="Fit function name")
parser.add_argument("--cat", required=True, help="Category descriptor")
parser.add_argument("-o", "--outdir", default="./bias_plots", help="Output directory")
parser.add_argument("--min-eff", type=float, default=0.10,
                     help="Minimum fraction of toys with a valid MINOS error required to trust a Gaussian fit (default 0.10)")
parser.add_argument("--err-floor", type=float, default=1e-4,
                     help="rLoErr/rHiErr below this are treated as 'MINOS failed' (default 1e-4)")
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

n_total = t.GetEntries()
r_in = args.r_truth

pulls = []
n_status_fail = 0
n_err_fail = 0
for i in range(n_total):
    t.GetEntry(i)
    if not (t.fit_status == 0 or t.fit_status == 300):
        n_status_fail += 1
        continue
    if t.rLoErr <= args.err_floor or t.rHiErr <= args.err_floor:
        n_err_fail += 1
        continue
    r_fit = t.r
    sigma = t.rHiErr if r_fit < r_in else t.rLoErr
    if sigma > 0:
        pulls.append((r_fit - r_in) / sigma)

pulls = np.array(pulls)
n_valid = len(pulls)
eff = n_valid / n_total if n_total else 0.0

print(f"[INFO] {args.cat}: {n_valid}/{n_total} toys have a usable MINOS error ({100*eff:.1f}%); "
      f"{n_status_fail} failed fit_status, {n_err_fail} failed the error floor.")

title = f"Pull: r_{{in}}={r_in:.0f}, Truth={args.truth_func.upper()}, Fit={args.fit_func.upper()} ({args.cat})"
canv = ROOT.TCanvas("c", "c", 800, 600)

reliable = n_valid >= 30 and eff >= args.min_eff

if n_valid == 0:
    hist_pull = ROOT.TH1F("h", title, 40, -5, 5)
    hist_pull.GetXaxis().SetTitle("(r_{fit} - r_{in}) / #sigma_{fit}")
    hist_pull.GetYaxis().SetTitle("Entries")
    hist_pull.Draw("E")
    box_lines = [f"N_{{toys}} = {n_total}", "0 usable toys", "(all failed fit_status or MINOS error)"]
    fit_txt = None
    reliable = False
else:
    lo, hi = np.percentile(pulls, [1, 99])
    pad = 0.25 * max(hi - lo, 1e-6)
    lo, hi = lo - pad, hi + pad
    nbins = int(np.clip(n_valid // 8, 20, 60))
    hist_pull = ROOT.TH1F("h", title, nbins, lo, hi)
    hist_pull.GetXaxis().SetTitle("(r_{fit} - r_{in}) / #sigma_{fit}")
    hist_pull.GetYaxis().SetTitle(f"Entries / {(hi - lo) / nbins:.2f}")
    for p in pulls:
        hist_pull.Fill(p)
    hist_pull.SetLineColor(ROOT.kBlack)
    hist_pull.SetMarkerStyle(20)
    hist_pull.Draw("E")

    fit_txt = None
    if reliable:
        seed_mean, seed_sigma = float(np.mean(pulls)), float(np.std(pulls))
        seed_sigma = max(seed_sigma, 1e-3)
        fit_lo, fit_hi = seed_mean - 4 * seed_sigma, seed_mean + 4 * seed_sigma
        fg = ROOT.TF1("fg", "gaus", fit_lo, fit_hi)
        fg.SetParameters(hist_pull.GetMaximum(), seed_mean, seed_sigma)
        fg.SetLineColor(ROOT.kRed + 1)
        fg.SetLineWidth(2)
        fit_res = hist_pull.Fit(fg, "RLQS", "", fit_lo, fit_hi)
        fg.Draw("same")
        ok = int(fit_res.Get().Status()) == 0 if fit_res.Get() else False
        mean, mean_err = fg.GetParameter(1), fg.GetParError(1)
        sigma, sigma_err = fg.GetParameter(2), fg.GetParError(2)
        chi2, ndf = fg.GetChisquare(), fg.GetNDF()
        box_lines = [
            f"N_{{toys}} = {n_total}  ({100*eff:.1f}% usable)",
            f"Mean = {mean:.3f} #pm {mean_err:.3f}",
            f"Sigma = {sigma:.3f} #pm {sigma_err:.3f}",
            f"#chi^{{2}}/ndf = {chi2:.1f}/{ndf}" + ("" if ok else "  [fit did not fully converge]"),
        ]
    else:
        box_lines = [
            f"N_{{toys}} = {n_total}  ({100*eff:.1f}% usable)",
            f"Raw mean = {np.mean(pulls):.3f}, RMS = {np.std(pulls):.3f}",
            "TOO FEW USABLE TOYS FOR A",
            "RELIABLE GAUSSIAN FIT",
            "(most toys failed MINOS error",
            "determination - category is likely",
            "background-statistics limited)",
        ]

box = ROOT.TPaveText(0.47, 0.60, 0.89, 0.89, "NDC")
box.SetFillColor(0)
box.SetBorderSize(1)
box.SetTextAlign(12)
box.SetTextSize(0.026)
for line in box_lines:
    box.AddText(line)
box.Draw()

outname = f"{args.outdir}/pull_{args.cat}_truth_{args.truth_func}_fit_{args.fit_func}_r{int(r_in)}_v2.png"
canv.SaveAs(outname)
print(f"--> Saved pull plot: {outname}")
f.Close()
