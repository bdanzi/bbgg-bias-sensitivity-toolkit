# Bias Studies Toolkit

Self-contained scripts to run bias studies on a new 1D (`mass` only) or 2D
(`mass` + dijet mass) HH→bbγγ datacard. There are two independent kinds of
bias study, in their own subfolder:

| Folder | Question it answers | README |
|---|---|---|
| [`SculptingStudies/`](SculptingStudies/README.md) | If the real (MC-template) non-resonant background shape isn't exactly what the analytic envelope assumes, does the fit sculpt it and bias the signal strength? | [SculptingStudies/README.md](SculptingStudies/README.md) |
| [`StandardStudies/`](StandardStudies/README.md) | For the discrete-profiling (`RooMultiPdf`) envelope, how much does the fitted signal strength depend on which function generated the toy vs. which function is used to fit it, and how much extra "spurious signal" does letting the envelope float (vs. freezing it) inject? | [StandardStudies/README.md](StandardStudies/README.md) |

Both are driven by a `setup_new_run.sh <datacard.txt> <run_name>` script that
bootstraps a self-contained run directory (matching the convention already
used for the existing `datacard_v6_th10_*` runs) — nothing here depends on a
shared library, so each run directory can be archived/reproduced on its own.

This toolkit is a cleaned-up, documented copy of the scripts originally
developed in `../BiasStudiesWithYuxiangDatacardLateJune/`. That folder (and
its existing `datacard_v6_th10_BiasSculpting` / `datacard_v6_th10_StandardBias`
runs) is left untouched as the historical record; use this toolkit for new
datacards going forward.

## Prerequisites

- A CMSSW/`combine` environment (`cmsenv` in this `CMSSW_14_1_0_pre4` area),
  so that `combine` and `text2workspace.py` are on `PATH`.
- Python with `ROOT`, `awkward` (only needed for `SculptingStudies`, to read
  the MC parquet ntuples), `numpy`, `pandas`, `uproot`, `matplotlib` (needed
  by the `StandardStudies` reporting scripts).
- A full datacard (1D or 2D) for the new analysis, with categories named
  `cat0`, `cat1`, ... and background modeled per-category with a `RooMultiPdf`
  (`pdfindex_*`) envelope, following the same conventions as
  `Datacard_2016-2025_v6_th10_nosyst.txt`.
