# Standard Bias Studies

Four complementary checks of the discrete-profiling (`RooMultiPdf` envelope)
background model. All work on any 1D or 2D datacard whose per-category
background is a `RooMultiPdf` with a `pdfindex_*` discrete nuisance.

1. **Truth-vs-fit function matrix (per-category split datacard)** — for every
   pair of (truth function used to generate toys, function used to fit them)
   in the envelope, and for a few injected `r` values, measure the pull on
   `r`. Reveals which specific function pairings bias the fit. Uses a
   hand-split single-category datacard, which drops any nuisance whose name
   references another category (a known approximation — see caveat below).
2. **Masked envelope bias check (recommended)** — the same idea, but on the
   **full combined workspace** with the other categories switched off via
   `--channel-masks` instead of a split datacard, so every correlated
   systematic stays intact. Supports both "truth vs. fixed fit function"
   (comparable to #1) and, more importantly, **"truth vs. the envelope left
   floating"** — i.e. toys are thrown from one fixed truth function but fit
   exactly like combine would fit real data (envelope profiled, not frozen).
   This second mode is the flashggFinalFit convention and the one that
   actually matches analysis behavior, since real fits never freeze the
   discrete index.
3. **Full-workspace envelope bias check (no masking)** — same question as #2
   ("what if category J's truth function is i, i != 0"), but with every
   *other* category left completely normal: no `--channel-masks`, generation
   only ever perturbs category J's pdfindex (every other category is
   generated at its default index, 0, implicitly — nothing else needs to be
   set), and the envelope for every OTHER category is left floating in the
   fit rather than frozen. Two fit variants, both with the full envelope
   active everywhere except possibly category J:
   - `--fit-mode envelope`: fit with the envelope floating in **every**
     category, including J — the true "fit exactly like real data, only the
     toy's truth in J was function i" check.
   - `--fit-mode wrongfit`: freeze **only** category J's pdfindex to some
     function k != i (looping over every other function in J's envelope),
     while every other category's envelope still floats — tests how bad the
     bias gets if category J's discrete profiling ends up stuck on the wrong
     function while the rest of the fit behaves normally.
   Run over all `i` (every function in J's envelope) x all `J` (every
   category) by looping `--cat` and letting the script's own `TRUTH_FUNCTIONS`
   loop cover every `i` per category.
4. **Fixed-vs-envelope significance / spurious signal** — compare the
   background-only significance distribution when the envelope index is
   frozen to its best fit vs. left floating (profiled). If floating the
   envelope systematically inflates significance (Type-1 error rate) above
   what freezing it or a Gaussian would give, that's the classic "spurious
   signal from discrete profiling" bias.

## Step-by-step (new datacard, 1D or 2D)

```bash
# 0. Bootstrap a run directory (splits the datacard by category automatically)
./setup_new_run.sh /path/to/Datacard_newAnalysis.txt myRunName
cd myRunName

# 1. Build the per-category multipdf workspaces and print the RooMultiPdf map
#    (function name <-> discrete index), needed by parser_legs_matrix.py below.
./generate_workspaces_first.sh
```

### 1. Truth-vs-fit function matrix

`2b_standard_bias_studies_2D_1D_tryFitDiagnostic.sh` loops over all
(truth-function, fit-function, r) combinations for a category, using
`parser_legs_matrix.py` to look up each function's `pdfindex` value in the
workspace built above. Without `--run`, it only *prints* the commands
(dry-run) so you can sanity-check them before actually launching combine.

```bash
# Dry run first (prints the combine commands it would execute):
./2b_standard_bias_studies_2D_1D_tryFitDiagnostic.sh

# Actually run it for one category:
./2b_standard_bias_studies_2D_1D_tryFitDiagnostic.sh --run cat2

# If the category has independent HGG/HBB legs (combined datacards) and you
# only want to scan the HGG leg to save time:
./2b_standard_bias_studies_2D_1D_tryFitDiagnostic.sh --run cat2 --only-hgg
```

Edit the `TRUTH_FUNCTIONS` / `FIT_FUNCTIONS` / `R_TRUTH_VALUES` arrays at the
top of the script to match the function families available in your envelope
and the `r` values you want to scan. Each combination runs
`combine -M GenerateOnly --saveToys`, then `combine -M FitDiagnostics
--toysFile ... --toysFrequentist --robustFit 1`, then plots the pull with
`plot_bias_pull_FitDiagnostics.py` (and the r-only variant
`plot_bias_pull_FitDiagnostics_onlyrfit.py`) into
`./bias_plots_FitDiagnostics_allCombinations/`, appending each result to
`pull_summary.json` in that folder.

Already ran the generation+fit and just want to redo the plots quickly
(e.g. after tweaking a plotting cut)? Use the plotting-only variant instead
of re-running combine:

```bash
./2b_standard_bias_studies_2D_1D_tryFitDiagnostic_onlyplottingoption.sh --run cat2
```

`2b_standard_bias_studies_2D_1D_tryFitDiagnostic_vs_envelope.sh` is the same
matrix but additionally compares against a frozen-envelope fit per
combination — an optional, more expensive cross-check.

To see, per category, how often the envelope chose a non-truth function and
what the residual pull looks like once those "wrong pick" toys are filtered
out:

```bash
python3 analyze_envelope_choice_bias.py \
    -i fitDiagnostics.fit_cat2_both_truth_exp1_fit_bern1_r0.root \
    -v pdfindex_hgg_cat2_13TeV --truth-idx 1 --r-truth 0
```

Once you have enough entries in `pull_summary.json`, build the summary
tables (median pull ± error per truth/fit pair, per category and `r`):

```bash
python3 create_table.py
```

### 2. Masked envelope bias check (recommended)

`run_envelope_bias.sh` runs on the **combined** workspace (not a split
per-category datacard) and uses `--channel-masks` to switch off every
category except the one under study, so all cross-category correlated
nuisances stay exactly as in the real analysis. It supports the same
truth-vs-fixed-fit matrix as script #1 *and* the truth-vs-floating-envelope
check, from one script:

```bash
# Build the combined, channel-masked workspace once:
text2workspace.py Datacard_newAnalysis.txt --channel-masks -m 125 -o Datacard_newAnalysis.root

# Recommended: throw toys from one fixed truth function, fit with the
# envelope left floating (matches what combine does on real data):
./run_envelope_bias.sh --ws Datacard_newAnalysis.root --cat cat2 --fit-mode envelope

# Diagnostic: truth vs. a fixed (possibly different) fit function, same as
# script #1's matrix but on the combined+masked workspace:
./run_envelope_bias.sh --ws Datacard_newAnalysis.root --cat cat2 --fit-mode fixed

# Dry-run by default (prints the combine commands); add --run to execute:
./run_envelope_bias.sh --ws Datacard_newAnalysis.root --cat cat2 --fit-mode envelope --run
```

Under the hood it:
- Discovers `mask_*` parameters in the workspace and sets `mask_cat2=0`
  (active) / all others `=1` (masked out).
- Uses `resolve_pdfindex_legs.py <ws> <cat_number>` to map each envelope
  function name (`exp1`, `bern1`, `bern2`, `pow1`, `lau1`, `lau2`) to its
  `pdfindex` value **for that specific category only** — unlike
  `parser_legs_matrix.py`, which assumes a single-category workspace and can
  mis-associate function indices across categories if reused directly on a
  combined workspace.
- Freezes every *other* category's `pdfindex` (masked channels don't
  contribute to the likelihood, so their discrete index is both irrelevant
  and, left floating, a source of minimizer instability) and, on the fit
  step, adds the same `--X-rtd MINIMIZER_*` stability flags used by
  `RunBiasInSignificance.py` below.
