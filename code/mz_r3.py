#!/usr/bin/env python3
"""Multi-zone dwelling under the round-4 protocol (RULING_round4 §2, §5, §10 D2, §12.1; F19).

Plant: the exact coupled RC model of multizone.py (matrix exponential, lambda_ij across a shared
wall, default 12.5 W/K, sweep {12.5, 35}), per-city TMYx weather, 15-min step, C_th / band / c_sw
from the one config (headroom / final_tables). INDEPENDENT PER-ROOM UNITS ONLY: every room has its
own 2 kW unit. The shared-plant (m-limited) variant is DROPPED (§5, D2): `m` must be None and
Dwelling.arbitrate is inert.

Topologies (zone index r*n + c, multizone.topology) and glazed-facade azimuths (deg from north):
  1x1  S                                  the single zone (reproduces setback.sim, test_mz_r3)
  1x2  S, W
  2x2  SE, SW, NE, NW  = [(180,90),(180,270),(0,90),(0,270)]   (R4 S4 fix: zone 0=(r0,c0) and
       2=(r1,c0) share a wall, so both are on the EAST side; the old list coupled diagonal rooms)
  1x4  S, S, N, N  (a realisable row; the old S, W, N, E "row" was not a floor plan, R4 S4 / F-1)

Comfort and matching (§2) on the DWELLING: post-step T_{k+1}; deg_h_over and the corrected cold
rule metrics are summed over zones and divided by nz (per-room mean); admissible iff zero over
and zero cooling-caused under in EVERY tuning window (HOOK(F6): F.admissible); the matching
temperature is the dwelling clipped occupied mean (Rule B), pooled within 0.03 K of THERM
(fallback 0.10 K); objective = equalised tuning cost ratio (A4); held-out scoring by Rule C
against THERM(delta_w) of the same dwelling (one convention, pooled saving). Per-zone clipped
means and their spread are reported beside the dwelling mean.

Arms (rules): THERM (every zone 22.5/23.5), TUNED (one (on, off) pair for all zones, A4 coarse
0.05 K then iterated 0.01 K), guard (on = cap - 0.20, off = LO + 0.40, cap fitted by A4).
The MZ-fitted TUNED pair is written for mz_mpc's rollout terminal and fallback (R5-6 (5)).

Usage (one job per topology; jobq2 / jobs/round4.jsonl format, cmd run from the repo root):
  python3 mz_r3.py rules <city> <topology> [--lam-ij 12.5] [--setback] [--price 0.18]
  -> results/T31_mz_rules_<city>_<topo>_lij<x>[_sb]{tag}.csv (+ _perwindow),
     results/mz_tuned_<city>_<topo>_lij<x>[_sb]{tag}.json
"""
from __future__ import annotations
import sys, os, csv, json, time, argparse
sys.path.insert(0, os.environ.get("RBRL_ROOT", "/home/claude/rbrl"))
import numpy as np
import headroom as H
import setback as S
import final_tables as F
import multizone as MZ

K = F.MEAN_KEY
LO, HI = H.BAND_LO, H.BAND_HI
T0 = 23.0
TOL = 1e-9
POOL_TOL, POOL_TOL_FALLBACK = 0.03, 0.10
GUARD_HOT, GUARD_OFF = 0.20, H.BAND_LO + 0.40          # as t1_v2 (single zone)
NAN = float("nan")                                       # one object: dict == stays reflexive
TOPOLOGIES = ("1x1", "1x2", "2x2", "1x4")

# facade azimuths per zone (deg from north); a tuple = the zone's glazed faces (irradiance averaged
# over them, as multizone.build counts faces)
AZ = {"1x1": [(180,)],
      "1x2": [(180,), (270,)],
      "2x2": [(180, 90), (180, 270), (0, 90), (0, 270)],
      "1x4": [(180,), (180,), (0,), (0,)]}
_IRR = {}


