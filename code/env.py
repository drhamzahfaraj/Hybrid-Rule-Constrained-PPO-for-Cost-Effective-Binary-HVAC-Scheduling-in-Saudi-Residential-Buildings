#!/usr/bin/env python3
"""Gymnasium environment, rule layer, and non-learned baselines."""
from __future__ import annotations
import numpy as np, math, gymnasium as gym
from gymnasium import spaces
from hvac import HVACModel, Params, marginal_price, bill

HOURS_PER_MONTH = 720.0


class Rules:
    """Hard rule layer. R1/R2 are action projections; R3 is a logit bias.

    CC is the complete-cycle rule of Proposition 1: once cooling starts, keep
    cooling until the lower guard is reached, and once off stay off until the
    upper guard. This is what makes the minimum-switching schedule reachable
    and it is what the SLHA theory says an optimal schedule looks like.
    """

    def __init__(self, P: Params, use_hard=True, use_cc=True, use_r3=True):
        self.P, self.use_hard, self.use_cc, self.use_r3 = P, use_hard, use_cc, use_r3

    def r3_bias(self, T, t_out_now, t_out_next):
        """Soft pre-cooling signal -> additive logit bias (pre-sampling)."""
        if not self.use_r3:
            return np.zeros_like(T)
        P = self.P
        rising = (t_out_next - t_out_now) > 2.0
        headroom = T > (P.t_min + P.eps_lo)
        return np.where(rising & headroom, 1.5, 0.0)

    def project(self, u, T, prev_u, bias=None):
        """R1/R2 (+ complete cycle). Returns the executed action.

        `bias` is the R3 pre-cooling signal. For a non-learned controller it
        promotes an off-zone to on when the outdoor temperature is rising and
        there is headroom; for the learned policy the same quantity is added to
        the logits before sampling (see train.py), so the executed action is
        the sampled action and the PPO importance ratio is unbiased.
        """
        P = self.P
        u = u.astype(np.int8).copy()
        if bias is not None and self.use_r3:
            u = np.where((bias > 0) & (u == 0), 1, u)
        if self.use_cc:
            # mid-band hysteresis: hold the current mode until a guard is met
            mid = (T > P.t_min + P.eps_lo) & (T < P.t_max - P.eps_hi)
            u = np.where(mid, prev_u, u)
        if self.use_hard:
            u = np.where(T >= P.t_max - P.eps_hi, 1, u)   # R1 force on
            u = np.where(T <= P.t_min + P.eps_lo, 0, u)   # R2 force off
        return u.astype(np.int8)


