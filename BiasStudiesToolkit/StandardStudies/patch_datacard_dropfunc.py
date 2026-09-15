#!/usr/bin/env python3
"""Copy a datacard, redirecting ONLY the `bkg_mass` shapes line for one bin
to a new file (the drop-function workspace built by
build_dropfunc_workspace.py). The RooMultiPdf/pdfindex/_norm object names
are unchanged by that script, so the `multipdf:<name>` token on the shapes
line does not need to change -- only the file path does. Every other line
(including this bin's own `data_obs` shapes line, which still points at the
original file) is left untouched.

Usage:
  patch_datacard_dropfunc.py <in_datacard.txt> <bin> <new_ws_relpath> <out_datacard.txt>

<bin>             e.g. cat2 -- must match the bin column of the shapes line
<new_ws_relpath>  path to the new workspace file, written verbatim into the
                  patched line (so it must be correct relative to
                  <out_datacard.txt>'s own directory, exactly like every
                  other shapes line's path is relative to the datacard).
"""
import sys


def main():
    if len(sys.argv) != 5:
        sys.stderr.write(
            "Usage: patch_datacard_dropfunc.py <in_datacard.txt> <bin> <new_ws_relpath> <out_datacard.txt>\n"
        )
        sys.exit(1)

    in_path, bin_name, new_ws_relpath, out_path = sys.argv[1:5]

    with open(in_path) as fh:
        lines = fh.readlines()

    patched = 0
    out_lines = []
    for line in lines:
        fields = line.split()
        if len(fields) >= 5 and fields[0] == "shapes" and fields[1] == "bkg_mass" and fields[2] == bin_name:
            fields[3] = new_ws_relpath
            out_lines.append("shapes      " + "  ".join(fields[1:]) + "\n")
            patched += 1
        else:
            out_lines.append(line)

    if patched == 0:
        sys.exit(f"[ERROR] No 'shapes bkg_mass {bin_name} ...' line found in {in_path}")
    if patched > 1:
        sys.exit(f"[ERROR] Found {patched} 'shapes bkg_mass {bin_name} ...' lines in {in_path} -- expected exactly 1")

    with open(out_path, "w") as fh:
        fh.writelines(out_lines)

    print(f"[OK] Wrote {out_path} (bkg_mass/{bin_name} -> {new_ws_relpath})")


if __name__ == "__main__":
    main()
