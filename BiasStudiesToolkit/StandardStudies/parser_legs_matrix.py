#!/usr/bin/env python3
import ROOT
import sys

def main():
    if len(sys.argv) < 2:
        print("[ERROR] Please provide a workspace file path.", file=sys.stderr)
        sys.exit(1)

    ws_file = sys.argv[1]
    f = ROOT.TFile.Open(ws_file)
    if not f or f.IsZombie():
        sys.exit(1)
        
    w = f.Get('w')
    if not w:
        sys.exit(1)

    # 1. Mapping tags of functions to the internal index of RooMultiPdf
    pdf_map = {}
    all_objs = w.allPdfs()
    iterator = all_objs.createIterator()
    obj = iterator.Next()

    while obj:
        if obj.ClassName() == 'RooMultiPdf':
            mpdf_name = obj.GetName()
            for i in range(obj.getNumPdfs()):
                pdf_name = obj.getPdf(i).GetName().lower()
                tag = "unknown"
                
                # recognize the PDF from its name
                if 'exp1' in pdf_name: tag = "exp1"
                elif 'bern1' in pdf_name or 'flat0' in pdf_name: tag = "bern1"
                elif 'bern2' in pdf_name: tag = "bern2"
                elif 'pow1' in pdf_name: tag = "pow1"
                elif 'lau1' in pdf_name: tag = "lau1"
                elif 'lau2' in pdf_name: tag = "lau2"
                
                # Save index associated to the pair (NameMultiPdf, TypeFunction)
                pdf_map[(mpdf_name, tag)] = i
        obj = iterator.Next()

    # 2. Find variables of categories (hgg and hbb)
    cats = w.allCats()
    cat_iterator = cats.createIterator()
    cat_obj = cat_iterator.Next()
    pdfindex_names = []
    
    while cat_obj:
        name = cat_obj.GetName()
        if 'pdfindex' in name or 'shapeBkg' in name:
            pdfindex_names.append(name)
        cat_obj = cat_iterator.Next()

    hgg_var, hbb_var = "", ""
    for p_name in pdfindex_names:
        p_lower = p_name.lower()
        is_hgg = 'hgg' in p_lower or 'cat1' in p_lower or 'obsonly' in p_lower or 'mass_cat' in p_lower
        is_hbb = 'hbb' in p_lower
        
        if is_hgg: hgg_var = p_name
        elif is_hbb: hbb_var = p_name

        # 3. Estrai dinamicamente tutti i tag trovati nel workspace (evita liste fisse!)
        extracted_tags = set(tag for (mpdf_name, tag) in pdf_map.keys() if tag != "unknown")

        for t in extracted_tags:
            for (mpdf_name, tag), idx in pdf_map.items():
                if tag == t:
                    # Associate HGG variables to MultiPdf HGG, HBB to MultiPdf HBB
                    if (is_hgg and ('hgg' in mpdf_name.lower() or 'cat1' in mpdf_name.lower() or 'mass_cat' in mpdf_name.lower())) or \
                       (is_hbb and 'hbb' in mpdf_name.lower()):
                        print(f"IDX_{p_name}_{t}='{p_name}={idx}'")

    # Print variables for Bash
    print(f"HGG_VAR='{hgg_var}'")
    print(f"HBB_VAR='{hbb_var}'")

if __name__ == '__main__':
    main()
