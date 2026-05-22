# Hybrid Rule-Constrained PPO for Cost-Optimal Binary HVAC Scheduling in Saudi Residential Buildings

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-green.svg)](https://www.python.org/)
[![PyTorch 2.1](https://img.shields.io/badge/PyTorch-2.1.0-orange.svg)](https://pytorch.org/)

**Journal:** Journal of King Saud University – Engineering Sciences (JKSUES)

## Author

**Hamzah Faraj**
Department of Science and Technology  
Ranyah College, Taif University  
Taif 21944, Saudi Arabia
Email: f.hamzah@tu.edu.sa

## Repository Structure

```
hvac-scheduling-saudi-arabia/
├── README.md                 # This file
├── LICENSE                   # MIT License
├── requirements.txt          # Python dependencies
├── main.tex                  # Paper source (LaTeX, elsarticle 3p)
├── references.bib            # Bibliography (47 entries, all with DOIs)
├── main.pdf                  # Compiled paper (22 pages)
├── src/
│   ├── __init__.py           # Package metadata
│   ├── environment.py        # RC thermal simulation (Gymnasium)
│   ├── cost_models.py        # Models L, E, S (Saudi tariff)
│   ├── rules.py              # Hard safety rules R1–R3
│   ├── agent.py              # PPO wrapper (Stable-Baselines3)
│   ├── train.py              # Training with grid search
│   └── evaluate.py           # Evaluation and baselines
├── configs/
│   ├── riyadh_4x4.yaml       # Riyadh configuration
│   └── jeddah_4x4.yaml       # Jeddah configuration
├── data/
│   └── README.md             # EPW dataset instructions
├── results/
│   └── README.md             # Pre-computed results
├── energyplus/
│   └── README.md             # Validation protocol (future work)
└── figures/
    └── README.md             # TikZ figure notes
```

## Abstract

Residential buildings in Saudi Arabia account for approximately half of national electricity consumption, with HVAC systems responsible for up to 70% of residential demand. This paper formulates binary HVAC scheduling as a constrained optimisation over an infinite time horizon under Saudi Arabia's four-tier step-wise electricity tariff. The single-zone constant-tariff subproblem is identified as a Simple Linear Hybrid Automaton (SLHA), for which the infinite-horizon optimum is reachable in LogSpace; multi-zone extensions with non-convex tariffs inherit NP-hardness.

A hybrid Rule-Based Reinforcement Learning (RBRL) framework combines hard constraint rules with PPO. Under the actual Saudi tariff, RBRL demonstrates in simulation monthly per-zone cost reductions of **18.2% (Riyadh)** and **16.8% (Jeddah)** relative to the unoptimised thermostat, with **zero comfort violations**.

**Keywords:** HVAC scheduling · deep reinforcement learning · proximal policy optimisation · building energy management · step-wise electricity tariff · thermal comfort · Saudi Arabia · demand-side management

## Key Results

| Metric                | Riyadh    | Jeddah    |
|----------------------|-----------|-----------|
| RBRL saving vs THERM | **18.2%** | **16.8%** |
| Comfort violations   | 0%        | 0%        |
| Training time (4×4)  | 3.1 h     | 3.1 h     |
| Inference latency    | 0.52 ms   | 0.52 ms   |

### Ablation Study and Benchmarking

| Variant              | J̄/Nz (SAR)   | vc (%) | Δ vs RBRL  |
|---------------------|---------------|--------|------------|
| THERM (thermostat)  | 2.42 ± 0.18   | 0.0    | +22.2%     |
| GA (genetic alg.)   | 2.16 ± 0.15   | 0.0    | +9.1%      |
| SA (simulated ann.) | 2.19 ± 0.16   | 0.0    | +10.6%     |
| RL only (no rules)  | 2.03 ± 0.22   | 0.5    | +2.5%      |
| RBRL hard-only      | 2.05 ± 0.16   | 0.0    | +3.5%      |
| **RBRL full**       | **1.98 ± 0.13** | **0.0** | **—**    |

### Cost Model Comparison

| Cost Model     | Riyadh | Jeddah | True-Cost Penalty |
|---------------|--------|--------|-------------------|
| Linear (L)    | 15.6%  | 14.6%  | +13.1%            |
| Exponential   | 15.5%  | 14.6%  | +6.6%             |
| **Step-wise** | **18.2%** | **16.8%** | **— (baseline)** |

### Scalability

| Config | Nz | Saving (%) | Train (h) | Inference (ms) |
|--------|-----|-----------|-----------|----------------|
| 1×1    | 1   | 18.6      | 1.2       | 0.08           |
| 2×2    | 4   | 17.2      | 1.7       | 0.13           |
| 4×4    | 16  | 18.2      | 3.1       | 0.52           |

### State-of-the-Art Comparison

| Method          | Year | Saving    | Basis          |
|----------------|------|-----------|----------------|
| Drgona (MPC)   | 2020 | 10–30%    | vs rule-based  |
| Du (DDPG)      | 2021 | 15%       | vs baseline    |
| Wang (SAC)     | 2024 | 37%       | vs thermostat  |
| **RBRL (ours)** | **2026** | **18.2%** | **vs thermostat** |

## Contributions

1. **C1** — Constrained binary scheduling with three optimality conditions (comfort, cost, switching)
2. **C2** — SLHA theoretical anchor: LogSpace for single-zone, NP-hard for multi-zone
3. **C3** — Hybrid PPO + hard rules guaranteeing zero comfort violations
4. **C4** — Three-way cost model comparison; 13.1% penalty from tariff mismatch
5. **C5** — Dual-city validation across Riyadh (hot-arid) and Jeddah (hot-humid)

## Methodology: Mechanism of Energy Savings

1. **Pre-cooling (Tariff Awareness):** Front-load cooling in Tier 1 to build thermal buffer
2. **Hard Safety Rules:** R1 (force-on), R2 (force-off), R3 (cycle guard) — zero violations
3. **Inter-zone Coordination:** Agent observes adjacent temperatures to prevent cascades

## Dataset

EPW files from [energyplus.net/weather](https://energyplus.net/weather):
- `SAU_Riyadh.404380_IWEC.epw` (BWh, CDD ≈ 3,400)
- `SAU_Jeddah.410240_IWEC.epw` (BSh, CDD ≈ 2,900)

Building parameters follow SBC 2018. Comfort band [22, 26] °C per ASHRAE 55-2023.

## Running Experiments

```bash
pip install -r requirements.txt
python src/train.py --config configs/riyadh_4x4.yaml --cost-model S --seed 42
python src/evaluate.py --model checkpoints/riyadh_16z_S.zip --config configs/riyadh_4x4.yaml
```

## Limitations

1. **Sensible heat only** — latent loads add ~54% in Jeddah; percentage savings preserved
2. **Air-mass Cth** — sensitivity analysis (77–1200 kJ/K) shows <1pp variation
3. **No occupancy** — evening peaks (18:00–23:00) coincide with high tariff
4. **Perfect forecast** — 3-step outdoor temperature assumed error-free
5. **Simulation only** — EnergyPlus and hardware validation planned as future work

## License

MIT License — see [LICENSE](LICENSE).

## Acknowledgments

The author acknowledges the Deanship of Graduate Studies and Scientific Research, Taif University, for funding this work.

## Citation

```bibtex
@article{Faraj2026RBRL,
  author  = {Faraj, Hamzah},
  title   = {Hybrid Rule-Constrained {PPO} for Cost-Optimal Binary {HVAC}
             Scheduling in Saudi Residential Buildings},
  journal = {Journal of King Saud University -- Engineering Sciences},
  year    = {2026},
  note    = {Under review}
}
```
