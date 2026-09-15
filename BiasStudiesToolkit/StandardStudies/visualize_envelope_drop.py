#!/usr/bin/env python3
"""Visualize what build_dropfunc_workspace.py actually does to a category's
RooMultiPdf envelope: fit every candidate function to that category's data
and plot them together (left), then plot only the functions that survive
after dropping one (right) -- the same tag-matching logic and the same
drop as build_dropfunc_workspace.py, just for inspection, not a real
workspace edit.

Usage:
  visualize_envelope_drop.py <in_ws.root> <cat_number> <drop_tag> <out_png> [--leg hgg|hbb]
"""
import argparse
import sys

import ROOT

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from build_dropfunc_workspace import filter_by_leg, find_multipdf_names, tag_of

ROOT.gErrorIgnoreLevel = ROOT.kError
ROOT.gROOT.SetBatch(True)

COLORS = [ROOT.kBlue, ROOT.kGreen + 2, ROOT.kOrange + 7, ROOT.kMagenta, ROOT.kCyan + 2, ROOT.kViolet]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("in_ws")
    p.add_argument("cat_number")
    p.add_argument("drop_tag")
    p.add_argument("out_png")
    p.add_argument("--leg", choices=["hgg", "hbb"], default=None)
    args = p.parse_args()

    cat_token = f"cat{args.cat_number}"
    f = ROOT.TFile.Open(args.in_ws)
    w = f.Get("multipdf")
    if not w:
        sys.exit(f"[ERROR] No RooWorkspace 'multipdf' in {args.in_ws}")

    candidates = filter_by_leg(find_multipdf_names(w, cat_token), args.leg)
    if len(candidates) != 1:
        sys.exit(f"[ERROR] Expected exactly 1 RooMultiPdf for '{cat_token}', found {candidates}. Use --leg to disambiguate.")
    mpdf_name = candidates[0]
    mpdf = w.pdf(mpdf_name)
    n = mpdf.getNumPdfs()
    names = [mpdf.getPdf(i).GetName() for i in range(n)]
    tags = [tag_of(name) for name in names]
    if args.drop_tag not in tags:
        sys.exit(f"[ERROR] Tag '{args.drop_tag}' not among {mpdf_name}'s functions: {list(zip(names, tags))}")

    mass = w.var("mass")
    data_name = f"roohist_data_mass_{cat_token}"
    data = w.data(data_name)
    if data is None:
        sys.exit(f"[ERROR] No data object '{data_name}' in {args.in_ws}")

    print(f"Envelope for {mpdf_name}:", list(zip(names, tags)))

    fitted = []
    for i in range(n):
        pdf = mpdf.getPdf(i)
        pdf.fitTo(data, ROOT.RooFit.Strategy(0), ROOT.RooFit.PrintLevel(-1), ROOT.RooFit.Save())
        fitted.append(pdf)

    canvas = ROOT.TCanvas("c", "c", 1600, 700)
    canvas.Divide(2, 1)
    NBINS = 40

    canvas.cd(1).SetLogy()
    frame1 = mass.frame(ROOT.RooFit.Title(f"{cat_token}: FULL envelope (what GEN toys are thrown from)"))
    data.plotOn(frame1, ROOT.RooFit.Binning(NBINS), ROOT.RooFit.Name("data"))
    legend1 = ROOT.TLegend(0.55, 0.55, 0.89, 0.89)
    legend1.AddEntry(frame1.findObject("data"), "data (binned)", "pe")
    for i, pdf in enumerate(fitted):
        tag = tags[i]
        is_dropped = tag == args.drop_tag
        color = ROOT.kRed if is_dropped else COLORS[i % len(COLORS)]
        style = 2 if is_dropped else 1
        width = 3 if is_dropped else 2
        pdf.plotOn(frame1, ROOT.RooFit.LineColor(color), ROOT.RooFit.LineStyle(style),
                   ROOT.RooFit.LineWidth(width), ROOT.RooFit.Name(f"pdf{i}"))
        label = f"{tag}  <-- DROPPED for the fit" if is_dropped else tag
        legend1.AddEntry(frame1.findObject(f"pdf{i}"), label, "l")
    frame1.Draw()
    legend1.Draw()

    canvas.cd(2).SetLogy()
    frame2 = mass.frame(ROOT.RooFit.Title(f"{cat_token}: REDUCED envelope (what FitDiagnostics sees)"))
    data.plotOn(frame2, ROOT.RooFit.Binning(NBINS), ROOT.RooFit.Name("data"))
    legend2 = ROOT.TLegend(0.55, 0.55, 0.89, 0.89)
    legend2.AddEntry(frame2.findObject("data"), "data (binned)", "pe")
    kept_idx = 0
    for i, pdf in enumerate(fitted):
        if tags[i] == args.drop_tag:
            continue
        color = COLORS[kept_idx % len(COLORS)]
        kept_idx += 1
        pdf.plotOn(frame2, ROOT.RooFit.LineColor(color), ROOT.RooFit.LineWidth(2), ROOT.RooFit.Name(f"pdf2_{i}"))
        legend2.AddEntry(frame2.findObject(f"pdf2_{i}"), tags[i], "l")
    frame2.Draw()
    legend2.Draw()

    canvas.SaveAs(args.out_png)
    print("Wrote", args.out_png)


if __name__ == "__main__":
    main()
