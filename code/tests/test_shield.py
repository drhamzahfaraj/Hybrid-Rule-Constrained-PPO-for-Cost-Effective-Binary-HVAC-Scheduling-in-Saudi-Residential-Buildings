"""F13 (RULING_round4 §3): the exact one-step shield D1.

Acceptance: on TUNE_W, zero over-temperature and zero cooling-caused under-temperature by
construction, for sigma in {0, 0.05, 0.1} K, for the latch, for random base policies, and for a
saved PPO model (if present). Plus: batched simulator == setback.sim(shielded(...)).

Run: cd /home/claude/rbrl && OMP_NUM_THREADS=1 nice python3 -I -m pytest -q tests/test_shield.py
"""
import os, sys, glob
import numpy as np
import pytest

ROOT = os.environ.get("RBRL_ROOT", "/home/claude/rbrl")
sys.path.insert(0, ROOT)
import headroom as H
import setback as S
import final_tables as F
import shield as D1

CITIES = ("riyadh", "taif")
CAPS = np.round(np.arange(H.BAND_HI - 0.5, H.BAND_HI + 1e-9, 0.1), 2)


def _grid():
    c, s = np.meshgrid(CAPS, D1.SIGMAS)
    return c.ravel(), s.ravel()


@pytest.mark.parametrize("city", CITIES)
def test_latch_zero_over_zero_cmd_under(city):
    caps, sig = _grid()
    for w in F.TUNE_W:
        r = D1.sim_shield_batch(city, w, 0.18, caps, sig)
        assert r["conflict_steps"].max() == 0
        assert r["deg_h_over"].max() == 0.0, (w, r["deg_h_over"].max())
        assert r["deg_h_cmd_under"].max() == 0.0, (w, r["deg_h_cmd_under"].max())
        assert r["starts"].min() > 0                     # the shield really switches


@pytest.mark.parametrize("city", CITIES)
def test_random_base_zero_over_zero_cmd_under(city):
    """'By construction': the guarantee does not depend on the base policy."""
    caps, sig = _grid()
    rng = np.random.default_rng(7)
    for w in F.TUNE_W:
        base = lambda T, prev, k: rng.random(len(T)) < 0.5
        r = D1.sim_shield_batch(city, w, 0.18, caps, sig, base=base)
        assert r["deg_h_over"].max() == 0.0
        assert r["deg_h_cmd_under"].max() == 0.0
        always_on = D1.sim_shield_batch(city, w, 0.18, caps, sig,
                                        base=lambda T, prev, k: np.ones(len(T), bool))
        assert always_on["deg_h_cmd_under"].max() == 0.0 and always_on["deg_h_over"].max() == 0.0


def test_sigma_tightens_both_edges():
    """With margin sigma the shielded latch stays within [T_min+sigma-~, cap-sigma] at the switches:
    occupied post-step max <= cap - sigma whenever the step was not forced on."""
    city, w = "riyadh", F.TUNE_W[0]
    r0 = D1.sim_shield_batch(city, w, 0.18, [24.0], [0.0])
    r1 = D1.sim_shield_batch(city, w, 0.18, [24.0], [0.1])
    assert r1["T_mean_occ"][0] < r0["T_mean_occ"][0]
    assert r1["starts"][0] >= r0["starts"][0]


@pytest.mark.parametrize("sigma", D1.SIGMAS)
def test_batch_equals_scalar_sim(sigma):
    city, w = "taif", F.TUNE_W[1]
    N, occ, lo, hi = F._ctx(city, w, False)
    sh = D1.Shield(city, w)
    for cap in (23.6, 24.0):
        cnt = dict(forced_on=0, forced_off=0, conflict_steps=0)
        r = S.sim(D1.shielded(D1.latch_base, sh, cap, sigma, cnt), city, F.FACES, F.C_TH,
                  H.price_flat(N, 0.18), lo, hi, occ, 168, w, F.T0, c_sw=F.C_SW)
        b = D1.rows_of(D1.sim_shield_batch(city, w, 0.18, [cap], [sigma]), 0)
        for k in ("J", "E", "f_s", "T_mean_occ_clip", "deg_h_over", "deg_h_cmd_under",
                  "deg_h_ff_under", "T_end"):
            assert abs(r[k] - b[k]) <= 1e-10, (k, r[k], b[k])
        for k in cnt:
            assert cnt[k] == b[k]


