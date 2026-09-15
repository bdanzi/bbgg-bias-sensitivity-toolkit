# Sensitivity Checks Toolkit

Self-contained scripts to check how sensitive the expected result of a
datacard is to specific inputs (a background's acceptance uncertainty, its
normalization/rate, a likelihood scan, a final summary of expected limits).
Each independent kind of check lives in its own subfolder:

| Folder | Question it answers | README |
|---|---|---|
| [`UncertaintyImpactStudies/`](UncertaintyImpactStudies/README.md) | How much does the expected upper limit (or significance) change if a given process's acceptance uncertainty (lnN) or normalization (rate) is scanned, per category and globally? Which process/category combination matters most? | [UncertaintyImpactStudies/README.md](UncertaintyImpactStudies/README.md) |
| [`LikelihoodScan/`](LikelihoodScan/README.md) | What does the 1D profile likelihood (deltaNLL) vs the signal strength look like - is the minimum well-constrained, and where do the 1/2-sigma crossings fall? | [LikelihoodScan/README.md](LikelihoodScan/README.md) |
| [`SummaryPlot/`](SummaryPlot/README.md) | Plot a final Brazil-band-style summary of expected upper limits across a set of channels (e.g. per-category-group vs combined). | [SummaryPlot/README.md](SummaryPlot/README.md) |

`UncertaintyImpactStudies` and `LikelihoodScan` are driven by a
`setup_new_run.sh <datacard.txt> <run_name>` script that bootstraps a
self-contained run directory, matching the convention used by
`../BiasStudiesToolkit/`. `SummaryPlot` is a plain plotting utility (no
datacard/combine involved - see its README).

This toolkit is a cleaned-up, documented, generalized rewrite of the scripts
originally developed in `../SensitivityChecks/` (`UncertaintiesStudy.py`,
`UncertaintiesStudySignificance.py`, `UncertaintiesStudy_rate.py`,
`checkdeltaNLL.py`, `make_ULResult.py`, `make_againn.py`). That folder (and
its existing `card_*`/`higgsCombine_*` outputs) is left untouched as the
historical record; use this toolkit for new datacards going forward.

**What changed vs the original scripts**, and why:
- The three near-duplicate `UncertaintiesStudy*.py` files (lnN-vs-AsymptoticLimits,
  lnN-vs-Significance, rate-vs-AsymptoticLimits) are now one
  `run_uncertainty_scan.py` with `--mode {lnN,rate}` and `--metric {limit,significance}`.
- The hardcoded `BKG_PROCESSES = ["ggh_mass", "tth_mass", "vbf_mass", "vh_mass", "bkg_mass"]`
  (exact process names from one specific analysis's datacard) is now
  **auto-discovered** from the datacard's own `process` line (every process
  name not containing `"HH"`, i.e. every non-signal process) - see
  `UncertaintyImpactStudies/README.md` for why this generalizes cleanly.
- All scan scripts are dry-run by default (print the planned combine-call
  matrix; `--run` to actually execute), matching `BiasStudiesToolkit`'s
  convention, since even fast Asimov (`-t -1`) fits add up across a full
  category x process x scan-point matrix.
- `make_ULResult.py`/`make_againn.py` (identical plotting code, two different
  hardcoded input JSON filenames) are merged into one `plot_summary_bands.py`
  with `--input`/`--output` args.

## Prerequisites

- A CMSSW/`combine` environment (`cmsenv` in this `CMSSW_14_1_0_pre4` area),
  so that `combine` and `text2workspace.py` are on `PATH`.
- Python with `ROOT`, `numpy`, `matplotlib` (all studies); `mplhep` is
  optional for `SummaryPlot` (falls back gracefully without the CMS style).
- A full (not per-category-split) datacard (1D or 2D), background modeled
  per-category with a `RooMultiPdf` (`pdfindex_*`) envelope, following the
  conventions used by `../BiasStudiesToolkit/`.