def zone_irr(city, topo, hours, w, year):
    from hvac import read_epw, vertical_irradiance
    key = (city, topo, year)
    if key not in _IRR:
        if year is None:
            tdb, dni, dhi = read_epw(f"/home/claude/rbrl/{city}.epw")
        else:
            rows = list(csv.DictReader(open(f"/home/claude/rbrl/amy/{city}_{year}.csv")))
            dni = np.array([float(r["dni_Wm2"]) for r in rows]); dhi = np.array([float(r["dhi_Wm2"]) for r in rows])
        per = []
        for azs in AZ[topo]:
            per.append(np.mean([vertical_irradiance(dni, dhi, H.CITIES[city], azimuth_deg=float(a)) for a in azs], axis=0))
        _IRR[key] = np.array(per)
    spd = int(round(1.0 / H.DT)); N = int(round(hours / H.DT)); h0 = w * 24
    return np.repeat(_IRR[key][:, h0:h0 + hours], spd, axis=1)[:, :N]


def geometry(topo, city, lam_ij=MZ.LAM_IJ):
    kind, n = {"1x1": ("single", 1), "1x2": ("linear", 2), "1x4": ("linear", 4),
               "2x2": ("grid", 2)}[topo]
    g = MZ.build(kind, n, city, lam_ij=lam_ij)
    assert g["nz"] == len(AZ[topo])
    return g


def _matvec(Mx, X):
    """X (..., nz) -> (..., nz) = X @ Mx.T, as explicit elementwise sums in a fixed order, so a row
    never depends on the batch it is in (BLAS kernels may change with the batch size; test 10)."""
    out = X[..., 0:1] * Mx[:, 0]
    for j in range(1, Mx.shape[1]):
        out = out + X[..., j:j + 1] * Mx[:, j]
    return out


class Dwelling:
    def __init__(self, city, topo, w, m=None, setback=False, year=None, lam_ij=MZ.LAM_IJ):
        if m is not None:
            raise ValueError("shared plant (m-limited) is DROPPED (RULING §5, D2): "
                             "independent per-room units only (m=None)")
        self.city, self.topo, self.w, self.m, self.setback = city, topo, w, None, setback
        self.g = geometry(topo, city, lam_ij); self.nz = self.g["nz"]; self.lam_ij = lam_ij
        self.C = self.g["c_th"]
        self.t_out, _, _ = (H.series(city, 168 + 48, w) if year is None
                            else H.series_amy(city, year, 168 + 48, w))
        self.irr = zone_irr(city, topo, 168 + 48, w, year)        # (nz, NN)
        self.N = 672
        NN = len(self.t_out)
        self.occ = S.occupancy(NN) if setback else np.ones(NN, bool)
        self.lo, self.hi = S.bands(self.occ, LO, HI, 18.0, H.AWAY_MAX)
        self.p_el = H.Q_HVAC / H.cop_series(self.t_out) / 1000.0
        import setback_arms as SA
        self.dnext = SA.steps_to_occ(self.occ)
        g = self.g
        f0 = (g["lam_env"][:, None] * self.t_out[None, :]
              + H.SHGC * H.A_GL * g["faces"][:, None] * self.irr) / self.C     # (nz, NN)
        self.Ti0 = (-g["Minv"] @ f0).T.copy()                                  # (NN, nz), u = 0
        self.B = g["Minv"] * (H.Q_HVAC / self.C)       # Ti(u) = Ti0 + B u  (since f has -Q u / C)
        self.A = g["A"]

    def arbitrate(self, u, T):
        return u                                        # independent units: inert (§5)

    def step(self, T, u, k):
        """Exact coupled update; T, u (..., nz)."""
        Ti = self.Ti0[k] + _matvec(self.B, np.asarray(u, float))
        return Ti + _matvec(self.A, T - Ti)

    def tinf0_min(self):
        """lowest all-off coupled equilibrium over the window (grid lower edge, R5-6 (4))."""
        return float(self.Ti0[:len(self.t_out)].min())

    def T_iz(self, T):
        liz = self.g["lam_iz"]
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(liz > 0, (self.g["L"] @ T) / np.where(liz > 0, liz, 1.0), T)

    def run(self, policy, price_v=None, c_sw=None):
        """Single policy(T (nz,), prev (nz,), k) -> u (nz,). Returns the run_batch dict (P = 1)."""
        r = self.run_batch(lambda T, prev, k: np.asarray(policy(T[0], prev[0], k), int)[None, :], 1,
                           price_v, c_sw)
        return row_of(r, 0)

    def run_batch(self, policy, P, price_v=None, c_sw=None):
        """P candidates in lock-step: policy(T (P, nz), prev (P, nz) int, k) -> u (P, nz)."""
        price_v = F.TARIFFS["inforce"] if price_v is None else price_v
        acc = Acc(self, P, price_v, c_sw)
        T = np.full((P, self.nz), T0); prev = np.zeros((P, self.nz), int)
        for k in range(self.N):
            u = np.asarray(policy(T, prev, k), int)
            T = acc.step(k, T, prev, u)
            prev = u
        return acc.result(T)


