#!/usr/bin/env python3
"""Read whatever higgsCombine*.root files a still-running run_uncertainty_scan.py
scan has already produced in --outdir, and render the same impact/heatmap/GLOBAL
plots _make_plots() would - without touching the live scan process or re-running
combine. Safe to run repeatedly against an in-progress --outdir.
"""
import argparse
import glob
import os
import re
import sys

import numpy as np
import ROOT

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_uncertainty_scan import (
    discover_categories_and_processes, group_processes, read_datacard, _make_plots,
)

ROOT.gROOT.SetBatch(True)


def read_value(fname, metric):
    f = ROOT.TFile.Open(fname)
    if not f or f.IsZombie():
        return None
    tree = f.Get("limit")
    if not tree:
        return None
    vals = [e.limit for e in tree]
    if metric == "limit":
        return vals[2] if len(vals) > 2 else None
    return vals[-1] if vals else None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datacard")
    ap.add_argument("--mode", choices=["lnN", "rate"], required=True)
    ap.add_argument("--metric", choices=["limit", "significance"], required=True)
    ap.add_argument("--merge-runs", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--plotdir", required=True)
    ap.add_argument("--scan-min", type=float, default=None)
    ap.add_argument("--scan-max", type=float, default=None)
    ap.add_argument("--scan-n", type=int, default=None)
    args = ap.parse_args()

    if args.mode == "lnN":
        scan_min, scan_max, scan_n = 1.00, 2.10, 11
    else:
        scan_min, scan_max, scan_n = 0.10, 2.10, 21
    if args.scan_min is not None:
        scan_min = args.scan_min
    if args.scan_max is not None:
        scan_max = args.scan_max
    if args.scan_n is not None:
        scan_n = args.scan_n
    scan_values = np.linspace(scan_min, scan_max, scan_n)

    lines = read_datacard(args.datacard)
    bins, procs, categories, auto_processes = discover_categories_and_processes(lines, drop_signal=True)
    processes = auto_processes
    if args.mode == "rate":
        processes = [p for p in processes if p != "bkg_mass"]
    process_groups = group_processes(processes, args.merge_runs)
    group_labels = [label for label, _ in process_groups]

    method = "AsymptoticLimits" if args.metric == "limit" else "Significance"
    scopes = list(categories) + [None]

    results = {}
    n_found = 0
    for cat in scopes:
        scope_label = "GLOBAL" if cat is None else cat
        results[scope_label] = {}
        for group_label, _ in process_groups:
            # Walk every scan index up to scan_n, NOT just a contiguous
            # prefix - a still-running scan simply hasn't produced the
            # later files yet (trailing NaNs, fine to harvest as partial),
            # but a completed run with one FAILED point in the middle used
            # to have every later (perfectly good) point silently dropped
            # by stopping at the first gap, instead of being kept aligned
            # with scan_values via a NaN placeholder like main() now does.
            vals = []
            for i in range(len(scan_values)):
                tag = f"{args.mode}_{scope_label}_{group_label}_{i}"
                fname = os.path.join(args.outdir, f"higgsCombine_{tag}.{method}.mH125.root")
                v = read_value(fname, args.metric) if os.path.exists(fname) else None
                vals.append(v if v is not None else float("nan"))
                if v is not None:
                    n_found += 1
            results[scope_label][group_label] = vals

    os.makedirs(args.plotdir, exist_ok=True)

    class _Args:
        pass
    plot_args = _Args()
    plot_args.mode = args.mode
    plot_args.metric = args.metric
    plot_args.plotdir = args.plotdir

    _make_plots(results, categories, group_labels, list(scan_values), plot_args)
    print(f"[INFO] harvested {n_found} existing combine results, wrote plots to {args.plotdir}")


if __name__ == "__main__":
    main()
