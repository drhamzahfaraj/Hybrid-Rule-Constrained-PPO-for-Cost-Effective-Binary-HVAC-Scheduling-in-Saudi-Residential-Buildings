"""F5 (ruling round 4, Sec. 2.1/3): the corrected cold rule.

  "A cooling step may never end below T_min (the occupied lower limit), at every
   step including away; switching off / free float is always allowed."

Run: cd /home/claude/rbrl && OMP_NUM_THREADS=1 nice python3 -I -m pytest -q tests/test_core_f5.py
(about 30 s on one core)."""
import os, sys
import numpy as np
import pytest

ROOT = os.environ.get("RBRL_ROOT", "/home/claude/rbrl")
sys.path.insert(0, ROOT)
import headroom as H
import setback as S
import final_tables as F
import r3_dp as D
import mpc_lambda as M

LAM_TAIF = {6.0: 0.230547, 24.0: 0.231759}      # T21v2 Taif lam (perfect forecast)


def _sb_ctx(city, w):
    N = 672
    occ = S.occupancy(N)
    lo, hi = S.bands(occ, H.BAND_LO, H.BAND_HI, 18.0, H.AWAY_MAX)
    return N, occ, lo, hi, H.price_flat(N, 0.18)


def _replay_actions(city, w, acts, occ, lo, hi, price):
    a = np.asarray(acts, int)
    return S.sim(lambda T, p, k: a[k], city, F.FACES, F.C_TH, price, lo, hi, occ, 168, w,
                 F.T0, c_sw=F.C_SW, record=True)


def test_step_ok_predicate():
    # u=1 may never end below T_min, occupied (hi=24) or away (hi=AWAY_MAX)
    assert not D.step_ok(21.95, 1, H.BAND_HI) and not D.step_ok(21.95, 1, H.AWAY_MAX)
    assert D.step_ok(22.0, 1, H.BAND_HI)
    # u=0 has no lower limit, at any state and any free-float equilibrium
    assert D.step_ok(18.0, 0, H.BAND_HI) and D.step_ok(21.95, 0, H.AWAY_MAX)
    # upper limit applies to both actions; relaxed tolerance widens both sides
    assert not D.step_ok(24.01, 0, H.BAND_HI) and D.step_ok(24.004, 0, H.BAND_HI, hh=0.005)
    assert D.step_ok(21.996, 1, H.BAND_HI, hh=0.005)
    # vectorised
    ok = D.step_ok(np.array([21.9, 22.5, 24.5]), 1, 24.0)
    assert ok.tolist() == [False, True, False]


def test_precool_then_coast_is_out_of_domain_and_never_chosen():
    """(a) Pre-cool below the band while away, then coast: excluded from D, and
    neither the setback CLV (replay of the Lagrangian DP) nor the setback MPC
    produces it. (Under the round-3 predicate the same CLV cooled to below
    22 C while away: 0.71 K h of commanded under-temperature at lam=0.)"""
    city, w = "riyadh", 121
    N, occ, lo, hi, price = _sb_ctx(city, w)

    def precool(T, prev, k):
        if not occ[k]:
            return int(T > 21.0)          # cool deep while away, then coast
        return 1 if T >= 23.5 else (0 if T <= 22.5 else prev)
    r = S.sim(precool, city, F.FACES, F.C_TH, price, lo, hi, occ, 168, w, F.T0,
              c_sw=F.C_SW, record=True)
    ok, info = S.in_domain(r["u"], r["T_next"], occ, hi)
    assert not ok and info["n_cmd_under"] > 0 and r["deg_h_cmd_under"] > 0

    for lam in (0.0, 0.5):
        c = D.replay(city, w, 0.18, lam, setback=True, n_grid=1601, record=True)
        ok, info = S.in_domain(c["u"], c["T_next"], occ, hi)
        assert ok, info
        assert c["deg_h_cmd_under"] == 0.0 and c["fallback_steps"] == 0

    m = M.mpc_lams(city, w, [0.0], 6.0, 801, setback=True, sb_rule=(23.6, 22.35, 8),
                   return_actions=True)[0]
    assert m["deg_h_cmd_under"] == 0.0 and m["fallback_steps"] == 0
    rr = _replay_actions(city, w, m["actions"], occ, lo, hi, price)
    assert abs(rr["J"] - m["J"]) < 1e-9
    ok, info = S.in_domain(rr["u"], rr["T_next"], occ, hi)
    assert ok, info


