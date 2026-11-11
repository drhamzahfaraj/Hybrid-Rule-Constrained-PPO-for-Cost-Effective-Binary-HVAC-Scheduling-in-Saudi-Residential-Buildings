# Rule-Constrained PPO for Binary HVAC Scheduling in Saudi Residential Buildings

*Cost Savings, Their Governing Parameters, and an Optimality Bracket*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-green.svg)](https://www.python.org/)

**Journal:** Journal of King Saud University – Engineering Sciences (JKSU-ES), under revision.

**Author:** Hamzah Faraj, Department of Science and Technology, Ranyah College,
Taif University, Taif 21944, Saudi Arabia — [email removed]

> **Repository renamed?** This repository's URL still carries the paper's
> earlier title. The paper was retitled during revision; the content here is the
> revised study.

## What this repository is for

Every number in the paper can be traced, re-derived and challenged from here.

- **[`VALUES_REGISTRY.md`](VALUES_REGISTRY.md)** — start here. Every reported
  value, the manuscript location it appears in, the result file it is read
  from, the script that produced that file, and the check that pins it. The
  registry is *generated from the result files*, so it cannot disagree with
  the data. It also has a "reviewer question → where to look" table and a
  catalogue marking every result file as CURRENT or SUPERSEDED.
- **`code/`** — the code of record. All scripts use repository-relative paths.
- **`code/results/`** — every result file (CSV/JSON) the paper draws on.
- **`code/amy/`** — 45 actual meteorological years (2009–2023, three cities,
  ERA5 reanalysis) used for the inter-annual spread study.
- **`paper/`** — LaTeX source and compiled PDF of the current manuscript.
  `paper/repository-figures/` holds the figures the paper references here
  rather than printing (the admissibility sweeps and the guard-band diagram).
- **`archive/withdrawn-pipeline/`** — the earlier pipeline, kept for the
  record and **not** the source of any current figure. Its README lists what
  was withdrawn.

## What the paper finds, in one paragraph

On a code-compliant single zone at the tariff in force, a well-tuned
two-threshold thermostat rule is the controller to beat. It saves about 9 % in
Riyadh and Jeddah and about 5 % in Taif against a 1 K-deadband thermostat at a
matched mean occupied temperature, significant on seven paired held-out weeks.
The saving is almost entirely avoided compressor starts, not energy. The PPO
agent under hard comfort rules reproduces the rules' own hysteresis exactly in
nine of ten runs and adds nothing, for a reason the paper proves. A
receding-horizon controller with a perfect day-ahead forecast does not beat the
tuned rule; lookahead begins to pay only at the scale of the plant's ~56 h time
constant. A clairvoyant schedule and a grid-converged Lagrangian bound bracket
what any mean-matched schedule could achieve. The result's sign depends on the
installed thermostats' deadband, which only field measurement can settle. The
exact figures are in `VALUES_REGISTRY.md`.

## Verify everything

```bash
pip install -r requirements.txt
cd code
python3 invariants.py         # gate: 100+ invariants; exits non-zero on any failure
python3 verify_numbers.py     # re-derives every printed figure from its result file
python3 verify_optimality.py  # backward check of the clairvoyant schedule
python3 build_registry.py     # regenerates ../VALUES_REGISTRY.md
```

The gate and the re-derivation both run in minutes on a laptop CPU; no GPU is
needed. Re-running the studies themselves (PPO training, MPC sweeps, dynamic
programmes) takes hours; the generator of each result file is named in the
registry.

## Model

Single-zone first-order RC thermal model with exact zero-order-hold
(matrix-exponential) integration, Δt = 15 min, C_th = 4,800 kJ/K, SBC 2018
prescriptive envelope, per-city infiltration, south-facing plane-of-array
solar from SRC-TMYx 2009–2023 weather (WMO 404380 Riyadh, 410240 Jeddah,
410360 Taif). The model is an **uncalibrated reference model** in the sense of
ASHRAE Guideline 14: no measured data exist for this dwelling, so every claim
is a relative comparison between controllers on one common model at a matched
mean occupied temperature.

## Data

- Weather (headline): `code/riyadh.epw`, `code/jeddah.epw`, `code/taif.epw`,
  from climate.onebuilding.org (SRC-TMYx).
- Weather (spread study): `code/amy/{city}_{year}.csv`, ERA5 reanalysis via the
  Open-Meteo archive API; fetched by `code/amy_fetch.py` / `amy_retry.py`.
  Used for inter-annual spread only.

## Citation

See [`CITATION.cff`](CITATION.cff). The multi-zone and inter-zone coupling
results for this setting are in Faraj (2026), *JKSU-ES* 38:58,
doi:10.1007/s44444-026-00131-0.

## License

MIT — see [`LICENSE`](LICENSE).
