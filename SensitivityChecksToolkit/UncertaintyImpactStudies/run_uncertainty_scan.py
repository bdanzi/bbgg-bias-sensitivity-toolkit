#!/usr/bin/env python3
"""Scan a per-process acceptance uncertainty (lnN) or rate scale (rateParam)
and measure the impact on the expected upper limit or significance.

Generalizes the original UncertaintiesStudy.py / UncertaintiesStudySignificance.py /
UncertaintiesStudy_rate.py scripts (previously three near-duplicate files) into one
parameterized tool: --mode selects lnN-nuisance-scan vs rateParam-scan,
--metric selects AsymptoticLimits vs Significance.

Unlike a split-per-category datacard, this works directly on the *full* combined
datacard: each scan point adds one nuisance/rateParam line that only touches a
single (category, process) column (or, in --global mode, one process across all
categories), so every other category and every correlated systematic stays exactly
as in the real fit.
"""
import argparse
import os
import re
import subprocess
import sys

import numpy as np
import ROOT

ROOT.gROOT.SetBatch(True)

# Matches a run-period tag like "_run2_13TeV" or "_run3_13p6TeV" so run2/run3
# variants of the same physics process (e.g. "ggH_run2_13TeV_hgg" and
# "ggH_run3_13p6TeV_hgg") can be recognized as one group. Generic pattern, not
# hardcoded to specific run-period labels.
RUN_PERIOD_RE = re.compile(r"_run\d+_\d+p?\d*TeV")


def canonical_group(proc_name):
    """Strip the run-period tag to get the group label a process belongs to."""
    return RUN_PERIOD_RE.sub("", proc_name)


def group_processes(processes, merge_runs):
    """Return an ordered list of (label, [member process names]).

    With merge_runs=False, every process is its own singleton group (the
    original per-process-name behavior). With merge_runs=True (default),
    processes that share a canonical (run-period-stripped) label are grouped
    together, so e.g. ggH_run2_13TeV_hgg and ggH_run3_13p6TeV_hgg are scanned
    as one correlated group instead of two independent ones.
    """
    if not merge_runs:
        return [(p, [p]) for p in processes]
    groups = {}
    order = []
    for p in processes:
        label = canonical_group(p)
        if label not in groups:
            groups[label] = []
            order.append(label)
        groups[label].append(p)
    return [(label, groups[label]) for label in order]


def read_datacard(path):
    with open(path) as f:
        return f.readlines()


def find_bin_process_lines(lines):
    """Locate the per-(bin,process) 'bin' and 'process' (name) lines.

    Mirrors the heuristic from the original scripts: the last 'bin ' line
    before the first 'process ' line that names the ggHH/qqHH signal process
    (identified by the 'HH' substring) is the expanded per-column bin line.
    """
    bin_line = proc_line = None
    for i, line in enumerate(lines):
        if line.startswith("bin ") and "cat" in line:
            bin_line = i
        if line.startswith("process ") and "HH" in line:
            proc_line = i
            break
    if bin_line is None or proc_line is None:
        raise RuntimeError(
            "Could not locate the per-process 'bin'/'process' lines in the datacard "
            "(expected a 'bin <cat> <cat> ...' line followed by a 'process <name> ...' "
            "line naming an HH signal process)."
        )
    return bin_line, proc_line


def discover_categories_and_processes(lines, drop_signal=True):
    bin_line, proc_line = find_bin_process_lines(lines)
    bins = lines[bin_line].split()[1:]
    procs = lines[proc_line].split()[1:]
    if len(bins) != len(procs):
        raise RuntimeError("bin/process line column count mismatch in datacard.")

    categories = list(dict.fromkeys(bins))  # preserve first-seen order, dedup
    processes = []
    for p in procs:
        if p in processes:
            continue
        if drop_signal and "HH" in p:
            continue
        processes.append(p)
    return bins, procs, categories, processes