class Acc:
    """§2.1 metric accumulator shared by the rule arms (run_batch) and mz_mpc (P = #lambda)."""

    def __init__(self, D, P, price_v, c_sw=None):
        self.D, self.P, self.price_v = D, P, price_v
        self.swc = (F.C_SW if c_sw is None else c_sw) + price_v * H.E_START
        nz = D.nz
        self.J = np.zeros(P); self.E = np.zeros(P); self.starts = np.zeros(P)
        self.over = np.zeros(P); self.under = np.zeros(P); self.cmd = np.zeros(P); self.ff = np.zeros(P)
        self.Tsum = np.zeros(P); self.Tcl = np.zeros(P); self.Tz = np.zeros((P, nz)); self.cnt = 0
        self.tmax_away = np.full(P, -np.inf); self.n_away = 0
        self.fallback = np.zeros(P, int)

    def step(self, k, T, prev, u):
        D = self.D
        st = ((u == 1) & (prev == 0)).sum(1)
        self.J += self.swc * st + self.price_v * D.p_el[k] * H.DT * u.sum(1)
        self.E += D.p_el[k] * H.DT * u.sum(1) + H.E_START * st; self.starts += st
        T = D.step(T, u, k)
        self.cmd += (np.where(u == 1, np.maximum(0.0, LO - T - TOL), 0.0)).sum(1) * H.DT
        if D.occ[k]:
            self.over += np.maximum(0.0, T - D.hi[k] - TOL).sum(1) * H.DT
            self.under += np.maximum(0.0, D.lo[k] - T - TOL).sum(1) * H.DT
            self.ff += (np.where(u == 0, np.maximum(0.0, LO - T - TOL), 0.0)).sum(1) * H.DT
            cl = np.maximum(T, D.lo[k])
            self.Tsum += T.mean(1); self.Tcl += cl.mean(1); self.Tz += cl; self.cnt += 1
        else:
            self.tmax_away = np.maximum(self.tmax_away, T.max(1)); self.n_away += 1
        return T

    def result(self, T):
        D = self.D; nz = D.nz; d = D.N * H.DT / 24.0
        J = self.J + self.price_v * (T - T0).sum(1) * D.C / 3.6e6 / H.COP_RATED
        Tz = self.Tz / max(1, self.cnt)
        return dict(J=J / d / nz, E=self.E / d / nz, f_s=self.starts / d / nz, starts=self.starts,
                    deg_h_over=self.over / nz, deg_h_under=self.under / nz,
                    deg_h_occ=(self.over + self.under) / nz,
                    deg_h_cmd_under=self.cmd / nz, deg_h_ff_under=self.ff / nz,
                    T_mean_occ=self.Tsum / max(1, self.cnt), T_mean_occ_clip=self.Tcl / max(1, self.cnt),
                    T_zone_clip=Tz, T_zone_spread=Tz.max(1) - Tz.min(1),
                    T_end=T.mean(1),
                    T_max_away=(self.tmax_away if self.n_away else np.full(self.P, np.nan)),
                    fallback_steps=self.fallback.copy())


