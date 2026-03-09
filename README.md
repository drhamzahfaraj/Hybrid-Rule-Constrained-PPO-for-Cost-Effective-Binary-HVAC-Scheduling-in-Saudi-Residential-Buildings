# Constrained Optimal Binary HVAC Scheduling in Saudi Residential Buildings

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## Overview

This repository contains the complete implementation and publication materials for:

**"Constrained Optimal Binary HVAC Scheduling over an Infinite Time Horizon in Saudi Residential Buildings: A Hybrid Rule-Based Reinforcement Learning Framework"**

## Contact

**Hamzah Faraj**  
- Department of Science and Technology  
- Ranyah College, Taif University, Taif 21944, Saudi Arabia  
- Email: [email removed]

## Abstract

Residential buildings in Saudi Arabia account for approximately 50% of national electricity consumption, with HVAC systems responsible for up to 70% of residential demand. This work presents a hybrid Rule-Based Reinforcement Learning (RBRL) framework that combines hard thermal comfort constraints with Proximal Policy Optimization (PPO) to minimize electricity costs under Saudi Arabia's four-tier step-wise tariff structure.

### Key Results
- **18.2% cost reduction** in Riyadh (hot-arid climate)
- **16.9% cost reduction** in Jeddah (hot-humid climate)
- **Zero comfort violations** across all configurations
- Validated on single-zone, linear array (1×N), and grid (N×N) topologies

## Repository Structure

```
hvac-scheduling-saudi-arabia/
├── README.md                 # This file
├── METHODS.md                # Detailed methodology and algorithms
├── LICENSE                   # MIT License
├── requirements.txt          # Python dependencies
│
├── paper/                    # Publication materials
│   ├── main-6.tex            # LaTeX manuscript (publication-ready)
│   └── references-2.bib      # Bibliography
│
├── data/                     # Experimental results and metadata
│   ├── results_model_comparison.csv      # Model L/E/S performance
│   ├── results_topology_comparison.csv   # 1×1, 1×4, 4×4 configurations
│   ├── ablation_results.csv              # Ablation study data
│   ├── monthly_trajectories.csv          # 12-month cost trajectories
│   ├── riyadh_epw_metadata.txt           # Weather data summary (Riyadh)
│   └── jeddah_epw_metadata.txt           # Weather data summary (Jeddah)
│
├── src/                      # Source code
│   ├── __init__.py
│   ├── thermal_model.py      # RC thermal dynamics (Eq. 2)
│   ├── cost_models.py        # Models L, E, S implementation
│   ├── rbrl_agent.py         # Hybrid RBRL framework
│   ├── rbrl_optimizer.py     # PPO-based optimizer (NEW)
│   ├── ppo_trainer.py        # PPO training loop
│   ├── rules.py              # Hard comfort constraint rules (R1, R2, R3)
│   ├── environment.py        # Gym-compatible HVAC environment
│   └── utils.py              # Helper functions and constants
│
├── examples/                 # Usage examples (NEW)
│   └── train_and_extract_schedule.py  # Complete workflow demo
│
├── docs/                     # Documentation (NEW)
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
- Python 3.8 or higher
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

# Train PPO agent
model = train_rbrl_ppo(
    Nz=4,
    topology="1x4",
    city="Riyadh",
    total_episodes=2000,
    model_save_path="models/ppo_riyadh_1x4",
)

# Extract optimal 30-day schedule
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
    --episodes 2000 \
    --output models/ppo_riyadh_1x4
```

### Option 3: Using Original Experiment Scripts

```bash
# Train RBRL agent
python experiments/train_rbrl.py --config experiments/config_riyadh.yaml --topology 4x4

# Evaluate baselines
python experiments/evaluate_baselines.py --city riyadh --model S --topology 4x4

# Reproduce paper figures
python figures/generate_figures.py --output-dir figures/

# Run ablation study
python experiments/run_ablation.py --config experiments/config_riyadh.yaml
```

## Key Features

### Hybrid RBRL Framework
- **Hard Rules (R1-R3)**: Guarantee thermal comfort at all times
- **PPO Agent**: Learns optimal switching strategy within safe region
- **State Space**: Includes inter-zone temperatures for coordination
- **Model S**: Actual Saudi 4-tier step-wise tariff implementation

### Cost Models
1. **Model L (Linear)**: Constant tariff (baseline)
2. **Model E (Exponential)**: Smooth approximation
3. **Model S (Step-wise)**: Actual Saudi 4-tier tariff

### Zone Configurations
- Single zone (1×1)
- Linear array (1×2, 1×4, 1×6)
- Grid (2×2, 3×3, 4×4)

## Experimental Results

### Cost Reduction vs. THERM (Model S, 4×4 Grid)

| City | Monthly Savings | Zero Violations |
|------|----------------|----------------|
| Riyadh | 18.2% | ✓ |
| Jeddah | 16.9% | ✓ |

### Comparison with State-of-the-Art

| Method | Saving | Control Type | Saudi Tariff |
|--------|--------|--------------|-------------|
| RBRL (ours) | 18.2% | Binary on/off | ✓ |
| GA-MADDPG [Xue2025] | 6.7% | Continuous | ✗ |
| DDPG [Du2021] | 15% | Continuous | ✗ |
| Q-learning [Azuatalam2020] | 22% | Continuous | ✗ |

## Documentation

- **[METHODS.md](METHODS.md)**: Detailed methodology, algorithms, and theoretical foundations
- **[docs/OPTIMIZER_USAGE.md](docs/OPTIMIZER_USAGE.md)**: Complete optimizer usage guide with examples
- **[examples/](examples/)**: Practical examples and workflow demonstrations

## Citation

If you use this code or methodology in your research, please cite:

```bibtex
@article{Faraj2026HVAC,
  author = {Faraj, Hamzah},
  title = {Constrained Optimal Binary {HVAC} Scheduling over an Infinite Time Horizon in {Saudi} Residential Buildings: A Hybrid Rule-Based Reinforcement Learning Framework},
  journal = {[Under Review]},
  year = {2026}
}
```

## Data Availability

All experimental data, trained models, and weather files (EPW format) are available in the `data/` and `models/` directories.

- **Weather Data**: EnergyPlus Weather (EPW) files for Riyadh and Jeddah
- **Results**: CSV files with complete experimental results
- **Models**: Pre-trained RBRL agents for reproducibility

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

This research was supported by Taif University, Saudi Arabia.

---

**Keywords**: HVAC optimization, reinforcement learning, thermal comfort, Saudi Arabia, step-wise tariff, multi-zone buildings, binary scheduling
