#!/usr/bin/env python3
"""Summary plot: dropfunc fit_mean/fit_sigma (from FitDiagnostics pull toys)
vs the dropped truth function's own pdfindex value, per category.

Reads bias_plots_dropfunc_cat<N>/pull_summary.json (fit_func always
'envelope_minus_<truth_func>' -- the truth function is genuinely absent
from the fit's RooMultiPdf) and the function<->pdfindex mapping resolved
by resolve_pdfindex_legs.py against the ORIGINAL, unmasked Datacard.root
(dropfunc never uses --channel-masks).
"""
import glob
import json
import os
import re
import subprocess

import matplotlib.pyplot as plt
import mplhep as hep
from matplotlib.ticker import MultipleLocator

hep.style.use("CMS")
# hep.style.use("CMS") sets font sizes tuned for a single full-width plot;
# this figure has two narrow side-by-side panels, so scale everything down
# to keep the CMS/ROOT look (serif-ish font, ticks in on all sides) without
# every label colliding.
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

WS = "Datacard.root"
CAT0_WS = "Datacard_cat0truthstandard.root"
CAT0_JSON = "bias_plots_cat0_fixedmodel_default0/pull_summary.json"

CAT_RE = re.compile(r"bias_plots_dropfunc_cat(\d+)$")


def resolve_pdfindex_map(cat_number, ws=WS):
    out = subprocess.run(
        ["python3", "resolve_pdfindex_legs.py", ws, str(cat_number)],
        capture_output=True, text=True, check=True,
    ).stdout
    mapping = {}
    for line in out.splitlines():
        m = re.match(r"IDX_\S+_(\w+)='[^=]+=(\d+)'", line)
        if m:
            mapping[m.group(1)] = int(m.group(2))
    return mapping


def main():
    cats = sorted(
        int(m.group(1))
        for d in glob.glob("bias_plots_dropfunc_cat*")
        if (m := CAT_RE.match(d))
    )

    entries_map = {}
    for cat in cats:
        idx_map = resolve_pdfindex_map(cat)
        with open(f"bias_plots_dropfunc_cat{cat}/pull_summary.json") as f:
            entries_map[cat] = (idx_map, json.load(f))

    if os.path.exists(CAT0_JSON):
        with open(CAT0_JSON) as f:
            cat0_entries = json.load(f)
        if cat0_entries:
            entries_map[0] = (resolve_pdfindex_map(0, ws=CAT0_WS), cat0_entries)

    ordered_cats = ([0] if 0 in entries_map else []) + cats

    fig, axes = plt.subplots(1, 2, figsize=(16, 7), sharey=True)
    r_values = [0.0, 2.0]
    colors = plt.cm.tab10.colors
    n_cats = len(ordered_cats)
    jitter_width = 0.5

    for cat_i, cat in enumerate(ordered_cats):
        jitter = (cat_i - (n_cats - 1) / 2) * (jitter_width / max(n_cats - 1, 1))
        idx_map, entries = entries_map[cat]

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

            xs_jit = [x + jitter for x in xs]
            ax.errorbar(
                xs_jit, ys, yerr=yerr, fmt="o", capsize=4, ms=6,
                color=colors[cat_i % len(colors)],
                label=f"cat{cat}",
            )
            for x, y, lab in zip(xs_jit, ys, labels):
                ax.annotate(lab, (x, y), textcoords="offset points",
                            xytext=(0, 8 + 10 * cat_i), ha="center", fontsize=6.5,
                            color=colors[cat_i % len(colors)])

    for ax, r_truth in zip(axes, r_values):
        ax.axhline(0.0, color="gray", ls="--", lw=1)
        ax.set_xlabel("truth function's pdfindex (within its own category envelope)")
        ax.set_title(f"Test with Expected signal (r) = {r_truth:.0f}")
        ax.yaxis.set_major_locator(MultipleLocator(0.25))
        ax.yaxis.set_minor_locator(MultipleLocator(0.05))
        ax.grid(which="major", alpha=0.3, lw=0.2)
        ax.grid(which="minor", alpha=0.12, lw=0.1)
    axes[0].set_ylabel(r"Gaussian fit mean $\pm$ $\sigma$ (pull units)")
    axes[0].legend(title="category", fontsize=9)

    # Manual CMS-style tags instead of hep.cms.text/lumitext: those helpers
    # assume a single full-width panel and use absolute font sizes that
    # collide with everything else on a narrow 2-panel figure like this one.
    axes[0].text(0.0, 1.02, "CMS", transform=axes[0].transAxes,
                 fontsize=15, fontweight="bold", ha="left", va="bottom")
    axes[0].text(0.13, 1.02, "Work in Progress", transform=axes[0].transAxes,
                 fontsize=13, fontstyle="italic", ha="left", va="bottom")
    axes[1].text(1.0, 1.02, LUMI_LABEL, transform=axes[1].transAxes,
                 fontsize=12, ha="right", va="bottom")

    fig.suptitle(
        "Dropfunc bias (truth function absent from envelope):\n"
        "Gaussian fit mean $\\pm$ $\\sigma$ vs truth-function pdfindex, per category (default idx=0 for other cats)",
        fontsize=13, y=1.08,
    )
    fig.tight_layout()
    outname = "summary_mean_sigma_vs_pdfindex_dropfunc_default0.png"
    fig.savefig(outname, dpi=200, bbox_inches="tight")
    print(f"--> Saved {outname}")


if __name__ == "__main__":
    main()