def row_of(res, i):
    """candidate i of a run_batch/mz_mpc dict as plain Python scalars (nan -> the one NAN object)."""
    out = {}
    for k, v in res.items():
        x = v[i]
        if np.ndim(x):
            out[k] = [float(y) for y in x]
        else:
            x = x.item() if hasattr(x, "item") else x
            out[k] = NAN if isinstance(x, float) and x != x else x
    return out


# ----------------------------------------------------------------- policies (batched)
def hyst_batch(on, off, nz):
    on = np.asarray(on, float)[:, None]; off = np.asarray(off, float)[:, None]
    def pol(T, prev, k):
        return np.where(T >= on, 1, np.where(T <= off, 0, prev))
    return pol


def sb_hyst_batch(on, off, L, D, nz):
    """setback rule: occupied (or within the lead L) thresholds, away thresholds tied to AWAY_MAX."""
    on = np.asarray(on, float)[:, None]; off = np.asarray(off, float)[:, None]
    L = np.asarray(L)[:, None]; a_on = H.AWAY_MAX - 0.2; a_off = a_on - 0.8
    def pol(T, prev, k):
        act = D.dnext[k] <= L
        return np.where(act, np.where(T >= on, 1, np.where(T <= off, 0, prev)),
                        np.where(T >= a_on, 1, np.where(T <= a_off, 0, prev)))
    return pol


def hyst_all(on_, off_):
    def pol(T, prev, k):
        return np.where(T >= on_, 1, np.where(T <= off_, 0, prev))
    return pol


def therm(D, delta=0.0, price_v=None):
    return D.run(hyst_all(H.THERM_SET + 0.5 + delta, H.THERM_SET - 0.5 + delta), price_v)


# ----------------------------------------------------------------- Rule C on the dwelling
DELTAS = np.round(np.arange(-0.4, 0.4 + 1e-12, 0.002), 6)
_CURVE = {}


def therm_curve(D, price_v=None):
    """THERM(delta) of this dwelling on the §2.3 delta grid, one batch: dict of raw (NOT
    monotone-ised) per-delta arrays (dwelling clipped mean K, J, E, f_s, delta) for F.equalise_curve."""
    price_v = F.TARIFFS["inforce"] if price_v is None else price_v
    key = (D.city, D.topo, D.w, D.setback, D.lam_ij, D.C, price_v, H.THERM_SET)
    if key not in _CURVE:
        r = D.run_batch(hyst_batch(H.THERM_SET + 0.5 + DELTAS, H.THERM_SET - 0.5 + DELTAS, D.nz),
                        len(DELTAS), price_v)
        _CURVE[key] = {K: np.asarray(r[K], float), "J": np.asarray(r["J"], float),
                       "E": np.asarray(r["E"], float), "f_s": np.asarray(r["f_s"], float),
                       "delta": DELTAS}
    return _CURVE[key]


def equalise(D, target, price_v=None):
    """Rule C on the dwelling mean: the shared helper F.equalise_curve (minimum-J crossing of the
    raw delta-grid curve, clipping against its true min/max; RULING §13.3)."""
    return F.equalise_curve(therm_curve(D, price_v), target, mean_key=K)


def admissible(r, w=None):
    """§2.2 condition 1 on one tuning window: the single helper F.admissible (F6)."""
    return bool(F.admissible(r, w))


