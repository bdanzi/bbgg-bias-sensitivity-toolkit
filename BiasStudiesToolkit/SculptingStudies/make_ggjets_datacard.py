#!/usr/bin/env python3
"""Build the hybrid *_GGJets.txt datacard used for Sculpting Bias Studies.

Starting from a per-category datacard produced by 0_split_datacard.py, this
replaces the `bkg_mass` and `data_obs` `shapes` lines for that category with
pointers into the RooHistPdf-based truth workspace built by GGJets_improved.py
(nominal_pdfs/GGjetsWS_<SR>_<dim>.root), instead of the analytic multipdf
background. Everything else in the datacard (signal shapes, rates, nuisances)
is left untouched.

Which category corresponds to which SR name is a physics choice (which
categories are GGJets/non-resonant-background dominated) and must be given
explicitly -- it is not inferred from the datacard.
"""

import argparse
import re
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datacard", help="Per-category datacard, e.g. datacard_cat2.txt")
    parser.add_argument("sr_name", help="SR label matching the GGjetsWS workspace, e.g. SR1")
    parser.add_argument("dim", choices=["1D", "2D"], help="Dimensionality of the fit")
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output path (default: <datacard>_GGJets.txt next to the input)",
    )
    parser.add_argument(
        "--workspace-dir", default="./nominal_pdfs",
        help="Directory containing GGjetsWS_<SR>_<dim>.root (default: ./nominal_pdfs)",
    )
    args = parser.parse_args()

    out_path = args.output
    if out_path is None:
        if args.datacard.endswith(".txt"):
            out_path = args.datacard[: -len(".txt")] + "_GGJets.txt"
        else:
            out_path = args.datacard + "_GGJets.txt"

    ws_file = f"{args.workspace_dir}/GGjetsWS_{args.sr_name}_{args.dim}.root"

    with open(args.datacard) as f:
        lines = f.readlines()

    out_lines = []
    replaced = {"bkg_mass": False, "data_obs": False}
    for line in lines:
        tokens = line.split()
        if len(tokens) >= 2 and tokens[0] == "shapes" and tokens[1] in replaced:
            proc = tokens[1]
            cat = tokens[2]
            obj = "roohistpdf_%s" % args.sr_name if proc == "bkg_mass" else "roodataset_nonrestoy_%s" % args.sr_name
            out_lines.append(f"shapes       {proc:<50} {cat:<40} {ws_file} w:{obj}\n")
            replaced[proc] = True
        else:
            out_lines.append(line)

    missing = [proc for proc, done in replaced.items() if not done]
    if missing:
        print(f"[ERROR] Could not find 'shapes' line(s) for: {', '.join(missing)} in {args.datacard}", file=sys.stderr)
        sys.exit(1)

    with open(out_path, "w") as f:
        f.writelines(out_lines)

    print(f"Written {out_path} (bkg_mass, data_obs -> {ws_file})")


if __name__ == "__main__":
    main()