def find_existing_syst_line(lines, syst_name):
    """Find an existing lnN systematic row by exact name (first whitespace
    token), e.g. 'bbH_norm_ggH'. Returns the line index, or None if not found."""
    for i, line in enumerate(lines):
        toks = line.split()
        if toks and toks[0] == syst_name:
            return i
    return None


def scale_lnN_token(tok, factor):
    """Scale one lnN value token by `factor`, handling both a plain kappa
    ('2.0') and an asymmetric kappa ('0.936/1.067'). '-' (no effect on this
    column) is left untouched."""
    if tok == "-":
        return "-"
    if "/" in tok:
        lo, hi = tok.split("/")
        return f"{float(lo) * factor:.4f}/{float(hi) * factor:.4f}"
    return f"{float(tok) * factor:.4f}"


def discover_single_H_systematics(lines, procs):
    """Auto-discover existing *normalization* lnN systematic rows (name
    contains 'norm', e.g. bbH_norm_ggH) whose non-'-' entries touch ONLY
    single-Higgs background columns - never an HH-signal column, never
    bkg_mass (the data-driven RooMultiPdf envelope, not a modeled template).
    These are exactly the rows it's safe to rescale 'all together' as one
    combined single-H-background-normalization-assumption trial. Restricted
    to 'norm'-named rows on purpose - broader single-H-only systematics (QCD
    scale, pdf, MC stat, ...) are a different kind of assumption, not asked
    for here."""
    names = []
    for line in lines:
        toks = line.split()
        if len(toks) < 3 or toks[1] != "lnN" or len(toks[2:]) != len(procs):
            continue
        name, values = toks[0], toks[2:]
        if "norm" not in name.lower():
            continue
        touches_only_singleH, touches_anything = True, False
        for v, p in zip(values, procs):
            if v == "-":
                continue
            touches_anything = True
            if "HH" in p or p == "bkg_mass":
                touches_only_singleH = False
                break
        if touches_anything and touches_only_singleH:
            names.append(name)
    return names


def find_existing_syst_lines(lines, syst_names):
    """Map each requested exact systematic name to its line index."""
    idx_map = {}
    for i, line in enumerate(lines):
        toks = line.split()
        if toks and toks[0] in syst_names:
            idx_map[toks[0]] = i
    return idx_map


def make_card_existing_syst(lines, syst_line_indices, factor, idx, outdir, tag,
                             bins=None, category_filter=None):
    """Write a scan-point datacard where every one of the given EXISTING lnN
    systematic rows (by line index) has its already-present values scaled by
    `factor`, in place - everything else in the card (every other systematic,
    every process/category rate) is untouched. Pass one line index for a
    single-systematic trial, or several for a combined 'all together' trial.
    This changes the analysis's *assumption* about the size of systematic(s)
    already in the card (central rate stays exactly as it is), rather than
    bolting a new, independent nuisance on top of what's already there.

    category_filter=None (the default, 'merged') scales every existing column
    the systematic already touches, across every category at once - matching
    how the systematic is already correlated in the real card. Pass a single
    category name to scale ONLY that category's column(s) instead, leaving
    every other category's already-existing value completely unchanged (not
    blanked out to '-' - the systematic still fully applies there, just at
    its original assumed size) - for a 'separated per category' trial.
    Requires `bins` (the datacard's expanded per-column bin list) when used."""
    out_lines = list(lines)
    for li in syst_line_indices:
        toks = lines[li].split()
        name, kind, values = toks[0], toks[1], toks[2:]
        if category_filter is None:
            new_values = [scale_lnN_token(v, factor) for v in values]
        else:
            new_values = [
                scale_lnN_token(v, factor) if b == category_filter else v
                for b, v in zip(bins, values)
            ]
        out_lines[li] = f"{name}\t{kind}\t" + "\t".join(new_values) + "\n"

    out_card = os.path.join(outdir, f"card_lnNexisting_{tag}_{idx}.txt")
    with open(out_card, "w") as f:
        f.writelines(out_lines)
    return out_card


