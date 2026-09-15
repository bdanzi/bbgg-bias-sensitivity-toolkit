#!/bin/bash

# Inline help function
show_help() {
    echo "Usage: ./run_bias_matrix_envelope.sh [options]"
    echo ""
    echo "Options:"
    echo "  --run catX        Physically execute fits and plots for the specified category (e.g., cat0, cat1, ...)"
    echo "  --only-hgg        Ignore HBB presence and run fewer combinations (HGG only)"
    echo "  --help            Show this help message"
    echo ""
    echo "If launched without --run, the script will run in DRY-RUN mode, only printing the commands."
    exit 0
}

# Parse input arguments
RUN_CAT=""
ONLY_HGG=false
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
        *)
            echo "[ERROR] Unknown option: $1"
            show_help
            ;;
    esac
done

# =========================================================================
# Verità (Iniezione): Generiamo i toy usando queste singole forme
# =========================================================================
TRUTH_FUNCTIONS=("exp1" "bern1" "bern2" "pow1" "lau1" "lau2")
R_TRUTH_VALUES=(1 0 3)

# Array of all categories to process by default
CATEGORIES=(0 1 2 3 4)

if [ ! -z "$RUN_CAT" ]; then
    CAT_NUM=$(echo "$RUN_CAT" | sed 's/cat//')
    CATEGORIES=($CAT_NUM)
    echo "RUN MODE ENABLED: Commands will be executed for cat${CAT_NUM}."
else
    echo "DRY-RUN MODE: Only printing commands. Use --run catX to run them."
fi

if [ "$ONLY_HGG" = true ]; then
    echo "HGG-ONLY MODE ENABLED: HBB channel will be ignored."
fi

