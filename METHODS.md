# Methodology: Constrained Optimal Binary HVAC Scheduling

This document describes the theoretical foundations, algorithmic design, and implementation details of the RBRL framework presented in the paper.

---

## 1. RC Thermal Model

Each zone i ∈ {1, …, Nz} is modelled as a first-order RC thermal node. The continuous-time energy balance is:

```
C_th · dT_i/dt = −Q_hvac · u_i(t)   [active cooling]
               − Λ_i (T_i − T_out)  [envelope loss/gain]
               + Σ_{j∈Ni} λ_ij (T_j − T_i)  [inter-zone transfer]
               + Q_sol^(i)(t)        [solar gain]
```

Discretised at Δt = 1 h via forward Euler:

```
T_i^(t+1) = T_i^(t) + (Δt / C_th) [
    −Q_hvac · u_i^(t)
    − Λ_i (T_i^(t) − T_out^(t))
    + Σ_{j∈Ni} λ_ij (T_j^(t) − T_i^(t))
    + Q_sol^(i,t)
]
```

**Zone parameters (4 m × 4 m × 4 m room, SBC 2018 compliant):**

| Symbol | Description | Value | Unit |
|--------|-------------|-------|------|
| C_th | Effective thermal capacity | 77.2 | kJ·K⁻¹ |
| λ_ext | Opaque-wall conductance | 25.0 | W·K⁻¹ |
| λ_win | Window conductance (double-glazed) | 8.0 | W·K⁻¹ |
| λ_ij | Inter-zone conductance | 12.5 | W·K⁻¹ |
| Q_hvac | Cooling extraction (COP 3.0) | 2.0 | kW |
| P_hvac | Electrical draw | 0.67 | kW |
| T_min / T_max | Comfort band | 22 / 26 | °C |
| ε_g | Guard band | 0.5 | °C |
| c_sw | Switch-on discrete cost | 0.15 | SAR |
| Δt | Scheduling interval | 1 | h |

**Effective inter-zone temperature** (observed directly in agent state):

```
T_iz,i^(t) = Σ_{j∈Ni} λ_ij T_j^(t)  /  Σ_{j∈Ni} λ_ij
```

This enables the agent to anticipate inter-zone heat cascades before they reach the comfort boundary.

---

## 2. Zone Topologies

Three topologies are studied:

- **Single zone (1×1):** one windowed exterior wall, no inter-zone coupling.
- **Linear array (1×N, N ∈ {2, 4, 6}):** N rooms in a row; end zones have one exterior wall; interior zones couple to two neighbours.
- **Grid (N×N, N ∈ {2, 3, 4}):** up to Nz = 16 zones; corner zones have two exterior walls, edge zones one.

---

## 3. Cost Models

### Model L (Linear)
```
f^L = c^L_r · P_hvac · u_i
```
Constant rate c^L_r = 0.12 SAR/kWh (weighted average). Standard assumption in most scheduling literature.

### Model E (Exponential)
```
f^E = c^E_r · exp(β · E_cum) · P_hvac · u_i
c^E_r = 0.05 SAR/kWh,  β = 5×10⁻⁴ kWh⁻¹
```
Calibrated to match Model S at Tier 1/2 and Tier 2/3 break-even points. Smooth but cannot represent discrete tier boundaries.

### Model S (Step-wise / Actual Saudi Tariff)
```
p(E_cum) =
    0.05 SAR/kWh   if E_cum ≤ 2,000 kWh
    0.10 SAR/kWh   if 2,000 < E_cum ≤ 4,000 kWh
    0.18 SAR/kWh   if 4,000 < E_cum ≤ 6,000 kWh
    0.30 SAR/kWh   if E_cum > 6,000 kWh
```
The actual Saudi four-tier residential tariff in force since 2018. Non-convex; tractable for model-free RL once E_cum is in the state.

