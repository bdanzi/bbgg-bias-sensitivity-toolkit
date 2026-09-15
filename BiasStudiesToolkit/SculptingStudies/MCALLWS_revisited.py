import ROOT
import awkward as ak
import argparse
import os

# --- Configuration ---
parser = argparse.ArgumentParser()
parser.add_argument("--dim", choices=["1D", "2D"], default="1D")
args = parser.parse_args()
is_2D = (args.dim == "2D")

# Path base for PDF files
base_dir = ""#/eos/home-e/evourlio/FinalFitForHHbbgg_summer2026_Run2Run3Split/CMSSW_14_1_0_pre4/src/flashggFinalFit/"

# --- Load Data ---
df = ak.from_parquet("/eos/user/e/evourlio/FinalFitForHHbbgg_summer2026_Run2Run3Split/CMSSW_14_1_0_pre4/src/flashggFinalFit/merged_scored_events_Version_20260222_bTagWPs_revisedNewBaseline_ResNonResggHHVBFHH_xsecWeightInSignal_1D_16-25_stopAt140Epochs_forPreApp_scaledByYuxiang.parquet")

df = df[(df['nonResReg_vbfpair_dijet_mass_DNNreg'] > 80.0) & (df['nonResReg_vbfpair_dijet_mass_DNNreg'] < 190.0) & (df['mass'] > 100.0) & (df['mass'] < 180.0)]
# --- Define Selection Masks ---
common_cuts = (
    (df['nonResReg_vbfpair_dijet_mass_DNNreg'] > 80.0) & 
    (df['nonResReg_vbfpair_dijet_mass_DNNreg'] < 190.0) & 
    (df['mass'] > 100.0) & 
    (df['mass'] < 180.0) & 
    (~df['is_boosted']) & 
    (df['is_VBFHH_sig_score'] < 0.774)
)

mask_sr1 = ((df['is_ggHH_sig_score'] > 0.992) & (df['is_nonRes_bkg_score'] < 0.00026) & (df['is_Res_bkg_score'] < 0.00526))
mask_sr2 = ((df['is_ggHH_sig_score'] > 0.268) & (df['is_nonRes_bkg_score'] < 0.00066) & (df['is_Res_bkg_score'] < 0.008)) & ~mask_sr1
mask_sr3 = ((df['is_ggHH_sig_score'] > 0.868) & (df['is_nonRes_bkg_score'] < 0.002) & (df['is_Res_bkg_score'] < 0.018)) & ~mask_sr1 & ~mask_sr2

cats = {"SR2": mask_sr1 & common_cuts, "SR3": mask_sr2 & common_cuts, "SR4": mask_sr3 & common_cuts}