class HVACEnv(gym.Env):
    """One 168-h or 720-h rollout of the coupled model."""

    def __init__(self, model: HVACModel, t_out, irr, start_pool,
                 cost_model="S", horizon=168, P: Params | None = None,
                 rules: Rules | None = None, integrator="exact",
                 alpha=50.0, seed=0):
        super().__init__()
        self.m, self.P = model, P or model.P
        self.t_out, self.irr = t_out, irr
        self.start_pool = np.asarray(start_pool)
        self.cost_model, self.H = cost_model, horizon
        self.rules = rules or Rules(self.P)
        # When a learned policy is attached, train.py points this at the
        # policy's logit-bias holder. _obs() then publishes the forced-action
        # mask so R1/R2 are enforced BEFORE sampling: the sampled action already
        # complies, the executed action is the sampled action, and the PPO
        # importance ratio is unbiased. Previously R1/R2 were applied as a
        # post-hoc override, which rewrote 38.5%% of sampled zone-actions.
        self.logit_holder = None
        self.integrator = integrator
        self.alpha = alpha
        self.n = model.n
        self.rng = np.random.default_rng(seed)
        self.action_space = spaces.MultiBinary(self.n)
        # [T (n), T_iz (n), prev_u (n), t_out forecast (3), hour sin/cos, e_frac]
        self.observation_space = spaces.Box(-5.0, 5.0, (3 * self.n + 6,), np.float32)

    # ---------------------------------------------------------------- helpers
    def _e_base_window(self, k):
        """Non-HVAC load accrued from the start of the billing month to step k.

        Wraps at the billing-month boundary so a window spanning month-end is
        billed against the correct month.
        """
        h = (self.t0_month_h + k * self.P.dt) % HOURS_PER_MONTH
        return self.P.e_base * h / HOURS_PER_MONTH

    def _logit_mask(self, big=20.0):
        """Pre-sampling logit bias implementing R1, R2 and R3.

        R1/R2 are saturating (+/- big) so the sampled action complies with the
        hard rules; R3 is a soft additive nudge as before.
        """
        P, R = self.P, self.rules
        m = np.zeros(self.n, dtype=np.float32)
        if R.use_r3:
            N = len(self.t_out)
            t0 = self.t_out[(self.s + self.k) % N]
            t1 = self.t_out[(self.s + self.k + 1) % N]
            m += R.r3_bias(self.T, t0, t1).astype(np.float32)
        if R.use_hard:
            m = np.where(self.T >= P.t_max - P.eps_hi,  big, m)
            m = np.where(self.T <= P.t_min + P.eps_lo, -big, m)
        return m.astype(np.float32)

    def _obs(self):
        P = self.P
        if self.logit_holder is not None:
            self.logit_holder["bias"] = self._logit_mask()
        Tn = (self.T - 24.0) / 4.0
        deg = np.maximum(self.m.adj.sum(1), 1)
        Tiz = (self.m.adj @ self.T) / deg
        Tizn = (Tiz - 24.0) / 4.0
        N = len(self.t_out)
        f = [(self.t_out[(self.s + self.k + j) % N] - 35.0) / 10.0
             for j in (1, 2, 3)]
        spd = int(round(24.0 / self.P.dt))
        hod = ((self.s + self.k) % spd) * self.P.dt
        e_frac = self.e_hvac / 2000.0
        return np.concatenate([Tn, Tizn, self.prev_u.astype(float),
                               f, [math.sin(2 * math.pi * hod / 24),
                                   math.cos(2 * math.pi * hod / 24), e_frac]]
                              ).astype(np.float32)

    def reset(self, *, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.s = int(self.rng.choice(self.start_pool))
        # position of this window within its billing month
        self.t0_month_h = float((self.s * self.P.dt) % HOURS_PER_MONTH)
        self.T = np.full(self.n, 24.0)
        self.prev_u = np.zeros(self.n, dtype=np.int8)
        self.k = 0
        self.e_hvac = 0.0
        self.switches = 0
        self.viol = 0
        self.cost_sw = 0.0
        self.cost_en = 0.0
        self.T_sum = np.zeros(self.n)
        self.traj = []
        return self._obs(), {}

    def step(self, action):
        P = self.P
        idx = (self.s + self.k) % len(self.t_out)
        t_out, irr = self.t_out[idx], self.irr[idx]
        nxt = self.t_out[(self.s + self.k + 1) % len(self.t_out)]
        bias = self.rules.r3_bias(self.T, t_out, nxt)
        # R3 is already in the logits when a learned policy is attached, so
        # applying it again here would double-count it.
        u = self.rules.project(np.asarray(action), self.T, self.prev_u,
                               bias=None if self.logit_holder is not None else bias)

        new_on = int(np.sum((u == 1) & (self.prev_u == 0)))
        self.switches += new_on
        self.cost_sw += P.c_sw * new_on

        e_step = P.p_hvac * float(u.sum()) * P.dt           # kWh electrical
        p = marginal_price(self.cost_model,
                           self._e_base_window(self.k) + self.e_hvac, P)
        self.cost_en += p * e_step
        self.e_hvac += e_step

        if self.integrator == "exact":
            self.T = self.m.step_exact(self.T, t_out, irr, u, P.dt)
        else:
            self.T = self.m.step_euler(self.T, t_out, irr, u, P.dt)

        self.viol += int(np.sum((self.T < P.t_min - 1e-9) | (self.T > P.t_max + 1e-9)))
        self.T_sum += self.T
        self.traj.append((t_out, self.T.copy(), u.copy()))
        self.prev_u = u
        self.k += 1

        dev = np.maximum(0.0, np.maximum(P.t_min - self.T, self.T - P.t_max))
        reward = -(P.c_sw * new_on + p * e_step + self.alpha * float(np.sum(dev ** 2)))
        done = self.k >= self.H
        return self._obs(), reward, done, False, self.info() if done else {}

    def info(self):
        P, days = self.P, self.H * self.P.dt / 24.0
        base_end = self._e_base_window(self.H)
        exact_bill = bill(self.cost_model, self.e_hvac, P, base_end)
        J = exact_bill + self.cost_sw
        return dict(
            J_per_zone_day=J / self.n / days,
            cost_sw_share=(self.cost_sw / J if J else 0.0),
            E_per_zone_day=self.e_hvac / self.n / days,
            f_s=self.switches / self.n / days,
            v_c=100.0 * self.viol / (self.H * self.n),
            T_mean=float(self.T_sum.sum() / (self.H * self.n)),
            peak_kW=max(float(x[2].sum()) for x in self.traj) * P.p_hvac,
        )


# ------------------------------------------------------------- baselines
def run_policy(env, act_fn, start=None, seed=0):
    env.rng = np.random.default_rng(seed)
    obs, _ = env.reset(seed=seed)
    if start is not None:
        env.s = int(start); env.t0_month_h = float(start % int(HOURS_PER_MONTH))
        env.T = np.full(env.n, 24.0); env.prev_u = np.zeros(env.n, np.int8)
        obs = env._obs()
    done = False
    while not done:
        a = act_fn(env, obs)
        obs, _, done, _, info = env.step(a)
    return info


def therm(deadband_k: float):
    """Deadband thermostat centred in the comfort band.

    deadband_k = 4.0 reproduces the full-band (minimum-switching) thermostat;
    smaller values are the conventional narrow-deadband controller.
    """
    def act(env, obs):
        P = env.P
        lo = 24.0 - deadband_k / 2.0
        hi = 24.0 + deadband_k / 2.0
        u = np.where(env.T >= hi, 1, np.where(env.T <= lo, 0, env.prev_u))
        return u.astype(np.int8)
    return act


def always_on_floor():
    """Reference: hold at the top of the band (minimum-energy feasible)."""
    def act(env, obs):
        return (env.T >= env.P.t_max - env.P.eps_hi).astype(np.int8)
    return act
