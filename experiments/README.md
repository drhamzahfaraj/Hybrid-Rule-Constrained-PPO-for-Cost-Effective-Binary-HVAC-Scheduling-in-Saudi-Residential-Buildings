# Experimental Scripts

This directory contains all scripts for training, evaluation, and ablation studies.

## Quick Start

### 1. Train RBRL Agent

```bash
python train_rbrl.py --config config_riyadh.yaml --topology 4x4 --model S
```

**Arguments**:
- `--config`: Path to configuration file
- `--topology`: Zone configuration (1x1, 1x4, 4x4, etc.)
- `--model`: Cost model (L, E, S)
- `--episodes`: Number of training episodes (default: 52)
- `--output`: Directory for saving trained models

### 2. Evaluate Baselines

```bash
python evaluate_baselines.py --city riyadh --model S --topology 4x4
```

Evaluates THERM, GA, and SA baselines on test weeks.

**Arguments**:
- `--city`: City (riyadh or jeddah)
- `--model`: Cost model (L, E, S)
- `--topology`: Zone configuration
- `--test-weeks`: Number of test weeks (default: 30)

### 3. Run Ablation Study

```bash
python run_ablation.py --config config_riyadh.yaml
```

Runs all ablation experiments:
- No inter-zone temperature in state
- No switching cost
- No guard band
- Train on Model L, test on Model S

### 4. Sensitivity Analysis

```bash
python sensitivity_analysis.py --parameter switching_cost --range 0.05 0.30 --steps 6
```

## Configuration Files

### config_riyadh.yaml

```yaml
city: riyadh
epw_file: data/weather/SAU_Riyadh.404380_IWEC.epw

thermal_params:
  c_th: 77.2  # kJ/K
  lambda_ext: 25.0  # W/K
  lambda_win: 8.0  # W/K
  lambda_ij: 12.5  # W/K
  q_hvac: 2.0  # kW
  p_hvac: 0.67  # kW

comfort:
  t_min: 22  # °C
  t_max: 26  # °C
  epsilon_g: 0.5  # Guard band

cost:
  c_sw: 0.15  # SAR
  model: S  # L, E, or S

ppo_params:
  learning_rate: 0.0003
  gamma: 0.99
  gae_lambda: 0.95
  clip_range: 0.2
  ent_coef: 0.01
  vf_coef: 0.5
  n_epochs: 10
  batch_size: 64
  buffer_size: 2048

training:
  total_episodes: 52
  episode_hours: 168
  validation_weeks: 30
```

### config_jeddah.yaml

Same structure as Riyadh, with:
```yaml
city: jeddah
epw_file: data/weather/SAU_Jeddah.410240_IWEC.epw
```

## Output Structure

After running experiments:

```
models/
├── rbrl_riyadh_1x1_modelS.zip
├── rbrl_riyadh_4x4_modelS.zip
├── rbrl_jeddah_4x4_modelS.zip
└── training_logs/
    ├── riyadh_1x1_log.csv
    └── riyadh_4x4_log.csv

data/
├── results_model_comparison.csv
├── ablation_results.csv
└── sensitivity_results.csv
```

## Computational Requirements

### Training
- **GPU**: NVIDIA RTX 3080 or equivalent
- **Time**: ~8 hours per configuration
- **Memory**: 4 GB RAM

### Evaluation
- **CPU**: Any modern processor
- **Time**: ~2 minutes per configuration
- **Memory**: <1 GB RAM

## Troubleshooting

### Issue: Out of memory during training
**Solution**: Reduce `buffer_size` in config:
```yaml
ppo_params:
  buffer_size: 1024  # Instead of 2048
```

### Issue: EPW file not found
**Solution**: Download weather files and place in `data/weather/`:
```bash
mkdir -p data/weather
cd data/weather
wget https://energyplus.net/weather-download/[EPW_URL]
```

### Issue: Training does not converge
**Solution**: Adjust learning rate or increase episodes:
```yaml
ppo_params:
  learning_rate: 0.0001  # Lower learning rate
training:
  total_episodes: 100  # More episodes
```

## Citation

If you use these experimental scripts, please cite:

```bibtex
@article{Faraj2026HVAC,
  author = {Faraj, Hamzah},
  title = {Constrained Optimal Binary {HVAC} Scheduling},
  year = {2026}
}
```