def select(cand_rows, Ds, price_v):
    """A4 on the dwelling (shield.select_A4 with the dwelling's THERM curve and target)."""
    import shield as D1
    adm = {p: rr for p, rr in cand_rows.items() if all(admissible(rr[w], w) for w in rr)}
    tgt = float(np.mean([therm(Ds[w], 0.0, price_v)[K] for w in F.TUNE_W]))
    p, status, info = D1.select_A4(adm, Ds[F.TUNE_W[0]].city, price_v, windows=F.TUNE_W,
                                   jeq=lambda w, T: (lambda e: (e["J"], e["clipped"]))(equalise(Ds[w], T, price_v)),
                                   target=tgt)
    return p, status, info


def evaluate(D_eval, runs, price_v=None):
    """Rule C on EVAL_W: pooled equalised saving, s_raw, §2.1 metrics, per-zone spread."""
    pw = []
    for w in F.EVAL_W:
        D = D_eval[w]; a = runs[w]; th0 = therm(D, 0.0, price_v); e = equalise(D, a[K], price_v)
        pw.append(dict(window=w, J_arm=a["J"], J_eq=e["J"], J_therm0=th0["J"], delta_w=e["delta"],
                       bracket_gap=e["bracket_gap"], eq_clipped=e["clipped"],
                       n_crossings=int(e["n_crossings"]), J_eq_max=float(e["J_eq_max"]),
                       T_arm=a[K], T_therm0=th0[K], dT_w=a[K] - th0[K],
                       fs_arm=a["f_s"], fs_eq=e["f_s"], E_arm=a["E"], E_eq=e["E"],
                       deg_h_over=a["deg_h_over"], deg_h_under=a["deg_h_under"],
                       deg_h_cmd_under=a["deg_h_cmd_under"], deg_h_ff_under=a["deg_h_ff_under"],
                       T_end=a["T_end"], T_max_away=a["T_max_away"], fallback_steps=a["fallback_steps"],
                       T_zone_spread=a["T_zone_spread"],
                       **{f"T_clip_z{i}": t for i, t in enumerate(a["T_zone_clip"])}))
    S_ = lambda k: [r[k] for r in pw]
    nz = len(runs[F.EVAL_W[0]]["T_zone_clip"])
    s = dict(n_eval=len(pw), fit_windows="TUNE_W",
             s_pooled_eq=F.pooled_saving(S_("J_arm"), S_("J_eq")),
             s_raw=F.pooled_saving(S_("J_arm"), S_("J_therm0")),
             s_eq_minJ=F.pooled_saving(S_("J_arm"), S_("J_eq")),
             s_eq_maxJ=F.pooled_saving(S_("J_arm"), S_("J_eq_max")),
             n_eq_multi=int(sum(n > 1 for n in S_("n_crossings"))),
             start_sav_eq=F.pooled_saving(S_("fs_arm"), S_("fs_eq")),
             energy_sav_eq=F.pooled_saving(S_("E_arm"), S_("E_eq")),
             dT_pooled=float(np.mean(S_("dT_w"))), max_abs_dT_w=float(max(abs(x) for x in S_("dT_w"))),
             max_bracket_gap=float(max(S_("bracket_gap"))), n_eq_clipped=int(sum(S_("eq_clipped"))),
             deg_h_over=float(sum(S_("deg_h_over"))), deg_h_under=float(sum(S_("deg_h_under"))),
             deg_h_cmd_under=float(sum(S_("deg_h_cmd_under"))),
             deg_h_ff_under=float(sum(S_("deg_h_ff_under"))),
             T_end_mean=float(np.mean(S_("T_end"))), fallback_steps=int(sum(S_("fallback_steps"))),
             T_zone_spread_mean=float(np.mean(S_("T_zone_spread"))),
             **{f"T_clip_z{i}_mean": float(np.mean(S_(f"T_clip_z{i}"))) for i in range(nz)})
    if any(np.isfinite(x) for x in S_("T_max_away")):
        s["T_max_away"] = float(np.nanmax(S_("T_max_away")))
    return s, pw


