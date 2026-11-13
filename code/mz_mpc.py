#!/usr/bin/env python3
"""MPC-MZ: non-cooperative distributed MPC with one-step-delayed plan exchange (no optimality
guarantee), for the multi-zone dwelling of mz_r3 (RULING_round4 §5, §10 D2, §12.1; F19, R5-6).

Every room runs the single-zone lambda-MPC (same horizon, stage cost, mean-temperature multiplier,
pointwise band, rollout terminal): its plant model is the room's exact scalar update with the
neighbour temperatures entering as an exogenous forecast (the neighbours' own plans from the
previous step, shifted one step; held at their last value beyond). The true plant is the exact
coupled model (mz_r3.Dwelling). Independent per-room units only: no arbitration (shared plant
dropped, §5). Everything is vectorised over lambda and every lambda keeps its own neighbour plans,
so a batch run equals the single runs (test 10, tests/test_mz_mpc.py).

R5-6 fixes:
  (1)+(2) one feasibility predicate, r3_dp.step_ok (corrected cold rule, §2.1: u = 1 => T' >= T_min
          at every step; u = 0 unrestricted), per lambda and per grid node, in the recursion AND at
          the first step. The T_inf,0 exemption (and its .min() over the lambda batch) is gone.
  (3) setback rollout and fallback: occupied thresholds only within the lead before arrival, away
      thresholds tied to AWAY_MAX (on AWAY_MAX - 0.2, off on - 0.8); tail schedule at j + 96 (R5-7).
  (4) grid lower edge below the window's lowest free-float equilibrium (r3_dp.grid_for logic),
      upper edge AWAY_MAX + 0.1 under setback.
  (5) rollout terminal and fallback use the MZ-fitted TUNED (mz_r3 output, read via rbrl_io).
  (6) c_sw, price and C_th from the config (final_tables / headroom / multizone).
Also: rollout padded to 96 steps (sw3-8), end = min(k + Hh, NN) (sw3-7), nearest-node forward plan
(sw3-5), unclipped T_mean_occ (sw3-6), fallback_steps counted.

lambda is selected by THE single-zone selection, mpc_lambda.fit_lambda (V-res-5): full LAMS scan,
bisection, refinement rounds and the §16 back-off knob, with A4 / F.admissible / Rule C on the
dwelling mean (fit_mz); grid default mpc_lambda.HEADLINE_NGRID (1601). On 1x1 this reproduces the
single-zone MPC exactly (tests/test_mz_mpc.py).

Usage (one job per topology, after the matching mz_r3 rules job; jobs/round4.jsonl lines):
  python3 mz_mpc.py <city> <topology> [--lam-ij 12.5] [--horizon 24] [--setback] [--n-grid 1601]
  -> results/T31_mz_mpc_<city>_<topo>_lij<x>_h<H>[_sb]{tag}.csv (+ _perwindow)
  {"id":"mz_rules_2x2","cmd":"python3 mz_r3.py rules riyadh 2x2","env":{},
   "outputs":["results/T31_mz_rules_riyadh_2x2_lij12.5.csv","results/mz_tuned_riyadh_2x2_lij12.5.json"]}
  {"id":"mz_mpc_2x2","cmd":"python3 mz_mpc.py riyadh 2x2","env":{},
   "outputs":["results/T31_mz_mpc_riyadh_2x2_lij12.5_h24.csv"],"after":["mz_rules_2x2"]}
"""
from __future__ import annotations
import sys, os, json, time, argparse
sys.path.insert(0, os.environ.get("RBRL_ROOT", "/home/claude/rbrl"))
import numpy as np
import headroom as H
import final_tables as F
import r3_dp as DP
import mz_r3 as Z
import mpc_lambda as M

K = F.MEAN_KEY
LO, HI = H.BAND_LO, H.BAND_HI
NG = M.HEADLINE_NGRID                 # 1601, the single-zone headline grid (V-res-5; was 401)
ROLL = 96
LAMS = [0.0] + list(np.logspace(-2, np.log10(24.0), 24))     # as mpc_lambda.LAMS