**Pre-cooling incentive:** Model S uniquely creates a threshold incentive — concentrating cooling load in Tier 1 builds a thermal buffer that enables idle periods when the tariff rises. Models L and E cannot represent this behaviour, leading to a **13.1% true-cost penalty** when training under Model L.

---

## 4. Constrained Optimisation Problem

### Infinite Time Horizon & Limit-Average Cost

An infinite schedule σ = (u_i^(t))_{Nz×∞} has limit-average cost:

```
J̄^m_∞(σ) = lim sup_{H→∞} (1/H) Σ_{t=0}^{H-1} Σ_{i∈N} c_i^(t)
```

A schedule is **safe** if T_min ≤ T_i^(t) ≤ T_max for all i and all t ≥ 0.

### SLHA Connection

The single-zone constant-tariff (Model L) subproblem is a **Simple Linear Hybrid Automaton (SLHA)** with:
- Modes Q = {q0 (idle), q1 (cool)}
- Flows: Ṫ = a0 > 0 in q0, Ṫ = a1 < 0 in q1
- Invariants: T ≤ T_max in q0; T ≥ T_min in q1
- Transition q0→q1 on T ≥ T_max − ε_g, incurring cost c_sw
- Transition q1→q0 on T ≤ T_min + ε_g, zero cost

The optimal safe infinite schedule for this SLHA is to repeat the cheapest complete cycle indefinitely, achievable in **deterministic LogSpace** (Mousa et al., 2016). Multi-zone coupling, time-varying disturbances, and Model S's non-convex tier jumps inherit **NP-hardness**, motivating RBRL.

### Complete Cycle Structure (Proposition 1)

For the single-zone problem with c_sw > 0, the optimal schedule consists of complete cycles:
- **On-leap τ⁺:** cools from T_max to T_min at rate |a1|; duration τ⁺ = (T_max − T_min) / |a1|
- **Off-leap τ⁻:** warms from T_min to T_max at rate a0; duration τ⁻ = (T_max − T_min) / a0

Limit-average cost of repeating complete cycles:
```
c̄* = (c_sw + c_r · P_hvac · τ⁺) / (τ⁺ + τ⁻)
```

Running example (1×1, Riyadh, July, T_out = 40°C): τ⁺ ≈ 5.8 h, τ⁻ ≈ 2.6 h, c̄* ≈ 0.074 SAR/h.

### Three Optimality Conditions

A safe schedule σ* is optimal if it simultaneously satisfies:

- **(O1) Comfort feasibility:** T_i^(t) ∈ [T_min, T_max] for all i, t — hard, non-negotiable.
- **(O2) Minimum average running cost:** on-periods concentrated in the cheapest tariff window, exploiting the pre-cooling buffer under Model S.
- **(O3) Minimum switching frequency:** on-phases as long and infrequent as the thermal state permits, amortising c_sw per activation.

---

## 5. RBRL Framework

### Architecture

RBRL has two layers:
1. **Rule layer:** enforces O1 by overriding the RL agent whenever a zone temperature approaches a comfort boundary — safety guaranteed by construction.
2. **RL layer (PPO agent):** selects cost-minimising action within the safe subset, learning to exploit O2 and O3.

### State Space

```
s_t = [ T_i^(t)        for i∈N      (zone temperatures)
        T_iz,i^(t)     for i∈N      (effective inter-zone temps)
        T_out^(t:t+3)                (3-step outdoor forecast)
        h_t                          (hour of day)
        u_i^(t-1)      for i∈N      (previous HVAC actions)
        E_cum^(t)                    (cumulative billing energy)
      ]  ∈ R^{2Nz+5}
```

Two inclusions are essential:
- **T_iz,i:** without this the agent cannot anticipate inter-zone heat loading, inadvertently triggering Rule R1 in neighbours.
- **E_cum:** under Model S this encodes the active tariff tier, enabling condition O2.

### Rules

