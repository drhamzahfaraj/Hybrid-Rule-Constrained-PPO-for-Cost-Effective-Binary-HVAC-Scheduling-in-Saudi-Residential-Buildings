"""Model validation (V1) and integration stability (V2).

Neither requires a trained agent, so both run immediately.

    python validate_rc.py
"""
import numpy as np
from hvac_env import (HVACEnv, policy_therm, run_episode, P,
                      q_capacity, cop, monthly_bill)

class RC2Env(HVACEnv):
    """Same environment with a 3R2C reference core: air node + envelope mass."""
    def reset(self, *a, **k):
        o = super().reset(*a, **k)
        self.Tw = np.full(self.n, 26.0)
        return o
    def step(self, action):
        h = int(self.h0 + self.k*P.dt) % 8760
        t_out, ghi = self.t_out[h], self.ghi[h]
        from hvac_env import hard_rules
        u = hard_rules(np.asarray(action, dtype=int), self.T)
        sw = int(np.sum((u == 1) & (self.prev == 0)))
        qc = q_capacity(P.q_cool, t_out)
        p_el = qc/cop(t_out) + P.fan_w/1000.0
        kwh = p_el*u.sum()*P.dt + P.cd*(4/60)*p_el*sw
        from hvac_env import price
        cost = P.c_sw*sw + price(self.model, self.e_cum)*kwh
        self.e_cum += kwh
        c_air, c_wall = 0.30*P.c_th, 1.4*P.c_th
        hi = ho = 2.0*P.lam_ext
        q_sol = P.shgc*P.a_gl*ghi*self.ext
        q_iz = P.lam_iz*(self.adj @ self.T - self.deg*self.T)
        for _ in range(4):
            qa = (-qc*1000.0*u + hi*(self.Tw-self.T)
                  + P.lam_win*self.ext*(t_out-self.T) + q_iz + q_sol)
            qw = hi*(self.T-self.Tw) + ho*(t_out-self.Tw)
            self.T  = self.T  + (P.dt/4)*3600.0/(c_air*1000.0)*qa
            self.Tw = self.Tw + (P.dt/4)*3600.0/(c_wall*1000.0)*qw
        nviol = int(np.sum((self.T > P.t_max+1e-9) | (self.T < P.t_min-1e-9)))
        self.prev = u; self.k += 1
        return (self._obs(), -cost, self.k >= int(self.rollout_hours/P.dt), False,
                dict(cost=cost, kwh=kwh, switches=sw, nviol=nviol,
                     e_cum=self.e_cum, u=u.copy(), T=self.T.copy()))

class SubStepEnv(HVACEnv):
    """Same 1R1C core integrated with `sub` equal sub-steps per interval."""
    def __init__(self, *a, sub=1, **k):
        super().__init__(*a, **k); self.sub = sub
    def step(self, action):
        h = int(self.h0 + self.k*P.dt) % 8760
        t_out, ghi = self.t_out[h], self.ghi[h]
        from hvac_env import hard_rules, price
        u = hard_rules(np.asarray(action, dtype=int), self.T)
        sw = int(np.sum((u == 1) & (self.prev == 0)))
        qc = q_capacity(P.q_cool, t_out)
        p_el = qc/cop(t_out) + P.fan_w/1000.0
        kwh = p_el*u.sum()*P.dt + P.cd*(4/60)*p_el*sw
        cost = P.c_sw*sw + price(self.model, self.e_cum)*kwh
        self.e_cum += kwh
        lam = (P.lam_ext + P.lam_win)*self.ext
        q_sol = P.shgc*P.a_gl*ghi*self.ext
        for _ in range(self.sub):
            q_iz = P.lam_iz*(self.adj @ self.T - self.deg*self.T)
            q = -qc*1000.0*u - lam*(self.T - t_out) + q_iz + q_sol
            self.T = self.T + (P.dt/self.sub)*3600.0/(P.c_th*1000.0)*q
        nviol = int(np.sum((self.T > P.t_max+1e-9) | (self.T < P.t_min-1e-9)))
        self.prev = u; self.k += 1
        return (self._obs(), -cost, self.k >= int(self.rollout_hours/P.dt), False,
                dict(cost=cost, kwh=kwh, switches=sw, nviol=nviol,
                     e_cum=self.e_cum, u=u.copy(), T=self.T.copy()))

if __name__ == "__main__":
    print("="*74); print("V1  MODEL VALIDATION: 1R1C vs 3R2C reference"); print("="*74)
    print(f"  {'city':>8} {'1R1C':>9} {'3R2C':>9} {'deviation':>11}")
    for city in ("riyadh","jeddah"):
        ho = HVACEnv(city,"4x4","S")._starts(train=False)
        starts = [d for d in ho if 150 <= d <= 260][:10]   # summer held-out days
        a = np.mean([run_episode(HVACEnv(city,"4x4","S"), policy_therm,
                                 start_day=int(s))["E"] for s in starts])
        b = np.mean([run_episode(RC2Env(city,"4x4","S"), policy_therm,
                                 start_day=int(s))["E"] for s in starts])
        print(f"  {city:>8} {a:>9.3f} {b:>9.3f} {100*(a-b)/b:>10.2f}%")

    print("\n"+"="*74); print("V2  INTEGRATION STABILITY"); print("="*74)
    tau = P.c_th*1000/(P.lam_ext+P.lam_win)/3600
    print(f"  tau = C/Lambda = {tau:.1f} h ;  dt = {P.dt} h ;  dt/tau = {P.dt/tau:.5f}\n")
    print(f"  {'sub-steps':>10} {'dt_sub':>9} {'kWh/z/day':>11} {'deviation':>11}")
    ho = HVACEnv("riyadh","4x4","S")._starts(train=False)
    starts = [d for d in ho if 150 <= d <= 260][:10]
    ref = None
    for sub,lbl in [(1,"15 min"),(3,"5 min"),(15,"1 min"),(60,"15 s")]:
        v = np.mean([run_episode(SubStepEnv("riyadh","4x4","S",sub=sub),
                                 policy_therm, start_day=int(s))["E"]
                     for s in starts])
        if ref is None: ref = v
        print(f"  {sub:>10} {lbl:>9} {v:>11.4f} {100*(v-ref)/ref:>10.3f}%")
