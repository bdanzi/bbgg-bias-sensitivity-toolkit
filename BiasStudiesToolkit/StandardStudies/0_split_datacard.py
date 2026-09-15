#!/usr/bin/env python3

import re
import sys

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 split_datacard.py datacard.txt")
        sys.exit(1)

    datacard = sys.argv[1]

    with open(datacard, "r") as f:
        raw_lines = [x.rstrip("\n") for x in f]

    lines = []
    current_line = ""
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        if stripped.endswith("\\"):
            current_line += line.rstrip("\\") + " "
        else:
            tokens = stripped.split()
            if (
                current_line 
                and not tokens[0].startswith("bin") 
                and not tokens[0].startswith("process") 
                and not tokens[0].startswith("rate") 
                and not tokens[0].startswith("observation")
                and not tokens[0].startswith("shapes")
                and not tokens[0].startswith("imax")
                and not tokens[0].startswith("jmax")
                and not tokens[0].startswith("kmax")
                and not "_" in tokens[0]
            ):
                current_line += " " + line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = line

    if current_line:
        lines.append(current_line)

    text = "\n".join(lines)

    categories = sorted(
        set(re.findall(r"cat\d+", text)),
        key=lambda x: int(x.replace("cat", ""))
    )

    print("Found categories:", categories)

    block_start = None

    for i in range(len(lines)):
        if not lines[i].startswith("bin"):
            continue

        if i + 3 >= len(lines):
            continue

        if (
            lines[i + 1].startswith("process")
            and lines[i + 2].startswith("process")
            and lines[i + 3].startswith("rate")
        ):
            block_start = i
            break

    if block_start is None:
        raise RuntimeError("Could not find process block")

    bin_tokens = lines[block_start].split()[1:]
    proc_names = lines[block_start + 1].split()[1:]
    proc_ids = lines[block_start + 2].split()[1:]
    rates = lines[block_start + 3].split()[1:]

    cat_columns = {}
    for cat in categories:
        idx = []
        for i, b in enumerate(bin_tokens):
            if b == cat:
                idx.append(i)
        cat_columns[cat] = idx
        print(cat, "->", len(idx), "columns")

    nuisance_start = block_start + 4

    for cat in categories:
        keep = cat_columns[cat]
        outfile = f"datacard_{cat}.txt"

        with open(outfile, "w") as out:
            for line in lines[:block_start]:
                if line.startswith("shapes"):
                    tokens = line.split()
                    if len(tokens) > 2 and tokens[2] == cat:
                        out.write(line + "\n")
                elif (
                    line.startswith("imax") 
                    or line.startswith("jmax") 
                    or line.startswith("kmax")
                ):
                    out.write(line + "\n")

            out.write("\n-----------------------------------------------------------------\n")
            out.write(f"bin          {cat}\n")
            out.write("observation  -1\n")
            out.write("-----------------------------------------------------------------\n")

            out.write("bin      " + " ".join(bin_tokens[i] for i in keep) + "\n")
            out.write("process  " + " ".join(proc_names[i] for i in keep) + "\n")
            out.write("process  " + " ".join(proc_ids[i] for i in keep) + "\n")
            out.write("rate     " + " ".join(rates[i] for i in keep) + "\n")
            out.write("-----------------------------------------------------------------\n")

            for line in lines[nuisance_start:]:
                if not line.strip():
                    continue

                if line.startswith("pdfindex_"):
                    if cat in line:
                        out.write(line + "\n")
                    continue

                tokens = line.split()
                if len(tokens) < 3:
                    continue

                name = tokens[0]
                ntype = tokens[1]

                if ntype == "lnN":
                    # Se il nome della sistematica contiene un'altra categoria (es. MCStat_cat1 dentro la card di cat2), saltala
                    if "cat" in name and cat not in name:
                        continue

                    values = tokens[2:]
                    if len(values) != len(bin_tokens):
                        continue
                    
                    selected = [values[i] for i in keep]
                    out.write(f"{name:<35} lnN " + " ".join(selected) + "\n")
                else:
                    if cat in line:
                        out.write(line + "\n")

        print("Written", outfile)

if __name__ == "__main__":
    main()
