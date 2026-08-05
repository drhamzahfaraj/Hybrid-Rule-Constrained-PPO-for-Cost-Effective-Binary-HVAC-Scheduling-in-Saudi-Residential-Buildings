# Hybrid Rule-Constrained PPO for Cost-Effective Binary HVAC Scheduling in Saudi Residential Buildings

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-green.svg)](https://www.python.org/)
[![PyTorch 2.1](https://img.shields.io/badge/PyTorch-2.1.0-orange.svg)](https://pytorch.org/)

**Journal:** Journal of King Saud University – Engineering Sciences (JKSUES)

## Author

**Hamzah Faraj**
Department of Science and Technology, Ranyah College, Taif University
Taif 21944, Saudi Arabia — f.hamzah@tu.edu.sa

## Abstract

Residential buildings in Saudi Arabia account for approximately half of national
electricity consumption, with HVAC responsible for up to 70 % of residential
demand. This paper formulates binary HVAC scheduling as a constrained
optimisation over an infinite time horizon under a step-wise electricity tariff.
The single-zone constant-tariff subproblem is identified as a Simple Linear
Hybrid Automaton (SLHA), for which the infinite-horizon optimum is reachable in
LogSpace; multi-zone extensions with non-convex tariffs inherit NP-hardness.

A hybrid Rule-Based Reinforcement Learning (RBRL) framework combines hard
constraint rules with PPO. Under Model S, RBRL demonstrates in simulation
monthly per-zone cost reductions of **18.2 % (Riyadh)** and **16.8 % (Jeddah)**
relative to the unoptimised thermostat, with **zero comfort violations**.

## Repository structure

```
.
├── README.md                     This file
├── LICENSE                       MIT
├── CITATION.cff                  Citation metadata
├── .gitignore                    Excludes checkpoints, build products, caches
├── requirements.txt              Python dependencies
├── main.tex / references.bib / main.pdf     Paper source and compiled PDF
├── src/                          Package that produced the reported results
│   ├── __init__.py
│   ├── rbrl_optimizer.py         PPO wrapper, training, monthly schedule extraction
│   └── MISSING_MODULES.md        *** modules still to be added — read this ***
├── metadata.json                 Machine-readable study metadata
├── pyproject.toml                Package metadata and tool configuration
├── Makefile                      make paper | verify | validate | test | reference-check
├── .editorconfig                 Editor conventions
├── .github/workflows/ci.yml      CI: table verification and manuscript build
├── tests/test_tables.py          Consistency tests for the published tables
├── configs/
│   ├── riyadh_4x4.yaml           Riyadh 4x4 run configuration
│   └── jeddah_4x4.yaml           Jeddah 4x4 run configuration
├── results/
│   ├── tables/*.csv              Every table in the paper, machine-readable
│   ├── tables/SCHEMA.md          Column definitions, units, provenance
│   ├── load_tables.py            Re-verifies the tables reproduce (CI-usable)
│   └── plot_results.py           Regenerates the summary figures
├── figures/*.png                 Summary figures built from the CSVs
├── simulation/                   Weather profiles and hourly rollouts (see its README
│                                 for how these differ from the manuscript's setup)
├── reference_implementation/     Independent single-file reimplementation (see its README)
├── data/                         EPW dataset instructions
├── results/                      Reported results summary
├── energyplus/                   Planned co-simulation protocol
└── figures/                      Figure notes
```

> **Important.** `src/` is the code that produced the results in the paper.
> `reference_implementation/` is a *separate, independent* reimplementation used
> for cross-checking; it did **not** generate any number in the manuscript. Do not
> mix the two when reproducing results.

## Reported results (Model S)

| Metric                     | Riyadh | Jeddah |
|---------------------------|--------|--------|
| Monthly saving vs THERM   | 18.2 % | 16.8 % |
| Weekly saving vs THERM    | 18.2 % | 16.6 % |
| Comfort violations        | 0 %    | 0 %    |
| Training time (4x4)       | 3.1 h  | 3.1 h  |
| Inference latency         | 0.52 ms| 0.52 ms|

Two evaluation horizons are reported and should not be conflated: weekly
(168-hour) rollouts and the monthly (720-hour) billing horizon. They differ by up
to ~1.5 percentage points for the smaller topologies because only over a full
billing month does cumulative consumption traverse the tariff tiers. See
Section "Robustness of the reported results" in the paper.

## Run configuration (as used for the reported results)

    c_th 77.2 kJ/K   lambda_ext 20.5 W/K   lambda_win 12.5 W/K   lambda_iz 12.5 W/K
    q_hvac 2.0 kW    p_hvac 0.67 kW        c_sw 0.15 SAR         dt 1.0 h
    comfort band [22, 26] C                horizon 168 h (weekly) / 720 h (monthly)
    E_base 800 kWh/month  (non-HVAC household load: lighting, appliances, water heating)

The cumulative-energy state is initialised with the non-HVAC base load because the
Saudi tariff is levied on the whole customer account. For Riyadh 4x4 this gives
~1,910 kWh/month of HVAC plus 800 kWh base = ~2,710 kWh, crossing the first tier
boundary (2,000 kWh) around day 22 of the billing month; the 4,000 and 6,000 kWh
boundaries are not reached by a villa of this size.

Total envelope conductance Lambda = 33 W/K, matching the running example in the
paper. Note the paper's Table 2 presents the same total with a different
opaque/window split (25.0 + 8.0); the dynamics depend only on the total.

## Reproducing

```bash
make install          # or: pip install -r requirements.txt
make verify           # re-verify the published tables reproduce
make validate         # RC model validation and integration stability
make paper            # compile main.pdf
```

Training and evaluation entry points (`src/train.py`, `src/evaluate.py`) are not
yet included in this repository; see `src/MISSING_MODULES.md` for what remains to
be added before the pipeline can be run end to end. Everything else above runs
today.

Training runs for a fixed budget with no early stopping and no intermediate
checkpoint selection; the saved policy is the final one. Hyperparameters were
selected on a held-out 2x2 validation configuration, so the 30 test weeks are
used exactly once, at the end.

Seeds {42, 43, 44, 45, 46}; all reported figures are the mean +/- std over all
five, with no seed discarded and no best-of-n selection.

## Dataset

IWEC typical-year EPW files from https://energyplus.net/weather:

- `SAU_Riyadh.404380_IWEC.epw` (WMO 404380, BWh, CDD ~ 3,400)
- `SAU_Jeddah.410240_IWEC.epw` (WMO 410240, BSh, CDD ~ 2,900)

Building parameters follow SBC 2018; comfort band [22, 26] C per ASHRAE 55-2023.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

The author acknowledges the Deanship of Graduate Studies and Scientific Research,
Taif University, for funding this work.

## Citation

```bibtex
@article{Faraj2026RBRL,
  author  = {Faraj, Hamzah},
  title   = {Hybrid Rule-Constrained {PPO} for Cost-Effective Binary {HVAC}
             Scheduling in Saudi Residential Buildings},
  journal = {Journal of King Saud University -- Engineering Sciences},
  year    = {2026}
}
```