def _lerp(a, b, t):
    """linear interpolation treating an infeasible (inf) neighbour as infeasible (no NaN)."""
    with np.errstate(invalid="ignore"):
        v = a + t * (b - a)
    return np.where(np.isfinite(a) & np.isfinite(b), v, np.inf)


def _grid(D, n_grid):
    """R5-6 (4): lower edge = min(LO - 0.1, floor(lowest free-float equilibrium - 0.05)); the room
    model's equilibrium with neighbours at that same temperature is never lower than the coupled
    all-off one, so no reachable state is clipped."""
    lo_g, hi_g = (17.90, H.AWAY_MAX + 0.10) if D.setback else (LO - 0.10, HI + 0.10)
    lo_g = min(lo_g, float(np.floor((D.tinf0_min() - 0.05) * 10) / 10))
    n = n_grid if not D.setback else 3 * n_grid
    return np.linspace(lo_g, hi_g, n)


def mz_mpc_run(D, lams, horizon_h, rule, price_v=None, sb_rule=None, n_grid=None, backoff=0.0):
    """One window of the dwelling, vectorised over lams. rule = MZ-fitted TUNED (on, off);
    sb_rule = (on, off, lead) under setback. backoff: the §16 knob (the planner's occupied ceiling
    HI - b; comfort still scored against HI). Returns one mz_r3 metric dict per lambda."""
    price_v = F.TARIFFS["inforce"] if price_v is None else price_v
    g = D.g; nz = D.nz; lams = np.asarray(lams, float); L = len(lams); ar = np.arange(L)
    Hh = int(round(horizon_h / H.DT)); N = D.N; NN = len(D.t_out)
    if Hh < 1 or N + Hh > NN:
        raise ValueError(f"horizon {horizon_h} h does not fit the {NN}-step record")
    C = D.C; dts = H.DT * 3600.0
    lam_env, Lm = g["lam_env"], g["L"]; lam_tot = lam_env + g["lam_iz"]
    decay = np.exp(-dts * lam_tot / C)                               # (nz,)
    n_occ = int(D.occ[:N].sum()); wl = lams / max(1, n_occ)          # (L,)
    Tg = _grid(D, NG if n_grid is None else n_grid); n = len(Tg)
    run_c = price_v * D.p_el * H.DT
    swc = F.C_SW + price_v * H.E_START
    therm_c = price_v * C / 3.6e6 / H.COP_RATED
    import setback as S, setback_arms as SA
    occ_x = S.occupancy(NN + ROLL) if D.setback else np.ones(NN + ROLL, bool)   # known schedule
    assert np.array_equal(occ_x[:NN], D.occ)
    if D.setback:
        on_at, off_at, LEAD = sb_rule[:3]
        dnext = SA.steps_to_occ(occ_x)
    else:
        on_at, off_at = rule
        LEAD, dnext = 0, np.zeros(NN + ROLL, int)
    A_ON = H.AWAY_MAX - 0.2; A_OFF = A_ON - 0.8
    thr = lambda js: (on_at, off_at) if dnext[js] <= LEAD else (A_ON, A_OFF)
    qs = H.SHGC * H.A_GL * g["faces"][:, None] * D.irr               # (nz, NN)
    hi_plan = np.where(D.occ, D.hi - float(backoff), D.hi) if backoff else D.hi   # planner's upper limit

    def tinf(i, j, Tn, u):
        """room i's relaxation temperature at step j given the neighbour forcing Tn (L,)."""
        return (lam_env[i] * D.t_out[j] + Tn + qs[i, j] - H.Q_HVAC * u) / lam_tot[i]

    def nearest(x):
        i = np.clip(np.searchsorted(Tg, x) - 1, 0, n - 2)
        return np.where(np.abs(Tg[i + 1] - x) < np.abs(x - Tg[i]), i + 1, i)

    acc = Z.Acc(D, L, price_v)
    T = np.full((L, nz), Z.T0); prev = np.zeros((L, nz), int)
    plans = np.repeat(T[:, :, None], Hh + 1, axis=2)                  # (L, nz, Hh+1) planned temps
    for k in range(N):
        end = min(k + Hh, NN)
        hor = end - k
        u_now = np.zeros((L, nz), int); fb_now = np.zeros((L, nz), bool)
        newplans = np.empty_like(plans)
        for i in range(nz):
            # neighbour forcing sum_j lambda_ij T_j over the horizon, per lambda, fixed order
            nb = np.zeros((L, hor))
            for jz in range(nz):
                if Lm[i, jz] != 0.0:
                    nb = nb + Lm[i, jz] * plans[:, jz, 1:hor + 1]
            # terminal: rollout of the MZ-fitted TUNED rule for 96 steps on persistence weather
            # (the 96 steps before `end`, padded), schedule = the tail's own steps end .. end+95
            idx = np.arange(max(0, end - ROLL), end)
            if len(idx) < ROLL:
                idx = np.concatenate([np.full(ROLL - len(idx), idx[0]), idx])
            V = []
            for p0 in (0, 1):
                x = np.broadcast_to(Tg[:, None], (n, L)).copy(); pv = np.full((n, L), p0)
                c = np.zeros((n, L))
                for jj, js in zip(idx, range(end, end + ROLL)):
                    a_on, a_off = thr(js)
                    u = np.where(x >= a_on, 1, np.where(x <= a_off, 0, pv))
                    c += np.where((u == 1) & (pv == 0), swc, 0.0) + run_c[jj] * u
                    ti = tinf(i, jj, nb[:, -1][None, :], u)
                    x = ti + (x - ti) * decay[i]
                    if occ_x[js]:
                        c += wl[None, :] * np.maximum(x, LO)
                    pv = u
                V.append(c + therm_c * (x - Z.T0))
            V0, V1 = V
            pol = np.zeros((hor, n, L, 2), np.int8)
            for h in range(hor - 1, 0, -1):
                j = k + h
                nx = []
                for u, Vu in ((0, V0), (1, V1)):
                    ti = tinf(i, j, nb[:, h][None, :], u)                  # (1, L)
                    Tp = ti + (Tg[:, None] - ti) * decay[i]                # (n, L)
                    ok = DP.step_ok(Tp, u, hi_plan[j], t_min=LO)           # per lambda, per node
                    x = np.clip(Tp, Tg[0], Tg[-1])
                    ix = np.clip(np.searchsorted(Tg, x) - 1, 0, n - 2)
                    t = (x - Tg[ix]) / (Tg[ix + 1] - Tg[ix])
                    Vn = _lerp(np.take_along_axis(Vu, ix, 0), np.take_along_axis(Vu, ix + 1, 0), t)
                    stage = run_c[j] * u + (wl[None, :] * np.maximum(Tp, LO) if D.occ[j] else 0.0)
                    nx.append(np.where(ok, stage + Vn, np.inf))
                pol[h, :, :, 0] = (swc + nx[1] < nx[0])
                pol[h, :, :, 1] = (nx[1] < nx[0])
                V0 = np.minimum(nx[0], swc + nx[1]); V1 = np.minimum(nx[0], nx[1])
            # first step: exact values at the true state, same predicate (R5-6 (2))
            j = k
            best = np.full(L, np.inf); bu = np.full(L, -1)
            for u, Vu in ((0, V0), (1, V1)):
                ti = tinf(i, j, nb[:, 0], u)
                Tp = ti + (T[:, i] - ti) * decay[i]
                ok = DP.step_ok(Tp, u, hi_plan[j], t_min=LO)
                x = np.clip(Tp, Tg[0], Tg[-1])
                ix = np.clip(np.searchsorted(Tg, x) - 1, 0, n - 2)
                t = (x - Tg[ix]) / (Tg[ix + 1] - Tg[ix])
                Vn = _lerp(Vu[ix, ar], Vu[ix + 1, ar], t)
                c = run_c[j] * u + ((u == 1) & (prev[:, i] == 0)) * swc \
                    + (wl * np.maximum(Tp, LO) if D.occ[j] else 0.0) + Vn
                c = np.where(ok, c, np.inf)
                better = c < best
                best = np.where(better, c, best); bu = np.where(better, u, bu)
            a_on, a_off = thr(k)
            base = np.where(T[:, i] >= a_on, 1, np.where(T[:, i] <= a_off, 0, prev[:, i]))
            fb_now[:, i] = bu < 0
            u_now[:, i] = np.where(bu < 0, base, bu)
            # forward plan of this room for the neighbours: chosen action, then nearest-node policy
            x = T[:, i].copy(); newplans[:, i, 0] = x; pv = u_now[:, i].copy()
            ti = tinf(i, k, nb[:, 0], pv); x = ti + (x - ti) * decay[i]
            if hor >= 1:
                newplans[:, i, 1] = x
            for h in range(1, hor):
                j = k + h
                u = pol[h, nearest(x), ar, pv]
                ti = tinf(i, j, nb[:, h], u)
                x = ti + (x - ti) * decay[i]; pv = u
                newplans[:, i, h + 1] = x
            newplans[:, i, hor + 1:] = x[:, None]
        acc.fallback += fb_now.sum(1)
        T = acc.step(k, T, prev, u_now)
        prev = u_now
        plans = np.concatenate([newplans[:, :, 1:], newplans[:, :, -1:]], axis=2)
    res = acc.result(T)
    return [Z.row_of(res, l) for l in range(L)]