```
R1 (hard, force on):  T_i^(t) ≥ T_max − ε_g  →  u_i^(t) = 1
R2 (hard, force off): T_i^(t) ≤ T_min + ε_g  →  u_i^(t) = 0
R3 (soft, pre-cool):  T_i^(t) < T_max−1.5 ∧ T_out^(t+1) > T_out^(t)+3  →  bias logit toward u_i=1
```

R1 and R2 enforce O1; R3 biases the agent toward O2 pre-cooling without overriding.

### Action Space

```
a_t = (u_1^(t), …, u_{Nz}^(t))  ∈  {0,1}^{Nz}
```

- For Nz ≤ 6: a single shared PPO head.
- For Nz ≥ 9: factored independent heads sharing lower layers (centralised training, decentralised execution), keeping inference O(Nz).

### Reward Function

```
r_t = − Σ_i c_i^(t)
      − α Σ_i [ max(0, T_i^(t) − T_max)² + max(0, T_min − T_i^(t))² ]
α = 50
```

The quadratic comfort penalty drives the agent away from boundaries during training; it is identically zero at deployment (hard rules prevent all violations).

### PPO Network

- **Policy:** two fully-connected layers (256–128 units, ReLU) → per-zone Bernoulli probabilities
- **Value head:** shared with lower layers
- **Clip coefficient:** ε_clip = 0.2
- **Training:** 2 × 10⁵ episodes of 168-step rollouts; start dates sampled uniformly from full EPW year
- **Convergence:** ~1.5 × 10⁵ episodes (reward stabilises within 1% of final value)

---

## 6. Algorithm 1: RBRL Training and Schedule Extraction

```
Require: RC simulation, weather profile W, cost model m, horizon H, switching cost c_sw
Ensure: Near-optimal safe schedule σ*

 1: Initialise PPO policy π_θ randomly
 2: for e = 1 to 2×10⁵ do
 3:   Sample start date d0 ~ W; reset to T_i^(0) = 24°C
 4:   for t = 0 to H−1 do
 5:     Observe s_t via state equation
 6:     for each zone i do
 7:       if T_i^(t) ≥ T_max − ε_g then u_i^(t) ← 1        [R1, enforce O1]
 8:       else if T_i^(t) ≤ T_min + ε_g then u_i^(t) ← 0   [R2, enforce O1]
 9:       else u_i^(t) ~ π_θ(s_t); apply soft R3
10:     end for
11:     Step RC env (Eq. 2); compute c_i^(t), r_t
12:   end for
13:   Update π_θ via PPO gradient step
14: end for
15: return greedy σ* = {arg max π_θ(·|s_t)}
```

---

## 7. Competing Methods

| Method | Type | Tariff-aware | Deployment |
|--------|------|-------------|------------|
| **THERM** | Fixed-setpoint thermostat | No | Real-time |
| **GA** | Day-ahead offline solver (Npop=200, 500 gen.) | Yes | Offline only |
| **SA** | Day-ahead offline solver (T0=500, α=0.99, 10⁴ iter.) | Yes | Offline only |
| **RBRL** | Hybrid PPO+rules | Yes (Model S) | Real-time, <1 ms |

GA and SA require ~10⁵ full RC simulation calls per daily planning cycle — impractical for real-time embedded deployment. After one-time ~3 h training, RBRL evaluates in <1 ms and adapts online to updated forecasts.

---

## 8. Case Studies

### Riyadh (BWh, 24.7°N)
- Hot-arid inland desert climate
- Summer highs exceeding 45°C; July diurnal swing ≈ 14°C
- CDD ≈ 3,400 — large pre-cooling headroom
- Enables strong O2 exploitation: end zones pre-cool 1 h before interior zones in 1×4 arrays

### Jeddah (BSh, 21.5°N)
- Hot-humid Red Sea coastal climate
- Humidity exceeding 70% year-round; overnight T_out > 32°C
- CDD ≈ 2,900; diurnal swing only ~6°C
- Forces near-continuous operation (22 h/day); pre-cooling headroom minimal
- Latent load: SHR ≈ 0.65 → true demand ~54% higher; percentage savings remain valid since both baselines share this penalty

