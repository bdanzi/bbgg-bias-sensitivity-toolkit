"""
Same as ../../../make_pull_summary.py (Irene's approach: pull = (r-r_inj) /
((|rLoErr|+|rHiErr|)/2), with convergence/boundary/sigma filtering), but
adapted to the cat1 envelope (isolated, masked) toy files produced by
StandardStudies/run_envelope_bias.sh (fitDiagnostics.fit_cat1_envelope_truth_
<func>_fit_envelope_r<r>.root), which used rMin=-50/rMax=50 (not -5/5) and
scan truth functions instead of pdf indices.
"""
import os
import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(1111)
ROOT.gStyle.SetOptFit(1)

_CANVAS = ROOT.TCanvas("c_pulls", "c_pulls", 800, 600)

COMBOS = [
    ("exp1", 0.0), ("exp1", 2.0),
    ("bern1", 0.0), ("bern1", 2.0),
    ("pow1", 0.0), ("pow1", 2.0),
    ("lau1", 0.0), ("lau1", 2.0),
]

R_MIN, R_MAX = -50.0, 50.0
BOUNDARY_TOL = 0.01
FILE_TEMPLATE = "fitDiagnostics.fit_cat1_envelope_truth_{func}_fit_envelope_r{r:.0f}.root"
MIN_TRUSTED_FOR_FIT = 10

OUTDIR = "pull_bias_scan_cat1_envelope_irene"
os.makedirs(OUTDIR, exist_ok=True)


def analyze_toy_file(func, r_truth):
    fname = FILE_TEMPLATE.format(func=func, r=r_truth)
    if not os.path.exists(fname):
        print(f"[WARNING] Missing file: {fname}")
        return None

    f = ROOT.TFile.Open(fname)
    if not f or f.IsZombie():
        print(f"[WARNING] Could not open: {fname}")
        return None

    tree = f.Get("tree_fit_sb")
    if not tree:
        print(f"[WARNING] No tree_fit_sb in {fname}")
        f.Close()
        return None

    hname = f"pulls_cat1_{func}_r{r_truth:.0f}"
    pulls = ROOT.TH1F(
        hname,
        f"Pull distribution cat1 (isolated) for r={r_truth:.0f}, truth={func}, fit=envelope;pull;toys",
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

        pull = (r - r_truth) / sigma
        pulls.Fill(pull)
        nTrusted += 1

    print(f"--- cat1, truth={func}, r={r_truth:.0f} ---")
    print(f"  Total toys:        {nTotal}")
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
    _CANVAS.SaveAs(os.path.join(OUTDIR, f"pulls_cat1_{func}_r{r_truth:.0f}.png"))

    result = {
        "nTotal": nTotal,
        "nTrusted": nTrusted,
        "bias": bias,
        "biasErr": biasErr,
        "width": width,
        "meanRaw": pulls.GetMean(),
        "rmsRaw": pulls.GetRMS(),
    }
    f.Close()
    return result


results = {}
for func, r_truth in COMBOS:
    res = analyze_toy_file(func, r_truth)
    if res is not None:
        results[(func, r_truth)] = res

# ---------------- Combined summary plot: bias vs truth function, one curve per r ----------------
colors = [ROOT.kRed + 1, ROOT.kBlue + 1]
funcs = ["bern1", "exp1", "pow1", "lau1"]
func_x = {f: i for i, f in enumerate(funcs)}

c2 = ROOT.TCanvas("summary", "Bias summary", 900, 650)
mg = ROOT.TMultiGraph()
legend = ROOT.TLegend(0.72, 0.78, 0.90, 0.90)

graphs = []
for idx, r_truth in enumerate([0.0, 2.0]):
    xs, ys, eys = [], [], []
    for func in funcs:
        r = results.get((func, r_truth))
        if r is None or r["bias"] is None:
            continue
        xs.append(func_x[func])
        ys.append(r["bias"])
        eys.append(r["biasErr"] if r["biasErr"] else 0.0)
    if not xs:
        continue
    g = ROOT.TGraphErrors(len(xs))
    for i, (x, y, ey) in enumerate(zip(xs, ys, eys)):
        g.SetPoint(i, x, y)
        g.SetPointError(i, 0, ey)
    color = colors[idx % len(colors)]
    g.SetLineColor(color)
    g.SetMarkerColor(color)
    g.SetMarkerStyle(20)
    g.SetLineWidth(2)
    g.SetTitle(f"r={r_truth:.0f}")
    graphs.append(g)
    mg.Add(g, "LP")
    legend.AddEntry(g, f"r={r_truth:.0f}", "lp")

if graphs:
    mg.SetTitle("cat1 (isolated) pull bias vs truth function;truth function;Bias (fitted Gaussian mean of pull)")
    mg.Draw("A")
    mg.GetYaxis().SetRangeUser(-0.5, 0.5)
    zero_line = ROOT.TLine(-0.5, 0, len(funcs) - 0.5, 0)
    zero_line.SetLineStyle(2)
    zero_line.SetLineColor(ROOT.kGray + 2)
    zero_line.Draw()
    legend.Draw()
    c2.SaveAs(os.path.join(OUTDIR, "bias_summary_cat1_envelope.png"))
else:
    print("[WARNING] No combos had enough trusted toys to build the summary plot.")

print("\n=== SUMMARY TABLE ===")
header = f"{'truth':6s} {'r':4s} {'NTotal':8s} {'NTrusted':9s} {'Bias':10s} {'BiasErr':10s} {'Width':8s}"
print(header)
print("-" * len(header))
for func, r_truth in COMBOS:
    r = results.get((func, r_truth))
    if r is None:
        print(f"{func:6s} {r_truth:<4.0f} {'MISSING':>8s}")
        continue
    bias_str = f"{r['bias']:.4f}" if r["bias"] is not None else "N/A"
    biasErr_str = f"{r['biasErr']:.4f}" if r["biasErr"] is not None else "N/A"
    width_str = f"{r['width']:.4f}" if r["width"] is not None else "N/A"
    print(f"{func:6s} {r_truth:<4.0f} {r['nTotal']:<8d} {r['nTrusted']:<9d} {bias_str:10s} {biasErr_str:10s} {width_str:8s}")

print(f"\nAll plots written to: {OUTDIR}/")
