#!/usr/bin/env python3
"""Summary plot for cat0 (default0 variant): fit_mean/fit_sigma (from
FitDiagnostics pull toys) vs the truth function's pdfindex, read from
bias_plots_cat0_fixedmodel_default0/pull_summary.json (produced by
run_cat0_fixedmodel_bias_default0.sh). Standalone counterpart to
plot_mean_sigma_vs_pdfindex_dropfunc.py, same style, single category.

The pdfindex x-axis is resolved against Datacard_cat0truthstandard.root
(cat0's standard 4-function envelope), not Datacard.root, since the real
workspace fixes cat0 to a single function.
"""
import json
import re
import subprocess

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
    "legend.title_fontsize": 10,
})
LUMI_LABEL = "421 fb$^{-1}$ (13 TeV + 13.6 TeV)"

WS = "Datacard_cat0truthstandard.root"
JSON_PATH = "bias_plots_cat0_fixedmodel_default0/pull_summary.json"


def resolve_pdfindex_map():
    out = subprocess.run(
        ["python3", "resolve_pdfindex_legs.py", WS, "0"],
        capture_output=True, text=True, check=True,
    ).stdout
    mapping = {}
    for line in out.splitlines():
        m = re.match(r"IDX_\S+_(\w+)='[^=]+=(\d+)'", line)
        if m:
            mapping[m.group(1)] = int(m.group(2))
    return mapping


def main():
    idx_map = resolve_pdfindex_map()
    with open(JSON_PATH) as f:
        entries = json.load(f)

    fig, axes = plt.subplots(1, 2, figsize=(16, 7), sharey=True)
    r_values = [0.0, 2.0]

    for ax, r_truth in zip(axes, r_values):
        pts = [e for e in entries if e["r_truth"] == r_truth]
        xs = [idx_map.get(e["truth_func"]) for e in pts]
        ys = [e["fit_mean"] for e in pts]
        yerr = [e["fit_sigma"] for e in pts]
        labels = [e["truth_func"] for e in pts]

        keep = [i for i, x in enumerate(xs) if x is not None]
        xs, ys, yerr, labels = (
            [xs[i] for i in keep],
            [ys[i] for i in keep],
            [yerr[i] for i in keep],
            [labels[i] for i in keep],
        )
        if not xs:
            continue

        order = sorted(range(len(xs)), key=lambda i: xs[i])
        xs, ys, yerr, labels = (
            [xs[i] for i in order],
            [ys[i] for i in order],
            [yerr[i] for i in order],
            [labels[i] for i in order],
        )

        ax.errorbar(xs, ys, yerr=yerr, fmt="o", capsize=4, ms=6, color="C0")
        for x, y, lab in zip(xs, ys, labels):
            ax.annotate(lab, (x, y), textcoords="offset points",
                        xytext=(0, 8), ha="center", fontsize=8, color="C0")

        ax.axhline(0.0, color="gray", ls="--", lw=1)
        ax.set_xlabel("truth function's pdfindex")
        ax.set_title(f"Test with Expected signal (r) = {r_truth:.0f}")
        ax.yaxis.set_major_locator(MultipleLocator(0.25))
        ax.yaxis.set_minor_locator(MultipleLocator(0.05))
        ax.grid(which="major", alpha=0.3, lw=0.2)
        ax.grid(which="minor", alpha=0.12, lw=0.1)
    axes[0].set_ylabel(r"Gaussian fit mean $\pm$ $\sigma$ (pull units)")

    axes[0].text(0.0, 1.02, "CMS", transform=axes[0].transAxes,
                 fontsize=15, fontweight="bold", ha="left", va="bottom")
    axes[0].text(0.13, 1.02, "Work in Progress", transform=axes[0].transAxes,
                 fontsize=13, fontstyle="italic", ha="left", va="bottom")
    axes[1].text(1.0, 1.02, LUMI_LABEL, transform=axes[1].transAxes,
                 fontsize=12, ha="right", va="bottom")

    fig.suptitle(
        "cat0 bias: Gaussian fit mean $\\pm$ $\\sigma$ vs truth-function pdfindex "
        "(other cats default idx=0)",
        fontsize=13, y=1.08,
    )
    fig.tight_layout()
    outname = "summary_mean_sigma_vs_pdfindex_cat0_default0.png"
    fig.savefig(outname, dpi=200, bbox_inches="tight")
    print(f"--> Saved {outname}")


if __name__ == "__main__":
    main()