# Main category loop
for c in "${CATEGORIES[@]}"; do
    ws="workspace_multipdf_cat${c}.root"
    
    if [ ! -z "$RUN_CAT" ] && [ ! -f "$ws" ]; then
        echo "[WARNING] Workspace $ws not found in the current directory. Skipping category cat${c}."
        continue 
    fi

    echo ""
    echo "========================================================================="
    echo " ENVELOPE BIAS MATRIX FOR CATEGORY: cat${c}"
    echo "========================================================================="
    
    if [ -f "$ws" ]; then
        eval $(python3 parser_legs_matrix.py "$ws" 2>/dev/null)
    fi

    # Determine multi-leg presence
    HAS_HGG=false; HAS_HBB=false
    if [ ! -z "$HGG_VAR" ]; then HAS_HGG=true; fi
    if [ ! -z "$HBB_VAR" ] && [ "$ONLY_HGG" = false ]; then HAS_HBB=true; fi

    # 1. Loop through injected Truth forms
    for t_func in "${TRUTH_FUNCTIONS[@]}"; do
        # 2. Loop through Signal Strengths (r=1 and r=0)
        for r_truth in "${R_TRUTH_VALUES[@]}"; do

            # --- CONFIGURATION 1: FIT WITH FULL ENVELOPE (Index FLOATS during fit) ---
            
            # Per la Generazione congeliamo l'indice sulla verità
            FREEZE_GEN="MH"
            SET_GEN_BOTH=""
            
            # Per il Fit NON congeliamo l'indice del multipdf (lasciamo l'envelope libero)
            FREEZE_FIT_ENVELOPE="MH"
            
            if [ "$HAS_HGG" = true ]; then
                idx_gen="IDX_${HGG_VAR}_${t_func}"
                if [ -z "${!idx_gen}" ]; then continue; fi
                FREEZE_GEN="${FREEZE_GEN},${HGG_VAR}"
                SET_GEN_BOTH="${!idx_gen}"
            fi

            if [ "$HAS_HBB" = true ]; then
                idx_gen="IDX_${HBB_VAR}_${t_func}"
                if [ -z "${!idx_gen}" ]; then continue; fi
                FREEZE_GEN="${FREEZE_GEN},${HBB_VAR}"
                [ -z "$SET_GEN_BOTH" ] && SET_GEN_BOTH="${!idx_gen}" || SET_GEN_BOTH="${SET_GEN_BOTH},${!idx_gen}"
            fi

            # Gestione fallback per cat0 split files layout (mantenuta dal tuo script)
            WS_GEN_CMD="$ws"
            WS_FIT_CMD="$ws"
            if [ -z "$SET_GEN_BOTH" ] && [ "$c" -eq 0 ]; then
                FILE_GEN="CMS-HGG_multipdf_cat0_new_exponential.root"
                if [[ "$t_func" == *"bern"* ]] || [[ "$t_func" == *"pow"* ]]; then FILE_GEN="CMS-HGG_multipdf_cat0_new_linear.root"; fi
                if [ ! -z "$RUN_CAT" ]; then
                    sed "s/CMS-HGG_multipdf_cat0.root/${FILE_GEN}/g" datacard_cat0.txt > datacard_cat0_truth_${t_func}.txt
                    text2workspace.py datacard_cat0_truth_${t_func}.txt -o ws_truth_${t_func}_cat0.root -m 125 &>/dev/null || continue
                fi
                WS_GEN_CMD="ws_truth_${t_func}_cat0.root"
                # Il fit usa il file standard per avere tutto l'envelope
                WS_FIT_CMD="$ws" 
            fi

            LABEL_MODE="ENVELOPE FIT"
            if [ "$ONLY_HGG" = true ] || [ "$HAS_HBB" = false ]; then LABEL_MODE="ENVELOPE FIT (ONLY HGG ACTIVE)"; fi
            
            NAME_BOTH="cat${c}_truth_${t_func}_fit_ENVELOPE_r${r_truth}"

            echo "-------------------------------------------------------------------------"
            echo " PAIRING [${LABEL_MODE}]: Truth [${t_func^^}] vs Fit [ENVELOPE] | r=${r_truth}"
            echo "-------------------------------------------------------------------------"

            # Generazione: Congela l'indice sulla funzione t_func
            CMD_GEN="combine -M GenerateOnly $WS_GEN_CMD -m 125 -t 1000 -s 123456 -n .gen_${NAME_BOTH} --expectSignal ${r_truth} ${SET_GEN_BOTH:+--setParameters ${SET_GEN_BOTH}} --freezeParameters ${FREEZE_GEN} --cminDefaultMinimizerStrategy 0 --rMin -10 --rMax 10 --saveToys"
            
            # Fit: L'indice della funzione (HGG_VAR / HBB_VAR) NON è in freezeParameters, quindi fluttua nell'envelope
            CMD_FIT="combine -M FitDiagnostics $WS_FIT_CMD -m 125 -t 1000 -s 123456 -n .fit_${NAME_BOTH} --expectSignal ${r_truth} --toysFile higgsCombine.gen_${NAME_BOTH}.GenerateOnly.mH125.123456.root --freezeParameters ${FREEZE_FIT_ENVELOPE} --cminDefaultMinimizerStrategy 0 --robustFit 1 --rMin -10 --rMax 10"
            
            CMD_PLOT="python3 plot_bias_pull_FitDiagnostics.py -i fitDiagnostics.fit_cat${c}_truth_${t_func}_fit_ENVELOPE_r${r_truth}.root --r-truth ${r_truth} --truth-func ${t_func} --fit-func envelope --cat cat${c}_envelope_r${r_truth} -o ./bias_plots_FitDiagnostics"
            CMD_PLOT_1="python3 plot_bias_pull_FitDiagnostics_onlyrfit.py -i fitDiagnostics.fit_cat${c}_truth_${t_func}_fit_ENVELOPE_r${r_truth}.root --r-truth ${r_truth} --truth-func ${t_func} --fit-func envelope --cat cat${c}_envelope_r${r_truth} -o ./bias_plots_FitDiagnostics"

            echo "  [GEN]  $CMD_GEN"
            echo "  [FIT]  $CMD_FIT"
            echo "  [PLOT] $CMD_PLOT"
            echo "  [PLOT] $CMD_PLOT_1"

            if [ ! -z "$RUN_CAT" ]; then
                eval $CMD_GEN > combine_gen_${NAME_BOTH}.log 2>&1
                if [ $? -ne 0 ]; then 
                    echo "[ERROR] Generation failed for ${NAME_BOTH}. Skipping."; 
                    continue; 
                fi
                eval $CMD_FIT > combine_fit_${NAME_BOTH}.log 2>&1
                if [ $? -ne 0 ]; then 
                    echo "[ERROR] Fit failed for ${NAME_BOTH}. Skipping plot."; 
                fi
                mkdir -p bias_plots_FitDiagnostics
                eval $CMD_PLOT
                eval $CMD_PLOT_1
            fi

            # --- CONFIGURATIONS 2 & 3: ENVELOPE PARZIALE (Se presenti entrambe le leg) ---
            # Se vuoi studiare l'impatto lasciando l'envelope su una sola leg e congelando l'altra
            if [ "$HAS_HGG" = true ] && [ "$HAS_HBB" = true ]; then
                
                # --- HGG ENVELOPE (HBB FIXED sulla Verità) ---
                FREEZE_HBB_FIXED="MH,${HBB_VAR}" # HGG_VAR è libero -> fa envelope
                idx_gen_hbb="IDX_${HBB_VAR}_${t_func}"
                idx_gen_hgg="IDX_${HGG_VAR}_${t_func}"
                
                NAME_HGG_ENV="cat${c}_hggEnvelope_hbbFixed_truth_${t_func}_r${r_truth}"
                echo "-------------------------------------------------------------------------"
                echo " PAIRING [HGG ENVELOPE, HBB FIXED]: Truth [${t_func^^}] vs HGG Envelope | r=${r_truth}"
                echo "-------------------------------------------------------------------------"
                
                CMD_GEN_HGG="combine -M GenerateOnly $ws -m 125 -t 1000 -s 123456 -n .gen_${NAME_HGG_ENV} --expectSignal ${r_truth} --setParameters ${!idx_gen_hgg},${!idx_gen_hbb} --freezeParameters MH,${HGG_VAR},${HBB_VAR} --cminDefaultMinimizerStrategy 0 --rMin -10 --rMax 10 --saveToys"
                CMD_FIT_HGG="combine -M FitDiagnostics $ws -m 125 -t 1000 -s 123456 -n .fit_${NAME_HGG_ENV} --expectSignal ${r_truth} --toysFile higgsCombine.gen_${NAME_HGG_ENV}.GenerateOnly.mH125.123456.root --setParameters ${!idx_gen_hbb} --freezeParameters ${FREEZE_HBB_FIXED} --cminDefaultMinimizerStrategy 0 --robustFit 1 --rMin -10 --rMax 10"
                
                echo "  [GEN]  $CMD_GEN_HGG"
                echo "  [FIT]  $CMD_FIT_HGG"
                if [ ! -z "$RUN_CAT" ]; then
                    eval $CMD_GEN_HGG > combine_gen_${NAME_HGG_ENV}.log 2>&1
                    if [ $? -eq 0 ]; then
                        eval $CMD_FIT_HGG > combine_fit_${NAME_HGG_ENV}.log 2>&1
                    fi
                fi

                # --- HBB ENVELOPE (HGG FIXED sulla Verità) ---
                FREEZE_HGG_FIXED="MH,${HGG_VAR}" # HBB_VAR è libero -> fa envelope
                NAME_HBB_ENV="cat${c}_hbbEnvelope_hggFixed_truth_${t_func}_r${r_truth}"
                echo "-------------------------------------------------------------------------"
                echo " PAIRING [HBB ENVELOPE, HGG FIXED]: Truth [${t_func^^}] vs HBB Envelope | r=${r_truth}"
                echo "-------------------------------------------------------------------------"
                
                CMD_GEN_HBB="combine -M GenerateOnly $ws -m 125 -t 1000 -s 123456 -n .gen_${NAME_HBB_ENV} --expectSignal ${r_truth} --setParameters ${!idx_gen_hgg},${!idx_gen_hbb} --freezeParameters MH,${HGG_VAR},${HBB_VAR} --cminDefaultMinimizerStrategy 0 --rMin -10 --rMax 10 --saveToys"
                CMD_FIT_HBB="combine -M FitDiagnostics $ws -m 125 -t 1000 -s 123456 -n .fit_${NAME_HBB_ENV} --expectSignal ${r_truth} --toysFile higgsCombine.gen_${NAME_HBB_ENV}.GenerateOnly.mH125.123456.root --setParameters ${!idx_gen_hgg} --freezeParameters ${FREEZE_HGG_FIXED} --cminDefaultMinimizerStrategy 0 --robustFit 1 --rMin -10 --rMax 10"
                
                echo "  [GEN]  $CMD_GEN_HBB"
                echo "  [FIT]  $CMD_FIT_HBB"
                if [ ! -z "$RUN_CAT" ]; then
                    eval $CMD_GEN_HBB > combine_gen_${NAME_HBB_ENV}.log 2>&1
                    if [ $? -eq 0 ]; then
                        eval $CMD_FIT_HBB > combine_fit_${NAME_HBB_ENV}.log 2>&1
                    fi
                fi
            fi
        done
    done 
done
