text2workspace.py datacard_cat0.txt -o workspace_multipdf_cat0.root -m 125
text2workspace.py datacard_cat1.txt -o workspace_multipdf_cat1.root -m 125
text2workspace.py datacard_cat2.txt -o workspace_multipdf_cat2.root -m 125
text2workspace.py datacard_cat3.txt -o workspace_multipdf_cat3.root -m 125
text2workspace.py datacard_cat4.txt -o workspace_multipdf_cat4.root -m 125

python3 -c "                                                                                                                                     
import ROOT, os                                                                                                                                  
                                                                                                                                                 
for c in range(5):                                                                                                                               
    fname = f'workspace_multipdf_cat{c}.root'                                                                                                    
    if not os.path.exists(fname):                                                                                                                
        continue                                                                                                                                 
                                                                                                                                                 
    f = ROOT.TFile.Open(fname)                                                                                                                   
    w = f.Get('w')                                                                                                                               
    if not w:                                                                                                                                    
        continue                                                                                                                                 
                                                                                                                                                 
    print(f'\n=================== FINAL MAP: cat{c} ===================')                                                                        
    all_objs = w.allPdfs()                                                                                                                       
    iterator = all_objs.createIterator()                                                                                                         
    obj = iterator.Next()                                                                                                                        
    found = False                                                                                                                                
                                                                                                                                                 
    while obj:                                                                                                                                   
        if obj.ClassName() == 'RooMultiPdf':                                                                                                     
            found = True                                                                                                                         
            print(f'-> MultiPdf Nome: {obj.GetName()}')                                                                                          
            for i in range(obj.getNumPdfs()):                                                                                                    
                print(f'   Index {i}: {obj.getPdf(i).GetName()}')                                                                                
        obj = iterator.Next()                                                                                                                    
                                                                                                                                                 
    if not found:                                                                                                                                
        print('   [WARNING] NO RooMultiPdf found in this category')                                                                              
"