def make_card(lines, bins, procs, cat_target, members, label, value, idx, mode, outdir):
    """Write a scan-point datacard with one extra accUnc/rateParam line (or,
    for a merged run2/run3 group, one rateParam line per member process, all
    sharing the same name so they're tied to one correlated scale factor).

    cat_target=None means the "global" (all-categories) variant. `members` is
    the list of actual process names in this group (a singleton list unless
    run2/run3 merging is active); `label` is the group's display/tag name.
    """
    member_set = set(members)
    tag = "GLOBAL" if cat_target is None else cat_target
    new_lines = []

    if mode == "lnN":
        values = []
        for b, p in zip(bins, procs):
            match = (p in member_set) if cat_target is None else (b == cat_target and p in member_set)
            values.append(f"{value:.3f}" if match else "-")
        new_lines.append(f"accUnc_{tag}_{label} lnN " + " ".join(values) + "\n")
    else:
        scope = "*" if cat_target is None else cat_target
        for m in members:
            new_lines.append(f"rateScale_{tag}_{label} rateParam {scope} {m} 1 [0,5]\n")

    out_lines = list(lines)
    try:
        insert_idx = next(i for i, l in enumerate(out_lines) if l.startswith("pdfindex"))
    except StopIteration:
        insert_idx = len(out_lines)
    for j, nl in enumerate(new_lines):
        out_lines.insert(insert_idx + j, nl)

    out_card = os.path.join(outdir, f"card_{mode}_{tag}_{label}_{idx}.txt")
    with open(out_card, "w") as f:
        f.writelines(out_lines)
    return out_card