- Reuses `plot_bias_pull_FitDiagnostics.py` for plotting, writing to
  `./bias_plots_masked_<cat>_<fit-mode>/`.

`--ntoys`, `--seed`, `--rmin`/`--rmax` and `--only-hgg` (for categories with
both an HGG and HBB leg) are all overridable flags — see `--help`.

### 3. Full-workspace envelope bias check (no masking)

```bash
# Build the combined workspace once -- plain, NO --channel-masks needed:
text2workspace.py Datacard_newAnalysis.txt -m 125 -o Datacard_newAnalysis.root

# Fit with the full envelope floating everywhere (recommended: matches real data):
./run_full_envelope_bias.sh --ws Datacard_newAnalysis.root --cat cat2 --fit-mode envelope

# Freeze ONLY cat2 to a wrong function (k != truth i), envelope floats elsewhere:
./run_full_envelope_bias.sh --ws Datacard_newAnalysis.root --cat cat2 --fit-mode wrongfit

# Dry-run by default (prints the combine commands); add --run to execute:
./run_full_envelope_bias.sh --ws Datacard_newAnalysis.root --cat cat2 --fit-mode envelope --run
```

Under the hood, for every truth function `i` present in cat2's envelope
(discovered via `resolve_pdfindex_legs.py`, same as `run_envelope_bias.sh`):
- **Generation** (identical in both fit modes): `--setParameters` sets ONLY
  cat2's pdfindex to `i`; `--freezeParameters` freezes it there, plus every
  other category's pdfindex with no explicit value (so they stay at the
  workspace default, index 0). No `--channel-masks`, no `mask_*` parameters
  at all — every category's data goes into the toy exactly as it would for
  a real combined dataset.