# ----------------------------------------------------------------- fitting (A4)
def _pairs(on_v, off_v):
    return [(round(float(a), 2), round(float(b), 2)) for a in on_v for b in off_v
            if a - b >= 0.1 - 1e-9 and a <= HI + 1e-9 and b >= LO - 1e-9]


def _tune_rows(Ds, cands, make_pol, price_v):
    rows = {}
    for w in F.TUNE_W:
        r = Ds[w].run_batch(make_pol(cands, Ds[w]), len(cands), price_v)
        for i, p in enumerate(cands):
            rows.setdefault(p, {})[w] = row_of(r, i)
    return rows


def fit_tuned(Ds, price_v, sb=False, step=0.05):
    """TUNED (on, off[, lead]) by A4: coarse 0.05 K grid, then iterated 0.01 K refinement around the
    optimum until it is interior (the single-zone search procedure, §5 extension 6)."""
    nz = Ds[F.TUNE_W[0]].nz
    leads = list(range(0, 25, 4)) if sb else [None]

    def make(cands, D):
        on = [c[0] for c in cands]; off = [c[1] for c in cands]
        if sb:
            return sb_hyst_batch(on, off, [c[2] for c in cands], D, nz)
        return hyst_batch(on, off, nz)

    def expand(pairs):
        return [p + (L,) for p in pairs for L in leads] if sb else pairs
    grid = np.arange(LO, HI + 1e-9, step)
    best, status, info = select(_tune_rows(Ds, expand(_pairs(grid, grid)), make, price_v), Ds, price_v)
    if best is None:
        return None, "none", info
    nb = np.round(np.arange(-0.05, 0.0501, 0.01), 2)
    for _ in range(8):
        cands = _pairs(best[0] + nb, best[1] + nb)
        cands = [c + (best[2],) for c in cands] if sb else cands
        nbest, nstatus, ninfo = select(_tune_rows(Ds, cands, make, price_v), Ds, price_v)
        if nbest is None or nbest == best:
            break
        best, status, info = nbest, nstatus, ninfo
    return best, status, info


def fit_guard(Ds, price_v):
    nz = Ds[F.TUNE_W[0]].nz
    caps = [round(float(c), 2) for c in np.arange(HI - 0.50, HI + 1e-9, 0.01)]
    make = lambda cands, D: hyst_batch([c - GUARD_HOT for c in cands], [GUARD_OFF] * len(cands), nz)
    return select(_tune_rows(Ds, caps, make, price_v), Ds, price_v)


def tag(topo, lam_ij, sb):
    return f"{topo}_lij{lam_ij:g}{'_sb' if sb else ''}"


