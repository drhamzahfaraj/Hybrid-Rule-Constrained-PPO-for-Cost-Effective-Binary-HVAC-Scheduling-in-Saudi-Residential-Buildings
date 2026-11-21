# Modules still required for `src/` to import

`src/__init__.py` imports six modules. Two are present; **five are missing** and
must be added before the package will import or the reproduction commands will
run:

| Module | Status | Provides |
|---|---|---|
| `rbrl_optimizer.py` | present | `RBRLWrapper`, `train_rbrl_ppo`, `extract_monthly_schedule` |
| `__init__.py` | present | package metadata and exports |
| `thermal_model.py` | **missing** | `ThermalModel`, `Zone` — RC dynamics and C_th |
| `environment.py` | **missing** | `HVACEnvironment` — Gymnasium env, rule application, violation accounting |
| `cost_models.py` | **missing** | `LinearCostModel`, `ExponentialCostModel`, `StepwiseCostModel` |
| `rules.py` | **missing** | `HardConstraintRules` — R1, R2, R3 |
| `rbrl_agent.py` | **missing** | `RBRLAgent` |

Also required by the README's reproduction commands but not yet present:
`train.py` and `evaluate.py`.

## Naming inconsistency to resolve

`__init__.py` imports `from .rbrl_agent import RBRLAgent`, while the repository
README lists the file as `agent.py`. Pick one name and make both agree, or the
import will fail.

## Why this matters for the paper

Reviewers asked for full reproducibility (Comment 3). A reader who clones this
repository currently cannot run the pipeline. Adding these five modules — in the
exact state used for the reported runs — is the single highest-value action for
the artifact. In particular, `thermal_model.py` and `environment.py` document how
the comfort band is maintained at a 1-hour interval, which is what Comment 8
probes.