- **Fit, `--fit-mode envelope`**: only `MH` is frozen. Every category's
  pdfindex (including cat2's) is left floating, so combine discrete-profiles
  the envelope everywhere, exactly like it would on real data.
- **Fit, `--fit-mode wrongfit`**: `MH` plus cat2's pdfindex are frozen, set
  to some function `k != i` (loops over every other function in cat2's
  envelope); every other category's pdfindex is still left floating.

Because the envelope floats in every *other* category in both modes here
(unlike `run_envelope_bias.sh`, which freezes them since they're masked
out), this is a much bigger discrete-combinatorial fit if you have several
multi-function categories — expect it to run slower. The `--X-rtd
MINIMIZER_*` stability flags are therefore ON by default (they were
deliberately left off in `run_envelope_bias.sh` only because they crash
`--channel-masks` + `FitDiagnostics` specifically, per that script's
comments — that combination doesn't apply here). Use
`--no-stability-flags` if you run into trouble.

Reuses `plot_bias_pull_FitDiagnostics.py` for plotting, writing to
`./bias_plots_full_<cat>_<fit-mode>/`. Same `--ntoys`, `--seed`,
`--rmin`/`--rmax`, `--only-hgg` flags as `run_envelope_bias.sh` — see
`--help`.

### 4. Fixed-vs-envelope significance (spurious signal)

`RunBiasInSignificance.py` runs the classic combine discrete-profiling bias
recipe against the **full/combined workspace** (`text2workspace.py` output
for the whole datacard, not a single category):

```bash
text2workspace.py Datacard_newAnalysis.txt -o Datacard.root -m 125

python3 RunBiasInSignificance.py --inputWSFile Datacard.root --mode setup \
    --initial-fit-param <low_impact_nuisance_name>
python3 RunBiasInSignificance.py --inputWSFile Datacard.root --mode generate --nToys 2000
python3 RunBiasInSignificance.py --inputWSFile Datacard.root --mode fixed    --nToys 2000
python3 RunBiasInSignificance.py --inputWSFile Datacard.root --mode envelope --nToys 2000

python3 SummaryBiasSignificance.py
```

`--initial-fit-param` must name any single low-impact nuisance already in the
datacard (e.g. a luminosity term) — combine needs at least one floating
parameter to seed the initial fit. `SummaryBiasSignificance.py` writes
`plots/summary_significance.{png,pdf}`: the Type-1 error rate vs. Z-score for
`fixed` vs `envelope` vs the Gaussian expectation. Envelope tracking above the
`fixed`/Gaussian curves by more than ~10-20% indicates the discrete profiling
is inflating significance (i.e. injecting bias / look-elsewhere-like effect).

### 5. Follow-up checks used for the v7 final results

These scripts were added for the v7 final datacard
(`v7_SnTV7F1E500T0821thTest_resample_DDonly_min`) and assume its category
layout (cat0 boosted with a single fixed function, cat1-4 with a
`RooMultiPdf` envelope). Run them from the bootstrapped run directory.

- **cat0 fixed model.** `run_cat0_fixedmodel_bias.sh` /
  `run_cat0_fixedmodel_bias_default0.sh` test truth = exp1/pow1;
  `run_cat0_fixedmodel_bias_extra.sh` / `run_cat0_fixedmodel_bias_default0_extra.sh`
  add the missing truth = bern1/lau1 and append to the same
  `pull_summary.json`. Other categories are frozen to their best-fit index
  (`bestfit`) or to index 0 (`default0`). Summary plots:
  `plot_mean_sigma_vs_pdfindex_cat0_bestfit.py`,
  `plot_mean_sigma_vs_pdfindex_cat0_default0.py`.
- **dropfunc summaries.** `plot_mean_sigma_vs_pdfindex_dropfunc.py` and
  `plot_mean_sigma_vs_pdfindex_dropfunc_bestfit.py` now include cat0 (read
  from the cat0 fixed-model `pull_summary.json`) as the first panel when it
  exists. The `_bestfit` variant reads the published `pull_summary.json`
  files under `~/public_html`.
- **cat1 checks.** `run_cat1_standalone_check.sh` (cat1 workspace alone),
  `run_cat1_altws_gen_nofreezeothers.sh` + `run_cat1_altws_nofreezeothers.sh`
  (alternative workspace, other categories not frozen; set `ALTWS=` to point
  to it) and the pull summaries `make_pull_summary_cat1_envelope.py` /
  `make_pull_summary_cat1_reproducibility_check.py` (pull =
  (r - r_inj) / ((|rLoErr| + |rHiErr|) / 2), fixed Gaussian range [-2, 2]).

`plot_bias_pull_FitDiagnostics.py` draws the fitted Gaussian on a clone over
the full window (the previous version clipped the curve at the core-fit
range) and, for r_truth != 0, reuses the core-fit window of the r_truth = 0
plot of the same truth/fit combination (cached in
`<outdir>/.core_range_cache.json`), so plots at different injected r are
directly comparable. Run the r = 0 case first.

### 6. Final summary (dropfunc + cat0 fixed model)

This is how the v7 final summary
(`~/public_html/BiasSensitivityStudies_v7_final_summary_rMin-5rMax5_1000toys/StandardStudies_summary/`)
was produced. Everything runs from the bootstrapped run directory, on the
combined workspace **without channel masks**: one category J is perturbed at a
time, the fit uses all categories, so `r` is the combined signal strength.

```bash
# 0. Combined workspace + best-fit pdfindex of every category on data
#    (writes higgsCombine_initial.MultiDimFit.mH125.root, then cached by
#    get_bestfit_pdfindices.py into bestfit_pdfindices.sh on first use).
text2workspace.py Datacard.txt -m 125 -o Datacard.root
python3 RunBiasInSignificance.py --inputWSFile Datacard.root --mode setup \
    --initial-fit-param <low_impact_nuisance_name>

# 1. dropfunc, cat1-4: truth function i generated in cat J, then REMOVED from
#    the RooMultiPdf of cat J before the fit (truth not in the envelope).
#    Other categories: set + frozen to their data best-fit index.
#    Defaults: 1000 toys, r_truth = 0,2, rMin/rMax = -5/5. Dry run without --run.
for c in cat1 cat2 cat3 cat4; do
    ./run_dropfunc_envelope_bias.sh --ws Datacard.root --datacard Datacard.txt \
        --cat $c --run --parallel --publish
done
#    -> bias_plots_dropfunc_<cat>/pull_summary.json + pull_*.png

# 2. cat0 (single fixed function, nothing to drop): toys from its standard
#    4-function envelope, fit with cat0 fixed (see section 5).
./run_cat0_fixedmodel_bias.sh          && ./run_cat0_fixedmodel_bias_extra.sh
./run_cat0_fixedmodel_bias_default0.sh && ./run_cat0_fixedmodel_bias_default0_extra.sh

# 3. Summary plots: pull mean/sigma vs truth pdfindex, cat0 first, then cat1-4.
python3 plot_mean_sigma_vs_pdfindex_dropfunc_bestfit.py   # reads the published dropfunc/cat0 pull_summary.json
python3 plot_mean_sigma_vs_pdfindex_dropfunc.py           # reads local bias_plots_dropfunc_cat*/ (default0 runs)
python3 plot_mean_sigma_vs_pdfindex_cat0_bestfit.py
python3 plot_mean_sigma_vs_pdfindex_cat0_default0.py
```

Notes:
- The `default0` dropfunc results (other categories at pdfindex 0, published
  in `..._dropfunc_cat*_default0_...`) come from an earlier pass of
  `run_dropfunc_envelope_bias.sh`; the current script always freezes the
  other categories to their best-fit index.
- The AN table `bias_tests_dropfunc_cat0.tex` in the summary page was written
  by hand from the `pull_summary.json` files; no script in this repo produces
  it (`create_table.py` makes the truth-vs-fit matrix table of section 1).
- Still open: `run_cat0_wrongfit_bias*.sh` (truth = cat0 fixed function, fit
  forced on a wrong one) was never completed or published.