def run_combine(card, tag, metric, outdir):
    """Run combine for a plain lnN-scan card (no extra --setParameters needed:
    the scan value is already baked into the card's accUnc lnN line)."""
    method = "AsymptoticLimits" if metric == "limit" else "Significance"
    cmd = [
        "combine", "-M", method, os.path.basename(card),
        "--X-rtd", "TMCSO_AdaptivePseudoAsimov=10",
        "--cminDefaultMinimizerStrategy", "0",
        "--cminFallbackAlgo", "Minuit2,Migrad,0:0.1",
        "--X-rtd", "MINIMIZER_freezeDisassociatedParams",
        "--X-rtd", "MINIMIZER_multiMin_hideConstants",
        "--X-rtd", "MINIMIZER_multiMin_maskConstraints",
        "--X-rtd", "MINIMIZER_multiMin_maskChannels=2",
        "--verbose", "0",
        "-m", "125", "-t", "-1",
        "-n", f"_{tag}",
    ]
    if metric == "significance":
        cmd += ["--expectSignal=1"]
    try:
        subprocess.run(cmd, cwd=outdir, check=True,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print(f"[ERROR] combine failed for {tag}", file=sys.stderr)
        return None

    fname = os.path.join(outdir, f"higgsCombine_{tag}.{method}.mH125.root")
    try:
        f = ROOT.TFile.Open(fname)
        tree = f.Get("limit")
        vals = [e.limit for e in tree]
    except Exception:
        print(f"[ERROR] could not read {fname}", file=sys.stderr)
        return None

    if metric == "limit":
        # AsymptoticLimits writes [-2s,-1s,median,+1s,+2s(,obs)]; index 2 is the median expected.
        return vals[2] if len(vals) > 2 else None
    return vals[-1] if vals else None


def run_combine_rate(card, tag, metric, rate_param_name, value, outdir):
    method = "AsymptoticLimits" if metric == "limit" else "Significance"
    cmd = [
        "combine", "-M", method, os.path.basename(card),
        "--X-rtd", "TMCSO_AdaptivePseudoAsimov=10",
        "--cminDefaultMinimizerStrategy", "0",
        "--cminFallbackAlgo", "Minuit2,Migrad,0:0.1",
        "--X-rtd", "MINIMIZER_freezeDisassociatedParams",
        "--X-rtd", "MINIMIZER_multiMin_hideConstants",
        "--X-rtd", "MINIMIZER_multiMin_maskConstraints",
        "--X-rtd", "MINIMIZER_multiMin_maskChannels=2",
        "--verbose", "0",
        "-m", "125", "-t", "-1",
        "--setParameters", f"{rate_param_name}={value}",
        "--freezeParameters", rate_param_name,
        "-n", f"_{tag}",
    ]
    if metric == "significance":
        cmd += ["--expectSignal=1"]
    try:
        subprocess.run(cmd, cwd=outdir, check=True,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print(f"[ERROR] combine failed for {tag}", file=sys.stderr)
        return None

    fname = os.path.join(outdir, f"higgsCombine_{tag}.{method}.mH125.root")
    try:
        f = ROOT.TFile.Open(fname)
        tree = f.Get("limit")
        vals = [e.limit for e in tree]
    except Exception:
        print(f"[ERROR] could not read {fname}", file=sys.stderr)
        return None

    if metric == "limit":
        return vals[2] if len(vals) > 2 else None
    return vals[-1] if vals else None


def rate_param_name(tag, proc_target):
    return f"rateScale_{tag}_{proc_target}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("datacard", help="Full combined datacard (not split by category).")
    ap.add_argument("--mode", choices=["lnN", "rate"], default="lnN",
                     help="lnN: rescale an EXISTING lnN systematic's assumed value (found by exact "
                          "name via --systematics), in place, one systematic at a time - the process "
                          "central rate is untouched. rate: scan a frozen rateParam (process "
                          "normalization), existing systematics untouched. Default: lnN.")
    ap.add_argument("--systematics", nargs="*", default=["bbH_norm_ggH", "bbH_norm_qqH", "ALL_SINGLE_H"],
                     help="lnN mode only: existing systematic names (exact match on the datacard's "
                          "first column) to rescale, one at a time. The special name 'ALL_SINGLE_H' "
                          "expands to every auto-discovered existing lnN row that touches only "
                          "single-Higgs background columns (never HH-signal, never bkg_mass) and "
                          "rescales all of them together at once, as one combined trial. "
                          "Default: bbH_norm_ggH bbH_norm_qqH ALL_SINGLE_H.")
    ap.add_argument("--metric", choices=["limit", "significance"], default="limit",
                     help="limit: expected AsymptoticLimits median. "
                          "significance: expected Significance at --expectSignal=1. Default: limit.")
    ap.add_argument("--categories", nargs="*", default=None,
                     help="Categories to scan per-category (default: auto-discovered from the datacard).")
    ap.add_argument("--processes", nargs="*", default=None,
                     help="Processes to scan (default: auto-discovered background-like processes, "
                          "i.e. every process name not containing 'HH').")
    ap.add_argument("--scan-min", type=float, default=None, help="Override scan range minimum.")
    ap.add_argument("--scan-max", type=float, default=None, help="Override scan range maximum.")
    ap.add_argument("--scan-n", type=int, default=None, help="Override number of scan points.")
    ap.add_argument("--only-global", action="store_true",
                     help="Skip the per-category loop, only run the all-categories ('GLOBAL') scan.")
    ap.add_argument("--merge-runs", action=argparse.BooleanOptionalAction, default=True,
                     help="Group run2/run3 variants of the same process (e.g. ggH_run2_13TeV_hgg and "
                          "ggH_run3_13p6TeV_hgg) into one correlated scan instead of two independent "
                          "ones. Default: on. Use --no-merge-runs to scan every process name separately.")
    ap.add_argument("--outdir", default=".", help="Directory for generated cards/combine outputs.")
    ap.add_argument("--plotdir", default="./sensitivity_plots", help="Directory for output plots.")
    ap.add_argument("--run", action="store_true",
                     help="Actually execute combine. Without this flag, only prints the planned scan matrix.")
    args = ap.parse_args()

    lines = read_datacard(args.datacard)
    bins, procs, auto_categories, auto_processes = discover_categories_and_processes(
        lines, drop_signal=True
    )
    categories = args.categories if args.categories else auto_categories

    if args.mode == "lnN":
        run_lnN_existing_scan(args, lines, bins, procs, categories)
        return

    # --- rate mode: unchanged from before - scale a process's central rate via
    # a fresh rateParam, every existing systematic (including any lnN on that
    # same process) stays exactly as in the card. ---
    scan_min, scan_max, scan_n = 0.10, 2.10, 21
    if args.scan_min is not None:
        scan_min = args.scan_min
    if args.scan_max is not None:
        scan_max = args.scan_max
    if args.scan_n is not None:
        scan_n = args.scan_n
    scan_values = np.linspace(scan_min, scan_max, scan_n)

    processes = args.processes if args.processes else auto_processes
    # A rateParam scan on bkg_mass (the data-driven RooMultiPdf envelope, not a
    # normalized template) doesn't make physical sense - drop it like the
    # original UncertaintiesStudy_rate.py did.
    processes = [p for p in processes if p != "bkg_mass"]

    process_groups = group_processes(processes, args.merge_runs)
    group_labels = [label for label, _ in process_groups]

    print(f"Datacard: {args.datacard}")
    print(f"Mode: {args.mode}  Metric: {args.metric}")
    print(f"Categories ({len(categories)}): {categories}")
    if args.merge_runs:
        print(f"Process groups ({len(process_groups)}, run2/run3 merged):")
        for label, members in process_groups:
            print(f"  {label}: {members}")
    else:
        print(f"Processes ({len(process_groups)}): {group_labels}")
    print(f"Scan: {scan_n} points in [{scan_min}, {scan_max}]")
    n_percat = 0 if args.only_global else len(categories) * len(process_groups) * scan_n
    n_global = len(process_groups) * scan_n
    print(f"Planned combine calls: {n_percat} per-category + {n_global} global = {n_percat + n_global}")

    if not args.run:
        print("\nDRY-RUN MODE: pass --run to actually execute combine. "
              "(Each call is a single Asimov fit -t -1, not toy-based, but the total count above can still add up.)")
        return

    os.makedirs(args.outdir, exist_ok=True)
    os.makedirs(args.plotdir, exist_ok=True)

    results = {}  # results[cat_or_GLOBAL][proc] = [values...]
    scopes = [] if args.only_global else list(categories)
    scopes.append(None)  # None => GLOBAL

    for cat in scopes:
        scope_label = "GLOBAL" if cat is None else cat
        results[scope_label] = {}
        for group_label, members in process_groups:
            print(f"\n=== {scope_label} | {group_label} ===")
            results[scope_label][group_label] = []
            for i, val in enumerate(scan_values):
                tag = f"{args.mode}_{scope_label}_{group_label}_{i}"
                card = make_card(lines, bins, procs, cat, members, group_label, val, i, args.mode, args.outdir)
                r = run_combine_rate(card, tag, args.metric, rate_param_name(scope_label, group_label), val, args.outdir)
                if r is None:
                    print(f"[WARNING] scan point {i} failed for {scope_label} {group_label}; "
                          f"keeping its slot as NaN so later points stay aligned with scan_values")
                # Always append (NaN on failure) - never skip. Dropping a failed
                # point here used to shift every later point one slot left
                # relative to scan_values, silently mislabeling their x-axis
                # value in every downstream plot.
                results[scope_label][group_label].append(r if r is not None else float("nan"))

        # Refresh the plots after every scope (category, then finally GLOBAL)
        # instead of only once at the very end, so partial progress is visible
        # while a long scan is still running.
        _make_plots(results, categories, group_labels, scan_values, args)
        print(f"[INFO] refreshed plots in {args.plotdir} after finishing scope '{scope_label}'")


def run_lnN_existing_scan(args, lines, bins, procs, categories):
    """Corrected lnN mode: rescale an EXISTING lnN systematic's already-present
    value(s), one systematic (or the combined 'ALL_SINGLE_H' group) at a time,
    in place - no new nuisance is added on top of what's already in the card.
    Run both a 'merged' trial (every category the systematic already touches,
    scaled together at once - matching how it's already correlated in the
    real card) and a 'separated' trial per category (scaling only that one
    category's existing value, every other category left exactly as-is)."""
    scan_min, scan_max, scan_n = 0.5, 2.0, 11
    if args.scan_min is not None:
        scan_min = args.scan_min
    if args.scan_max is not None:
        scan_max = args.scan_max
    if args.scan_n is not None:
        scan_n = args.scan_n
    scan_factors = np.linspace(scan_min, scan_max, scan_n)

    requested = list(args.systematics)
    plain_names = [n for n in requested if n != "ALL_SINGLE_H"]
    idx_map = find_existing_syst_lines(lines, plain_names)
    missing = [n for n in plain_names if n not in idx_map]
    if missing:
        print(f"[WARNING] systematic name(s) not found in datacard, skipping: {missing}")

    def nominal_of(line_indices):
        """The systematic's existing (pre-scan) lnN value, if all its non-'-'
        entries share one common value - used to plot the actual scanned lnN
        value instead of an abstract factor. None if the group mixes several
        different nominal values (e.g. ALL_SINGLE_H), where 'the value' isn't
        a single number."""
        vals = set()
        for li in line_indices:
            for tok in lines[li].split()[2:]:
                if tok == "-":
                    continue
                v = tok.split("/")[0] if "/" in tok else tok
                vals.add(round(float(v), 6))
        return vals.pop() if len(vals) == 1 else None

    groups = []  # (tag, [line_indices], nominal_or_None)
    for n in plain_names:
        if n in idx_map:
            groups.append((n, [idx_map[n]], nominal_of([idx_map[n]])))
    if "ALL_SINGLE_H" in requested:
        single_h_names = discover_single_H_systematics(lines, procs)
        single_h_idx = find_existing_syst_lines(lines, single_h_names)
        line_indices = list(single_h_idx.values())
        groups.append(("ALL_SINGLE_H", line_indices, nominal_of(line_indices)))
        print(f"[INFO] ALL_SINGLE_H expands to {len(single_h_names)} existing systematics: {single_h_names}")

    scopes = list(categories) + [None]  # None => merged (all categories together)

    print(f"Datacard: {args.datacard}")
    print(f"Mode: lnN (rescale existing systematic assumption)  Metric: {args.metric}")
    print(f"Systematic trials ({len(groups)}): {[g[0] for g in groups]}")
    print(f"Scopes: merged + per-category ({len(categories)}): {categories}")
    print(f"Scan: {scan_n} factors in [{scan_min}, {scan_max}] (multiplying the existing value(s))")
    print(f"Planned combine calls: {len(groups) * len(scopes) * scan_n}")

    if not args.run:
        print("\nDRY-RUN MODE: pass --run to actually execute combine.")
        return

    os.makedirs(args.outdir, exist_ok=True)
    os.makedirs(args.plotdir, exist_ok=True)

    for cat in scopes:
        scope_label = "merged" if cat is None else cat
        scope_results = {}
        for tag, line_indices, nominal in groups:
            if not line_indices:
                print(f"[WARNING] '{tag}' matched no existing systematic rows, skipping.")
                continue
            nom_str = f"{nominal:.3f}" if nominal is not None else "mixed"
            print(f"\n=== [{scope_label}] {tag} (rows: {len(line_indices)}, existing value: {nom_str}) ===")
            scope_results[tag] = {"y": [], "nominal": nominal}
            for i, factor in enumerate(scan_factors):
                run_tag = f"lnNexisting_{scope_label}_{tag}_{i}"
                card = make_card_existing_syst(lines, line_indices, factor, i, args.outdir,
                                                f"{scope_label}_{tag}", bins=bins, category_filter=cat)
                r = run_combine(card, run_tag, args.metric, args.outdir)
                if r is None:
                    print(f"[WARNING] skipping [{scope_label}] {tag} scan point {i}")
                    continue
                scope_results[tag]["y"].append(r)
        _make_plots_lnN_existing(scope_results, scan_factors, args, scope_label)
        print(f"[INFO] refreshed plots in {args.plotdir} after finishing scope '{scope_label}'")


def _make_plots_lnN_existing(results, scan_factors, args, scope_label):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ylabel = ("Limit / nominal" if args.metric == "limit"
              else "Significance / nominal (expectSignal=1)")

    plt.figure()
    ranking = []
    has_mixed = False
    for tag, entry in results.items():
        y = np.array(entry["y"], dtype=float)
        nominal = entry["nominal"]
        if len(y) == 0 or y[0] == 0:
            continue
        # The ratio y/y[0] is normalized to the FIRST scan point, which is
        # always lnN=1.0 (factor=0.5 x the card's value) i.e. "no systematic
        # effect at all" - that's the true baseline for this plot. The
        # "card value=X" annotation below is just informational (what's
        # currently written in the real datacard), NOT the normalization
        # point - do not call it "nominal", that name belongs to the y=1.0
        # (no-uncertainty) baseline instead and was confusing here.
        if nominal is not None:
            x = scan_factors[: len(y)] * nominal
            label = f"{tag} (card value={nominal:.2f})"
        else:
            x = scan_factors[: len(y)]
            label = f"{tag} (mixed card values - shown as scale factor)"
            has_mixed = True
        plt.plot(x, y / y[0], marker=".", label=label, linewidth=2)
        ranking.append((tag, y[-1] / y[0] - 1.0))
    plt.title(f"Impact of rescaling existing single-H systematic assumption(s) [{scope_label}]")
    xlabel = "Assumed lnN value" if not has_mixed else "Assumed lnN value (or scale factor where nominals differ)"
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.legend(fontsize=8)
    plt.grid(True)
    # When the effect is tiny (e.g. significance barely moves), matplotlib
    # defaults to a confusing offset+scale axis label like "1e-5+9.999e-1".
    # Plain, un-offset tick labels are much clearer for this kind of ratio plot.
    plt.gca().ticklabel_format(axis="y", style="plain", useOffset=False)
    plt.tight_layout()
    plt.savefig(os.path.join(args.plotdir, f"impact_lnNexisting_{scope_label}_{args.metric}.png"))
    plt.close()

    if ranking:
        print(f"\n=== [{scope_label}] Ranking (fractional change, factor={scan_factors[0]:.2f} -> {scan_factors[-1]:.2f}) ===")
        for tag, val in sorted(ranking, key=lambda x: -abs(x[1])):
            print(f"{tag:25s} : {val:+.3f}")


def _make_plots(results, categories, processes, scan_values, args):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cmap = plt.get_cmap("tab10")
    colors = {p: cmap(i % 10) for i, p in enumerate(processes)}
    ylabel = ("Limit / nominal" if args.metric == "limit"
              else "Significance / nominal (expectSignal=1)")
    xlabel = "lnN value" if args.mode == "lnN" else "rate scale"

    # 'nominal' for a rate scan is the point where rate_scale=1.0 (the
    # process at its unperturbed, as-written-in-the-card rate) - NOT
    # scan_values[0], which is whatever --scan-min happens to be (e.g. 0.0,
    # meaning the process fully zeroed out). Normalizing by index 0 instead
    # of the actual scale=1 point silently forces that point's ratio to 1.0
    # by construction, which reads as "zeroing this process has no effect"
    # even when it does. nominal_idx picks the scan point closest to 1.0.
    nominal_idx = int(np.argmin(np.abs(scan_values - 1.0)))
    if abs(scan_values[nominal_idx] - 1.0) > 1e-6:
        print(f"[WARNING] no scan point lands exactly on rate_scale=1.0; using the nearest "
              f"one ({scan_values[nominal_idx]:.3f}) as the 'nominal' baseline for ratio plots.")

    def _baseline(y):
        """y[nominal_idx], the significance/limit at rate_scale=1.0 - or,
        if that particular scan point failed (NaN - see the main() loop,
        which now keeps a NaN placeholder for a failed combine call instead
        of dropping it and shifting every later point out of alignment with
        scan_values), the nearest surviving non-NaN point instead."""
        idx = nominal_idx if nominal_idx < len(y) else len(y) - 1
        if not np.isnan(y[idx]):
            return y[idx]
        finite = np.flatnonzero(~np.isnan(y))
        if finite.size == 0:
            return np.nan
        nearest = finite[np.argmin(np.abs(finite - idx))]
        return y[nearest]

    scopes = [c for c in results if c != "GLOBAL"]
    for cat in scopes:
        plt.figure()
        for proc in processes:
            y = np.array(results[cat].get(proc, []), dtype=float)
            base = _baseline(y) if len(y) else np.nan
            if len(y) == 0 or base == 0 or np.isnan(base):
                continue
            plt.plot(scan_values[: len(y)], y / base, label=proc, color=colors[proc], linewidth=2)
        # This is always the FULL combined-datacard metric (all categories),
        # with only this one (category, process) column's rate/systematic
        # scanned - "{cat}" names which column is varied, not what the
        # metric is computed on.
        plt.title(f"Full combined {args.metric} vs {cat}/process rate scan (all categories in the fit)")
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.legend(fontsize=6)
        plt.grid(True)
        plt.savefig(os.path.join(args.plotdir, f"impact_{cat}_{args.mode}_{args.metric}.png"))
        plt.close()

    if scopes:
        matrix = np.zeros((len(scopes), len(processes)))
        for i, cat in enumerate(scopes):
            for j, proc in enumerate(processes):
                y = np.array(results[cat].get(proc, []), dtype=float)
                base = _baseline(y) if len(y) else np.nan
                if len(y) == 0 or base == 0 or np.isnan(base) or np.isnan(y[-1]):
                    continue
                matrix[i, j] = y[-1] / base - 1.0
        plt.figure(figsize=(max(6, len(processes)), max(4, len(scopes))))
        im = plt.imshow(matrix, aspect="auto")
        plt.xticks(range(len(processes)), processes, rotation=45, ha="right", fontsize=7)
        plt.yticks(range(len(scopes)), scopes)
        plt.xlabel("Process")
        plt.ylabel("Category")
        plt.title(f"Impact matrix ({args.mode}, {args.metric})")
        for i in range(len(scopes)):
            for j in range(len(processes)):
                plt.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", color="white", fontsize=7)
        plt.colorbar(im)
        plt.tight_layout()
        plt.savefig(os.path.join(args.plotdir, f"heatmap_impact_{args.mode}_{args.metric}.png"))
        plt.close()

    if "GLOBAL" in results:
        plt.figure()
        ranking = []
        for proc in processes:
            y = np.array(results["GLOBAL"].get(proc, []), dtype=float)
            base = _baseline(y) if len(y) else np.nan
            if len(y) == 0 or base == 0 or np.isnan(base):
                continue
            plt.plot(scan_values[: len(y)], y / base, label=proc, color=colors[proc], linewidth=2)
            if not np.isnan(y[-1]):
                ranking.append((proc, y[-1] / base - 1.0))
        # GLOBAL scans that same process across every category's column at
        # once (still the same full combined-datacard metric as above).
        plt.title(f"Full combined {args.metric} vs process rate scan (GLOBAL: every category's column at once)")
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.legend(fontsize=6)
        plt.grid(True)
        plt.savefig(os.path.join(args.plotdir, f"impact_GLOBAL_{args.mode}_{args.metric}.png"))
        plt.close()

        print("\n=== GLOBAL ranking (fractional change nominal -> last scan point) ===")
        for proc, val in sorted(ranking, key=lambda x: -x[1]):
            print(f"{proc:45s} : {val:+.3f}")


if __name__ == "__main__":
    main()