# ----------------------------------------------------------------- lambda by A4, Rule C
def mz_tuned(city, topo, lam_ij, sb):
    """MZ-fitted TUNED (R5-6 (5)), read through rbrl_io so its sha lands in the provenance."""
    import rbrl_io as IO
    p = IO.read_json(f"mz_tuned_{city}_{Z.tag(topo, lam_ij, sb)}")
    if p.get("fit_status") in (None, "none"):
        raise SystemExit(f"{city} {topo}: no admissible MZ TUNED (run mz_r3 rules first)")
    return (p["on"], p["off"]) + ((int(p["lead"]),) if sb else ())


class Budget(Exception):
    """raised when a budgeted run (--budget-min) would start a new uncached window batch."""


class RunCache:
    """Resumable runs (jobq2 hard-kills at 2 h): every (window, lam, b) row of mz_mpc_run is kept in
    a pickle keyed by the run's identity AND the code sha, so a chain of budgeted jobs replays the
    deterministic selection from the cache and continues where the previous job stopped. path None:
    no cache, no budget."""

    def __init__(self, path, ident, budget_s=None, log=print):
        import rbrl_io as IO, pickle
        self.path, self.budget_s, self.t0, self.log = path, budget_s, time.time(), log
        self.ident = dict(ident, code=IO.code_sha())
        self.rows = {}; self.n_new = 0
        if path and os.path.exists(path):
            d = pickle.load(open(path, "rb"))
            if d.get("ident") == self.ident:
                self.rows = d["rows"]
                log(f"   cache: {len(self.rows)} rows from {os.path.basename(path)}")
            else:
                log(f"   cache: {os.path.basename(path)} is for another run/code; ignored")

    def save(self):
        if self.path:
            import rbrl_io as IO, pickle
            IO._atomic(self.path, lambda f: pickle.dump(dict(ident=self.ident, rows=self.rows), f), mode="wb")

    def run(self, tag, w, D, lams, fn):
        """rows of fn(D, missing lams) for (tag, w, lam), computing only the missing lams."""
        miss = [x for x in lams if (tag, w, float(x)) not in self.rows]
        if miss:
            if self.budget_s is not None and self.n_new and time.time() - self.t0 > self.budget_s:
                self.save()
                raise Budget()
            for x, r in zip(miss, fn(D, miss)):
                self.rows[(tag, w, float(x))] = r
            self.n_new += 1
            self.save()
        return [self.rows[(tag, w, float(x))] for x in lams]


