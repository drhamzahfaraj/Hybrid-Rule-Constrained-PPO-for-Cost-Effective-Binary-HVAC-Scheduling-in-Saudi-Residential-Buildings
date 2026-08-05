# Figures

## In the paper

All figures in `main.tex` are generated inline with TikZ/pgfplots — climate
comparison, cost-model schedules, optimal single-zone trajectory, multi-zone
Gantt schedule, monthly savings with ±1σ bands, training convergence, and the
cost-model comparison. There are no external image dependencies, so the
manuscript compiles with pdflatex + bibtex alone.

## In this folder

Summary figures regenerated from the published tables by
`../results/plot_results.py`:

| File | Shows |
|---|---|
| `savings_by_config.png` | Monthly saving by zone configuration, both cities |
| `cost_models.png` | Saving under Models L, E and S (4×4) |
| `switching_tradeoff.png` | Cost against switching frequency as c_sw varies |
| `capacity_sensitivity.png` | Saving across the thermal-capacity range (<1 pp) |

Regenerate with:

```bash
python results/plot_results.py
```

These read only `results/tables/*.csv` and need no trained agent.
