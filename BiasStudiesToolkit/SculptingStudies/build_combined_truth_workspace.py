#!/usr/bin/env python3
"""Build ONE combined multi-category GGJets/DDQCDGJets/TTGG truth workspace
and the corresponding combined hybrid ("truth") datacard, for the sculpting
bias check on ALL categories together (cat0-cat4), instead of the per-category
hand-split workflow in GGJets_improved.py/MCALLWS_revisited.py/make_ggjets_datacard.py.

For each category, every bkg_mass/data_obs shapes line in the full combined
datacard is replaced by a RooHistPdf built from the real (GGJets+DDQCDGJets+TTGG)
MC events passing that category's own selection cut - everything else (signal
shapes, systematics, rateParams) is left untouched, so the fit retains the full
cross-category correlated-nuisance structure.
"""
import argparse
import os
import re

import numpy as np
import pyarrow.parquet as pq
import ROOT

ROOT.gROOT.SetBatch(True)

# Default = the scored-events parquet of the v7 final datacard on UAF; override with --parquet.
DEFAULT_PARQUET = "/home/users/bdanzi/HHbbgg/CombineForBiasTests/CMSSW_14_1_0_pre4/src/HiggsAnalysis/CombinedLimit/BiasStudiesToolkit/packaged_datacard_v7_SnTV7F1E500T0821thTest_resample_DDonly_min_latest/merged_scored_events_SnTV7F1E500T0821.parquet"

MASS_MIN, MASS_MAX, MASS_NBINS = 100.0, 180.0, 80

