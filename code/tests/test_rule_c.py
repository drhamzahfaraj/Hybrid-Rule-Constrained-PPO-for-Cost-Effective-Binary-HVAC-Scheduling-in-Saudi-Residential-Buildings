"""RULING_round4 §13 (V-code-24/25): one Rule C helper, minimum-J crossing, true-extreme clipping.

Run: cd /home/claude/rbrl && OMP_NUM_THREADS=1 nice python3 -m pytest -q tests/test_rule_c.py
"""
import os, sys
import numpy as np

sys.path.insert(0, os.environ.get("RBRL_ROOT", "/home/claude/rbrl"))
import final_tables as F


def _old_bisection(m, J, T):
    """the pre-§13 final_tables._bracket + j_eq (reference for the monotone case)."""
    a, b = 0, len(m) - 1
    if not (m[a] <= T <= m[b]):
        e = a if T < m[a] else b
        return float(J[e]), True
    while b - a > 1:
        k = (a + b) // 2
        if m[k] <= T:
            a = k
        else:
            b = k
    span = m[b] - m[a]
    t = 0.0 if span <= 1e-12 else (T - m[a]) / span
    return float(J[a] + t * (J[b] - J[a])), False


def test_a_three_crossings_min_J():
    d = np.arange(7) * 0.1
    m = np.array([0.0, 1.0, 2.0, 1.0, 2.0, 1.5, 3.0])    # T = 1.25 crosses 3 segments + none exact
    J = np.array([9.0, 8.0, 7.0, 6.5, 5.0, 4.0, 3.0])
    rc = F.rule_c(m, J, 1.25, d)
    # crossings: seg 1-2 (t=.25, J=7.75), seg 2-3 (t=.75, J=6.625), seg 3-4 (t=.25, J=6.125)
    assert rc["n_crossings"] == 3 and not rc["clipped"]
    assert abs(rc["J"] - 6.125) < 1e-12 and (rc["a"], rc["b"]) == (3, 4)
    assert abs(rc["J_max"] - 7.75) < 1e-12 and abs(rc["delta"] - 0.325) < 1e-12
    # other metrics use the SAME crossing
    E = np.arange(7, dtype=float) * 10
    assert abs(F.lerp(E, rc) - 32.5) < 1e-12
    c = {F.MEAN_KEY: m, "J": J, "E": E, "f_s": E, "delta": d}
    e = F.equalise_curve(c, 1.25)
    assert e["J"] == rc["J"] and e["E"] == F.lerp(E, rc) and e["n_crossings"] == 3
    assert e["J_eq_max"] == rc["J_max"] and abs(e["resid"]) < 1e-12 and abs(e["bracket_gap"] - 1.0) < 1e-12
    # an exact grid hit counts once (t = 0); T = 2.0 hits points 2 and 4 and segment 5-6
    rc2 = F.rule_c(m, J, 2.0, d)
    assert rc2["n_crossings"] == 3 and rc2["J"] == 4.0 + (0.5 / 1.5) * (3.0 - 4.0) and rc2["J_max"] == 7.0


def test_b_monotone_identical_to_bisection():
    rng = np.random.default_rng(0)
    m = np.cumsum(rng.uniform(1e-4, 5e-3, 401)) + 22.0
    J = 1.3 - np.cumsum(rng.uniform(0, 1e-3, 401))
    Ts = np.concatenate([rng.uniform(m[0], m[-1], 500), m[[0, 7, 200]], [m[0] - 0.1, m[-1] + 0.1]])
    for T in Ts:
        rc = F.rule_c(m, J, T)
        j0, c0 = _old_bisection(m, J, T)
        assert rc["J"] == j0 and rc["clipped"] == c0, T          # bit for bit
        assert rc["n_crossings"] == (0 if c0 else 1) and rc["J_max"] == rc["J"]


def test_c_clipping_uses_true_extremes():
    d = np.arange(5) * 0.1
    m = np.array([1.0, 0.5, 2.0, 3.0, 2.5])                  # ends 1.0 / 2.5 are not the extremes
    J = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    for T, clipped in ((0.7, False), (2.8, False), (0.4, True), (3.1, True)):
        rc = F.rule_c(m, J, T, d)
        assert rc["clipped"] == clipped, T
    lo, hi = F.rule_c(m, J, 0.4, d), F.rule_c(m, J, 3.1, d)
    assert lo["a"] == 1 and lo["J"] == 4.0 and hi["a"] == 3 and hi["J"] == 2.0
    assert lo["n_crossings"] == hi["n_crossings"] == 0
    # the old end-point test would have clipped T = 2.8 to the last point
    assert _old_bisection(m, J, 2.8)[1]


def test_c_real_curve_is_nonmonotone_and_selection_equals_evaluation():
    w = F.TUNE_W[0]
    m, J = F.therm_curve("riyadh", w, 0.18)
    assert np.any(np.diff(m) < 0)
    for T in np.linspace(m.min() - 0.05, m.max() + 0.05, 41):
        e = F.equalise("riyadh", w, 0.18, T)
        rc = F.j_eq("riyadh", w, 0.18, T, full=True)
        assert e["J"] == rc["J"] and e["clipped"] == rc["clipped"] and e["n_crossings"] == rc["n_crossings"]
        assert e["J"] <= e["J_eq_max"] and (e["clipped"] or e["resid"] < 1e-9)


def test_d_mz_1x1_equals_single_zone():
    import mz_r3 as Z
    w = F.EVAL_W[0]
    D = Z.Dwelling("riyadh", "1x1", w)
    a = F.rule_run("riyadh", w, 0.18, 23.7, 22.3)
    for T in (a[F.MEAN_KEY], F.therm_run("riyadh", w, 0.18)[F.MEAN_KEY] + 1e-4):
        z = Z.equalise(D, T, 0.18)
        s = F.equalise("riyadh", w, 0.18, T)
        assert z["n_crossings"] == s["n_crossings"] and z["clipped"] == s["clipped"]
        for k in ("J", "E", "f_s", "delta", "J_eq_max"):
            assert abs(z[k] - s[k]) <= 1e-8, (k, z[k], s[k])


def test_e_a4_nests_therm():
    """THERM is a TUNED candidate: TUNED's A4 objective <= THERM's. THERM's own objective is
    exactly 1 on W1 (delta = 0 is the cheapest crossing there) and never < 1 elsewhere
    (min-J comparator: THERM's own saving is <= 0)."""
    W1 = [F.TUNE_W[0]]
    g = F.fit_param([(23.5, 22.5)], lambda p, w: F.rule_run("riyadh", w, 0.18, *p), W1,
                    city="riyadh", price_v=0.18)
    assert g[0] == 1.0 and g.info["tune_saving"] == 0.0
    f = F.tune_rule("riyadh", 0.18, W1)
    assert f[0] <= g[0]
    for w in F.TUNE_W:
        th = F.therm_run("riyadh", w, 0.18)
        assert F.j_eq("riyadh", w, 0.18, th[F.MEAN_KEY])[0] <= th["J"] + 1e-12
