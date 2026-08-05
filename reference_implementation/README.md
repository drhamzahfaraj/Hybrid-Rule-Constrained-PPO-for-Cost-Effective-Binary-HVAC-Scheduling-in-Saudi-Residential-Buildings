# Reference implementation (NOT the code behind the paper's results)

This folder holds an **independent, single-file reimplementation** of the RBRL
environment, written to cross-check the published pipeline. **No number in the
manuscript was produced here.** The code of record is `../src/`.

It is included because independent reimplementation is a useful robustness check
and because several of the utilities below are directly reusable.

## Contents

| File | Purpose |
|---|---|
| `hvac_env.py` | Self-contained RC environment, tariff, unit model, rule layer, thermostat baseline |
| `bc_pretrain.py` | Behaviour cloning from a per-exposure-class dynamic programme |
| `train_ppo.py` | PPO training with held-out scoring and ablation flags |
| `make_tables.py` | Emits table data from trained checkpoints |
| `validate_rc.py` | 1R1C vs 3R2C validation and sub-step convergence (runs standalone) |
| `rerun_corrected.py` | Thermostat baselines and DP optimality ceiling |
| `tariff_aware_baseline.py` | Tariff-aware rule-based controller (Comment 4 comparator) |
| `verify_accepted_config.py` | Checks whether a given parameter set keeps the thermostat inside the comfort band |
| `weather/` | **TMYx (2009-2023)** EPW files for Riyadh and Jeddah. Note: the manuscript's results used the older **IWEC** files; see `../simulation/README.md` for how the two datasets differ. |

## Important differences from `src/`

This reimplementation does **not** use the published run configuration by
default. Its defaults were chosen for numerical headroom while cross-checking:

- `c_th = 6700 kJ/K` (effective capacity) vs the paper's `77.2 kJ/K` (air mass)
- `dt = 0.25 h` vs the paper's `1.0 h`

Consequently its absolute costs differ from the manuscript's tables. To compare
like with like, load `../configs/riyadh_4x4.yaml` values explicitly.

## Baseline scoring

Baselines must be scored **without** the RBRL rule layer:

```python
run_episode(env, policy_therm, start_day=d, baseline=True)
```

Scoring the thermostat *through* the rule layer gives it RBRL's pre-cooling and
then charges it the extra switching cost, which inflates the apparent saving.

## Quick start

```bash
pip install -r ../requirements.txt
python validate_rc.py                 # no agent required
python rerun_corrected.py --stage 1   # thermostat baselines + DP ceiling
```
