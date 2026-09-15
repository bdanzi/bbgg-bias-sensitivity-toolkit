#!/usr/bin/env python3
import ROOT
import sys
import os
import argparse

ROOT.gROOT.SetBatch(True)
#ROOT.gStyle.SetOptStat(110)
ROOT.gStyle.SetOptStat("mr")
ROOT.gStyle.SetOptFit(111)

parser = argparse.ArgumentParser(description='Plot Pull from FitDiagnostics Matrix')
parser.add_argument('-i', '--input', required=True, help='Input fitDiagnostics file')
parser.add_argument('--r-truth', type=float, required=True, help='Injected r value')
parser.add_argument('--truth-func', required=True, help='Truth function name')
parser.add_argument('--fit-func', required=True, help='Fit function name')
parser.add_argument('--cat', required=True, help='Category descriptor')
parser.add_argument('-o', '--outdir', default='./bias_plots', help='Output directory')
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

# Error branch logic handling asymmetric errors from FitDiagnostics tree
r_in = args.r_truth

plotting = ""
if "2" in args.cat or "4" in args.cat or "3" in args.cat:
    #plotting += f"(r-{r_in})/((rLoErr/rHiErr>5.0 || rHiErr/rLoErr>5.0) ? rErr : (r>{r_in} ? rLoErr : rHiErr))>>h"
    plotting += f"(r-{r_in})/((rLoErr/rHiErr>3.0 || rHiErr/rLoErr>3.0) ? ((rLoErr+rHiErr)/2) : (r>{r_in} ? rLoErr : rHiErr))>>h" # r = 2 sculpting for all categories and cat2sculpting
    #plotting += f"(r-{r_in})/((rLoErr+rHiErr)/2)>>h"
    #plotting += f"((r-{r_in})/(r>{r_in} ? rLoErr : rHiErr))>>h"
    #plotting += f"((r-{r_in})/ rErr)>>h"
    #plotting += f"((r-{r_in})/(r>{r_in} ? rLoErr : rHiErr))>>h" # r = 3
else:
    plotting += f"(r-{r_in})/((rLoErr+rHiErr)/2)>>h"
todraw = f"{plotting}"
base_cut = "(fit_status==0 || fit_status==300)"
# base_cut = "(fit_status==0)" same function

if "2" in args.cat or "4" in args.cat or "3" in args.cat:
    #base_cut += " && rLoErr > 0.5 && rHiErr > 0.5"# && rErr > 0.5" for same PDFs
    base_cut += " && rLoErr > 0.05 && rHiErr > 0.05"# r = 2 all categories merged + cat2sculpting
else:
    base_cut += " && rLoErr > 0.05 && rHiErr > 0.05"

"""    
diff_cut = 5
if "4" in args.cat:
    diff_cut = 10
base_cut += f" && abs((r-{r_in}))<{diff_cut}"
"""
t.Draw(todraw, base_cut, "goff")

canv = ROOT.TCanvas("c", "c", 800, 600)
hist_pull.Draw("E")

maxX = 5.0
maxFit = 5.0
fg = ROOT.TF1("fg", "gaus", -maxX, maxX)
#fg.SetParameters(
#    hist_pull.GetMaximum(),
#    hist_pull.GetMean(),
#    hist_pull.GetRMS()
#)
fg.SetLineColor(2)
fg.SetLineWidth(2)
hist_pull.Fit(fg, "RL", "", -maxFit, maxFit)
#fg.Draw("same")

outname = f"{args.outdir}/pull_{args.cat}_truth_{args.truth_func}_fit_{args.fit_func}_r{int(r_in)}.png"
canv.SaveAs(outname)
print(f"--> Saved pull plot: {outname}")
f.Close()