def main_rules(city, topo, lam_ij=MZ.LAM_IJ, sb=False, price_v=None):
    import rbrl_io as IO
    price_v = F.TARIFFS["inforce"] if price_v is None else price_v
    t0 = time.time()
    Ds = {w: Dwelling(city, topo, w, None, sb, lam_ij=lam_ij) for w in F.TUNE_W}
    De = {w: Dwelling(city, topo, w, None, sb, lam_ij=lam_ij) for w in F.EVAL_W}
    nz = Ds[F.TUNE_W[0]].nz
    out, perw, params = [], [], {}
    common = dict(city=city, topology=topo, nz=nz, lam_ij=lam_ij, setback=sb, units="independent",
                  price=price_v, c_sw=F.C_SW, C_th=Ds[F.TUNE_W[0]].C / 1e3)
    # THERM: no parameter; scored by the same Rule C (s = 0 up to bracket interpolation)
    runs = {w: therm(De[w], 0.0, price_v) for w in F.EVAL_W}
    s, pw = evaluate(De, runs, price_v)
    out.append(dict(common, arm="THERM", params=json.dumps([H.THERM_SET + 0.5, H.THERM_SET - 0.5]),
                    fit_status="reference", **s))
    perw += [dict(common, arm="THERM", **r) for r in pw]
    for arm in ("TUNED", "guard"):
        if arm == "TUNED":
            best, status, info = fit_tuned(Ds, price_v, sb)
        else:
            best, status, info = fit_guard(Ds, price_v)
        if best is None:
            print(f"{city} {topo} lij={lam_ij:g} sb={sb} {arm}: no admissible parameter "
                  f"(fit_status none; not tabulated)", flush=True)
            continue
        if arm == "TUNED":
            pol = (sb_hyst_batch([best[0]], [best[1]], [best[2]], None, nz) if sb
                   else hyst_batch([best[0]], [best[1]], nz))
            par = list(best)
        else:
            pol = hyst_batch([best - GUARD_HOT], [GUARD_OFF], nz); par = [best - GUARD_HOT, GUARD_OFF]
        runs = {}
        for w in F.EVAL_W:
            p = (sb_hyst_batch([best[0]], [best[1]], [best[2]], De[w], nz) if (sb and arm == "TUNED")
                 else pol)
            runs[w] = row_of(De[w].run_batch(p, 1, price_v), 0)
        s, pw = evaluate(De, runs, price_v)
        out.append(dict(common, arm=arm, params=json.dumps([float(x) for x in par]),
                        **{**info, **s, "fit_status": status}))
        perw += [dict(common, arm=arm, **r) for r in pw]
        if arm == "TUNED":
            params = dict(on=float(best[0]), off=float(best[1]), fit_status=status,
                          lead=(int(best[2]) if sb else None), city=city, topology=topo,
                          lam_ij=lam_ij, setback=sb, C_th=common["C_th"], c_sw=F.C_SW)
        print(f"{city} {topo} lij={lam_ij:g} sb={sb} {arm} {par} [{status}] "
              f"s_eq={s['s_pooled_eq']:+.2f}% s_raw={s['s_raw']:+.2f}% dT={s['dT_pooled']:+.4f} "
              f"over={s['deg_h_over']:.3f} cmd={s['deg_h_cmd_under']:.3f} "
              f"spread={s['T_zone_spread_mean']:.3f} ({time.time() - t0:.0f}s)", flush=True)
    inputs = [f"{IO.ROOT}/{city}.epw"]
    import v3_names as V
    name = V.MZ_RULES.replace("riyadh", city).format(topo=topo, lij=lam_ij) + ("_sb" if sb else "")
    assert name == f"T31_mz_rules_{city}_{tag(topo, lam_ij, sb)}"
    IO.write_csv(name, out, inputs=inputs, impl="mz_r3.py")
    IO.write_csv(name + "_perwindow", perw, inputs=inputs, impl="mz_r3.py")
    if params:
        IO.write_json(f"mz_tuned_{city}_{tag(topo, lam_ij, sb)}", params, inputs=inputs, impl="mz_r3.py")
    return out


# ----------------------------------------------------------------- RBRL-MZ: DROPPED
def main_rbrl(*a, **k):
    raise SystemExit("RBRL-MZ is DROPPED (RULING_round4 §5, D2). The round-3 code is in git "
                     "history (d9494c4, mz_r3.py:248-338); it is not run and not reported.")


def cli(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=("rules", "rbrl"))
    ap.add_argument("city"); ap.add_argument("topology", choices=TOPOLOGIES)
    ap.add_argument("--lam-ij", type=float, default=MZ.LAM_IJ)
    ap.add_argument("--setback", action="store_true")
    ap.add_argument("--price", type=float, default=None)
    ap.add_argument("--m", default="none", help="shared plant: only 'none' (independent units)")
    a = ap.parse_args(argv)
    if a.m != "none":
        raise SystemExit("shared plant (m-limited) is DROPPED (RULING §5, D2)")
    if a.mode == "rbrl":
        main_rbrl()
    main_rules(a.city, a.topology, a.lam_ij, a.setback, a.price)


if __name__ == "__main__":
    H.require_headline_dt("mz_r3 (N = 672 steps)")
    cli()
