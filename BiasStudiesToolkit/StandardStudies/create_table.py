import json
import matplotlib.pyplot as plt

# 1. Load the full JSON summary file
with open('./bias_plots_FitDiagnostics_allCombinations/pull_summary.json', 'r') as f:
    data = json.load(f)

# 2. Group the data dynamically by Category -> r_truth -> truth_func -> fit_func
structured = {}
all_funcs = set()

for entry in data:
    cat = entry["category"]
    r_val = entry["r_truth"]
    t_func = entry["truth_func"]
    f_func = entry["fit_func"]
    
    # Collect all unique function names to build consistent table matrices
    all_funcs.add(t_func)
    all_funcs.add(f_func)
    
    # Initialize dictionary nesting levels if they do not exist
    if cat not in structured:
        structured[cat] = {}
    if r_val not in structured[cat]:
        structured[cat][r_val] = {}
    if t_func not in structured[cat][r_val]:
        structured[cat][r_val][t_func] = {}
        
    # Extract results and format them as "median_pull ± error_median_pull"
    med = entry.get("median_pull", None)
    err = entry.get("error_median_pull", None)
    if med is not None and err is not None:
        structured[cat][r_val][t_func][f_func] = f"{med:.2f} ± {err:.2f}"
    else:
        structured[cat][r_val][t_func][f_func] = "-"

# Sort functions to ensure rows and columns are always in the same order
sorted_funcs = sorted(list(all_funcs))

# 3. Generate a separate PNG image for each category and r_truth combination
for cat, r_dict in structured.items():
    for r_val, t_dict in r_dict.items():
        #cell_text = []
        #columns = ["Truth \\ Fit"] + sorted_funcs
        # Populate rows corresponding to each truth function
        #for t_func in sorted_funcs:
        #    row = [t_func]
        #    for f_func in sorted_funcs:
        #        row.append(t_dict.get(t_func, {}).get(f_func, "-"))
        #    cell_text.append(row)
        # Keep only functions with a value different than -
        active_truth = []
        active_fit = []
        # Keep truth functions
        for t_func in sorted_funcs:
            if any(t_dict.get(t_func, {}).get(f_func, "-") != "-" for f_func in sorted_funcs):
                active_truth.append(t_func)
        for f_func in sorted_funcs:
            if any(t_dict.get(t_func, {}).get(f_func, "-") != "-" for t_func in sorted_funcs):
                active_fit.append(f_func)
        columns = ["Truth \\ Fit"] + active_fit
        cell_text = []
        for t_func in active_truth:
            row = [t_func]
            for f_func in active_fit:
                row.append(t_dict.get(t_func, {}).get(f_func, "-"))
            cell_text.append(row)
        # Create a new matplotlib figure for the table plot
        fig, ax = plt.subplots(figsize=(6, 2.5), dpi=300)
        ax.axis('off')  # Hide the default plot axes
        
        # Draw the table on the empty plot axis
        table = ax.table(
            cellText=cell_text,
            colLabels=columns,
            loc='center',
            cellLoc='center'
        )
        
        # Adjust table font size and scale cells for clean spacing
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.6)
        
        # Style headers (first row and first column) and borders
        for (row, col), cell in table.get_celld().items():
            if row == 0 or col == 0:
                cell.set_text_props(weight='bold', color='#1a365d')
                cell.set_facecolor('#f7fafc')
            cell.set_edgecolor('#cbd5e0')
            
        # Set an informative title above the table matrix
        plt.title(f"Category: {cat} | r_truth = {r_val}", fontsize=11, weight='bold', color='#2b6cb0', pad=10)
        
        # Sanitize r_truth formatting for safe file naming (e.g., 2.0 -> 2_0)
        r_str = str(r_val).replace('.', '_')
        filename = f"median_results_{r_str}_{cat}.png"
        
        # Save the layout as a high-resolution PNG image
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close()
        print(f"Generated file: {filename}")
