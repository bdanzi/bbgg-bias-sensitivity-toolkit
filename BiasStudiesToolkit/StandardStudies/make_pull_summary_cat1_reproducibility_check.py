"""
Same analysis convention as make_pull_summary.py / make_pull_summary_altws_cat2.py
(Irene's script: fixed gaus fit range -2,2, no iterative core-range determination),
adapted to run on the 5 cat1 masked-isolation reproducibility-check toy files
(see description.txt in this directory) without touching the original scripts
or their outputs.
"""

import os
import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(1111)
ROOT.gStyle.SetOptFit(1)

_CANVAS = ROOT.TCanvas("c_pulls", "c_pulls", 800, 600)

CAT = "cat1"
PDF = 0  # truth = bern1 (pdfindex_hgg_cat1_13TeV=0) for all 5 combos
R_MIN, R_MAX = -50.0, 50.0
BOUNDARY_TOL = 0.01
MIN_TRUSTED_FOR_FIT = 10

# label -> (fname, r_truth/expectSignal)
RUNS = {
    "FINAL_r0":       ("fitDiagnostics.fit_cat1_envelope_CHECK_truth_bern1_r0.root",             0.0),
    "FINAL_r1":       ("fitDiagnostics.fit_cat1_envelope_CHECK_truth_bern1_r1_masked.root",       1.0),
    "ALT_r1":         ("fitDiagnostics.fit_cat1_envelope_CHECK_truth_bern1_r1_altws.root",        1.0),
    "ALT_r0":         ("fitDiagnostics.fit_cat1_envelope_CHECK_truth_bern1_r0_altws.root",         0.0),
    "LATESTFINAL_r0": ("fitDiagnostics.fit_cat1_envelope_CHECK_truth_bern1_r0_latestfinal.root",   0.0),
}

OUTDIR = "pull_bias_scan_cat1_reproducibility_check"
os.makedirs(OUTDIR, exist_ok=True)

results = {}
for label, (fname, expect_signal) in RUNS.items():
    if not os.path.exists(fname):
        print(f"[WARNING] Missing file: {fname}")
        continue

    f = ROOT.TFile.Open(fname)
    if not f or f.IsZombie():
        print(f"[WARNING] Could not open: {fname}")
        continue

    tree = f.Get("tree_fit_sb")
    if not tree:
        print(f"[WARNING] No tree_fit_sb in {fname}")
        f.Close()
        continue

    hname = f"pulls_{CAT}_pdf{PDF}_{label}"
    pulls = ROOT.TH1F(
        hname,
        f"Pull distribution {CAT} for r={expect_signal:g} with full envelope, "
        f"toys thrown on pdf{PDF} ({label});pull;toys",
        50, -5, 5,
    )

    nTotal = tree.GetEntries()
    nPinnedLow = nPinnedHigh = nBadStatus = nBadSigma = nTrusted = 0

    for i in range(nTotal):
        tree.GetEntry(i)
        r = tree.r
        lo = tree.rLoErr
        hi = tree.rHiErr
        status = tree.fit_status

        if status == -1:
            nBadStatus += 1
            continue
        if r <= (R_MIN + BOUNDARY_TOL):
            nPinnedLow += 1
            continue
        if r >= (R_MAX - BOUNDARY_TOL):
            nPinnedHigh += 1
            continue

        sigma = 0.5 * (abs(lo) + abs(hi))
        if sigma <= 0:
            nBadSigma += 1
            continue

        pull = (r - expect_signal) / sigma
        pulls.Fill(pull)
        nTrusted += 1

    print(f"--- {CAT}, pdf{PDF}, {label} ---")
    print(f"  Total toys:        {nTotal}")
    if nTotal:
        print(f"  Failed fit status: {nBadStatus} ({100.0*nBadStatus/nTotal:.1f}%)")
        print(f"  Pinned at rMin:    {nPinnedLow} ({100.0*nPinnedLow/nTotal:.1f}%)")
        print(f"  Pinned at rMax:    {nPinnedHigh} ({100.0*nPinnedHigh/nTotal:.1f}%)")
        print(f"  Bad sigma (<=0):   {nBadSigma} ({100.0*nBadSigma/nTotal:.1f}%)")
        print(f"  Trusted toys used: {nTrusted} ({100.0*nTrusted/nTotal:.1f}%)")

    bias = biasErr = width = None
    if nTrusted > MIN_TRUSTED_FOR_FIT:
        pulls.Fit("gaus", "Q", "", -2, 2)
        fit = pulls.GetFunction("gaus")
        bias = fit.GetParameter(1)
        biasErr = fit.GetParError(1)
        width = fit.GetParameter(2)
    else:
        print(f"  WARNING: too few trusted toys ({nTrusted}) to fit a Gaussian reliably")

    _CANVAS.cd()
    _CANVAS.Clear()
    pulls.Draw()
    _CANVAS.SaveAs(os.path.join(OUTDIR, f"pulls_{CAT}_pdf{PDF}_{label}.png"))

    results[label] = {
        "nTotal": nTotal,
        "nTrusted": nTrusted,
        "bias": bias,
        "biasErr": biasErr,
        "width": width,
        "meanRaw": pulls.GetMean(),
        "rmsRaw": pulls.GetRMS(),
    }

    f.Close()

print("\n=== SUMMARY (Irene-style gaus fit, range -2,2) ===")
header = f"{'Label':16s} {'NTotal':8s} {'NTrusted':9s} {'Bias':10s} {'BiasErr':10s} {'Width':8s}"
print(header)
print("-" * len(header))
for label, r in results.items():
    bias_str = f"{r['bias']:.4f}" if r["bias"] is not None else "N/A"
    biasErr_str = f"{r['biasErr']:.4f}" if r["biasErr"] is not None else "N/A"
    width_str = f"{r['width']:.4f}" if r["width"] is not None else "N/A"
    print(f"{label:16s} {r['nTotal']:<8d} {r['nTrusted']:<9d} {bias_str:10s} {biasErr_str:10s} {width_str:8s}")

print(f"\nAll plots written to: {OUTDIR}/")
