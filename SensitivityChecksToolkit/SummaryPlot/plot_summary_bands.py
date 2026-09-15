#!/usr/bin/env python3
"""Plot a Brazil-band-style summary of per-channel expected upper limits.

Generalizes the original make_ULResult.py / make_againn.py (two near-identical
hardcoded scripts, one per input JSON) into one CLI tool: --input picks the
JSON, --output picks the destination file.

This script does NOT compute the numbers itself - it only plots a
hand-curated JSON of already-computed results, one entry per channel:

{
  "channels": [
    {"name": "<channel label>",
     "mu0": {"minus2sigma": ..., "minus1sigma": ..., "median": ...,
             "plus1sigma": ..., "plus2sigma": ...},
     "mu1": {"minus2sigma": ..., "minus1sigma": ..., "median": ...,
             "plus1sigma": ..., "plus2sigma": ...}}
  ]
}

Producing that JSON is a physics/bookkeeping decision (which combine runs map
to which "channel" - e.g. per-category vs a combined subset) specific to each
analysis; it is not automated by this toolkit.
"""
import argparse
import json

import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-i", "--input", required=True, help="Input JSON (see module docstring for format).")
    ap.add_argument("-o", "--output", default="summary_bands.pdf", help="Output plot file.")
    ap.add_argument("--title", default=r"HH $\rightarrow$ bb$\gamma\gamma$",
                     help="Analysis label shown on the plot.")
    ap.add_argument("--lumi", default="", help="Luminosity string for the CMS label (e.g. '138/283').")
    ap.add_argument("--com", default="13/13.6", help="Center-of-mass energy string for the CMS label.")
    args = ap.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    try:
        import mplhep as hep
        hep.style.use("CMS")
        has_hep = True
    except ImportError:
        has_hep = False

    with open(args.input) as f:
        data = json.load(f)

    channels = data["channels"]
    names = [c["name"] for c in channels]
    n_channels = len(names)
    y = np.arange(n_channels)

    fig, ax = plt.subplots(figsize=(11, 6))
    height = 1.0
    color_2sigma = "#85D1FBff"
    color_1sigma = "#FFDF7Fff"
    color_mu1 = "#1f77b4"
    xmax = max(max(c["mu0"]["plus2sigma"], c["mu1"]["median"]) for c in channels) * 1.15

    for i, c in enumerate(channels):
        mu0, mu1 = c["mu0"], c["mu1"]
        ax.barh(y[i], mu0["plus2sigma"] - mu0["minus2sigma"], left=mu0["minus2sigma"],
                height=height, color=color_2sigma, edgecolor="none", zorder=1)
        ax.barh(y[i], mu0["plus1sigma"] - mu0["minus1sigma"], left=mu0["minus1sigma"],
                height=height, color=color_1sigma, edgecolor="none", zorder=2)
        ax.plot([mu0["median"], mu0["median"]], [y[i] - height / 2, y[i] + height / 2],
                linestyle="--", color="black", linewidth=1.5, zorder=3)
        ax.plot([mu1["median"], mu1["median"]], [y[i] - height / 2, y[i] + height / 2],
                linestyle="--", color=color_mu1, linewidth=1.5, zorder=4)
        ax.text(-0.3, y[i], c["name"], va="bottom", ha="right", fontsize=12, weight="bold")
        ax.text(-0.3, y[i] + 0.3, f"Exp: {mu0['median']:.2f} (mu=0) / {mu1['median']:.2f} (mu=1)",
                va="bottom", ha="right", fontsize=10)

    ax.set_yticks([])
    ax.set_yticklabels([])
    ax.invert_yaxis()
    ax.set_xlim(0, xmax * 1.2)
    ax.set_xlabel(r"95% CL upper limit on $\mathit{\mu}$", fontsize=16)
    ax.grid(axis="x", linestyle="", alpha=0.4)
    ax.axvline(1.0, color="red", linestyle="--", linewidth=1)

    if has_hep:
        hep.cms.label("Work in Progress", data=False, lumi=args.lumi, com=args.com, ax=ax, fontsize=12)
    ax.text(0.45, 1.05, args.title, ha="left", va="top", fontsize=12, transform=ax.transAxes)

    legend_elements = [
        Line2D([0], [0], color="black", linestyle="--", lw=1.5, label=r"Expected Median ($\mu=0$)"),
        Line2D([0], [0], color=color_mu1, linestyle="--", lw=1.5, label=r"Expected Median ($\mu=1$)"),
        Patch(facecolor=color_1sigma, label=r"Expected $\pm1\sigma$ ($\mu=0$)"),
        Patch(facecolor=color_2sigma, label=r"Expected $\pm2\sigma$ ($\mu=0$)"),
        Line2D([0], [0], color="red", linestyle="--", lw=1, label=r"SM ($\mu=1$)"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=12, frameon=False, framealpha=0.9)
    plt.tight_layout()
    plt.savefig(args.output)
    print(f"[INFO] wrote {args.output}")


if __name__ == "__main__":
    main()
