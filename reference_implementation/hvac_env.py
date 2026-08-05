"""Gymnasium environment for rule-constrained binary HVAC scheduling.

Self-contained: physics, tariff, unit model and rule layer in one file.
Requires only numpy and gymnasium; PyTorch is needed by the training script,
not by this module.

Parameter provenance
--------------------
tariff      SEC / ECRA residential schedule effective 1 Jan 2018:
            0.18 SAR/kWh up to 6,000 kWh/month, 0.30 SAR/kWh above.
lam_win     SBC 601 (2018) Zone 1 residential, U_window <= 3.0 W/m2K,
            over A_gl = 2.0 m2  ->  6.0 W/K.
c_th        Build-up for a 4x4x4 m room in concrete/hollow-block
            construction: air 77 + furnishings 816 + participating inner
            fabric ~8,100  ->  9,000 kJ/K.
Q, COP      AHRI 210/240 rating point 35 C; capacity derate
            Q(T) = Q_r [1 - 0.010 (T-35)];  COP = 5.35 - 0.0675 T;
            cycling degradation coefficient C_D = 0.25.
c_sw        Compressor start wear amortised over service life; 0.15 SAR is
            adopted (Table 2) as the conservative value of the 0.04-0.15 range.
"""
from __future__ import annotations
import os
import numpy as np
try:
    import gymnasium as gym
    from gymnasium import spaces
    _GYM = True
except ImportError:                       # allow use without gymnasium
    _GYM = False
    class _Box:
        def __init__(self, lo, hi, shape, dtype): self.shape = shape
    class _MultiBinary:
        def __init__(self, n): self.n = n
    class spaces:                          # noqa: N801
        Box, MultiBinary = _Box, _MultiBinary
    class gym:                             # noqa: N801
        class Env:
            def reset(self, *a, **k): pass

# ------------------------------------------------------------------ tariff
def price_S(e):                      # SAR/kWh, marginal, excl. VAT
    return 0.18 if e <= 6000.0 else 0.30

def price(model, e):
    if model == "L":
        return 0.20                  # consumption-weighted average
    if model == "E":
        return 0.18 * np.exp(8.5e-5 * e)
    return price_S(e)

def monthly_bill(e, vat=0.15, meter=10.0):
    c = min(e, 6000.0)*0.18 + max(0.0, e-6000.0)*0.30
    return (c + meter) * (1 + vat)

def cop(t_out):
    return float(np.clip(5.35 - 0.0675*t_out, 1.5, 5.0))

def q_capacity(q_rated, t_out):
    return q_rated * max(0.6, 1.0 - 0.010*(t_out - 35.0))


# ------------------------------------------------------------------ params
class Params:
    c_th    = 6700.0      # kJ/K effective (air 77 + furnishings 816 + fabric 5829)
    lam_ext = 25.0        # W/K opaque envelope (SBC 601, U<=0.45)
    lam_win = 6.0         # W/K double glazing (U = 3.0 W/m2K over 2 m2, SBC 601)
    lam_iz  = 12.5        # W/K per shared inter-zone wall
    q_cool  = 2.0         # kW rated at 35 C
    shgc    = 0.25
    a_gl    = 2.0         # m2
    fan_w   = 70.0        # W indoor fan
    cd      = 0.25        # AHRI cycling degradation coefficient
    t_min   = 22.0
    t_max   = 26.0
    eps_g   = 0.30        # guard band > per-step cooling drift (0.26 C) at dt=0.25 h
    c_sw    = 0.15        # SAR per start (Table 2; wear amortisation, see paper)
    e_base  = 2500.0      # kWh/month non-HVAC
    dt      = 0.25        # h (15 min); see Remark on control interval
    alpha   = 50.0        # comfort penalty weight in the reward

P = Params()

CONFIGS = {"1x1": (1,1), "1x2": (1,2), "1x4": (1,4), "1x6": (1,6),
           "2x2": (2,2), "3x3": (3,3), "4x4": (4,4)}


def adjacency(r, c):
    n = r*c
    A = np.zeros((n, n))
    for i in range(r):
        for j in range(c):
            k = i*c + j
            if j+1 < c: A[k, k+1] = A[k+1, k] = 1.0
            if i+1 < r: A[k, k+c] = A[k+c, k] = 1.0
    return A


def exterior_mask(r, c):
    """1 for zones with a windowed exterior wall, 0 for fully interior zones."""
    return np.array([1.0 if (i in (0, r-1) or j in (0, c-1)) else 0.0
                     for i in range(r) for j in range(c)])


def weather(city, hours=8760):
    h = np.arange(hours)
    day = 2*np.pi*(h - 9)/24.0
    yr  = 2*np.pi*(h - 2900)/8760.0
    if city == "riyadh":
        t = 26.0 + 11.0*np.sin(yr) + 7.0*np.sin(day)
    elif city == "jeddah":
        t = 29.0 + 5.5*np.sin(yr) + 3.0*np.sin(day)
    else:
        raise ValueError(city)
    ghi = np.maximum(0.0, 900*np.sin(np.pi*((h % 24) - 6)/12.0))
    return t, ghi