def _progress(cache, state):
    """chain marker results/mz_cache/<name>.progress (the declared output of non-final chain jobs)."""
    if cache.path:
        import rbrl_io as IO
        IO._atomic(cache.path[:-4] + ".progress",
                   lambda f: f.write(f"{state} rows={len(cache.rows)} utc={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n"))


def fit_mz(Ds, hh, rule, price_v, sb_rule, n_grid, log, cache=None):
    """lambda (and, only if no lambda is admissible, the §16 back-off b) by THE single-zone
    selection mpc_lambda.fit_lambda (V-res-5): full LAMS scan, bisection, refinement rounds, back-off
    knob, with the dwelling's batch, the dwelling A4 selector (mz_r3.select: F.admissible, A4, Rule C
    on the dwelling mean) and the dwelling's THERM target. Returns (lam, b, fit_status, info, n_cand)."""
    tw = list(F.TUNE_W)
    tgt = float(np.mean([Z.therm(Ds[w], 0.0, price_v)[K] for w in tw]))
    seen = {}

    def batch(lams, b):
        f = lambda D, ls: mz_mpc_run(D, ls, hh, rule, price_v, sb_rule, n_grid, backoff=b)
        res = {w: (f(Ds[w], lams) if cache is None else cache.run(("tune", float(b)), w, Ds[w], lams, f))
               for w in tw}
        for l, x in enumerate(lams):
            seen[(float(b), float(x))] = 1
        return [res[w] for w in tw]

    last = {}

    def select(cands, rows):
        p, status, info = Z.select({c: dict(zip(tw, rr)) for c, rr in zip(cands, rows)}, Ds, price_v)
        last.clear(); last.update(info)
        return (None if p is None else cands.index(p)), status, info

    city = Ds[tw[0]].city
    lam, _, _, status = M.fit_lambda(city, hh, None, n_grid, log, with_status=True, batch=batch,
                                     select=select, target=tgt)
    b = float(M.KNOB["backoff"]) if lam is not None else 0.0
    return lam, b, status, dict(last), len(seen)


