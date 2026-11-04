#!/usr/bin/env python3
"""Summary plot: combined (all-categories, unmasked) sculpting bias test.

Truth = real GGJets+DDQCDGJets+TTGG MC-template shape (RooHistPdf) in every
category simultaneously; Fit = the real analytic envelope datacard. Gaussian
fit mean/sigma of the pull, per injected r_truth, taken from the core-fit
values already reported by plot_bias_pull(_FitDiagnostics).py in
bias_plots_combined/pull_combined_truth_GGJetsDDQCDTTGG_fit_envelope_r*.png
(no separate JSON summary exists for this study, so these are transcribed
from the fitted stat boxes -- r0 from the _v2/iterative-core-fit version,
r2 from the plain version, since that's what's on disk).
"""
import matplotlib.pyplot as plt
import mplhep as hep
from matplotlib.ticker import MultipleLocator

hep.style.use("CMS")
plt.rcParams.update({
    "font.size": 13,
    "axes.labelsize": 13,
    "axes.titlesize": 13,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.fontsize": 9,
})
LUMI_LABEL = "421 fb$^{-1}$ (13 TeV + 13.6 TeV)"

# (r_truth, mean, mean_err, sigma, sigma_err)
POINTS = [
    (0.0, -0.176, 0.037, 1.127, 0.026),
    (2.0, -0.2926, 0.0354, 1.115, 0.025),
]

fig, ax = plt.subplots(figsize=(9, 7))

xs = [p[0] for p in POINTS]
ys = [p[1] for p in POINTS]
yerr_mean = [p[2] for p in POINTS]
sigma = [p[3] for p in POINTS]

ax.errorbar(xs, ys, yerr=sigma, fmt="o", ms=9, capsize=6, lw=1.5,
            color="firebrick", label=r"Gaussian fit $\sigma$ (pull spread)")
ax.errorbar(xs, ys, yerr=yerr_mean, fmt="o", ms=9, capsize=0, lw=3,
            color="black", label=r"Gaussian fit mean $\pm$ error")

for x, y, s in zip(xs, ys, sigma):
    ax.annotate(f"mean = {y:+.3f}\n$\\sigma$ = {s:.3f}", (x, y),
                textcoords="offset points", xytext=(18, 0), ha="left", va="center", fontsize=11)

ax.axhline(0.0, color="gray", ls="--", lw=1)
ax.set_xlim(-0.5, 3.0)
ax.set_xticks([0, 2])
ax.set_xlabel("Injected signal strength, Expected signal (r)")
ax.set_ylabel(r"Gaussian fit mean $\pm$ $\sigma$ (pull units)")
ax.yaxis.set_major_locator(MultipleLocator(0.25))
ax.yaxis.set_minor_locator(MultipleLocator(0.05))
ax.grid(which="major", alpha=0.3, lw=0.2)
ax.grid(which="minor", alpha=0.12, lw=0.1)
ax.legend(loc="lower left", fontsize=9)

ax.text(0.0, 1.02, "CMS", transform=ax.transAxes,
        fontsize=16, fontweight="bold", ha="left", va="bottom")
ax.text(0.1, 1.02, "Work in Progress", transform=ax.transAxes,
        fontsize=13, fontstyle="italic", ha="left", va="bottom")
ax.text(1.0, 1.02, LUMI_LABEL, transform=ax.transAxes,
        fontsize=12, ha="right", va="bottom")

fig.suptitle(
    "Combined sculpting bias: truth = GGJets+DDQCDGJets+TTGG MC template (all categories),\n"
    "fit = analytic envelope",
    fontsize=13, y=1.1,
)
fig.tight_layout()
outname = "summary_combined_sculpting.png"
fig.savefig(outname, dpi=200, bbox_inches="tight")
print(f"--> Saved {outname}")