# --- Workspace Generation ---
for SRname, total_mask in cats.items():
    print(f"--- Processing {SRname} ---")
    w = ROOT.RooWorkspace("w")
    mh = w.var("MH")
    if mh:
        mh.setVal(125)
        mh.setConstant(True)
        print("Higgs mass set to",mh.getValV())
    else:
        print("MH variable not found in the workspace")
    # 1. Setup Variabili
    if is_2D:
        w.factory("mass[100,180]")
        w.factory("nonResReg_vbfpair_dijet_mass_DNNreg[80,190]")
        obs = ROOT.RooArgSet(w.var("mass"), w.var("nonResReg_vbfpair_dijet_mass_DNNreg"))
    else:
        w.factory("mass[100,180]")
        obs = ROOT.RooArgSet(w.var("mass"))
    getattr(w, 'import')(obs)
    
    # Add Internal Samples (nonRes + DD)
    # Group for non res 
    samples = {"nonRes": (df['sample']=="GGJets") ^ (df['sample']=="TTGG"), "DD": (df['sample']=="DDQCDGJets")}
    combined_mask = (samples["nonRes"] | samples["DD"]) & total_mask
    subset = df[combined_mask]
    
    # Create Dataset for non res bkg
    data_nonRes = ROOT.RooDataSet(f"data_nonRes_{SRname}", "Dataset nonRes", obs, ROOT.RooFit.WeightVar("weight_tot"))
    mgg_arr, mjj_arr, w_arr = ak.to_numpy(subset['mass']), ak.to_numpy(subset['nonResReg_vbfpair_dijet_mass_DNNreg']), ak.to_numpy(subset['weight_tot'])
    for i in range(len(mgg_arr)):
        w.var("mass").setVal(mgg_arr[i])
        if is_2D: w.var("nonResReg_vbfpair_dijet_mass_DNNreg").setVal(mjj_arr[i])
        data_nonRes.add(obs, w_arr[i])
    getattr(w, 'import')(data_nonRes)

    # Generate Toy for the non-resonant background (dggj)
    nevents = float(sum(w_arr))
    dh_nonRes = ROOT.RooDataHist(f"dh_nonRes_{SRname}", "dh", obs, data_nonRes)
    pdf_nonRes = ROOT.RooHistPdf(f"pdf_nonRes_{SRname}", "pdf", obs, dh_nonRes)
    n_nonRes = ROOT.RooRealVar(f"n_nonRes_{SRname}", "n_nonRes", int(nevents))
    getattr(w, 'import')(n_nonRes)
    epdf_nonRes = ROOT.RooExtendPdf(f"ext_nonRes_{SRname}", "ext", pdf_nonRes, n_nonRes)
    dggj = epdf_nonRes.generate(obs, ROOT.RooFit.Extended(True))
    dggj.SetName(f"roodataset_nonrestoy_{SRname}")
    getattr(w, 'import')(dggj)

    # 3. Add External PDF Samples (TT, VH, Res)
    cat_num = SRname.replace("SR", "")
    proc_map = {
        "TTH": f"hggpdfsmrel_mgg_TTH_2016-2025_cat{cat_num}_13TeV",
        "VH":  f"hggpdfsmrel_mgg_VH_2016-2025_cat{cat_num}_13TeV",
        "GG2H": f"hggpdfsmrel_mgg_GG2H_2016-2025_cat{cat_num}_13TeV",
        "VBF": f"hggpdfsmrel_mgg_VBF_2016-2025_cat{cat_num}_13TeV"
        
    }

    #file_path = f"{base_dir}/Background/outdir_packaged/CMS-HGG_multipdf_packaged_cat{cat_num}.root"
    file_path = f"./CMS-HGG_multipdf_packaged_cat{cat_num}.root"
    if os.path.exists(file_path):
        print("Opening file", file_path)
        f = ROOT.TFile.Open(file_path)
        w_ext = f.Get("multipdf")
        for proc, pdf_name in proc_map.items():
            pdf = w_ext.pdf(pdf_name).Clone(f"{pdf_name}_clone")
            norm = w_ext.function(f"{pdf_name}_norm").Clone(f"{pdf_name}_norm_clone")
            rate = w_ext.function(f"rate_mgg_{proc}_2016-2025_cat{cat_num}_13TeV").Clone(f"rate_mgg_{proc}_2016-2025_cat{cat_num}_13TeV_clone")
            if not pdf or not norm:
                print(f"CRITICAL: Could not find {pdf_name} or {pdf_name} in workspace!")
                continue
            getattr(w, 'import')(pdf, ROOT.RooFit.RecycleConflictNodes())
            getattr(w, 'import')(norm, ROOT.RooFit.RecycleConflictNodes())
            my_pdf = w.pdf(pdf_name)
            my_norm = w.function(f"{pdf_name}_norm_clone")
            print(int(my_norm.getVal()))
            my_rate = w.function(f"rate_mgg_{proc}_2016-2025_cat{cat_num}_13TeV_clone")
            print(int(my_rate.getVal()))
            epdf = ROOT.RooExtendPdf(f"ext_{proc}_{SRname}", "ext", my_pdf, my_norm)
            #epdf = ROOT.RooExtendPdf(f"ext_{proc}_{SRname}", "ext", pdf, norm)
            d_toy = epdf.generate(obs, int(my_norm.getVal()))
            d_toy.SetName(f"roodataset_{proc}_{SRname}")
            getattr(w, 'import')(d_toy)
        f.Close()

    # 4. Final Merge
    all_datasets = [w.data(name.GetName()) for name in w.allData() if "roodataset_" in name.GetName()]
    master_data = all_datasets[0].Clone(f"roodataset_final_{SRname}")
    for d in all_datasets[1:]:
        master_data.append(d)
    getattr(w, 'import')(master_data)

    # Save
    os.makedirs("nominal_pdfs", exist_ok=True)
    w.writeToFile(f"nominal_pdfs/MCALLWS_{SRname}_{args.dim}.root", True)
    print(f"Workspace salvato: nominal_pdfs/MCALLWS_{SRname}_{args.dim}.root")
