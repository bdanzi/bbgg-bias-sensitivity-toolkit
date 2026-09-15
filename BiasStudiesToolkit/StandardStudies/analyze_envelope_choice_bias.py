#!/usr/bin/env python3
import ROOT
import sys
import collections
import argparse

def main():
    parser = argparse.ArgumentParser(description='Filter out truth-matching envelope choices from FitDiagnostics.')
    parser.add_argument('-i', '--input', default='fitDiagnostics.fit_cat2_envelope_vs_truth_exp1_r1.root', help='Input FitDiagnostics root file')
    parser.add_argument('-v', '--variable', default='pdfindex_hgg_cat2_13TeV', help='Name of the pdfindex branch')
    parser.add_argument('-t', '--truth-idx', type=int, default=1, help='The discrete index corresponding to the truth function')
    parser.add_argument('-r', '--r-truth', type=float, default=1.0, help='Injected signal strength value')
    args = parser.parse_args()

    # Open the output fit diagnostics file
    f = ROOT.TFile.Open(args.input)
    if not f or f.IsZombie():
        print(f"[ERROR] Could not open file {args.input}", file=sys.stderr)
        sys.exit(1)

    tree = f.Get("tree_fit_sb")
    if not tree:
        print("[ERROR] TTree 'tree_fit_sb' not found in the ROOT file.", file=sys.stderr)
        sys.exit(1)

    print("\n" + "="*60)
    print("             ENVELOPE FILTERING & BIAS REPORT")
    print("="*60)

    choices = []
    clean_pulls = []
    tot_toys = 0
    failed_toys = 0

    for entry in tree:
        tot_toys += 1
        
        # Check fit convergence status
        if entry.fit_status != 0:
            failed_toys += 1
            continue
            
        # Extract the index that the envelope picked for this specific toy
        chosen_index = int(getattr(entry, args.variable))
        choices.append(chosen_index)
        
        # FILTER CONDITION: Only keep the toy if the fit chose an ALTERNATIVE function
        if chosen_index != args.truth_idx:
            pull = (entry.r - args.r_truth) / entry.rErr
            clean_pulls.append(pull)

    # Calculate selection frequencies
    counts = collections.Counter(choices)

    print(f"Total toys parsed: {tot_toys}")
    print(f"Failed toys (non-converged fits skipped): {failed_toys}\n")
    print("Envelope function selection breakdown:")
    
    for idx in sorted(counts.keys()):
        percentage = (counts[idx] / len(choices)) * 100
        flag = " (TRUTH FUNCTION -> SKIPPED/EXCLUDED)" if idx == args.truth_idx else ""
        print(f"  --> Index [{idx}]: Chosen {counts[idx]} times ({percentage:.1f}%){flag}")

    print("-"*60)
    print(f"Remaining toys used for actual Bias calculation: {len(clean_pulls)}")
    
    if len(clean_pulls) > 0:
        avg_pull = sum(clean_pulls) / len(clean_pulls)
        print(f"Calculated Average Pull on alternative models: {avg_pull:.4f}")
    else:
        print("[WARNING] Zero alternative toys available. The envelope always selected the truth function.")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
