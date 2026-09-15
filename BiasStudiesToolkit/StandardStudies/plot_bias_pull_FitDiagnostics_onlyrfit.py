#!/usr/bin/env python3
import ROOT
import sys
import os
import argparse
import array
ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(1110)
#ROOT.gStyle.SetOptStat("mr")
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
hist_pull = ROOT.TH1F("h", title, 40, -10, 10)
hist_pull.GetXaxis().SetTitle("r_{fit} - r_{in}")
hist_pull.GetYaxis().SetTitle("Entries / 0.25")

# Error branch logic handling asymmetric errors from FitDiagnostics tree
r_in = args.r_truth

todraw = f"(r-{r_in})>>h"
diff_cut = 5
if "4" in args.cat:
    diff_cut = 10
    
t.Draw(todraw, f"fit_status>=0 && abs((r-{r_in}))<{diff_cut} && rLoErr > 0.05 && rHiErr > 0.05", "goff")


canv = ROOT.TCanvas("c", "c", 800, 600)
hist_pull.Draw("E")

maxX = 10.0
maxFitX = 1.0
fg = ROOT.TF1("fg", "gaus", -maxX, maxX)
fg.SetLineColor(2)
fg.SetLineWidth(2)
hist_pull.Fit(fg, "0LR", "", -maxFitX, maxFitX)
fg.Draw("same")

outname = f"{args.outdir}/pull_{args.cat}_truth_{args.truth_func}_fit_{args.fit_func}_r{int(r_in)}_rfitonly.png"
canv.SaveAs(outname)
print(f"--> Saved pull plot: {outname}")

# --- Histograms for r and rErr ---
hist_r = ROOT.TH1F("hist_r", f"r distribution ({args.cat});r;Events", 40, -5, 5)
hist_lo = ROOT.TH1F("hist_lo", f"r Lower Error ({args.cat});#sigma(low);Events", 40, -5, 5)
hist_hi = ROOT.TH1F("hist_hi", f"r Upper Error ({args.cat});#sigma(high);Events", 40, -5, 5)
hist_sym = ROOT.TH1F("hist_sym", f"r Symmetric Error ({args.cat});average #sigma;Events", 40, -5, 5)
hist_rerr = ROOT.TH1F("hist_rerr", f"r uncertainty ({args.cat});rErr;Events", 40, -5, 5)
for i in range(t.GetEntries()):
    t.GetEntry(i)

    if not hasattr(t, "r"):
        continue
    #print(t.fit_status)
    r = t.r
    if t.fit_status<0:
        r = -5
    #    continue
    #r = t.r
    #if ((t.r-args.r_truth)/((t.rLoErr/t.rHiErr>2.0 || t.rHiErr/t.rLoErr>2.0) ? (t.rLoErr+t.rHiErr)/2 : (r > r_truth ? t.rLoErr : t.rHiErr))) > -2:
    #    continue
    hist_r.Fill(r)
    # --- asymmetric errors ---
    if hasattr(t, "rLoErr") and hasattr(t, "rHiErr"):
        lo = t.rLoErr
        hi = t.rHiErr

        hist_lo.Fill(lo)
        hist_hi.Fill(hi)
        hist_sym.Fill(0.5 * (lo + hi))
    if hasattr(t, "rErr"):
        hist_rerr.Fill(t.rErr)


c3 = ROOT.TCanvas("c3", "r", 800, 600)
hist_r.SetLineColor(ROOT.kBlue+1)
hist_r.Draw("HIST")
xq = array.array("d", [0.5])
yq = array.array("d", [0.0])
hist_r.GetQuantiles(1, yq, xq)
median_r = yq[0]
box = ROOT.TPaveText(0.3, 0.5, 0.90, 0.82, "NDC")
box.AddText(f"Median = {median_r:.3f}")
box.SetFillStyle(0)
box.SetBorderSize(0)
box.Draw()
ROOT.gPad.Update()
ROOT.gPad.Modified()
print("Median:", median_r)
#c3.Modified()
#c3.Update()
outname = f"{args.outdir}/pull_{args.cat}_truth_{args.truth_func}_fit_{args.fit_func}_r{int(r_in)}_r.png"
c3.SaveAs(outname)
print(f"--> Saved pull plot: {outname}")

c2 = ROOT.TCanvas("c2", "r", 800, 600)
hist_lo.SetLineColor(ROOT.kBlue+1)
hist_lo.Draw("HIST")
outname = f"{args.outdir}/pull_{args.cat}_truth_{args.truth_func}_fit_{args.fit_func}_r{int(r_in)}_loerr.png"
c2.SaveAs(outname)
print(f"--> Saved pull plot: {outname}")

c5 = ROOT.TCanvas("c5", "r", 800, 600)
hist_hi.SetLineColor(ROOT.kBlue+1)
hist_hi.Draw("HIST")
outname = f"{args.outdir}/pull_{args.cat}_truth_{args.truth_func}_fit_{args.fit_func}_r{int(r_in)}_hierr.png"
c5.SaveAs(outname)
print(f"--> Saved pull plot: {outname}")

c4 = ROOT.TCanvas("c4", "comparison", 800, 600)
hist_lo.SetLineColor(ROOT.kRed)
hist_hi.SetLineColor(ROOT.kGreen+2)
hist_lo.Draw("HIST")
hist_hi.Draw("HIST SAME")
leg = ROOT.TLegend(0.65, 0.75, 0.88, 0.88)
leg.AddEntry(hist_lo, "rLoErr", "l")
leg.AddEntry(hist_hi, "rHiErr", "l")
leg.Draw()
outname = f"{args.outdir}/pull_{args.cat}_truth_{args.truth_func}_fit_{args.fit_func}_r{int(r_in)}_hierrlowerr.png"
c4.SaveAs(outname)
print(f"--> Saved pull plot: {outname}")

c_rerr = ROOT.TCanvas("c_rerr", "rErr", 800, 600)
hist_rerr.SetLineColor(ROOT.kRed+1)
hist_rerr.SetFillColorAlpha(ROOT.kRed+1, 0.3)
hist_rerr.Draw("HIST")
c_rerr.SaveAs(
    f"{args.outdir}/pull_{args.cat}_truth_{args.truth_func}_fit_{args.fit_func}_r{int(r_in)}_rErr.png"
)

print("--> Saved rErr plot")

c_errsym = ROOT.TCanvas("c_errsym", "average error", 800, 600)
hist_sym.SetLineColor(ROOT.kRed+1)
hist_sym.SetFillColorAlpha(ROOT.kRed+1, 0.3)
hist_sym.Draw("HIST")
c_errsym.SaveAs(
    f"{args.outdir}/pull_{args.cat}_truth_{args.truth_func}_fit_{args.fit_func}_r{int(r_in)}_errSym.png"
)

f.Close()
