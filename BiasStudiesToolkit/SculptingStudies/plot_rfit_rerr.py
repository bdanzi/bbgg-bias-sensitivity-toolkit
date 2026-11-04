#!/usr/bin/env python3
"""Plot the raw fitted signal strength (r_fit) and its fit error (rErr)
distributions from a FitDiagnostics toy tree -- complementary to the pull
plot (which is (r_fit - r_in)/sigma_fit), showing the two ingredients on
their own physical scale instead of pull units.

Same toy-quality cuts as plot_bias_pull_FitDiagnostics.py, for consistency.
"""
import argparse
import os
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(111111)

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input", required=True)
parser.add_argument("--r-truth", type=float, required=True)
parser.add_argument("--cat", required=True)
parser.add_argument("-o", "--outdir", default="./bias_plots")
parser.add_argument("--r-min", type=float, default=None)
parser.add_argument("--r-max", type=float, default=None)
parser.add_argument("--boundary-eps", type=float, default=1e-3)
args = parser.parse_args()

os.makedirs(args.outdir, exist_ok=True)

if not os.path.exists(args.input):
    sys.exit(f"[ERROR] Input file {args.input} missing.")

f = ROOT.TFile.Open(args.input)
t = f.Get("tree_fit_sb")
if not t:
    sys.exit(f"[ERROR] tree_fit_sb missing in {args.input}")

base_cut = "(fit_status==0 || fit_status==300) && rLoErr > 0.05 && rHiErr > 0.05"
if args.r_min is not None:
    base_cut += f" && abs(r-({args.r_min}))>{args.boundary_eps}"
if args.r_max is not None:
    base_cut += f" && abs(r-({args.r_max}))>{args.boundary_eps}"

canv = ROOT.TCanvas("c", "c", 800, 600)
canv.SetGridx()
canv.SetGridy()

# --- r_fit ---
n_r = t.Draw("r>>hr", base_cut, "goff")
hr = ROOT.gDirectory.Get("hr")
if hr and hr.GetEntries() > 0:
    hr.SetTitle(f"r_{{fit}}: r_{{in}}={args.r_truth} ({args.cat})")
    hr.GetXaxis().SetTitle("r_{fit}")
    hr.GetYaxis().SetTitle(f"Entries / {hr.GetBinWidth(1):.3g}")
    hr.SetLineColor(ROOT.kBlue + 1)
    hr.Draw("E")
    line = ROOT.TLine(args.r_truth, 0, args.r_truth, hr.GetMaximum() * 1.05)
    line.SetLineColor(ROOT.kRed)
    line.SetLineStyle(2)
    line.SetLineWidth(2)
    line.Draw()
    outname_r = f"{args.outdir}/rfit_{args.cat}_r{int(args.r_truth)}.png"
    canv.SaveAs(outname_r)
    print(f"--> Saved r_fit plot: {outname_r} (mean={hr.GetMean():.3f}, RMS={hr.GetRMS():.3f}, N={n_r})")
else:
    print(f"[WARN] No usable toys for r_fit plot ({args.cat}, r={args.r_truth})")

# --- rErr ---
# combine's own "rErr" branch is always 0 in this FitDiagnostics output (a
# known quirk: with asymmetric/MINOS errors it never fills the symmetric
# branch, only rLoErr/rHiErr). Use the same effective-error construction as
# plot_bias_pull_FitDiagnostics.py's pull denominator instead: the symmetric
# average when the two sides differ by more than a factor of 3, otherwise
# the error on the side r actually moved towards relative to r_in.
r_in = args.r_truth
eff_err_expr = f"(rLoErr/rHiErr>3.0 || rHiErr/rLoErr>3.0) ? (rLoErr+rHiErr)/2 : (r>{r_in} ? rLoErr : rHiErr)"
n_e = t.Draw(f"{eff_err_expr}>>he", base_cut, "goff")
he = ROOT.gDirectory.Get("he")
if he and he.GetEntries() > 0:
    he.SetTitle(f"Effective rErr: r_{{in}}={args.r_truth} ({args.cat})")
    he.GetXaxis().SetTitle("effective rErr (side-picked/symmetrized fit uncertainty on r)")
    he.GetYaxis().SetTitle(f"Entries / {he.GetBinWidth(1):.3g}")
    he.SetLineColor(ROOT.kGreen + 2)
    he.Draw("E")
    outname_e = f"{args.outdir}/rerr_eff_{args.cat}_r{int(args.r_truth)}.png"
    canv.SaveAs(outname_e)
    print(f"--> Saved rErr plot: {outname_e} (mean={he.GetMean():.3f}, RMS={he.GetRMS():.3f}, N={n_e})")
else:
    print(f"[WARN] No usable toys for rErr plot ({args.cat}, r={args.r_truth})")

f.Close()
