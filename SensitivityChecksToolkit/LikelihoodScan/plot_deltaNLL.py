#!/usr/bin/env python3
"""Plot a 1D MultiDimFit likelihood scan (deltaNLL vs r).

Generalizes the original checkdeltaNLL.py (which had the input filename and
POI name hardcoded) into a small CLI tool.

Produce the scan first, e.g.:
    combine -M MultiDimFit ws.root -m 125 --algo grid --points 50 \\
        --rMin -5 --rMax 5 -n .scan_r
"""
import argparse

import ROOT

ROOT.gROOT.SetBatch(True)


def find_best_and_interval(x, y, level=1.0):
    """Best-fit (min y) and the +-1sigma (2*deltaNLL=level) crossing points,
    found by linear interpolation between adjacent scan points either side of
    the minimum. x must be sorted ascending. Returns (xbest, lo, hi); lo/hi
    fall back to the scan edge if the curve never crosses `level` there."""
    imin = min(range(len(y)), key=lambda i: y[i])
    xbest = x[imin]

    def interp(i0, i1):
        x0, y0, x1, y1 = x[i0], y[i0], x[i1], y[i1]
        if y1 == y0:
            return x1
        t = (level - y0) / (y1 - y0)
        return x0 + t * (x1 - x0)

    lo = x[0]
    for i in range(imin, 0, -1):
        if y[i - 1] >= level:
            lo = interp(i - 1, i)
            break

    hi = x[-1]
    for i in range(imin, len(y) - 1):
        if y[i + 1] >= level:
            hi = interp(i, i + 1)
            break

    return xbest, lo, hi


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-i", "--input", required=True, help="higgsCombine*.MultiDimFit.mH125.root file.")
    ap.add_argument("--poi", default="r", help="POI branch name in the 'limit' tree (default: r).")
    ap.add_argument("--ylim", type=float, default=100, help="Upper y-axis limit for deltaNLL (default: 100).")
    ap.add_argument("-o", "--outbase", default="scan_r_plot", help="Output file basename (writes .pdf and .png).")
    args = ap.parse_args()

    f = ROOT.TFile.Open(args.input)
    if not f or f.IsZombie():
        raise SystemExit(f"[ERROR] could not open {args.input}")
    tree = f.Get("limit")
    if not tree:
        raise SystemExit(f"[ERROR] no 'limit' tree in {args.input}")

    poi_vals, deltaNLL_vals = [], []
    n_failed = 0
    for event in tree:
        # combine writes deltaNLL=9990 as a sentinel for a scan point where the
        # fit failed to converge - drop those rather than plotting a spurious spike.
        if event.deltaNLL >= 9990:
            n_failed += 1
            continue
        poi_vals.append(getattr(event, args.poi))
        deltaNLL_vals.append(2 * event.deltaNLL)
    if n_failed:
        print(f"[WARNING] dropped {n_failed} non-converged scan point(s) (deltaNLL sentinel).")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    order = sorted(range(len(poi_vals)), key=lambda i: poi_vals[i])
    x = [poi_vals[i] for i in order]
    y = [deltaNLL_vals[i] for i in order]

    xbest, lo, hi = find_best_and_interval(x, y, level=1.0)
    poi_label = r"$\mu$" if args.poi == "r" else args.poi
    result_label = f"{poi_label} = {xbest:.2f} +{hi - xbest:.2f}/-{xbest - lo:.2f}"
    print(f"[INFO] {result_label}  (68% CL, from 2*deltaNLL=1 crossing)")

    plt.figure()
    plt.plot(x, y, marker=".")
    plt.axhline(1.0, color="gray", linestyle="--", linewidth=1, label=r"$1\sigma$")
    plt.axhline(4.0, color="gray", linestyle=":", linewidth=1, label=r"$2\sigma$")
    plt.axvline(xbest, color="red", linestyle="-", linewidth=1)
    plt.text(0.03, 0.95, result_label, transform=plt.gca().transAxes,
              ha="left", va="top", fontsize=12,
              bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))
    plt.xlabel(args.poi)
    plt.ylabel("2 x deltaNLL")
    plt.ylim(0, args.ylim)
    plt.legend()
    plt.title(f"Likelihood scan: {args.poi}")
    plt.tight_layout()
    plt.savefig(f"{args.outbase}.pdf")
    plt.savefig(f"{args.outbase}.png")
    print(f"[INFO] wrote {args.outbase}.pdf / .png")


if __name__ == "__main__":
    main()
