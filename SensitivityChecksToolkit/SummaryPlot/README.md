# Summary Plot

**Question:** what's the final, presentation-ready summary of expected upper
limits (mu=0 and mu=1 expectations, +/-1/2-sigma bands) across a chosen set
of channels (e.g. per-category-group vs combined)?

This is a **plotting-only utility** - it does not run combine and does not
compute anything. It reads a small hand-curated JSON of already-computed
numbers and draws the Brazil-band-style horizontal summary plot used in the
original `make_ULResult.py`/`make_againn.py` (which were the same plotting
code duplicated across two hardcoded input filenames).

**Deciding which combine runs map to which "channel" in the JSON is a
physics/bookkeeping choice specific to each analysis** (e.g. which
categories count as "Boosted" vs "Resolved", or whether to show a
per-category breakdown instead) - this toolkit does not automate that
grouping. Fill in the JSON yourself from your `AsymptoticLimits` results
(the `--metric limit` runs from `../UncertaintyImpactStudies/`, or a plain
`combine -M AsymptoticLimits` per channel, give you the `mu0` median/+-1/2sigma
numbers directly from the `limit` tree; the `mu1` block needs the same run
with `--expectSignal 1` injected, e.g. via `-t -1 --expectSignal 1` Asimov).

## Usage

```json
{
  "channels": [
    {"name": "Resolved",
     "mu0": {"minus2sigma": 4.3, "minus1sigma": 6.5, "median": 11.0, "plus1sigma": 19.8, "plus2sigma": 33.3},
     "mu1": {"minus2sigma": 4.5, "minus1sigma": 7.0, "median": 12.3, "plus1sigma": 22.2, "plus2sigma": 37.3}},
    {"name": "Combined",
     "mu0": {"minus2sigma": 1.1, "minus1sigma": 1.5, "median": 2.3, "plus1sigma": 3.7, "plus2sigma": 5.9},
     "mu1": {"minus2sigma": 1.5, "minus1sigma": 2.2, "median": 3.5, "plus1sigma": 5.6, "plus2sigma": 8.6}}
  ]
}
```

```bash
python3 plot_summary_bands.py -i my_results.json -o summary.pdf \
    --title 'HH $\to$ bb$\gamma\gamma$, 1D fit' --lumi '138/283' --com '13/13.6'
```

`mplhep` is optional (used for the CMS plot style/label); without it the
plot is still produced, just without the CMS-style header.