### Building Code
All parameters comply with **Saudi Building Code (SBC) 2018** — opaque-wall U-value ≤ 0.45 W m⁻²K⁻¹, window SHGC ≤ 0.25, for both Climate Zone A (Jeddah) and Zone B (Riyadh).

---

## 9. Simulation Setup

```
Python 3.11, PyTorch 2.1.0, CUDA 11.8
Stable-Baselines3 v2.2.1 (PPO)
NumPy 1.26 (GA, SA)
Random seed: 42
Test set: 30 independently sampled test weeks (held-out year, no data leakage)
Solar gain: Q_sol^(i,t) = SHGC × A_gl × I(t)  [I(t) from EPW global horizontal irradiance]
Hardware: NVIDIA RTX 3080 (10 GB VRAM) for training; Intel Core i7-12700K for inference
```

**Training time (RTX 3080):**
- 1×1 → 1.2 h; 1×4 → 1.8 h; 3×3 → 2.6 h; 4×4 → 3.1 h (sub-linear due to shared lower layers)

**Inference time (i7-12700K, mean over 10⁴ evaluations):**
- 1×1 → 0.08 ms; 1×4 → 0.14 ms; 3×3 → 0.31 ms; 4×4 → 0.52 ms

---

## 10. Limitations

1. **Sensible heat only:** Latent heat adds ~54% to Jeddah loads (SHR ≈ 0.65) and ~18% to Riyadh (SHR ≈ 0.85); percentage savings remain valid since both baselines share the same latent penalty.
2. **Air-mass thermal capacity:** C_th = 77.2 kJ/K represents air mass only; including furniture and wall layers (C_th ~ 500–1500 kJ/K) would lengthen cycles proportionally but preserve percentage savings.
3. **No occupancy:** omitting internal gains (~80 W/person) shortens τ⁻ slightly but preserves the complete-cycle structure.
4. **Perfect forecast:** the 3-step outdoor temperature in the state is assumed error-free; robust training under stochastic forecasts is reserved for future work.
5. **Simulation only:** all results are from RC simulation; co-simulation (e.g., EnergyPlus) and hardware-in-the-loop validation are needed before field deployment.

---

## 11. Key Findings

1. RBRL reduces monthly per-zone cost by **16–19%** in simulation relative to the unoptimised thermostat under the actual step-wise tariff, with hard comfort guarantees across all seven zone configurations and all four seasons.
2. **Cost model fidelity = algorithmic choice in importance:** training under a linear tariff incurs a 13.1% true-cost penalty because the agent cannot perceive the Tier 1 pre-cooling threshold.
3. The **hard rule layer is necessary** for guaranteed comfort; soft pre-cooling rule R3 adds a further 3.5% reduction beyond hard rules alone.
4. **Adjacent zone temperatures (T_iz,i) must be in the agent state** to prevent inter-zone cascades in grid configurations — removing them causes ~8% more R1 overrides in 4×4 grids.
5. RBRL savings are **stable at 17.0–18.6%** from one zone to sixteen (Nz = 1 to 16, Riyadh), confirming scalability of the factored PPO architecture.

---

## References (Selected)

- Mousa et al. (2016): Optimal control for simple linear hybrid systems — TIME 2016, IEEE.
- Mousa et al. (2017): Optimal control for multi-mode systems with discrete costs — FORMATS 2017, Springer LNCS.
- Bacher & Madsen (2011): Identifying suitable models for the heat dynamics of buildings — Energy and Buildings.
- Risbeck et al. (2017): MILP model for real-time cost optimization of building HVAC — Energy and Buildings.
- Stable-Baselines3 (Raffin et al., 2021) — JMLR.
- SBC 2018: Saudi Building Code thermal envelope requirements.
- ASHRAE 55-2023: Thermal environmental conditions for human occupancy.
