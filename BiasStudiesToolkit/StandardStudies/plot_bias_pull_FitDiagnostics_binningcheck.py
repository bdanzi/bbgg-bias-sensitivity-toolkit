#!/usr/bin/env python3
"""Same pull-plotting logic as plot_bias_pull_FitDiagnostics.py, but with a
configurable number of histogram bins, to check whether the reported Gaussian
mean is sensitive to binning (40 bins, width 0.25, is the production default).
"""
import argparse
import os
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(110)
ROOT.gStyle.SetOptFit(111)

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--input', required=True)
parser.add_argument('--r-truth', type=float, required=True)
parser.add_argument('--truth-func', required=True)
parser.add_argument('--fit-func', required=True)
parser.add_argument('--cat', required=True)
parser.add_argument('-o', '--outdir', default='./bias_plots')
parser.add_argument('--nbins', type=int, required=True)
parser.add_argument('--suffix', default='_v2')
args = parser.parse_args()

os.makedirs(args.outdir, exist_ok=True)

f = ROOT.TFile.Open(args.input)
t = f.Get("tree_fit_sb")
if not t:
    print(f"[ERROR] tree_fit_sb missing in {args.input}")
    sys.exit(1)

title = f"Pull: r_{{in}}={args.r_truth}, Truth={args.truth_func.upper()}, Fit={args.fit_func.upper()} ({args.cat}) [{args.nbins} bins]"
hist_pull = ROOT.TH1F("h", title, args.nbins, -5, 5)
hist_pull.GetXaxis().SetTitle("(r_{fit} - r_{in}) / #sigma_{fit}")
hist_pull.GetYaxis().SetTitle(f"Entries / {10.0/args.nbins:.3f}")

r_in = args.r_truth
plotting = f"(r-{r_in})/((rLoErr/rHiErr>3.0 || rHiErr/rLoErr>3.0) ? (rLoErr+rHiErr)/2 : (r>{r_in} ? rLoErr : rHiErr))"
todraw = f"{plotting}>>h"
base_cut = "(fit_status==0 || fit_status==300) && rLoErr > 0.05 && rHiErr > 0.05"

t.Draw(todraw, base_cut, "goff")

canv = ROOT.TCanvas("c", "c", 800, 600)
hist_pull.Draw("E")

maxX = 5.0
fg = ROOT.TF1("fg", "gaus", -maxX, maxX)
fg.SetLineColor(2)
fg.SetLineWidth(2)

hist_pull.Fit(fg, "LRQ0", "", -maxX, maxX)
core_width = 2.0
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
hist_pull.Fit(fg, "LR", "", lo, hi)
fg.SetRange(-maxX, maxX)

n_entries = int(hist_pull.GetEntries())
raw_mean = hist_pull.GetMean()
raw_rms = hist_pull.GetRMS()
fit_mean = fg.GetParameter(1)
fit_mean_err = fg.GetParError(1)
fit_sigma = fg.GetParameter(2)

print(f"--> nbins={args.nbins}  n_entries={n_entries}  raw_hist_mean={raw_mean:.4f}  raw_hist_rms={raw_rms:.4f}")
print(f"--> Gaussian core fit: mean={fit_mean:.4f} +/- {fit_mean_err:.4f}, sigma={fit_sigma:.4f}, core range=[{lo:.2f},{hi:.2f}]")

outname = f"{args.outdir}/pull_{args.cat}_truth_{args.truth_func}_fit_{args.fit_func}_r{int(r_in)}{args.suffix}.png"
canv.SaveAs(outname)
print(f"--> Saved: {outname}")
f.Close()