def load_epw(path):
    """Replace the synthetic profile with a real EPW file.

    Returns (dry_bulb, ghi) arrays of length 8760.
    """
    import csv
    T, G = [], []
    with open(path) as f:
        for i, row in enumerate(csv.reader(f)):
            if i < 8:
                continue
            T.append(float(row[6])); G.append(float(row[13]))
    return np.asarray(T[:8760]), np.asarray(G[:8760])


# ------------------------------------------------------------------ rules
def hard_rules(u, T):
    """R1 force-on and R2 force-off. Guarantee the comfort band."""
    u = np.asarray(u, dtype=int).copy()
    u[T >= P.t_max - P.eps_g] = 1
    u[T <= P.t_min + P.eps_g] = 0
    return u


def r3_precool(T, t_out, t_next):
    """R3 soft pre-cool trigger (Eq. 12): headroom available, outdoor rising."""
    return (T < P.t_max - 1.5) & (t_next > t_out + 0.5)


# ------------------------------------------------------------------ env
class HVACEnv(gym.Env):
    """Binary multi-zone HVAC scheduling under the Saudi two-block tariff.

    Observation (per step):
        [ (T_i - 24)/4                for each zone
          (T_iz,i - 24)/4             effective inter-zone temperature
          (T_out - 30)/15  at t, t+1, t+2
          E_cum / 6000
          sin(2*pi*h/24), cos(2*pi*h/24) ]
    Action: MultiBinary(n_zones); hard rules are applied inside step().
    Reward: -(interval cost) - alpha * (squared comfort violation).
    """
    metadata = {"render_modes": []}

    def __init__(self, city="riyadh", cfg="4x4", cost_model="S",
                 epw=None, rollout_hours=168, r3=True, use_hard=True,
                 use_iz=True, seed=0):
        super().__init__()
        r, c = CONFIGS[cfg]
        self.n = r*c
        self.adj = adjacency(r, c)
        self.deg = self.adj.sum(1)
        self.ext = exterior_mask(r, c)
        self.city, self.cfg, self.model = city, cfg, cost_model
        self.rollout_hours = rollout_hours
        self.r3, self.use_hard, self.use_iz = r3, use_hard, use_iz
        # weather: explicit epw= path wins; otherwise use weather/<city>.epw if
        # present (real TMYx files ship in weather/), else the synthetic profile
        if epw is None:
            _auto = os.path.join(os.path.dirname(__file__), "weather",
                                 f"{city}.epw")
            epw = _auto if os.path.isfile(_auto) else None
        self.t_out, self.ghi = load_epw(epw) if epw else weather(city)

        # held-out split: final 10 days of every month
        L = [31,28,31,30,31,30,31,31,30,31,30,31]
        hold, s = [], 0
        for nd in L:
            hold += list(range(s+nd-10, s+nd)); s += nd
        self.hold = np.array(hold)
        self.train_days = np.setdiff1d(np.arange(365), self.hold)

        # Cooling season only (1 May - 31 Oct). The model has no heating: rule
        # R2 can only switch the compressor OFF, which cannot warm a zone that
        # has drifted below t_min. In Riyadh/Jeddah winter the zones simply
        # follow ambient, so a comfort band is not enforceable and the true
        # optimum is "do nothing". Including those days makes the thermostat
        # cost exactly zero and any relative saving meaningless.
        cool = np.arange(120, 304)
        self.hold = np.intersect1d(self.hold, cool)
        self.train_days = np.intersect1d(self.train_days, cool)

        # Observation includes the PREVIOUS action per zone. The optimal
        # switching policy is a function of (temperature, previous action):
        # without it the agent cannot express hysteresis, and small errors at
        # the switching boundary produce chattering.
        self.observation_space = spaces.Box(-10.0, 10.0,
                                            shape=(3*self.n + 6,), dtype=np.float32)
        self.action_space = spaces.MultiBinary(self.n)
        self._rng = np.random.default_rng(seed)

    # -------------------------------------------------------------- helpers
    def _starts(self, train):
        days = self.train_days if train else self.hold
        span = max(1, int(self.rollout_hours) // 24)
        sd = set(days.tolist())
        return np.array([d for d in days
                         if all((d+k) in sd for k in range(span))])

    def _t_iz(self):
        return np.where(self.deg > 0,
                        (self.adj @ self.T)/np.maximum(self.deg, 1e-9), self.T)

    def _obs(self):
        h = int(self.h0 + self.k*P.dt) % 8760
        hod = (self.h0 + self.k*P.dt) % 24
        tiz = self._t_iz() if self.use_iz else self.T
        return np.concatenate([
            (self.T - 24.0)/4.0,
            (tiz - 24.0)/4.0,
            self.prev.astype(float),
            [(self.t_out[h]-30.0)/15.0,
             (self.t_out[(h+1) % 8760]-30.0)/15.0,
             (self.t_out[(h+2) % 8760]-30.0)/15.0,
             self.e_cum/6000.0,
             np.sin(2*np.pi*hod/24), np.cos(2*np.pi*hod/24)]
        ]).astype(np.float32)

    # -------------------------------------------------------------- API
    def reset(self, seed=None, options=None, train=True, start_day=None):
        super().reset(seed=seed)
        if start_day is None:
            s = self._starts(train)
            start_day = int(self._rng.choice(s))
        self.h0 = int(start_day)*24
        self.k = 0
        self.T = np.full(self.n, 24.0)
        self.prev = np.zeros(self.n, dtype=int)
        self.e_cum = P.e_base
        return self._obs(), {}

    def step(self, action, apply_rules=True):
        """Advance one interval.

        `apply_rules=False` bypasses the RBRL rule layer (R3 soft pre-cooling
        and the R1/R2 hard overrides) so that a baseline controller such as the
        unoptimised thermostat is evaluated on its own logic. R3 belongs to the
        RBRL framework; applying it to a baseline would hand the baseline the
        method's pre-cooling and then charge it the extra switching cost, which
        biases the comparison. Baseline evaluation must therefore use
        `apply_rules=False` (see `run_episode(..., baseline=True)`).
        """
        h = int(self.h0 + self.k*P.dt) % 8760
        t_out, ghi = self.t_out[h], self.ghi[h]
        t_next = self.t_out[(h+1) % 8760]

        u = np.asarray(action, dtype=int).copy()
        if apply_rules and self.r3:
            # R3 (soft): promote pre-cooling when there is head-room and the
            # outdoor forecast is rising. np.maximum(u, 0) was an identity for
            # binary u (R3 never fired); force the pre-cool ON so R3 has effect
            # and the --no-r3 ablation is meaningful. R1/R2 below still govern
            # comfort, so R3 only ever brings a switch-on forward in time.
            trig = r3_precool(self.T, t_out, t_next)
            u = np.where(trig & (self.T > P.t_min + P.eps_g), 1, u)
        if apply_rules and self.use_hard:
            u = hard_rules(u, self.T)

        sw = int(np.sum((u == 1) & (self.prev == 0)))
        qc = q_capacity(P.q_cool, t_out)
        p_el = qc/cop(t_out) + P.fan_w/1000.0
        kwh = p_el*u.sum()*P.dt + P.cd*(4.0/60.0)*p_el*sw
        cost = P.c_sw*sw + price(self.model, self.e_cum)*kwh
        self.e_cum += kwh

        # RC update (Eq. 2), exterior zones only exchange with ambient
        lam = (P.lam_ext + P.lam_win)*self.ext
        q_sol = P.shgc*P.a_gl*ghi*self.ext
        q_iz = P.lam_iz*(self.adj @ self.T - self.deg*self.T)
        q = -qc*1000.0*u - lam*(self.T - t_out) + q_iz + q_sol
        self.T = self.T + P.dt*3600.0/(P.c_th*1000.0)*q

        viol = float(np.sum(np.maximum(0, self.T - P.t_max)**2
                            + np.maximum(0, P.t_min - self.T)**2))
        nviol = int(np.sum((self.T > P.t_max+1e-9) | (self.T < P.t_min-1e-9)))
        reward = -cost - P.alpha*viol

        self.prev = u
        self.k += 1
        done = self.k >= int(self.rollout_hours/P.dt)
        info = dict(cost=cost, kwh=kwh, switches=sw, nviol=nviol, u=u.copy(),
                    e_cum=self.e_cum, T=self.T.copy())
        return self._obs(), reward, done, False, info


# ------------------------------------------------------------------ baselines
def policy_therm(env):
    """Unoptimised thermostat: the deployed baseline."""
    u = env.prev.copy()
    u[env.T >= P.t_max - 0.5] = 1
    u[env.T <= P.t_min + 0.5] = 0
    return u


def run_episode(env, policy, train=False, start_day=None, baseline=False):
    """Roll out one episode.

    baseline=True evaluates the policy WITHOUT the RBRL rule layer (R3 soft
    pre-cooling, R1/R2 hard overrides). Use it for the unoptimised thermostat
    and any other reference controller: those baselines must be scored on their
    own logic, otherwise they inherit the method's pre-cooling and are charged
    its switching cost, biasing the comparison in favour of RBRL.
    """
    env.reset(train=train, start_day=start_day)
    C = K = S = NV = 0
    steps = int(env.rollout_hours/P.dt)
    for _ in range(steps):
        u = policy(env)
        _, _, done, _, info = env.step(u, apply_rules=not baseline)
        C += info["cost"]; K += info["kwh"]
        S += info["switches"]; NV += info["nviol"]
        if done:
            break
    days = steps*P.dt/24.0
    return dict(J=C/(env.n*days), E=K/(env.n*days), fs=S/(env.n*days),
                vc=100.0*NV/(steps*env.n), cost=C, kwh=K, e_cum=env.e_cum)
