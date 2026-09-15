#!/usr/bin/env python3
"""Best-fit RooMultiPdf function per category, read from a postfit workspace
snapshot (e.g. the output of RunBiasInSignificance.py --mode setup, which
does a real-data MultiDimFit with --saveWorkspace --saveSpecifiedIndex).

Unlike just reading the pdfindex branch/category value directly, this
resolves the index THROUGH the function name: for each RooMultiPdf, after
loading the fitted snapshot, calls multipdf.getCurrentPdf().GetName() and
matches it (same tag substrings as resolve_pdfindex_legs.py) against every
getPdf(i).GetName() to recover the index -- i.e. the index used downstream
is re-derived from the function name actually selected by the fit, not
merely trusted from the category's stored integer.

Usage: get_bestfit_pdfindices.py <fitted_workspace.root> [snapshot_name]

Prints bash-sourceable BESTIDX_<pdfindexvar>='<pdfindexvar>=<idx>' lines
(same VAR=value convention as resolve_pdfindex_legs.py's IDX_* lines) plus
ALL_BESTIDX_VARS listing every pdfindex variable found.
"""

import sys

import ROOT


def tag_for(pdf_name):
    name = pdf_name.lower()
    if "exp1" in name:
        return "exp1"
    if "bern1" in name or "flat0" in name:
        return "bern1"
    if "bern2" in name:
        return "bern2"
    if "bern3" in name:
        return "bern3"
    if "pow1" in name:
        return "pow1"
    if "lau1" in name:
        return "lau1"
    if "lau2" in name:
        return "lau2"
    return "unknown"


def main():
    if len(sys.argv) not in (2, 3):
        print("[ERROR] Usage: get_bestfit_pdfindices.py <fitted_workspace.root> [snapshot_name]", file=sys.stderr)
        sys.exit(1)

    ws_file = sys.argv[1]
    f = ROOT.TFile.Open(ws_file)
    if not f or f.IsZombie():
        print(f"[ERROR] Could not open {ws_file}", file=sys.stderr)
        sys.exit(1)
    w = f.Get("w")
    if not w:
        print(f"[ERROR] No RooWorkspace 'w' in {ws_file}", file=sys.stderr)
        sys.exit(1)

    snap_names = [s.GetName() for s in w.getSnapshots()]
    if len(sys.argv) == 3:
        snapshot = sys.argv[2]
        if snapshot not in snap_names:
            print(f"[ERROR] Snapshot '{snapshot}' not found in {ws_file}. Available: {snap_names}", file=sys.stderr)
            sys.exit(1)
    else:
        # Prefer the MultiDimFit best-fit snapshot (RunBiasInSignificance.py
        # convention) over the pre-fit 'clean' one, if present.
        snapshot = "MultiDimFit" if "MultiDimFit" in snap_names else (snap_names[0] if snap_names else None)
        if snapshot is None:
            print(f"[ERROR] No snapshots found in {ws_file}", file=sys.stderr)
            sys.exit(1)
    w.loadSnapshot(snapshot)
    print(f"# Loaded snapshot '{snapshot}' from {ws_file} (available: {snap_names})", file=sys.stderr)

    # 1. Every pdfindex-like category in the workspace, with its current
    #    (postfit) index -- kept only as a sanity cross-check, not trusted
    #    on its own.
    all_pdfindex = {}
    cit = w.allCats().createIterator()
    cobj = cit.Next()
    while cobj:
        name = cobj.GetName()
        if "pdfindex" in name:
            all_pdfindex[name] = cobj.getIndex()
        cobj = cit.Next()

    # 2. Every RooMultiPdf, resolved to its associated pdfindex category by
    #    "catN" (+ "hgg"/"hbb" leg where relevant) token matching, same
    #    convention as resolve_pdfindex_legs.py.
    results = {}
    it = w.allPdfs().createIterator()
    obj = it.Next()
    while obj:
        if obj.ClassName() == "RooMultiPdf":
            mpdf_name_lower = obj.GetName().lower()
            cur_name = obj.getCurrentPdf().GetName()
            tag = tag_for(cur_name)

            # Re-derive the index from the function name actually selected,
            # rather than trusting the category's stored int directly.
            idx = None
            for i in range(obj.getNumPdfs()):
                if obj.getPdf(i).GetName() == cur_name:
                    idx = i
                    break

            # Associate to the matching pdfindex category: same category
            # number, and same hgg/hbb leg if the RooMultiPdf name says so.
            is_hbb = "hbb" in mpdf_name_lower
            candidates = [p for p in all_pdfindex if p.lower().split("cat")[0] and "cat" in p.lower()]
            match = None
            for p in all_pdfindex:
                p_lower = p.lower()
                # category token: pull "catN" out of the pdfindex name and
                # require it to also appear in the RooMultiPdf name.
                import re
                m = re.search(r"cat\d+", p_lower)
                if not m:
                    continue
                cat_token = m.group(0)
                if cat_token not in mpdf_name_lower:
                    continue
                if ("hbb" in p_lower) != is_hbb:
                    continue
                match = p
                break

            if match is None or idx is None:
                print(f"[WARN] Could not resolve pdfindex var for RooMultiPdf '{obj.GetName()}' "
                      f"(current pdf '{cur_name}', tag '{tag}')", file=sys.stderr)
            else:
                stored_idx = all_pdfindex[match]
                if stored_idx != idx:
                    print(f"[WARN] {match}: stored index {stored_idx} != index derived from "
                          f"getCurrentPdf() name ({idx}, '{cur_name}') -- using the derived one", file=sys.stderr)
                results[match] = (idx, cur_name, tag)
        obj = it.Next()

    for var, (idx, cur_name, tag) in results.items():
        print(f"BESTIDX_{var}='{var}={idx}'  # {cur_name} (tag={tag})")
    print(f"ALL_BESTIDX_VARS='{' '.join(results.keys())}'")


if __name__ == "__main__":
    main()
