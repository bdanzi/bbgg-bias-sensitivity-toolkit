import ROOT
import numpy as np
import argparse
import os

ROOT.gROOT.SetBatch(True)

N_toys = 1000
r_truth = 1

truth_function = "exp"
fit_function = "poly"

name = "truth_%s_fit_%s" % (truth_function, fit_function)

parser = argparse.ArgumentParser(description="Plot Bias Test Pull Distributions from Combine.")
parser.add_argument("-i", "--input", required=True, help="Path to the input higgsCombine ROOT file")
parser.add_argument("-o", "--output-dir", default="./plots", help="Directory where to save the output plots")
parser.add_argument("--r-truth", type=float, default=0.0, help="The injected truth value of r (default: 0.0)")
parser.add_argument("--truth-func", default="exp", help="Name of the truth function used for generation")
parser.add_argument("--fit-func", default="poly", help="Name of the fit function used")
parser.add_argument("--cat", default="cat0", help="Category name for labels")

args = parser.parse_args()

if not os.path.exists(args.output_dir):
    os.makedirs(args.output_dir)
    
if not os.path.exists(args.input):
    raise FileNotFoundError(f"Input file {args.input} does not exist!")

f = ROOT.TFile.Open(args.input)
t = f.Get("limit")

name = f"truth_{args.truth_func}_fit_{args.fit_func}_{args.cat}"
hist_pull = ROOT.TH1F(f"pull_{name}", f"Pull: truth={args.truth_func}, fit={args.fit_func} ({args.cat})", 40, -4, 4)
hist_pull.GetXaxis().SetTitle("Pull = (r_{truth}-r_{fit})/#sigma_{fit}")
hist_pull.GetYaxis().SetTitle("Entries")

sigma_values = np.array([])

for i_toy in range(N_toys):
    # Best-fit value
    t.GetEntry(i_toy * 3)
    r_fit = getattr(t, "r")

    # -1 sigma value
    t.GetEntry(i_toy * 3 + 1)
    r_lo = getattr(t, "r")

    # +1 sigma value
    t.GetEntry(i_toy * 3 + 2)
    r_hi = getattr(t, "r")

    diff = r_truth - r_fit
    # Use uncertainty depending on where mu_truth is relative to mu_fit
    if diff > 0:
        sigma = abs(r_hi - r_fit)
    else:
        sigma = abs(r_lo - r_fit)

    if sigma != 0:
        sigma_values = np.append(sigma_values, sigma)
    else:
        sigma = sigma_values.mean()

    if sigma != 0:
        hist_pull.Fill(diff / sigma)

canv = ROOT.TCanvas()
hist_pull.Draw()

# Fit Gaussian to pull distribution
ROOT.gStyle.SetOptFit(111)
hist_pull.Fit("gaus")

canv.SaveAs("%s/part4_pull_%s.png" % (args.output_dir, name))
