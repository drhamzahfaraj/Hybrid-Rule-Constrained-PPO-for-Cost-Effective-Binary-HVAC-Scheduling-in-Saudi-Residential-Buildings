# RBRL PPO Optimizer Usage Guide

This document explains how to use the RBRL (Rule-Based Reinforcement Learning) PPO optimizer to train and extract optimal HVAC schedules for Saudi residential buildings.

## Overview

The optimizer implements the methodology described in the paper:

- **Hard Rules (R1, R2)**: Enforce thermal comfort constraints (O1) by forcing HVAC on/off when temperatures approach boundaries
- **Soft Rule (R3)**: Bias toward pre-cooling to exploit low-tariff periods (O2)
- **PPO Agent**: Learns cost-minimizing policy that satisfies switching frequency minimization (O3)
- **Model S**: Uses the actual Saudi four-tier step-wise electricity tariff

## Installation

Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

Key dependencies:
- `stable-baselines3>=2.0.0`
- `torch>=1.9.0`
- `gym>=0.21.0`
- `numpy>=1.21.0`

## Quick Start

### 1. Train a New Model

```python
from src.rbrl_optimizer import train_rbrl_ppo

# Train PPO agent for 4-zone linear topology in Riyadh
model = train_rbrl_ppo(
    Nz=4,
    topology="1x4",
    city="Riyadh",
    horizon_hours=168,        # 1 week episodes during training
    total_episodes=2000,
    steps_per_episode=168,
    learning_rate=3e-4,
    seed=42,
    model_save_path="models/ppo_riyadh_1x4",
    verbose=1,
)
```

### 2. Extract Optimal Monthly Schedule

```python
from src.rbrl_optimizer import extract_monthly_schedule
import numpy as np

# Extract 30-day optimal schedule (720 hours)
schedule, temps, costs = extract_monthly_schedule(
    model=model,
    Nz=4,
    topology="1x4",
    city="Riyadh",
    month_hours=720,
    seed=0,
    verbose=True,
)

# Save results
np.save("experiments/schedules/schedule_riyadh_1x4.npy", schedule)
np.save("experiments/schedules/temps_riyadh_1x4.npy", temps)
np.save("experiments/schedules/costs_riyadh_1x4.npy", costs)

print(f"Total monthly cost: {np.sum(costs):.2f} SAR")
print(f"Average cost per zone per day: {np.sum(costs) / (4 * 30):.2f} SAR")
```

### 3. Load Pre-trained Model and Extract Schedule

```python
from src.rbrl_optimizer import load_and_extract_schedule

schedule, temps, costs = load_and_extract_schedule(
    model_path="models/ppo_riyadh_1x4",
    Nz=4,
    topology="1x4",
    city="Riyadh",
    month_hours=720,
    seed=0,
)
```

## Command-Line Interface

The optimizer can be run directly from the command line:

```bash
# Train and extract schedule for Riyadh, 4 zones, 1x4 topology
python -m src.rbrl_optimizer \
    --Nz 4 \
    --topology 1x4 \
    --city Riyadh \
    --episodes 2000 \
    --horizon 168 \
    --lr 3e-4 \
    --seed 42 \
    --output models/ppo_riyadh_1x4
```

### CLI Arguments

- `--Nz`: Number of zones (default: 4)
- `--topology`: Zone topology ("1x1", "1x4", "2x2", "3x3", "4x4")
- `--city`: City name ("Riyadh" or "Jeddah")
- `--episodes`: Total training episodes (default: 2000)
- `--horizon`: Episode horizon in hours (default: 168)
- `--lr`: Learning rate (default: 3e-4)
- `--seed`: Random seed (default: 42)
- `--output`: Model save path (default: "models/ppo_rbrl_hvac")

## Configuration Details

### Zone Topologies

| Topology | Zones | Description |
|----------|-------|-------------|
| `1x1` | 1 | Single zone |
| `1x4` | 4 | Linear 1×4 array |
| `1x6` | 6 | Linear 1×6 array |
| `2x2` | 4 | 2×2 grid |
| `3x3` | 9 | 3×3 grid |
| `4x4` | 16 | 4×4 grid |

### Cities

**Riyadh** (BWh - Hot desert climate):
- Mean annual temperature: 24.7°C
- Summer diurnal swing: ~14°C
- Enables aggressive pre-cooling strategy
- Annual CDD (base 18°C): ~3,400

**Jeddah** (BSh - Hot semi-arid climate):
- Mean annual temperature: 21.5°C
- Summer diurnal swing: ~6°C
- Limited pre-cooling opportunity
- Annual CDD (base 18°C): ~2,900

### PPO Hyperparameters (from Paper)

```python
{
    "policy": "MlpPolicy",
    "net_arch": [256, 128],      # 2 FC layers with ReLU
    "learning_rate": 3e-4,
    "n_steps": 168,               # Episode length
    "batch_size": 64,
    "gamma": 0.99,
    "clip_range": 0.2,            # PPO clip coefficient
    "total_timesteps": 336000,    # 2000 episodes × 168 steps
}
```

### Comfort Parameters

```python
{
    "Tmin": 22.0,    # Minimum comfort temperature (°C)
    "Tmax": 26.0,    # Maximum comfort temperature (°C)
    "guard": 0.5,    # Guard band for rules R1, R2 (°C)
}
```

