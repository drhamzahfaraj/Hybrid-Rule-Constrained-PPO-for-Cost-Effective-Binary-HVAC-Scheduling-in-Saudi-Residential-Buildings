"""F10 (CLV) and F11 (bound) acceptance tests, short (RULING_round4 §3)."""
import os, sys
import numpy as np
import pytest

ROOT = os.environ.get("RBRL_ROOT", "/home/claude/rbrl")
sys.path.insert(0, ROOT)
import headroom as H
import final_tables as F
import r3_dp as D
import bound_v2 as B

K = F.MEAN_KEY


def test_up01_rounds_outward_only():
    assert B.up01(19.9) == 19.9 and B.up01(19.900000000001) == 20.0 and B.up01(19.81) == 19.9
    for x in np.linspace(10, 30, 997):
        assert B.up01(x) >= x


def test_grid_edges_cover_away_max_and_taif_h_le_riyadh():
    g = D.grid_for("riyadh", 121, True, 401)
    assert g[-1] >= H.AWAY_MAX + 0.1 - 1e-12 and abs(g[0] - 17.9) < 1e-12
    g0 = D.grid_for("riyadh", 121, False, 401)
    assert abs(g0[0] - (H.BAND_LO - 0.1)) < 1e-12 and abs(g0[-1] - (H.BAND_HI + 0.1)) < 1e-12
    hR = D.h_ref(401)
    for w in F.EVAL_W:
        assert np.diff(D.grid_for("riyadh", w, False, 401, h_max=hR)[:2])[0] == \
            np.diff(D.grid_for("riyadh", w, False, 401)[:2])[0]          # Riyadh unchanged
        assert np.diff(D.grid_for("taif", w, False, 401, h_max=hR)[:2])[0] <= hR + 1e-15


def test_relaxed_le_unrelaxed_pointwise():
    for lam in (0.0, 0.7, 3.0):
        r = D.lagrangian("taif", 289, 0.18, lam, relaxed=True, n_grid=401)["L"]
        u = D.lagrangian("taif", 289, 0.18, lam, relaxed=False, n_grid=401)["L"]
        assert r <= u + 1e-12


def test_clv_admissible_two_sided_and_certified():
    """CLV: admissible (F.admissible inside clv_fit), no fallback, never warmer than THERM + tol,
    resid within tol whenever tol_met; per-window certificate margin >= 0 against the relaxed
    per-window dual at THERM's mean; THERM itself also passes the certificate."""
    city, w = "taif", 289
    th = B.therm_eval(city, w, 0.18, False)          # J on the uniform O4 terminal, as the DP
    lam, r, info = D.clv_fit(city, w, 0.18, th[K], n_grid=801)
    assert r["fallback_steps"] == 0 and F.admissible(r, w)
    assert r[K] - th[K] <= D.CLV_TOL + 1e-12
    assert (abs(info["resid"]) <= D.CLV_TOL) == info["tol_met"]
    v, lw, _ = D.dual_max(lambda l: (D.lagrangian(city, w, 0.18, l, n_grid=401, relaxed=True)["L"], 7.0), th[K])
    assert D.certificate_margin(r["J"], r[K], v, lw, th[K]) >= 0
    assert D.certificate_margin(th["J"], th[K], v, lw, th[K]) >= 0


def test_ruled_bound_covers_in_rules_mpc_and_is_tighter():
    """ruled relaxed L(lam) <= J(in-rules MPC) + lam T_mpc / 7 (the ruled bound covers the arm);
    and free relaxed L <= ruled relaxed L (the ruled bound is the tighter one)."""
    import mpc_lambda as M
    city, w = "riyadh", 121
    m = M.mpc_lams(city, w, [0.5], 1.0, 201, rule=(23.5, 22.5), ruled=True)[0]
    assert m["fallback_steps"] == 0
    for lam in (0.0, 0.5, 2.0):
        Lr = D.lagrangian(city, w, 0.18, lam, relaxed=True, n_grid=401, ruled=True)["L"]
        Lf = D.lagrangian(city, w, 0.18, lam, relaxed=True, n_grid=401)["L"]
        assert Lr <= m["J"] + lam * m[K] / 7.0 + 1e-12
        assert Lf <= Lr + 1e-12


def test_ruled_cover_nesting():
    on, off = D.ruled_cover([(23.6, 22.4), (23.75, 22.3)])
    assert on == max(23.75, D.RULE_ON) and off == min(22.3, D.RULE_OFF)
    assert D.ruled_cover([]) == (D.RULE_ON, D.RULE_OFF)


def test_bound_at_s_le_B_and_certificate():
    import bound_at as BA
    curves = {"rel401": [(0.0, 1.0), (1.0, 4.4), (2.0, 7.7)], "unrel401": [(0.0, 9.0)]}
    rows = [dict(window=w, J_arm=1.25, J_eq=1.3, T_arm=23.0) for w in F.EVAL_W]
    o = BA.bound_for_arm(rows, curves)
    L = max(1.0, 4.4 - 23.0 / 7, 7.7 - 2 * 23.0 / 7)
    assert abs(o["B_a"] - 100 * (1 - L / 1.3)) < 1e-12 and o["s_le_B"]
    pwb = {w: dict(bound_J_w=1.0, lam_w=0.5, therm_T=23.0) for w in F.EVAL_W}
    assert abs(BA.bound_for_arm(rows, curves, pwb)["cert_min_margin"] - 0.25) < 1e-12


# ------------------------------------------------------------------ O4 (ruling §21.3)
def test_o4_uniform_terminal_bound_valid_and_consistent():
    """the uniform terminal adds c_sw/DELTA_CYCLE per K of T_N - T0 to the DP, the replay and
    THERM alike: relaxed <= unrelaxed; the dual bound at THERM's mean lower-bounds THERM's and the
    replay's uniform J; the replay's J = uniform_J(simulator J); energy terminal = the old DP."""
    city, w = "riyadh", 177
    th = B.therm_eval(city, w, 0.18, False)
    assert abs(th["J"] - D.uniform_J(th["J_energy_terminal"], th["T_end"], F.C_SW)) < 1e-15
    for lam in (0.0, 0.8, 2.5):
        Lr = D.lagrangian(city, w, 0.18, lam, relaxed=True, n_grid=401)["L"]
        Lu = D.lagrangian(city, w, 0.18, lam, relaxed=False, n_grid=401)["L"]
        assert Lr <= Lu + 1e-12
        assert Lr - lam * th[K] / 7.0 <= th["J"] + 1e-12
        Le = D.lagrangian(city, w, 0.18, lam, relaxed=True, n_grid=401, terminal="energy")["L"]
        assert Le != Lr
    rp = D.replay(city, w, 0.18, 0.8, n_grid=401)
    assert rp["terminal"] == "uniform"
    assert abs(rp["J"] - D.uniform_J(rp["J_energy_terminal"], rp["T_end"], F.C_SW)) < 1e-15
    assert rp["J"] >= D.lagrangian(city, w, 0.18, 0.8, relaxed=True, n_grid=401)["L"] - 0.8 * rp[K] / 7.0 - 1e-12


def test_o4_comparator_and_warm_end_penalty():
    city, w = "jeddah", 205
    th = B.therm_eval(city, w, 0.18, False)
    e = D.comparator_uniform(city, w, 0.18, th[K])
    assert e["J"] <= th["J"] + 1e-9                          # min-J crossing: delta = 0 is one crossing
    assert D.uniform_J(1.0, D.T0 + 1.0, 0.15) - D.uniform_J(1.0, D.T0, 0.15) == pytest.approx(0.15 / 7.0)
