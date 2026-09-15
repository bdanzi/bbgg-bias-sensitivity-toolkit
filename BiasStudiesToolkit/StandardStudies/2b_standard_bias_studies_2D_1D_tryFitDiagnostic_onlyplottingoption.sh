#!/bin/bash

# Inline help function
show_help() {
    echo "Usage: ./run_bias_matrix.sh [options]"
    echo ""
    echo "Options:"
    echo "  --run catX         Physically execute fits and plots for the specified category (e.g., cat0, cat1, ...)"
    echo "  --only-hgg         Ignore HBB presence and run fewer combinations (HGG only)"
    echo "  --only-plot        Skip generation and fitting; execute ONLY the plotting commands"
    echo "  --help             Show this help message"
    echo ""
    echo "If launched without --run or --only-plot, the script will run in DRY-RUN mode, only printing the commands."
    exit 0
}

# Parse input arguments
RUN_CAT=""
ONLY_HGG=false
ONLY_PLOT=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help)
            show_help
            ;;
        --run)
            if [ -z "$2" ] || [[ "$2" == --* ]]; then 
                echo "[ERROR] Please specify the category after --run (e.g., cat0)"
                exit 1
            fi
            RUN_CAT="$2"
            shift 2
            ;;
        --only-hgg)
            ONLY_HGG=true
            shift
            ;;
        --only-plot)
            ONLY_PLOT=true
            shift
            ;;
        *)
            echo "[ERROR] Unknown option: $1"
            show_help
            ;;
    esac
done

# Controllo mutuamente esclusivo (opzionale ma consigliato)
if [ ! -z "$RUN_CAT" ] && [ "$ONLY_PLOT" = true ]; then
    echo "[WARNING] Both --run and --only-plot were provided. --only-plot takes precedence (no fits will be run)."
fi

# =========================================================================
# Add all the functions to be tested
# =========================================================================
TRUTH_FUNCTIONS=("exp1" "bern1" "bern2" "pow1" "lau1" "lau2")
FIT_FUNCTIONS=("exp1" "bern1" "bern2" "pow1" "lau1" "lau2")
R_TRUTH_VALUES=(0)

# Array of all categories to process by default
#CATEGORIES=(0 1 2 3 4)
CATEGORIES=(2)
if [ "$ONLY_PLOT" = true ]; then
    echo "ONLY-PLOT MODE ENABLED: Skipping generation/fitting. Executing plotting scripts only."
elif [ ! -z "$RUN_CAT" ]; then
    CAT_NUM=$(echo "$RUN_CAT" | sed 's/cat//')
    CATEGORIES=($CAT_NUM)
    echo "RUN MODE ENABLED: Commands will be executed for cat${CAT_NUM}."
else
    echo "DRY-RUN MODE: Only printing commands. Use --run catX to run them, or --only-plot to plot."
fi

if [ "$ONLY_HGG" = true ]; then
    echo "HGG-ONLY MODE ENABLED: HBB channel will be ignored to save time and reduce combinations."
fi

