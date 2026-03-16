# Constrained Optimal Binary HVAC Scheduling in Saudi Residential Buildings

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![PyTorch 2.1](https://img.shields.io/badge/PyTorch-2.1.0-orange.svg)](https://pytorch.org/)

## Overview

This repository contains the complete implementation and publication materials for:

**"Constrained Optimal Binary HVAC Scheduling over an Infinite Time Horizon in Saudi Residential Buildings: A Hybrid Rule-Based Reinforcement Learning Framework"**

Hamzah Faraj — Department of Science and Technology, Ranyah College, Taif University, Taif 21944, Saudi Arabia

## Contact

**Hamzah Faraj**  
- Department of Science and Technology  
- Ranyah College, Taif University, Taif 21944, Saudi Arabia  
- Email: [email removed]

## Abstract

Residential buildings in Saudi Arabia account for approximately 50% of national electricity consumption, with HVAC systems responsible for up to 70% of residential demand. In cooling-dominated climates—Riyadh (hot-arid) and Jeddah (hot-humid)—optimal HVAC scheduling must simultaneously minimise electricity cost under a four-tier step-wise tariff and guarantee that indoor temperatures remain within the occupant comfort band at every interval.

This paper formulates the scheduling problem as a constrained binary optimisation over an infinite time horizon, where thermal comfort is a hard constraint, each switch-on incurs a discrete cost, and continuous running time incurs a tariff-weighted cost. The single-zone constant-tariff subproblem belongs to the class of Simple Linear Hybrid Automata (SLHA), for which the infinite-horizon optimum is reachable in LogSpace; extensions to multiple zones, non-convex step-wise tariffs, and time-varying disturbances inherit NP-hardness. A hybrid Rule-Based Reinforcement Learning (RBRL) framework is proposed, combining hard constraint rules with a Proximal Policy Optimisation (PPO) agent trained on the limit-average cost objective.

### Key Results
- **18.2% monthly cost reduction** in Riyadh (hot-arid climate, 4×4 grid)
- **16.8% monthly cost reduction** in Jeddah (hot-humid climate, 4×4 grid)
- **Zero comfort violations** across all configurations and all seasons
- Training under a linear tariff approximation incurs a **13.1% true-cost penalty**
- Validated across seven zone configurations: 1×1, 1×2, 1×4, 1×6, 2×2, 3×3, 4×4
- Inference time **< 1 ms** per interval — suitable for embedded microcontrollers

## Repository Structure

```
hvac-scheduling-saudi-arabia/
├── README.md                 # This file
├── METHODS.md                # Detailed methodology and algorithms
├── LICENSE                   # MIT License
├── requirements.txt          # Python dependencies
│
├── paper/                    # Publication materials
│   ├── main.tex              # LaTeX manuscript (publication-ready)
│   └── references.bib        # Bibliography (47 references)
│
├── data/                     # Experimental results and metadata
│   ├── results_model_comparison.csv      # Model L/E/S performance
│   ├── results_topology_comparison.csv   # All 7 configurations
│   ├── ablation_results.csv              # Component & cost-model ablation
│   ├── monthly_trajectories.csv          # 12-month cost trajectories
│   ├── scalability_results.csv           # Zone-count scalability (Table 10)
│   ├── riyadh_epw_metadata.txt           # Weather data summary (Riyadh)
│   └── jeddah_epw_metadata.txt           # Weather data summary (Jeddah)
│
├── src/                      # Source code
│   ├── __init__.py
│   ├── thermal_model.py      # RC thermal dynamics (Eq. 2)
│   ├── cost_models.py        # Models L, E, S implementation
│   ├── rbrl_agent.py         # Hybrid RBRL framework
│   ├── rbrl_optimizer.py     # PPO-based optimizer
│   ├── ppo_trainer.py        # PPO training loop (Algorithm 1)
│   ├── rules.py              # Hard comfort constraint rules (R1, R2, R3)
│   ├── environment.py        # Gym-compatible HVAC environment
│   └── utils.py              # Helper functions and constants
│
├── examples/                 # Usage examples
│   └── train_and_extract_schedule.py  # Complete workflow demo
│
├── docs/                     # Documentation
│   └── OPTIMIZER_USAGE.md    # Detailed optimizer usage guide
│
├── experiments/              # Experimental configurations
│   ├── config_riyadh.yaml    # Riyadh case study parameters
│   ├── config_jeddah.yaml    # Jeddah case study parameters
│   ├── train_rbrl.py         # Training script
│   ├── evaluate_baselines.py # THERM, GA, SA evaluation
│   └── run_ablation.py       # Ablation study experiments
│
└── models/                   # Trained model checkpoints
    ├── rbrl_riyadh_1x1.zip
    ├── rbrl_riyadh_4x4.zip
    └── rbrl_jeddah_4x4.zip
```

## Installation

### Prerequisites
- Python 3.11
- PyTorch 2.1.0 (CUDA 11.8 recommended for training)
- LaTeX distribution (for compiling paper)

### Setup

```bash
# Clone the repository
git clone https://github.com/drhamzahfaraj/hvac-scheduling-saudi-arabia.git
cd hvac-scheduling-saudi-arabia

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### Option 1: Using the RBRL Optimizer (Recommended)

```python
from src.rbrl_optimizer import train_rbrl_ppo, extract_monthly_schedule

# Train PPO agent (200,000 episodes, 168-step rollouts)
model = train_rbrl_ppo(
    Nz=4,
    topology="1x4",
    city="Riyadh",
    total_episodes=200000,
    model_save_path="models/ppo_riyadh_1x4",
)

# Extract optimal 30-day schedule (720 hours)
schedule, temps, costs = extract_monthly_schedule(
    model=model,
    Nz=4,
    topology="1x4",
    city="Riyadh",
    month_hours=720,
)

print(f"Total monthly cost: {sum(costs):.2f} SAR")
```

**Complete example with visualization:**

```bash
python examples/train_and_extract_schedule.py
```

See [docs/OPTIMIZER_USAGE.md](docs/OPTIMIZER_USAGE.md) for detailed documentation.

### Option 2: Command-Line Interface

```bash
# Train and extract schedule in one command
python -m src.rbrl_optimizer \
    --Nz 4 \
    --topology 1x4 \
    --city Riyadh \
    --episodes 200000 \
    --output models/ppo_riyadh_1x4
```

### Option 3: Using Original Experiment Scripts

```bash
# Train RBRL agent
python experiments/train_rbrl.py --config experiments/config_riyadh.yaml --topology 4x4

# Evaluate baselines
python experiments/evaluate_baselines.py --city riyadh --model S --topology 4x4

# Run ablation study
python experiments/run_ablation.py --config experiments/config_riyadh.yaml
```

## Zone Parameters

All rooms are 4 m × 4 m × 4 m. Key parameters (Table 2 in paper):

| Symbol | Description | Value | Unit |
|--------|-------------|-------|------|
| C_th | Effective thermal capacity | 77.2 | kJ·K⁻¹ |
| λ_ext | Opaque-wall conductance (SBC ≤ 0.45) | 25.0 | W·K⁻¹ |
| λ_win | Window conductance (double-glazed) | 8.0 | W·K⁻¹ |
| λ_ij | Inter-zone shared-wall conductance | 12.5 | W·K⁻¹ |
| Q_hvac | HVAC cooling extraction (COP 3.0) | 2.0 | kW |
| P_hvac | HVAC electrical draw | 0.67 | kW |
| T_min / T_max | Comfort band | 22 / 26 | °C |
| ε_g | Rule guard band | 0.5 | °C |
| c_sw | Switch-on discrete cost (default) | 0.15 | SAR |
| Δt | Scheduling interval | 1 | h |

## Saudi Four-Tier Tariff (Model S)

```
0.05 SAR/kWh   E_cum ≤ 2,000 kWh
0.10 SAR/kWh   2,000 < E_cum ≤ 4,000 kWh
0.18 SAR/kWh   4,000 < E_cum ≤ 6,000 kWh
0.30 SAR/kWh   E_cum > 6,000 kWh
```

Model S uniquely creates a **pre-cooling incentive**: concentrating cooling load during Tier 1 builds a thermal buffer that enables idle periods when the tariff rises to Tier 2 or beyond.

## Key Features

### Hybrid RBRL Framework
- **R1 (hard, force on):** T_i ≥ T_max − ε_g → u_i = 1
- **R2 (hard, force off):** T_i ≤ T_min + ε_g → u_i = 0
- **R3 (soft, pre-cool):** biases agent toward O2 pre-cooling without overriding
- **PPO Agent:** two fully-connected layers (256–128 units, ReLU); shares lower layers for Nz ≥ 9
- **State Space:** zone temperatures, effective inter-zone temperatures, 3-step outdoor forecast, hour-of-day, previous actions, cumulative energy

### PPO Hyperparameters

| Parameter | Value |
|-----------|-------|
| Network | FC 256–128, ReLU |
| Learning rate | 3 × 10⁻⁴ (Adam) |
| Discount γ / Clip ε | 0.99 / 0.2 |
| Entropy / Batch size | 0.01 / 64 |
| Training episodes | 2 × 10⁵, 168-step rollouts |
| Convergence | ~1.5 × 10⁵ episodes |

## Experimental Results

### Monthly Cost Savings vs. THERM (Model S)

| City | Config. | THERM (SAR/zone/mo) | RBRL (SAR/zone/mo) | Saving (%) |
|------|---------|-------------------|--------------------|------------|
| Riyadh | 1×1 | 64.6 | 52.7 | 18.4 |
| Riyadh | 1×4 | 68.5 | 55.7 | 18.7 |
| Riyadh | 2×2 | 67.0 | 54.5 | 18.7 |
| Riyadh | 4×4 | 73.0 | 59.7 | **18.2** |
| Jeddah | 1×1 | 58.9 | 49.5 | 16.0 |
| Jeddah | 1×4 | 61.5 | 51.2 | 16.7 |
| Jeddah | 2×2 | 60.2 | 50.2 | 16.6 |
| Jeddah | 4×4 | 65.5 | 54.5 | **16.8** |

### Scalability (Riyadh, Model S, Summer)

| Config. | Nz | Saving (%) | Train (h) | Infer. (ms) |
|---------|----|------------|-----------|-------------|
| 1×1 | 1 | 18.6 | 1.2 | 0.08 |
| 1×4 | 4 | 17.5 | 1.8 | 0.14 |
| 3×3 | 9 | 17.0 | 2.6 | 0.31 |
| 4×4 | 16 | 18.2 | 3.1 | 0.52 |

### State-of-the-Art Comparison

| Method | Year | Saving | Control Type | Saudi Tariff | Hard Comfort |
|--------|------|--------|--------------|-------------|-------------|
| **RBRL (ours)** | **2026** | **18.2%** | **Binary on/off** | **✓** | **✓** |
| GA-MADDPG [Xue2025] | 2025 | 6.7% | Continuous | ✗ | ◦ |
| DDPG multi-zone [Du2021] | 2021 | 15% | Continuous | ✗ | ◦ |
| Q-learning [Azuatalam2020] | 2020 | 22% | Continuous | ✗ | ◦ |
| DRL VAV [Wang2024] | 2024 | 37%* | Continuous VAV | ✗ | ◦ |
| Online RL [Solinas2024] | 2024 | 65%** | Continuous | ✗ | ✓ |

*Continuous VAV in simulated office — different hardware and building type.  
**Relative to no-HVAC baseline; saving vs. thermostat is substantially lower.

### Cost Model Ablation (4×4, Riyadh — train model vs. true Model S cost)

| Training Model | True Cost (SAR/zone/day) | Penalty |
|---------------|--------------------------|--------|
| Step-wise (S) | 1.98 ± 0.13 | — |
| Exponential (E) | 2.11 ± 0.13 | +6.6% |
| Linear (L) | 2.24 ± 0.14 | **+13.1%** |

## Simulation Environment

- **Python 3.11**, PyTorch 2.1.0, CUDA 11.8
- **RL library:** Stable-Baselines3 v2.2.1
- **Hardware:** Training on NVIDIA RTX 3080 (10 GB VRAM); inference on Intel Core i7-12700K
- **Weather:** EnergyPlus EPW files for Riyadh (BWh, 24.7°N) and Jeddah (BSh, 21.5°N)
- **Evaluation:** Mean ± std over 30 independently sampled test weeks, random seed 42
- **Training set:** Full EPW year (8,760 h); test set: 30 weeks drawn uniformly from held-out year

## Documentation

- **[METHODS.md](METHODS.md)**: Detailed methodology, algorithms, and theoretical foundations
- **[docs/OPTIMIZER_USAGE.md](docs/OPTIMIZER_USAGE.md)**: Complete optimizer usage guide with examples
- **[examples/](examples/)**: Practical examples and workflow demonstrations

## Citation

If you use this code or methodology in your research, please cite:

```bibtex
@article{Faraj2026HVAC,
  author  = {Faraj, Hamzah},
  title   = {Constrained Optimal Binary {HVAC} Scheduling over an Infinite Time Horizon
             in {Saudi} Residential Buildings: {A} Hybrid Rule-Based Reinforcement
             Learning Framework},
  journal = {[Under Review]},
  year    = {2026}
}
```

## Data Availability

Codes, datasets, and other related information are available at:  
https://github.com/drhamzahfaraj/hvac-scheduling-saudi-arabia

- **Weather Data:** EnergyPlus Weather (EPW) files for Riyadh and Jeddah
- **Results:** CSV files with complete experimental results
- **Models:** Pre-trained RBRL agents for reproducibility

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Acknowledgments

The authors acknowledge the Deanship of Graduate Studies and Scientific Research, Taif University for funding this work.

---

**Keywords:** constrained binary scheduling, infinite time horizon, HVAC optimisation, deep reinforcement learning, thermal comfort, Saudi Arabia, step-wise tariff, multi-zone buildings, simple linear hybrid systems
