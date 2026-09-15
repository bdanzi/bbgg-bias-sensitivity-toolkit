# HH→bbγγ Bias & Sensitivity Studies Toolkit

Self-contained `combine`/`text2workspace.py` scripts to run bias studies and
sensitivity checks on an HH→bbγγ datacard whose per-category background is
modeled with a `RooMultiPdf` discrete-profiling envelope.

## Contents

- **`BiasStudiesToolkit/`** — does the fitted signal strength depend on
  which background function generated the data vs. which one is used to
  fit it? Two independent studies, see
  [`BiasStudiesToolkit/README.md`](BiasStudiesToolkit/README.md):
  - `StandardStudies/` — discrete-profiling (envelope) bias: truth-vs-fit
    function matrices, masked/full-workspace envelope checks, "wrongfit"
    and "dropfunc" (truth function genuinely absent from the envelope)
    variants, and fixed-vs-envelope spurious-signal checks.
  - `SculptingStudies/` — does the analytic envelope sculpt the true
    MC-template non-resonant background shape and bias `r`?
- **`SensitivityChecksToolkit/`** — how sensitive is the expected result to
  a given uncertainty, and what does the profile likelihood scan look like?
  See [`SensitivityChecksToolkit/README.md`](SensitivityChecksToolkit/README.md).

## Prerequisites

A CMSSW/`combine` environment (`cmsenv`) so that `combine` and
`text2workspace.py` are on `PATH`, plus Python with `ROOT`, `numpy`,
`pandas`, `uproot`, `matplotlib` (and `awkward` for `SculptingStudies`'
MC-template builders).

## Quick start

Each study is bootstrapped against your own datacard with its own
`setup_new_run.sh`, which splits the datacard by category and copies in a
self-contained run directory — nothing here depends on a shared library, so
each run directory can be archived/reproduced independently:

```bash
cd BiasStudiesToolkit/StandardStudies
./setup_new_run.sh /path/to/YourDatacard.txt myRunName
cd myRunName
./generate_workspaces_first.sh
```

See each subfolder's own README for the specific studies it runs and how
to interpret the output (`pull_summary.json` + `pull_*.png` Gaussian-fit
pull plots).

## What's intentionally NOT in this repo

Analysis outputs — ROOT workspaces/toys/fits, logs, plots, and any
`setup_new_run.sh`-bootstrapped run directory — are datacard-specific and
regenerable, not code, so they're excluded (see `.gitignore`). Run the
scripts against your own datacard to produce your own outputs.