# Category selection cuts, verbatim from the user (dijet_mass == nonResReg_vbfpair_dijet_mass_DNNreg)
def category_masks(df):
    ggHH = df["is_ggHH_sig_score"]
    nonRes = df["is_nonRes_bkg_score"]
    res = df["is_Res_bkg_score"]
    vbf = df["is_VBFHH_sig_score"]
    dijet = df["nonResReg_vbfpair_dijet_mass_DNNreg"]
    boosted = df["is_boosted"]

    dijet_win = (dijet > 80.0) & (dijet < 190.0)
    resolved = boosted == 0

    is_cat0 = boosted == 1
    is_cat1 = (vbf >= 0.819) & dijet_win & resolved
    is_cat2 = (
        (ggHH > 0.368) & (nonRes < 0.0002144) & (res < 0.003782)
        & (~(vbf >= 0.819)) & dijet_win & resolved
    )
    cat2_tag = (ggHH > 0.368) & (nonRes < 0.0002144) & (res < 0.003782)
    is_cat3 = (
        (ggHH > 0.21) & (nonRes < 0.000849) & (res < 0.031798)
        & (~cat2_tag) & (~(vbf >= 0.819)) & dijet_win & resolved
    )
    cat3_tag = (ggHH > 0.21) & (nonRes < 0.000849) & (res < 0.031798)
    is_cat4 = (
        (ggHH > 0.638) & (nonRes < 0.0042192) & (res < 0.09995)
        & (~cat2_tag) & (~cat3_tag) & (~(vbf >= 0.819)) & dijet_win & resolved
    )
    return {"cat0": is_cat0, "cat1": is_cat1, "cat2": is_cat2, "cat3": is_cat3, "cat4": is_cat4}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datacard", help="Full combined analytic datacard, e.g. Datacard_2016-2025_allcats_final.txt")
    ap.add_argument("--outdir", default="nominal_pdfs_combined", help="Directory for the combined truth workspace.")
    ap.add_argument("-o", "--output", default=None, help="Output hybrid datacard path.")
    ap.add_argument("--parquet", default=DEFAULT_PARQUET, help="Merged scored-events parquet with the MC background events.")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    ws_path = os.path.join(args.outdir, "GGjetsWS_combined.root")

    print(f"[INFO] loading {args.parquet}")
    cols = ["sample", "mass", "weight_tot", "is_boosted", "is_VBFHH_sig_score",
            "is_ggHH_sig_score", "is_nonRes_bkg_score", "is_Res_bkg_score",
            "nonResReg_vbfpair_dijet_mass_DNNreg"]
    table = pq.read_table(args.parquet, columns=cols)
    n_all = table.num_rows
    print(f"[INFO] loaded {n_all} rows")

    sample = table.column("sample").to_numpy(zero_copy_only=False)
    bkg_mask_np = (sample == "GGJets") | (sample == "DDQCDGJets") | (sample == "TTGG")
    table_bkg = table.filter(bkg_mask_np)
    bkg = {c: table_bkg.column(c).to_numpy(zero_copy_only=False) for c in cols}
    n_bkg = len(bkg["mass"])
    print(f"[INFO] non-resonant background (GGJets+DDQCDGJets+TTGG): {n_bkg} rows")
    for s in ("GGJets", "DDQCDGJets", "TTGG"):
        print(f"  {s}: {int((bkg['sample'] == s).sum())}")

    masks = category_masks(bkg)

    w = ROOT.RooWorkspace("w")
    w.factory(f"mass[{MASS_MIN},{MASS_MAX}]")
    w.factory("MH[125]")
    w.var("MH").setConstant(True)
    obs = ROOT.RooArgSet(w.var("mass"))
    getattr(w, "import")(obs)

    summary = {}
    for cat, mask in masks.items():
        mask = np.asarray(mask)
        n_raw = int(mask.sum())
        weights = bkg["weight_tot"][mask].astype(np.float64)
        masses = bkg["mass"][mask].astype(np.float64)
        nevents = float(weights.sum()) if n_raw > 0 else 0.0
        summary[cat] = (n_raw, nevents)
        print(f"[INFO] {cat}: {n_raw} raw MC events passing cut, sum(weight_tot) = {nevents:.2f}")

        hist = ROOT.TH1F(f"h_mgg_{cat}", f"h_mgg_{cat}", MASS_NBINS, MASS_MIN, MASS_MAX)
        if n_raw > 0:
            hist.FillN(n_raw, masses, weights)

        data_hist = ROOT.RooDataHist(f"data_hist_{cat}", "Data hist", obs, hist)
        getattr(w, "import")(data_hist)
        pdf = ROOT.RooHistPdf(f"roohistpdf_{cat}", "Hist pdf", obs, data_hist)
        getattr(w, "import")(pdf)

        pdf_norm = ROOT.RooRealVar(f"roohistpdf_{cat}_norm", f"roohistpdf_{cat}_norm",
                                    nevents, max(0.001, nevents * 0.1), max(10.0, nevents * 10.0))
        pdf_norm.setConstant(False)
        getattr(w, "import")(pdf_norm)

        epdf = ROOT.RooExtendPdf(f"ext_{cat}", "ext", pdf, pdf_norm)
        if nevents > 0:
            toy = epdf.generate(obs, int(round(nevents)))
        else:
            toy = ROOT.RooDataSet(f"roodataset_nonrestoy_{cat}", "empty", obs)
        toy.SetName(f"roodataset_nonrestoy_{cat}")
        getattr(w, "import")(toy)

    w.writeToFile(ws_path, True)
    print(f"[INFO] wrote combined truth workspace: {ws_path}")

    zero_cats = [c for c, (n, _) in summary.items() if n == 0]
    if zero_cats:
        print(f"[WARNING] categories with ZERO passing MC events (cannot build a meaningful truth shape): {zero_cats}")

    # --- Build the combined hybrid datacard ---
    with open(args.datacard) as f:
        lines = f.readlines()

    # A swapped category's bkg_mass is now a plain RooHistPdf, not a RooMultiPdf -
    # the datacard's "pdfindex_..._<cat>_... discrete" line for that category must
    # be dropped too, or text2workspace segfaults trying to treat a non-RooMultiPdf
    # shape as a discrete-index envelope (confirmed by direct reproduction).
    pdfindex_res = [re.compile(rf"^pdfindex_\w*{re.escape(cat)}\w*\s") for cat in masks]

    out_lines = []
    replaced = {cat: {"bkg_mass": False, "data_obs": False} for cat in masks}
    for line in lines:
        if any(p.match(line) for p in pdfindex_res):
            continue
        tokens = line.split()
        if len(tokens) >= 3 and tokens[0] == "shapes" and tokens[1] in ("bkg_mass", "data_obs") and tokens[2] in masks:
            proc, cat = tokens[1], tokens[2]
            obj = f"roohistpdf_{cat}" if proc == "bkg_mass" else f"roodataset_nonrestoy_{cat}"
            out_lines.append(f"shapes       {proc:<50} {cat:<40} {ws_path} w:{obj}\n")
            replaced[cat][proc] = True
        else:
            out_lines.append(line)

    missing = [(c, p) for c, d in replaced.items() for p, done in d.items() if not done]
    if missing:
        raise RuntimeError(f"Could not find shapes line(s) for: {missing}")

    out_path = args.output or (args.datacard[:-4] + "_GGJetsCombined.txt" if args.datacard.endswith(".txt") else args.datacard + "_GGJetsCombined.txt")
    with open(out_path, "w") as f:
        f.writelines(out_lines)
    print(f"[INFO] wrote combined hybrid truth datacard: {out_path}")


if __name__ == "__main__":
    main()
