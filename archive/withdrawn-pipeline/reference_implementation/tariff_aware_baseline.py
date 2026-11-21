"""tariff_aware_baseline.py -- tariff-aware rule-based controllers (Comment 4).

Drop-in for the paper's pipeline: import alongside hvac_env and evaluate exactly
like policy_therm, e.g.

    from tariff_aware_baseline import policy_tariff_aware
    r = run_episode(env, policy_tariff_aware, start_day=d)

Two variants are provided. In a stable reconstruction on real EPW at the 22-26 C
band, both UNDERPERFORM the thermostat (pre-cooling's extra energy/switches
outweigh the small COP/tariff gain). Run them in your own environment (where
RBRL attains the reported savings) before deciding whether to report a column:
if they beat THERM there, they are a fair "stronger baseline"; if not, keep the
DP optimality bound as the strong reference and cite these as future work.
"""
import numpy as np
from hvac_env import P, hard_rules


def policy_tariff_aware(env):
    """Predictive complete-cycle pre-cooler.

    Runs one cooling phase to the low comfort band during the cool pre-peak
    window when an afternoon temperature rise is forecast, then coasts; uses
    complete cycles to limit switching. Falls back to thermostat hysteresis.
    """
    T = env.T
    k = env.k
    h = int(env.h0 + k * P.dt) % 8760
    hod = (env.h0 + k * P.dt) % 24
    future = [env.t_out[(h + i) % 8760] for i in range(1, 7)]     # next 6 h
    peak_coming = max(future) > env.t_out[h] + 2.0

    u = env.prev.copy()
    # complete-cycle: once cooling, finish down to the low band
    u[(env.prev == 1) & (T > P.t_min + P.eps_g)] = 1
    # pre-cool during the cool pre-peak window if a peak is forecast
    precool_window = (hod >= 2) & (hod <= 9) & peak_coming
    u[precool_window & (T > P.t_min + 1.0)] = 1
    # comfort thermostat backstop
    u[T >= P.t_max - 0.5] = 1
    u[T <= P.t_min + 0.5] = 0
    return hard_rules(u, T)


def policy_tariff_aware_greedy(env):
    """Naive variant: pre-cool whenever the forecast is rising and the account
    is still in a lower price block with head-room. Simpler but tends to
    over-cool (more switching, higher cost) than the complete-cycle version."""
    T = env.T
    h = int(env.h0 + env.k * P.dt) % 8760
    rising = env.t_out[(h + 1) % 8760] > env.t_out[h] + 0.5
    below_boundary = env.e_cum < 6000.0
    u = env.prev.copy()
    u[T >= P.t_max - 0.5] = 1
    u[T <= P.t_min + 0.5] = 0
    u[rising & below_boundary & (T < P.t_max - 1.0) & (T > P.t_min + P.eps_g)] = 1
    return hard_rules(u, T)
