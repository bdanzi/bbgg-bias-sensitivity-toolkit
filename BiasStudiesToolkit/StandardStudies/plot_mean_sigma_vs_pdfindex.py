#!/usr/bin/env python3
"""Summary plot: envelope fit_mean/fit_sigma (from FitDiagnostics pull toys)
vs the truth function's own discrete pdfindex value, per category.

Reads bias_plots_masked_cat<N>_envelope/pull_summary.json (fit_func=='envelope'
entries only -> the "truth fixed, envelope left floating" check, which is the
one that matches how combine fits real data) and the function<->pdfindex
mapping resolved by resolve_pdfindex_legs.py against Datacard_masked.root.
"""
import glob
import json
import re
import subprocess

import matplotlib.pyplot as plt

WS = "Datacard_masked.root"

CAT_RE = re.compile(r"bias_plots_masked_cat(\d+)_envelope")


def resolve_pdfindex_map(cat_number):
    out = subprocess.run(
        ["python3", "resolve_pdfindex_legs.py", WS, str(cat_number)],
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
        for d in glob.glob("bias_plots_masked_cat*_envelope")
        if (m := CAT_RE.match(d))
    )

    fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=True)
    r_values = [0.0, 2.0]
    colors = plt.cm.tab10.colors

    for cat in cats:
        idx_map = resolve_pdfindex_map(cat)
        with open(f"bias_plots_masked_cat{cat}_envelope/pull_summary.json") as f:
            entries = json.load(f)
        entries = [e for e in entries if e["fit_func"] == "envelope"]

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

            ax.errorbar(
                xs, ys, yerr=yerr, fmt="o", capsize=4, ms=6,
                color=colors[(cat - 1) % len(colors)],
                label=f"cat{cat}",
            )
            for x, y, lab in zip(xs, ys, labels):
                ax.annotate(lab, (x, y), textcoords="offset points",
                            xytext=(0, 8), ha="center", fontsize=7)

    for ax, r_truth in zip(axes, r_values):
        ax.axhline(0.0, color="gray", ls="--", lw=1)
        ax.set_xlabel("truth function's pdfindex (within its own category envelope)")
        ax.set_title(f"r_truth = {r_truth:.0f}")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel(r"fit mean $\pm$ fit $\sigma$ (pull units)")
    axes[0].legend(title="category", fontsize=8)

    fig.suptitle("Envelope bias: fit mean $\\pm$ $\\sigma$ of pull vs truth-function pdfindex, per category")
    fig.tight_layout()
    outname = "summary_mean_sigma_vs_pdfindex.png"
    fig.savefig(outname, dpi=200)
    print(f"--> Saved {outname}")


if __name__ == "__main__":
    main()