### Cost Model (Model S - Step-wise Tariff)

```python
# Saudi four-tier residential electricity tariff
tariff = {
    (0, 2000):       0.05,  # SAR/kWh (Tier 1)
    (2000, 4000):    0.10,  # SAR/kWh (Tier 2)
    (4000, 6000):    0.18,  # SAR/kWh (Tier 3)
    (6000, float('inf')): 0.30,  # SAR/kWh (Tier 4)
}

switching_cost = 0.15  # SAR per 0→1 transition
```

## Output Format

### Schedule Array

Shape: `(H, Nz)` where H=720 hours (30 days), Nz=number of zones

```python
schedule[t, i] ∈ {0, 1}  # HVAC state for zone i at hour t
                          # 0 = OFF (idle), 1 = ON (cooling)
```

### Temperature Array

Shape: `(H, Nz)`

```python
temps[t, i] ∈ [22°C, 26°C]  # Zone i temperature at hour t
                              # Must satisfy comfort constraint
```

### Cost Array

Shape: `(H,)`

```python
costs[t] = c_sw * switches[t] + p(E_cum) * E[t]  # Interval cost at hour t
                                                   # c_sw: switching cost
                                                   # p(E_cum): stepwise tariff
                                                   # E[t]: energy this interval
```

## Advanced Usage

### Custom Environment Configuration

```python
model = train_rbrl_ppo(
    Nz=4,
    topology="1x4",
    city="Riyadh",
    # Pass additional environment parameters
    switching_cost=0.20,        # Higher switching penalty
    Phvac=0.75,                 # kW electrical draw
    Qhvac=2.5,                  # kW cooling capacity
    Tmin=21.0,                  # Lower comfort bound
    Tmax=25.0,                  # Upper comfort bound
)
```

### Multi-City Training

```python
# Train separate models for each city
for city in ["Riyadh", "Jeddah"]:
    model = train_rbrl_ppo(
        Nz=4,
        topology="1x4",
        city=city,
        model_save_path=f"models/ppo_{city.lower()}_1x4",
    )
```

### Batch Schedule Extraction

```python
import os
import numpy as np
from src.rbrl_optimizer import load_and_extract_schedule

configs = [
    {"topology": "1x1", "Nz": 1},
    {"topology": "1x4", "Nz": 4},
    {"topology": "2x2", "Nz": 4},
    {"topology": "3x3", "Nz": 9},
]

for config in configs:
    for city in ["Riyadh", "Jeddah"]:
        model_path = f"models/ppo_{city.lower()}_{config['topology']}"
        
        if os.path.exists(f"{model_path}.zip"):
            schedule, temps, costs = load_and_extract_schedule(
                model_path=model_path,
                Nz=config["Nz"],
                topology=config["topology"],
                city=city,
            )
            
            # Save with descriptive name
            prefix = f"experiments/schedules/{city}_{config['topology']}"
            np.save(f"{prefix}_schedule.npy", schedule)
            np.save(f"{prefix}_temps.npy", temps)
            np.save(f"{prefix}_costs.npy", costs)
```

## Troubleshooting

### Issue: Training doesn't converge

**Solution**: Increase training episodes or adjust learning rate

```python
model = train_rbrl_ppo(
    total_episodes=5000,      # More episodes
    learning_rate=1e-4,       # Lower learning rate
)
```

### Issue: Comfort violations during deployment

**Solution**: This should never happen if rules R1, R2 are correctly implemented. Check:

1. Guard band is sufficient: `guard >= 0.5°C`
2. Rules are applied before PPO action
3. RC dynamics are stable

### Issue: High switching frequency

**Solution**: Increase switching cost penalty

```python
model = train_rbrl_ppo(
    switching_cost=0.30,  # Higher penalty (default: 0.15)
)
```

### Issue: Model doesn't exploit tariff tiers

**Solution**: Ensure cumulative energy `E_cum` is in the observation space and Model S is active:

```python
# Check environment wrapper
env = RBRLWrapper(
    ...,
    training=False,  # For deployment
)

# Verify cost model in HVACEnvironment
assert env.env.cost_model == "S"  # Step-wise tariff
```

## Performance Metrics

### Expected Cost Reductions (from Paper)

| City | Config | RBRL vs THERM |
|------|--------|---------------|
| Riyadh | Model S, 1×1 | 18.2% |
| Jeddah | Model S, 1×1 | 16.9% |
| Riyadh | Model S, 2×2 | 21.4% |
| Jeddah | Model S, 2×2 | 19.3% |

### Switching Frequency

- THERM (baseline): ~3.0 switches/zone/day
- RBRL (optimized): ~2.0 switches/zone/day
- Reduction: ~33%

## Citation

If you use this optimizer in your research, please cite:

```bibtex
@article{faraj2026hvac,
  title={Constrained Optimal Binary HVAC Scheduling over an Infinite Time Horizon in Saudi Residential Buildings: A Hybrid Rule-Based Reinforcement Learning Framework},
  author={Faraj, Hamzah},
  journal={Submitted},
  year={2026}
}
```

## Support

For questions or issues:
- Email: [email removed]
- GitHub Issues: [hvac-scheduling-saudi-arabia/issues](https://github.com/drhamzahfaraj/hvac-scheduling-saudi-arabia/issues)