# Main category loop
for c in "${CATEGORIES[@]}"; do
    ws="workspace_multipdf_cat${c}.root"
    
    # Se siamo in RUN mode (e non in ONLY_PLOT), verifichiamo il workspace
    if [ "$ONLY_PLOT" = false ] && [ ! -z "$RUN_CAT" ] && [ ! -f "$ws" ]; then
        echo "[WARNING] Workspace $ws not found in the current directory. Skipping category cat${c}."
        continue 
    fi

    echo ""
    echo "========================================================================="
    echo "   COMPREHENSIVE MULTI-LEG BIAS MATRIX FOR CATEGORY: cat${c}"
    echo "========================================================================="

    # Il parser serve a definire le variabili d'ambiente con gli indici delle funzioni
    if [ -f "$ws" ]; then
        eval $(python3 parser_legs_matrix.py "$ws" 2>/dev/null)
    fi

    # Determine multi-leg presence
    HAS_HGG=false; HAS_HBB=false
    if [ ! -z "$HGG_VAR" ]; then HAS_HGG=true; fi
    # If ONLY_HGG is active, mark HAS_HBB always as false
    if [ ! -z "$HBB_VAR" ] && [ "$ONLY_HGG" = false ]; then HAS_HBB=true; fi

    # 1. Loop through injected Truth forms
    for t_func in "${TRUTH_FUNCTIONS[@]}"; do
        # 2. Loop through fitted Model forms
        for f_func in "${FIT_FUNCTIONS[@]}"; do
            # 3. Loop through Signal Strengths
            for r_truth in "${R_TRUTH_VALUES[@]}"; do
                
                # --- CONFIGURATION 1: BOTH LEGS FIXED (OR JUST HGG IF ONLY_HGG=true) ---
                FREEZE_BOTH="MH"
                SET_GEN_BOTH=""; SET_FIT_BOTH=""
                
                if [ "$HAS_HGG" = true ]; then
                    idx_gen="IDX_${HGG_VAR}_${t_func}"
                    idx_fit="IDX_${HGG_VAR}_${f_func}"
                    if [ -z "${!idx_gen}" ] || [ -z "${!idx_fit}" ]; then continue; fi
                    
                    FREEZE_BOTH="${FREEZE_BOTH},${HGG_VAR}"
                    SET_GEN_BOTH="${!idx_gen}"
                    SET_FIT_BOTH="${!idx_fit}"
                fi
                if [ "$HAS_HBB" = true ]; then
                    idx_gen="IDX_${HBB_VAR}_${t_func}"
                    idx_fit="IDX_${HBB_VAR}_${f_func}"
                    if [ -z "${!idx_gen}" ] || [ -z "${!idx_fit}" ]; then continue; fi
                    
                    FREEZE_BOTH="${FREEZE_BOTH},${HBB_VAR}"
                    [ -z "$SET_GEN_BOTH" ] && SET_GEN_BOTH="${!idx_gen}" || SET_GEN_BOTH="${SET_GEN_BOTH},${!idx_gen}"
                    [ -z "$SET_FIT_BOTH" ] && SET_FIT_BOTH="${!idx_fit}" || SET_FIT_BOTH="${SET_FIT_BOTH},${!idx_fit}"
                fi

                # Specific filename fallback fix for cat0 split files layout
                WS_GEN_CMD="$ws"
                WS_FIT_CMD="$ws"
                if [ -z "$SET_GEN_BOTH" ] && [ "$c" -eq 0 ]; then
                    FILE_GEN="CMS-HGG_multipdf_cat0_new_exponential.root"
                    if [[ "$t_func" == *"bern"* ]] || [[ "$t_func" == *"pow"* ]]; then FILE_GEN="CMS-HGG_multipdf_cat0_new_linear.root"; fi
                    FILE_FIT="CMS-HGG_multipdf_cat0_new_linear.root"
                    if [[ "$f_func" == *"exp"* ]]; then FILE_FIT="CMS-HGG_multipdf_cat0_new_exponential.root"; fi
                    
                    if [ ! -z "$RUN_CAT" ] && [ "$ONLY_PLOT" = false ]; then
                        sed "s/CMS-HGG_multipdf_cat0.root/${FILE_GEN}/g" datacard_cat0.txt > datacard_cat0_truth_${t_func}.txt
                        sed "s/CMS-HGG_multipdf_cat0.root/${FILE_FIT}/g" datacard_cat0.txt > datacard_cat0_fit_${f_func}.txt
                        text2workspace.py datacard_cat0_truth_${t_func}.txt -o ws_truth_${t_func}_cat0.root -m 125 &>/dev/null || continue
                        text2workspace.py datacard_cat0_fit_${f_func}.txt -o ws_fit_${f_func}_cat0.root -m 125 &>/dev/null || continue
                    fi
                    WS_GEN_CMD="ws_truth_${t_func}_cat0.root"
                    WS_FIT_CMD="ws_fit_${f_func}_cat0.root"
                fi

                LABEL_MODE="BOTH LEGS FIXED"
                if [ "$ONLY_HGG" = true ] || [ "$HAS_HBB" = false ]; then LABEL_MODE="ONLY HGG ACTIVE"; fi

                NAME_BOTH="cat${c}_both_truth_${t_func}_fit_${f_func}_r${r_truth}"
                echo "-------------------------------------------------------------------------"
                echo "   PAIRING [${LABEL_MODE}]: Truth [${t_func^^}] vs Fit [${f_func^^}] | r=${r_truth}"
                echo "-------------------------------------------------------------------------"
                CMD_GEN="combine -M GenerateOnly $WS_GEN_CMD -m 125 -t 1000 -s 123456 -n .gen_${NAME_BOTH} --expectSignal ${r_truth} ${SET_GEN_BOTH:+--setParameters ${SET_GEN_BOTH}} --freezeParameters ${FREEZE_BOTH} --cminDefaultMinimizerStrategy 0  --rMin -10 --rMax 10 --saveToys"
                CMD_FIT="combine -M FitDiagnostics $WS_FIT_CMD -m 125 -t 1000 -s 123456 -n .fit_${NAME_BOTH} --expectSignal ${r_truth} --toysFile higgsCombine.gen_${NAME_BOTH}.GenerateOnly.mH125.123456.root ${SET_FIT_BOTH:+--setParameters ${SET_FIT_BOTH}} --freezeParameters ${FREEZE_BOTH} --cminDefaultMinimizerStrategy 0 --robustFit 1 --rMin -10 --rMax 10"
                CMD_PLOT="python3 plot_bias_pull_FitDiagnostics.py -i fitDiagnostics.fit_cat${c}_both_truth_${t_func}_fit_${f_func}_r${r_truth}.root --r-truth ${r_truth} --truth-func ${t_func} --fit-func ${f_func} --cat cat${c}_both_r${r_truth} -o ./bias_plots_FitDiagnostics_allCombinations"
                CMD_PLOT_1="python3 plot_bias_pull_FitDiagnostics_onlyrfit.py -i fitDiagnostics.fit_cat${c}_both_truth_${t_func}_fit_${f_func}_r${r_truth}.root --r-truth ${r_truth} --truth-func ${t_func} --fit-func ${f_func} --cat cat${c}_both_r${r_truth} -o ./bias_plots_FitDiagnostics_allCombinations"
                
                if [ "$ONLY_PLOT" = true ]; then
                    echo "  [PLOT] $CMD_PLOT"
                    echo "  [PLOT] $CMD_PLOT_1"
                    mkdir -p bias_plots_FitDiagnostics_allCombinations
                    eval $CMD_PLOT
                    eval $CMD_PLOT_1
                else
                    echo "  [GEN]  $CMD_GEN"
                    echo "  [FIT]  $CMD_FIT"
                    echo "  [PLOT] $CMD_PLOT"
                    echo "  [PLOT] $CMD_PLOT_1"
                    
                    if [ ! -z "$RUN_CAT" ]; then
                        eval $CMD_GEN > combine_gen_${NAME_BOTH}.log 2>&1
                        if [ $? -ne 0 ]; then echo "[ERROR] Generation failed for ${NAME_BOTH}. Skipping to next combination."; continue; fi
                        
                        eval $CMD_FIT > combine_fit_${NAME_BOTH}.log 2>&1
                        if [ $? -ne 0 ]; then 
                            echo "[ERROR] Fit failed for ${NAME_BOTH}. Skipping plot."
                        else 
                            mkdir -p bias_plots_FitDiagnostics_allCombinations
                            eval $CMD_PLOT
                            eval $CMD_PLOT_1
                        fi
                    fi
                fi

                # --- CONFIGURATIONS 2 & 3: SKIPPED AUTOMATICALLY IF HAS_HBB=false ---
                if [ "$HAS_HGG" = true ] && [ "$HAS_HBB" = true ]; then
                    # --- CONFIGURATION 2: HGG FIXED, HBB FLOATING ---
                    FREEZE_HGG_ONLY="MH,${HGG_VAR}"
                    idx_gen_hgg="IDX_${HGG_VAR}_${t_func}"
                    idx_fit_hgg="IDX_${HGG_VAR}_${f_func}"
                    if [ -z "${!idx_gen_hgg}" ] || [ -z "${!idx_fit_hgg}" ]; then continue; fi
                    
                    NAME_HGG_FIXED="cat${c}_hggFixed_hbbFloat_truth_${t_func}_fit_${f_func}_r${r_truth}"
                    echo "-------------------------------------------------------------------------"
                    echo "   PAIRING [HGG FIXED, HBB FLOATS]: HGG Truth [${t_func^^}] vs HGG Fit [${f_func^^}] | r=${r_truth}"
                    echo "-------------------------------------------------------------------------"
                    CMD_GEN_HGG="combine -M GenerateOnly $ws -m 125 -t 1000 -s 123456 -n .gen_${NAME_HGG_FIXED} --expectSignal ${r_truth} --setParameters ${!idx_gen_hgg} --freezeParameters ${FREEZE_HGG_ONLY} --cminDefaultMinimizerStrategy 0  --rMin -10 --rMax 10 --saveToys"
                    CMD_FIT_HGG="combine -M FitDiagnostics $ws -m 125 -t 1000 -s 123456 -n .fit_${NAME_HGG_FIXED} --expectSignal ${r_truth} --toysFile higgsCombine.gen_${NAME_HGG_FIXED}.GenerateOnly.mH125.123456.root --setParameters ${!idx_fit_hgg} --freezeParameters ${FREEZE_HGG_ONLY} --cminDefaultMinimizerStrategy 0 --robustFit 1 --rMin -10 --rMax 10"
                    CMD_PLOT_HGG="python3 plot_bias_pull_FitDiagnostics.py -i fitDiagnostics.fit_cat${c}_both_truth_${t_func}_fit_${f_func}_r${r_truth}.root --r-truth ${r_truth} --truth-func ${t_func} --fit-func ${f_func} --cat cat${c}_hggFixed_r${r_truth} -o ./bias_plots_FitDiagnostics_allCombinations"
                    CMD_PLOT_HGG_1="python3 plot_bias_pull_FitDiagnostics_onlyrfit.py -i fitDiagnostics.fit_cat${c}_both_truth_${t_func}_fit_${f_func}_r${r_truth}.root --r-truth ${r_truth} --truth-func ${t_func} --fit-func ${f_func} --cat cat${c}_hggFixed_r${r_truth} -o ./bias_plots_FitDiagnostics_allCombinations"
                    
                    if [ "$ONLY_PLOT" = true ]; then
                        echo "  [PLOT] $CMD_PLOT_HGG"
                        echo "  [PLOT] $CMD_PLOT_HGG_1"
                        eval $CMD_PLOT_HGG
                        eval $CMD_PLOT_HGG_1
                    else
                        echo "  [GEN]  $CMD_GEN_HGG"
                        echo "  [FIT]  $CMD_FIT_HGG"
                        echo "  [PLOT] $CMD_PLOT_HGG"
                        echo "  [PLOT] $CMD_PLOT_HGG_1"
                        
                        if [ ! -z "$RUN_CAT" ]; then
                            eval $CMD_GEN_HGG > combine_gen_${NAME_HGG_FIXED}.log 2>&1
                            if [ $? -eq 0 ]; then
                                eval $CMD_FIT_HGG > combine_fit_${NAME_HGG_FIXED}.log 2>&1
                                if [ $? -eq 0 ]; then eval $CMD_PLOT_HGG; eval $CMD_PLOT_HGG_1; else echo "[ERROR] Fit HGG failed. Skipping plot."; fi
                            else
                                echo "[ERROR] Gen HGG failed. Skipping.";
                            fi
                        fi
                    fi

                    # --- CONFIGURATION 3: HBB FIXED, HGG FLOATING ---
                    FREEZE_HBB_ONLY="MH,${HBB_VAR}"
                    idx_gen_hbb="IDX_${HBB_VAR}_${t_func}"
                    idx_fit_hbb="IDX_${HBB_VAR}_${f_func}"
                    if [ -z "${!idx_gen_hbb}" ] || [ -z "${!idx_fit_hbb}" ]; then continue; fi
                    
                    NAME_HBB_FIXED="cat${c}_hbbFixed_hggFloat_truth_${t_func}_fit_${f_func}_r${r_truth}"
                    echo "-------------------------------------------------------------------------"
                    echo "   PAIRING [HBB FIXED, HGG FLOATS]: HBB Truth [${t_func^^}] vs HBB Fit [${f_func^^}] | r=${r_truth}"
                    echo "-------------------------------------------------------------------------"
                    CMD_GEN_HBB="combine -M GenerateOnly $ws -m 125 -t 1000 -s 123456 -n .gen_${NAME_HBB_FIXED} --expectSignal ${r_truth} --setParameters ${!idx_gen_hbb} --freezeParameters ${FREEZE_HBB_ONLY} --cminDefaultMinimizerStrategy 0  --rMin -10 --rMax 10 --saveToys"
                    CMD_FIT_HBB="combine -M FitDiagnostics $ws -m 125 -t 1000 -s 123456 -n .fit_${NAME_HBB_FIXED} --expectSignal ${r_truth} --toysFile higgsCombine.gen_${NAME_HBB_FIXED}.GenerateOnly.mH125.123456.root --setParameters ${!idx_fit_hbb} --freezeParameters ${FREEZE_HBB_ONLY} --cminDefaultMinimizerStrategy 0  --robustFit 1 --rMin -10 --rMax 10"
                    CMD_PLOT_HBB="python3 plot_bias_pull_FitDiagnostics.py -i fitDiagnostics.fit_cat${c}_both_truth_${t_func}_fit_${f_func}_r${r_truth}.root --r-truth ${r_truth} --truth-func ${t_func} --fit-func ${f_func} --cat cat${c}_hbbFixed_r${r_truth} -o ./bias_plots_FitDiagnostics_allCombinations"
                    CMD_PLOT_HBB_1="python3 plot_bias_pull_FitDiagnostics_onlyrfit.py -i fitDiagnostics.fit_cat${c}_both_truth_${t_func}_fit_${f_func}_r${r_truth}.root --r-truth ${r_truth} --truth-func ${t_func} --fit-func ${f_func} --cat cat${c}_hbbFixed_r${r_truth} -o ./bias_plots_FitDiagnostics_allCombinations"
                    
                    if [ "$ONLY_PLOT" = true ]; then
                        echo "  [PLOT] $CMD_PLOT_HBB"
                        echo "  [PLOT] $CMD_PLOT_HBB_1"
                        eval $CMD_PLOT_HBB
                        eval $CMD_PLOT_HBB_1
                    else
                        echo "  [GEN]  $CMD_GEN_HBB"
                        echo "  [FIT]  $CMD_FIT_HBB"
                        echo "  [PLOT] $CMD_PLOT_HBB"
                        echo "  [PLOT] $CMD_PLOT_HBB_1"
                        
                        if [ ! -z "$RUN_CAT" ]; then
                            eval $CMD_GEN_HBB > combine_gen_${NAME_HBB_FIXED}.log 2>&1
                            if [ $? -eq 0 ]; then
                                eval $CMD_FIT_HBB > combine_fit_${NAME_HBB_FIXED}.log 2>&1
                                if [ $? -eq 0 ]; then eval $CMD_PLOT_HBB; eval $CMD_PLOT_HBB_1; else echo "[ERROR] Fit HBB failed. Skipping plot."; fi
                            else
                                echo "[ERROR] Gen HBB failed. Skipping.";
                            fi
                        fi
                    fi
                fi
            done
        done 
    done
done