def test_select_A4_status_and_admissibility():
    city = "riyadh"
    cand = {}
    tune = {w: D1.sim_shield_batch(city, w, 0.18, CAPS, 0.05) for w in F.TUNE_W}
    for i, c in enumerate(CAPS):
        cand[float(c)] = {w: D1.rows_of(tune[w], i) for w in F.TUNE_W}
    cap, status, info = D1.select_A4(cand, city, 0.18)
    assert status in ("pooled_0.03", "pooled_0.10", "none")
    if cap is not None:
        assert all(D1._admissible_w(cand[cap][w], w) for w in F.TUNE_W)
        assert np.isfinite(info["tune_ratio"])


MODELS = sorted(glob.glob(f"{ROOT}/results/models/rbrl_ppo5_v2_riyadh_riyadh_*.zip"))


@pytest.mark.skipif(not MODELS, reason="no saved PPO models")
def test_saved_ppo_model_shielded():
    pytest.importorskip("stable_baselines3")
    mp = MODELS[0]
    city = "riyadh"
    for w in F.TUNE_W[:2]:
        base = D1.ppo_base(mp, city, w)
        r = D1.sim_shield_batch(city, w, 0.18, [24.0, 23.8], [0.0, 0.05], base=base)
        assert r["deg_h_over"].max() == 0.0 and r["deg_h_cmd_under"].max() == 0.0
        assert r["conflict_steps"].max() == 0


TAIF_MODELS = sorted(glob.glob(f"{ROOT}/results/models/rbrl_ppo5_v2_taif_taif_4[2-6].zip"))


@pytest.mark.skipif(not TAIF_MODELS, reason="no saved Taif PPO models")
@pytest.mark.parametrize("mp", TAIF_MODELS, ids=lambda p: os.path.basename(p))
def test_taif_ppo_seeds_shielded(mp):
    """Saved Taif seeds 42-46 load through the batched forward pass (checked against predict)
    and are guaranteed by the shield on every tuning window, sigma in SIGMAS."""
    pytest.importorskip("stable_baselines3")
    caps, sig = _grid()
    for w in F.TUNE_W:
        r = D1.sim_shield_batch("taif", w, 0.18, caps, sig, base=D1.ppo_base(mp, "taif", w))
        assert r["conflict_steps"].max() == 0
        assert r["deg_h_over"].max() == 0.0 and r["deg_h_cmd_under"].max() == 0.0


def test_refuses_timetable_with_away_steps():
    """V-code-23: zero over is guaranteed only on an all-occupied timetable."""
    N, occ, lo, hi = F._ctx("riyadh", 121, True)
    assert not occ.all()
    with pytest.raises(ValueError):
        D1.sim_shield_batch("riyadh", 121, 0.18, [24.0], [0.0], occ=occ, lo=lo, hi=hi)
    with pytest.warns(UserWarning):
        D1.sim_shield_batch("riyadh", 121, 0.18, [24.0], [0.0], occ=occ, lo=lo, hi=hi,
                            allow_away=True)


@pytest.mark.skipif(not TAIF_MODELS, reason="no saved Taif PPO models")
def test_ppo_forward_checked_on_visited_states():
    pytest.importorskip("stable_baselines3")
    base = D1.ppo_base(TAIF_MODELS[0], "taif", F.TUNE_W[0])
    assert hasattr(base, "verify")
    D1.sim_shield_batch("taif", F.TUNE_W[0], 0.18, [24.0, 23.8], [0.0, 0.05], base=base)
