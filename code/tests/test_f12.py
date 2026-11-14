"""F12 (E2 env) and E1, short tests (RULING_round4 §3 F12)."""
import os, sys
import numpy as np
import pytest

ROOT = os.environ.get("RBRL_ROOT", "/home/claude/rbrl")
sys.path.insert(0, ROOT)
import config as CFG
import final_tables as F
import rbrl_e2 as E2


def test_e1_hold_is_the_lambda0_optimum():
    """E1: with lam = 0 the in-rule optimum is hold: J(hold) <= 1.01 J_DP on TUNE_W (Riyadh)."""
    r = E2.e1_rows(("riyadh",), n_grid=801)[0]
    assert r["ratio_hold_dp"] <= 1.01 and r["J_hold"] >= r["L_relaxed"] - 1e-12


@pytest.mark.parametrize("lam", [0.0, 1.3])
def test_e2_reward_is_the_simulator_objective(lam):
    """holding the previous action under R1/R2 in E2Env reproduces the guard hysteresis of the
    simulator: sum of rewards = -(7 J + lam * clipped mean) exactly (to rounding)."""
    w = F.TUNE_W[1]
    env = E2.E2Env("riyadh", [w], CFG.PRICE, lam)
    o, _ = env.reset(options={"window": w}); done = False; R = 0.0
    assert o.shape == (E2.N_OBS,) and o.dtype == np.float32
    while not done:
        o, r, done, _, _ = env.step(int(o[1]))           # a = prev (hold)
        R += r
    ref = F.rule_run("riyadh", w, CFG.PRICE, E2.R1, E2.R2)
    assert abs(R + 7.0 * ref["J"] + lam * ref[F.MEAN_KEY]) < 1e-9


def test_e2_forecast_features_are_perfect():
    import headroom as H
    w = F.EVAL_W[0]
    t, i, _ = H.series("riyadh", 168 + E2.EXTRA_H, w)
    o = E2.obs_vec(23.0, 0, 10, 672, t, i)
    assert np.allclose(o[8:12], (t[[14, 18, 22, 34]] - 35.0) / 10.0, atol=1e-6)
    assert np.allclose(o[12:], i[[14, 22]] / 500.0, atol=1e-6)


def test_numpy_policy_on_visited_float32_states():
    pytest.importorskip("stable_baselines3")
    from stable_baselines3 import PPO
    env = E2.E2Env("riyadh", [F.TUNE_W[0]], CFG.PRICE, 1.0)
    model = PPO("MlpPolicy", env, seed=0, verbose=0, n_steps=64, batch_size=32,
                policy_kwargs=dict(net_arch=[256, 128]))
    act = E2.forward32(model)
    st = E2.visited_states(act, "riyadh", [F.TUNE_W[0]], CFG.PRICE, 1.0)[:200]
    assert len(st) == 200 and st[0].dtype == np.float32
    assert E2.check_numpy_policy(model, act, st) >= 0.0


def test_zoneenv_untouched_by_e2():
    import rbrl_ppo as P
    assert P.N_OBS == 8 and not hasattr(P.ZoneEnv, "lam")