@pytest.mark.parametrize("w", [121, 289])
def test_therm_and_guard_in_domain_taif(w):
    """(b) THERM and the guard drift below 22 C in Taif (w289: 0.156 / 0.339 K h)
    by free float only, so they lie inside D (the round-3 predicate excluded
    3 / 4 of their steps in w289)."""
    city = "taif"
    N, occ, lo, hi = F._ctx(city, w, False)
    price = H.price_flat(N, 0.18)
    for pol in (S.hyst_abs(H.THERM_SET + 0.5, H.THERM_SET - 0.5), S.hyst_abs(23.66, 22.4)):
        r = S.sim(pol, city, F.FACES, F.C_TH, price, lo, hi, occ, 168, w, F.T0,
                  c_sw=F.C_SW, record=True)
        ok, info = S.in_domain(r["u"], r["T_next"], occ, hi)
        assert ok, info
        assert r["deg_h_cmd_under"] == 0.0
        assert abs(r["deg_h_under"] - r["deg_h_ff_under"]) < 1e-12


@pytest.mark.parametrize("w", [121, 289])
def test_no_fallback_mpc_clv_taif(w):
    """(c) fallback_steps = 0 for the MPC and the CLV replay (short check)."""
    city = "taif"
    # the TUNED rollout base, as tuned_params_v2 holds it (read raw: the file is regenerated with
    # provenance by J2; mpc_lambda.tuned_rule refuses files without a .meta.json, V-code-22 (4))
    import json
    p = json.load(open(f"{ROOT}/results/tuned_params_v2.json"))[f"{city}|inforce|TUNED"]
    m = M.mpc_lams(city, w, [LAM_TAIF[6.0]], 6.0, 801, rule=(p["on"], p["off"]))[0]
    assert m["fallback_steps"] == 0 and m["deg_h_cmd_under"] == 0.0
    c = D.replay(city, w, 0.18, LAM_TAIF[24.0], n_grid=1601)
    assert c["fallback_steps"] == 0 and c["deg_h_cmd_under"] == 0.0


def test_lagrangian_ordering_14():
    """(d) test 14: relaxed L <= unrelaxed L <= replay J + lam (mean - T*), per day.
    The first and the relaxed-vs-replay inequality are theorems. Unrelaxed <=
    replay is NOT a theorem: linear interpolation of V on the grid over-estimates
    a convex cost-to-go; it is checked to a grid tolerance (measured gap in Taif
    w121: 2.3e-4 SAR/day = 0.08 %, identical before F5)."""
    city, lam = "taif", LAM_TAIF[24.0]
    for w in (121, 289):
        Ts = F.therm_run(city, w, 0.18)[F.MEAN_KEY]
        Lr = D.lagrangian(city, w, 0.18, lam, relaxed=True, n_grid=1601)
        Lu = D.lagrangian(city, w, 0.18, lam, relaxed=False, n_grid=1601)
        rp = D.replay(city, w, 0.18, lam, n_grid=1601)
        d = Lu["days"]
        a, b = Lr["L"] - lam * Ts / d, Lu["L"] - lam * Ts / d
        c = rp["J"] + lam * (rp[F.MEAN_KEY] - Ts) / d
        assert a <= b + 1e-12 and a <= c + 1e-12
        assert b <= c + 2e-3 * abs(c), (w, a, b, c)
