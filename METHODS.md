# Methodology: Hybrid Rule-Based Reinforcement Learning (RBRL)

## Table of Contents

1. [Thermal Model](#thermal-model)
2. [Cost Models](#cost-models)
3. [Problem Formulation](#problem-formulation)
4. [RBRL Framework](#rbrl-framework)
5. [Training Procedure](#training-procedure)
6. [Evaluation Metrics](#evaluation-metrics)

---

## Thermal Model

### RC Network Dynamics

Each zone $i$ follows a first-order RC thermal model:

$$
C_{\text{th}}^{(i)} \frac{dT_i}{dt} = -Q_{\text{hvac}}^{(i)} u_i(t) - \Lambda_i (T_i - T_{\text{out}}) + \sum_{j \in \mathcal{N}_i} \lambda_{ij} (T_j - T_i) + Q_{\text{sol}}^{(i)}(t)
$$

**Parameters** (per 4×4×4 m room):
- $C_{\text{th}} = 77.2$ kJ/K (thermal capacity)
- $\lambda_{\text{ext}} = 25.0$ W/K (opaque wall conductance)
- $\lambda_{\text{win}} = 8.0$ W/K (window conductance)
- $\lambda_{ij} = 12.5$ W/K (inter-zone conductance)
- $Q_{\text{hvac}} = 2.0$ kW (cooling extraction, COP 3.0)
- $P_{\text{hvac}} = 0.67$ kW (electrical draw)

### Discretization

Forward Euler at $\Delta t = 1$ hour:

$$
T_i^{(t+1)} = T_i^{(t)} + \frac{\Delta t}{C_{\text{th}}^{(i)}} \left[ -Q_{\text{hvac}}^{(i)} u_i^{(t)} - \Lambda_i (T_i^{(t)} - T_{\text{out}}^{(t)}) + \sum_{j \in \mathcal{N}_i} \lambda_{ij} (T_j^{(t)} - T_i^{(t)}) + Q_{\text{sol}}^{(i,t)} \right]
$$

### Effective Inter-Zone Temperature

To capture multi-zone coupling:

$$
T_{\text{iz},i}^{(t)} = \frac{\sum_{j \in \mathcal{N}_i} \lambda_{ij} T_j^{(t)}}{\sum_{j \in \mathcal{N}_i} \lambda_{ij}}
$$

This conductance-weighted average enables the agent to anticipate inter-zone heat cascades.

---

## Cost Models

### Model L (Linear)

Constant rate: $c_r^L = 0.12$ SAR/kWh

$$
f^L = c_r^L \cdot P_{\text{hvac}} \cdot u_i
$$

### Model E (Exponential)

Smooth approximation:

$$
f^E = c_r^E \cdot e^{\beta E_{\text{cum}}} \cdot P_{\text{hvac}} \cdot u_i
$$

where $c_r^E = 0.05$ SAR/kWh, $\beta = 5 \times 10^{-4}$ kWh$^{-1}$

### Model S (Step-wise / Actual Tariff)

Saudi 4-tier structure:

$$
p(E_{\text{cum}}) = \begin{cases}
0.05 & E_{\text{cum}} \le 2000 \\
0.10 & 2000 < E_{\text{cum}} \le 4000 \\
0.18 & 4000 < E_{\text{cum}} \le 6000 \\
0.30 & E_{\text{cum}} > 6000
\end{cases} \text{ SAR/kWh}
$$

### Interval Cost

$$
c_i^{(t)} = c_{\text{sw}} \cdot \mathbb{1}[u_i^{(t)} > u_i^{(t-1)}] + f^m(u_i^{(t)}, E_{\text{cum}}^{(t)}) \cdot \Delta t
$$

where $c_{\text{sw}} = 0.15$ SAR (switching cost)

---

## Problem Formulation

### Infinite Horizon Optimization

Minimize limit-average cost:

$$
\bar{J}_\infty^m(\sigma) = \limsup_{H \to \infty} \frac{1}{H} \sum_{t=0}^{H-1} \sum_{i \in \mathcal{N}} c_i^{(t)}
$$

subject to:

$$
T_{\min} \le T_i^{(t)} \le T_{\max}, \quad \forall i, t \ge 0
$$

where $T_{\min} = 22°$C, $T_{\max} = 26°$C (ASHRAE 55 comfort band)

### Optimality Conditions

A schedule $\sigma^*$ is optimal if:
1. **Safety**: $T_{\min} \le T_i^{(t)} \le T_{\max}$ for all $i, t$
2. **Periodicity**: $\sigma^*$ is periodic with period $\tau$
3. **Minimality**: $\bar{J}_\infty^m(\sigma^*) \le \bar{J}_\infty^m(\sigma)$ for all safe $\sigma$

---

## RBRL Framework

### Architecture

The RBRL agent consists of two components:

#### 1. Hard Constraint Rules (R1-R3)

**Rule R1** (Upper bound enforcement):
```
IF T_i^{(t)} ≥ T_max - ε_g AND u_i^{(t-1)} = 0 THEN u_i^{(t)} ← 1
```

**Rule R2** (Lower bound enforcement):
```
IF T_i^{(t)} ≤ T_min + ε_g AND u_i^{(t-1)} = 1 THEN u_i^{(t)} ← 0
```

**Rule R3** (Inter-zone cascade prevention):
```
IF (T_iz,i^{(t)} - T_i^{(t)}) > θ_cascade AND T_i^{(t)} > T_min + 2ε_g THEN u_i^{(t)} ← 0
```

where $\epsilon_g = 0.5°$C (guard band), $\theta_{\text{cascade}} = 2.0°$C

#### 2. PPO Agent

When rules are not triggered, the PPO agent selects action.

**State space** (per zone $i$):

$$
s_i^{(t)} = [T_i^{(t)}, T_{\text{out}}^{(t)}, T_{\text{iz},i}^{(t)}, Q_{\text{sol}}^{(i,t)}, E_{\text{cum}}^{(t)}, u_i^{(t-1)}, h]
$$

where $h$ is hour-of-day (cyclic encoding: $\cos(2\pi h/24), \sin(2\pi h/24)$)

**Action space**: $a_i \in \{0, 1\}$ (binary: off/on)

**Reward function**:

$$
r_i^{(t)} = -c_i^{(t)} - \lambda_{\text{viol}} \cdot \mathbb{1}[T_i^{(t+1)} \notin [T_{\min}, T_{\max}]] - \lambda_{\text{switch}} \cdot \mathbb{1}[u_i^{(t)} \ne u_i^{(t-1)}]
$$

where $\lambda_{\text{viol}} = 10.0$ SAR (violation penalty), $\lambda_{\text{switch}} = 0.05$ SAR (soft switching penalty)

### Decision Logic

```python
def select_action(state, ppo_agent):
    # Check hard rules first
    if rule_r1_triggered(state):
        return 1  # Force ON
    elif rule_r2_triggered(state):
        return 0  # Force OFF
    elif rule_r3_triggered(state):
        return 0  # Prevent cascade
    else:
        return ppo_agent.predict(state)  # PPO decision
```

---

## Training Procedure

### PPO Hyperparameters

| Parameter | Value |
|-----------|-------|
| Learning rate | $3 \times 10^{-4}$ |
| Discount factor ($\gamma$) | 0.99 |
| GAE lambda ($\lambda$) | 0.95 |
| Clip range ($\epsilon$) | 0.2 |
| Entropy coefficient | 0.01 |
| Value function coefficient | 0.5 |
| Number of epochs | 10 |
| Batch size | 64 |
| Buffer size | 2048 |

### Training Episodes

1. **Episode duration**: 168 hours (1 week)
2. **Training weeks**: 52 weeks (1 year of data)
3. **Total timesteps**: ~900,000
4. **Validation**: 30 held-out test weeks

### Curriculum Strategy

**Phase 1** (Episodes 1-20): Train on moderate summer weeks (July, $T_{\text{out}} \approx 35-38°$C)

**Phase 2** (Episodes 21-40): Introduce extreme peaks (June-August, $T_{\text{out}} > 40°$C)

**Phase 3** (Episodes 41-52): Full year distribution

### Convergence Criterion

Training stops when:
- Average episode reward improvement < 1% over 5 consecutive episodes
- Zero comfort violations for 10 consecutive test episodes

---

## Evaluation Metrics

### Primary Metrics

1. **Average Cost per Zone** ($\bar{J}/N_z$, SAR/zone/day):
   $$
   \frac{1}{N_z \cdot T_{\text{test}}} \sum_{i=1}^{N_z} \sum_{t=0}^{T_{\text{test}}} c_i^{(t)}
   $$

2. **Switching Frequency** ($f_s$, switches/zone/day):
   $$
   \frac{1}{N_z \cdot T_{\text{test}}} \sum_{i=1}^{N_z} \sum_{t=0}^{T_{\text{test}}} \mathbb{1}[u_i^{(t)} > u_i^{(t-1)}]
   $$

3. **Comfort Violation Rate** (%):
   $$
   \frac{100}{N_z \cdot T_{\text{test}}} \sum_{i=1}^{N_z} \sum_{t=0}^{T_{\text{test}}} \mathbb{1}[T_i^{(t)} \notin [T_{\min}, T_{\max}]]
   $$

### Secondary Metrics

4. **Energy Consumption** (kWh/zone/month):
   $$
   \frac{P_{\text{hvac}}}{N_z} \sum_{i=1}^{N_z} \sum_{t=0}^{T_{\text{month}}} u_i^{(t)} \cdot \Delta t
   $$

5. **Pre-cooling Utilization** (Tier 1 fraction):
   $$
   \frac{\sum_{t: E_{\text{cum}}^{(t)} < 2000} \sum_i u_i^{(t)}}{\sum_t \sum_i u_i^{(t)}}
   $$

---

## Baseline Methods

### THERM (Unoptimized Thermostat)

Fixed dual-setpoint control:
- Turn ON when $T_i \ge T_{\max}$
- Turn OFF when $T_i \le T_{\min}$
- No tariff awareness

### GA (Genetic Algorithm)

Pre-computed 168-hour weekly schedule:
- Population: 50 chromosomes
- Crossover: 0.8, Mutation: 0.05
- Generations: 100
- Cannot adapt to forecast revisions

### SA (Simulated Annealing)

Adaptive but computationally intensive:
- Initial temperature: 100
- Cooling rate: 0.95
- Iterations: 5000 per hour

---

## Implementation Notes

### Weather Data

- **Source**: EnergyPlus Weather (EPW) files
- **Riyadh**: Station 404380 (24.7°N, 46.7°E)
- **Jeddah**: Station 410240 (21.7°N, 39.2°E)
- **Variables**: Dry-bulb temperature, solar irradiance

### Computational Requirements

- **Training**: ~8 hours on NVIDIA RTX 3080 (single GPU)
- **Evaluation**: ~2 minutes per configuration (CPU)
- **Memory**: <4 GB RAM

### Software Stack

- Python 3.8+
- Stable-Baselines3 (PPO implementation)
- NumPy, Pandas, Matplotlib
- PyTorch 1.9+

---

## References

Detailed references are available in `paper/references-2.bib`.

Key methodological foundations:
- **RC Thermal Modeling**: Bacher & Madsen (2011), Drgoňa et al. (2021)
- **SLHA Theory**: Mousa et al. (2018)
- **PPO Algorithm**: Schulman et al. (2017)
- **Hybrid RL**: Xu et al. (2025), Solinas et al. (2024)