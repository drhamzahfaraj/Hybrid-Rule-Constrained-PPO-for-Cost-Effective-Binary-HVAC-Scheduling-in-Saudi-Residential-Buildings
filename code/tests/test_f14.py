"""F14 setback acceptance tests, short (RULING_round4 §3 F14, SPEC_building_energy F-3/F-4, R5-7)."""
import os, sys, subprocess, inspect
import numpy as np
import pytest

ROOT = os.environ.get("RBRL_ROOT", "/home/claude/rbrl")
sys.path.insert(0, ROOT)
import config as CFG
import headroom as H
import setback as S
import final_tables as F
import setback_arms as SA

W2 = F.TUNE_W[:2]


def test_tuned_sb_tuning_cost_le_tuned():
    """nesting: TUNED's own pair without setback is a candidate, so TUNED-SB's A4 standing on the
    tuning windows is never worse than TUNED's (same objective, setback comparator)."""
    t = F.tune_rule("riyadh", CFG.PRICE, W2)
    b, st = SA.fit_rule("riyadh", windows=W2, tuned=(t[1], t[2]))
    tp = (round(t[1], 2), round(t[2], 2), SA.NO_SB, SA.AWAY_ON)
    rows = SA._rows_sb_batch("riyadh", W2, [tp, b[1]])
    s_t, s_b = F.score_candidates([tp, b[1]], rows, "riyadh", CFG.PRICE, W2, setback=True)
    assert not F.better_than(s_t, s_b)
    assert s_b["status"] == st and abs(s_b["obj"] - b[0]) < 1e-12
    assert b[1][3] == SA.AWAY_ON == CFG.AWAY_MAX - 0.2       # away thresholds tied to AWAY_MAX
    assert b.info["n_rounds"] >= 1


def test_batch_equals_run_rule_for_fixed_arms_and_no_setback():
    cands = list(SA.fixed_arms().values()) + [(23.6, 22.4, SA.NO_SB, SA.AWAY_ON), (23.6, 22.4, 4, SA.AWAY_ON)]
    w = F.EVAL_W[1]
    N, occ, lo, hi, _ = SA.ctx("riyadh", w)
    mask = F.lead_mask(S.occupancy(N + 200), np.array([c[2] for c in cands]), N)
    a_on = np.array([c[3] for c in cands], float)
    R = F.sim_hyst_batch("riyadh", w, CFG.PRICE, [c[0] for c in cands], [c[1] for c in cands],
                         occ=occ, lo=lo, hi=hi, active=mask, on_away=a_on, off_away=a_on - 0.8)
    for i, c in enumerate(cands):
        r = SA.run_rule("riyadh", w, *c)
        for k in ("J", "f_s", "E", F.MEAN_KEY, "T_end", "T_max_away", "deg_h_over"):
            assert abs(R[k][i] - r[k]) <= 1e-12, (c, k)
    man = SA.run_rule("riyadh", w, *SA.fixed_arms()["MANUAL"])
    assert np.isfinite(man["T_max_away"]) and man["T_max_away"] > SA.therm_sb("riyadh", w, 0.0)["T_max_away"]
    # no setback == the all-occupied rule on the same plant (cost and starts)
    nos = SA.run_rule("riyadh", w, 23.6, 22.4, SA.NO_SB)
    assert abs(nos["J"] - F.rule_run("riyadh", w, CFG.PRICE, 23.6, 22.4)["J"]) <= 1e-12


def test16_all_occupied_mpc_sb_equals_mpc(monkeypatch):
    import mpc_lambda as M
    rule = (23.6, 22.4)
    ref = M.mpc_lams("riyadh", 121, [0.3, 1.0], 1.0, 201, rule=rule, N=192)
    monkeypatch.setattr(S, "occupancy", lambda N, *a, **k: np.ones(N, bool))
    sb = M.mpc_lams("riyadh", 121, [0.3, 1.0], 1.0, 201, setback=True, sb_rule=rule + (4, SA.AWAY_ON), N=192)
    for a, b in zip(ref, sb):
        for k, v in a.items():
            if isinstance(v, float) and np.isnan(v):
                assert np.isnan(b[k]); continue
            assert v == b[k], k


def test_tail_schedule_is_the_tail_steps_own():
    """R5-7: the rollout tail reads occupancy / lead at the tail steps themselves (end .. end+95)."""
    import mpc_lambda as M
    src = inspect.getsource(M.mpc_lams)
    assert "sched = np.arange(end, end + ROLL)" in src and "dnext[js]" in src and "occ_x[js]" in src


def test_vacation_repool():
    pw = [dict(window=w, J_arm=1.0, J_eq=2.0) for w in F.EVAL_W]
    alt = {w: dict(J_arm="1.5", J_eq="2.0") for w in SA.VAC_W}
    s = SA.vacation_repool(pw, alt)
    assert abs(s - 100 * (1 - (4 * 1.0 + 3 * 1.5) / 14.0)) < 1e-12
    assert set(SA.VAC_W) <= set(F.EVAL_W)


@pytest.mark.parametrize("cmd", [["rbrl_sb.py"], ["rbrl_ppo.py", "--setback", "--cities", "riyadh"]])
def test_dropped_rbrl_sb_refuses(cmd):
    p = subprocess.run([sys.executable, "-I", "-B", *cmd], cwd=ROOT, capture_output=True, text=True,
                       env=dict(os.environ, OMP_NUM_THREADS="1"), timeout=120)
    assert p.returncode != 0 and "dropped arm" in p.stderr