def main(argv=None):
    import rbrl_io as IO
    ap = argparse.ArgumentParser(description="MPC-MZ (non-cooperative distributed MPC)")
    ap.add_argument("city"); ap.add_argument("topology", choices=Z.TOPOLOGIES)
    ap.add_argument("--lam-ij", type=float, default=Z.MZ.LAM_IJ)
    ap.add_argument("--horizon", type=float, default=24.0)
    ap.add_argument("--setback", action="store_true")
    ap.add_argument("--n-grid", type=int, default=NG)
    ap.add_argument("--price", type=float, default=None)
    ap.add_argument("--m", default="none", help="shared plant: only 'none' (independent units)")
    ap.add_argument("--budget-min", type=float, default=None,
                    help="stop (rc 0, cache saved) before starting a new window batch after this many minutes; "
                         "the next job of the chain resumes from results/mz_cache/ (jobq2 kills at 2 h)")
    ap.add_argument("--final", action="store_true",
                    help="last job of a chain: running out of budget is a failure (rc != 0)")
    a = ap.parse_args(argv)
    if a.m != "none":
        raise SystemExit("shared plant (m-limited) is DROPPED (RULING §5, D2)")
    city, topo, sb, hh = a.city, a.topology, a.setback, a.horizon
    price_v = F.TARIFFS["inforce"] if a.price is None else a.price
    par = mz_tuned(city, topo, a.lam_ij, sb)
    rule, sb_rule = (par[:2], par if sb else None)
    log = lambda s: print(s, flush=True)
    t0 = time.time()
    Ds = {w: Z.Dwelling(city, topo, w, None, sb, lam_ij=a.lam_ij) for w in F.TUNE_W}
    De = {w: Z.Dwelling(city, topo, w, None, sb, lam_ij=a.lam_ij) for w in F.EVAL_W}
    import v3_names as V
    name = (V.MZ_MPC.replace("riyadh", city).replace("_h{h:g}", "").format(topo=topo, lij=a.lam_ij)
            + ("_sb" if sb else "") + f"_h{hh:g}")
    cache = RunCache(f"{IO.R}/mz_cache/{name}{IO.tag()}.pkl",
                     dict(city=city, topo=topo, lij=a.lam_ij, sb=sb, hh=hh, n_grid=a.n_grid, price=price_v,
                          c_sw=F.C_SW, rule=list(par)),
                     None if a.budget_min is None else 60.0 * a.budget_min, log)
    try:
        lam, b, status, info, n_c = fit_mz(Ds, hh, rule, price_v, sb_rule, a.n_grid, log, cache)
        runs = None
        if lam is not None:
            f = lambda D, ls: mz_mpc_run(D, ls, hh, rule, price_v, sb_rule, a.n_grid, backoff=b)
            runs = {w: cache.run(("eval", float(b)), w, De[w], [lam], f)[0] for w in F.EVAL_W}
    except Budget:
        msg = f"{name}: budget of {a.budget_min:g} min reached; cache saved ({len(cache.rows)} rows)"
        if a.final:
            raise SystemExit(msg + " -- FINAL job of the chain: not finished") from None
        log(msg + "; the next job of the chain resumes")
        _progress(cache, "budget"); return
    common = dict(city=city, topology=topo, nz=Ds[F.TUNE_W[0]].nz, lam_ij=a.lam_ij, setback=sb,
                  units="independent", arm=f"MPC-MZ{hh:g}",
                  label="non-cooperative distributed MPC, one-step-delayed plan exchange "
                        "(no optimality guarantee)",
                  horizon_h=hh, n_grid=a.n_grid, price=price_v, c_sw=F.C_SW,
                  C_th=Ds[F.TUNE_W[0]].C / 1e3, rollout_rule=json.dumps(list(par)),
                  n_lams=n_c, knob="backoff" if b else "lambda", backoff=b)
    inputs = [f"{IO.ROOT}/{city}.epw"]
    if lam is None:
        log(f"{city} {topo} lij={a.lam_ij:g} sb={sb} MPC-MZ{hh:g}: no admissible lambda "
            f"(fit_status none; not tabulated) ({time.time() - t0:.0f}s)")
        IO.write_json(name + "_fit", dict(common, fit_status="none"), inputs=inputs, impl="mz_mpc.py")
        _progress(cache, "done_none"); return
    s, pw = Z.evaluate(De, runs, price_v)
    row = dict(common, lam=lam, **{**info, **s, "fit_status": status})
    log(f"{city} {topo} lij={a.lam_ij:g} sb={sb} MPC-MZ{hh:g} lam={lam:.4f} [{status}] "
        f"s_eq={s['s_pooled_eq']:+.2f}% s_raw={s['s_raw']:+.2f}% starts={s['start_sav_eq']:+.1f}% "
        f"E={s['energy_sav_eq']:+.1f}% fallback={s['fallback_steps']} ({time.time() - t0:.0f}s)")
    IO.write_csv(name, [row], inputs=inputs, impl="mz_mpc.py")
    IO.write_csv(name + "_perwindow", [dict(common, lam=lam, **r) for r in pw],
                 inputs=inputs, impl="mz_mpc.py")
    _progress(cache, "done")


if __name__ == "__main__":
    H.require_headline_dt("mz_mpc (ROLL = 96 steps)")
    main()
