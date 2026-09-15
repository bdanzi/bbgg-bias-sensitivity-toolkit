import ROOT
import awkward as ak
import argparse
import os

# --- Argument Parsing ---
parser = argparse.ArgumentParser()
parser.add_argument("--dim", choices=["1D", "2D"], default="1D", help="Choose between 1D (mass) or 2D (mass + dijet_mass) fit")
args = parser.parse_args()
is_2D = (args.dim == "2D")

# Creazione cartella di output se non esiste
os.makedirs("nominal_pdfs", exist_ok=True)

# --- Data Loading ---
df_multiclass = ak.from_parquet("/eos/user/e/evourlio/FinalFitForHHbbgg_summer2026_Run2Run3Split/CMSSW_14_1_0_pre4/src/flashggFinalFit/merged_scored_events_Version_20260222_bTagWPs_revisedNewBaseline_ResNonResggHHVBFHH_xsecWeightInSignal_1D_16-25_stopAt140Epochs_forPreApp_scaledByYuxiang.parquet")

# Filter for relevant background samples
nonRes_BKG = df_multiclass[
    (df_multiclass['sample']=="GGJets") ^
    (df_multiclass['sample']=="TTGG") ^
    (df_multiclass['sample']=="DDQCDGJETS")
]

# --- SR Definitions ---
common_cuts = (nonRes_BKG['nonResReg_vbfpair_dijet_mass_DNNreg'] > 80.0) & (nonRes_BKG['nonResReg_vbfpair_dijet_mass_DNNreg'] < 190.0) & (nonRes_BKG['mass'] > 100.0) & (nonRes_BKG['mass'] < 180.0) & ~nonRes_BKG['is_boosted'] & (nonRes_BKG['is_VBFHH_sig_score'] < 0.774)

SR1 = nonRes_BKG[(nonRes_BKG['is_ggHH_sig_score'] > 0.99274) & (nonRes_BKG['is_nonRes_bkg_score'] < 0.0003) & (nonRes_BKG['is_Res_bkg_score'] < 0.00392) & common_cuts]

SR2 = nonRes_BKG[(nonRes_BKG['is_ggHH_sig_score'] > 0.46212) & (nonRes_BKG['is_nonRes_bkg_score'] < 0.00066) & (nonRes_BKG['is_Res_bkg_score'] < 0.008) & ~((nonRes_BKG['is_ggHH_sig_score'] > 0.99274) & (nonRes_BKG['is_nonRes_bkg_score'] < 0.0003) & (nonRes_BKG['is_Res_bkg_score'] < 0.00392)) & common_cuts]

SR3 = nonRes_BKG[(nonRes_BKG['is_ggHH_sig_score'] > 0.868) & (nonRes_BKG['is_nonRes_bkg_score'] < 0.002) & (nonRes_BKG['is_Res_bkg_score'] < 0.018) & ~((nonRes_BKG['is_ggHH_sig_score'] > 0.46212) & (nonRes_BKG['is_nonRes_bkg_score'] < 0.00066) & (nonRes_BKG['is_Res_bkg_score'] < 0.008)) & ~((nonRes_BKG['is_ggHH_sig_score'] > 0.99274) & (nonRes_BKG['is_nonRes_bkg_score'] < 0.0003) & (nonRes_BKG['is_Res_bkg_score'] < 0.00392)) & common_cuts]

SRs = {"SR1": SR1, "SR2": SR2, "SR3": SR3}

# --- Workspace Generation ---
for SRname, non_res_bkg_SR in SRs.items():
    print(f"--- Processing {SRname} in {args.dim} mode ---")
    
    w = ROOT.RooWorkspace("w")
    
    if is_2D:
        w.factory("mass[100,180]")
        w.factory("Res_mjj_regressed[80,190]")
        obs = ROOT.RooArgSet(w.var("mass"), w.var("Res_mjj_regressed"))
        hist = ROOT.TH2F("h_mggmjj_%s"%SRname, "h_mggmjj_%s"%SRname, 40, 100, 180, 11, 80, 190)
        for mjj, mgg, weight in zip(non_res_bkg_SR['nonResReg_vbfpair_dijet_mass_DNNreg'], non_res_bkg_SR['mass'], non_res_bkg_SR['weight_tot']):
            hist.Fill(mgg, mjj, weight)
    else:
        w.factory("mass[100,180]")
        w.factory("MH[125]")
        obs = ROOT.RooArgSet(w.var("mass"))
        hist = ROOT.TH1F("h_mgg_%s"%SRname, "h_mgg_%s"%SRname, 40, 100, 180)
        for mgg, weight in zip(non_res_bkg_SR['mass'], non_res_bkg_SR['weight_tot']):
            hist.Fill(mgg, weight)

    nevents = hist.Integral(0,-1)
    getattr(w, 'import')(obs)

    # --- PDF Creation from dataHist---
    tn = "roohistpdf_%s"%SRname
    data_hist = ROOT.RooDataHist("data_hist_%s"%SRname, "Data hist", obs, hist)
    getattr(w, "import")(data_hist)
    pdf = ROOT.RooHistPdf(tn, "Hist pdf", obs, data_hist)
    mass = w.var("mass")
    frame = mass.frame()
    data_hist.plotOn(frame,ROOT.RooFit.Name("data"))
    pdf.plotOn(frame, ROOT.RooFit.Name("pdf"),ROOT.RooFit.LineColor(ROOT.kRed))
    c = ROOT.TCanvas("c","c",800,600)
    frame.Draw()
    leg = ROOT.TLegend(0.60, 0.70, 0.88, 0.88)
    leg.AddEntry(frame.findObject("data"), "DataHist", "pe")
    leg.AddEntry(frame.findObject("pdf"), "RooHistPdf", "l")
    leg.Draw()
    c.SaveAs(f"pdf_vs_data_{SRname}.pdf")
    epdf = ROOT.RooExtendPdf(tn+"_ext", "Extended hist pdf", pdf, nevents)
    getattr(w, "import")(pdf)
    
    # Define floating normalization
    pdf_norm = ROOT.RooRealVar(tn+"_norm", tn+"_norm", nevents, max(0.001, nevents*0.1), max(10.0, nevents*10.0))
    pdf_norm.setConstant(False)
    getattr(w, "import")(pdf_norm)
    
    # --- Generate toys with extended PDF ---- #
    toy = epdf.generate(obs, nevents, 0, 0, "", 0, 1)
    toy.Print()
    toy.SetName("roodataset_nonrestoy_%s"%SRname)
    getattr(w, "import")(toy)

    # --- ModelConfig Setup ---
    mc = ROOT.RooStats.ModelConfig("ModelConfig", w)
    mc.SetPdf(w.pdf("roohistpdf_%s"%SRname)) 
    mc.SetObservables(obs)
    
    # Define and set Parameter of Interest (POI)
    poi = ROOT.RooRealVar("r", "r", 1.0, 0.0, 10.0)
    getattr(w, "import")(poi)
    mc.SetParametersOfInterest(ROOT.RooArgSet(poi))
    getattr(w, "import")(mc)

    mc_bonly = mc.Clone("ModelConfig_bonly")
    mu = mc_bonly.GetParametersOfInterest().first()
    mu.setVal(0)
    mu.setConstant(True)
    getattr(w, "import")(mc_bonly)  

    # --- Save Workspace ---
    w.writeToFile("nominal_pdfs/GGjetsWS_%s_%s.root"%(SRname, args.dim), True)
    print(f"Workspace saved: nominal_pdfs/GGjetsWS_{SRname}_{args.dim}.root")
