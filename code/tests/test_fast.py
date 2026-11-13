"""Fast invariant tests for the RBRL code of record. Target: < 2 min on one core.
Run:  cd /home/claude/rbrl && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice python3 -I -m pytest -q -x tests -m "not slow"
"""
import importlib.util, json, os, subprocess, sys, pkgutil
import numpy as np
import pytest

ROOT = os.environ.get("RBRL_ROOT", "/home/claude/rbrl")
sys.path.insert(0, ROOT)
CLEAN = {k: v for k, v in os.environ.items() if not k.startswith("RBRL_")}


def _py(code, env=None):
    e = dict(CLEAN, **(env or {}))
    r = subprocess.run([sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {ROOT!r}); " + code],
                       capture_output=True, text=True, env=e, cwd=ROOT, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------- hygiene
def test_no_module_shadowing():
    """no local .py may share a name with a stdlib or installed top-level module (queue.py incident)."""
    local = {f[:-3] for f in os.listdir(ROOT) if f.endswith(".py")}
    installed = {m.name for m in pkgutil.iter_modules() if not m.module_finder.path.startswith(ROOT)}
    clash = sorted(local & (set(sys.stdlib_module_names) | installed))
    assert not clash, f"shadowing: {clash}"


def test_default_config_is_headline():
    d = _py("import headroom as H, final_tables as F, config as C; import json; print(json.dumps("
            "[H.BAND_LO, H.BAND_HI, H.THERM_SET, H.COP_MODEL, H.TAG, H.AWAY_MAX, F.C_SW, H.C_SW,"
            " H.C_TH, F.C_TH, C.RULE_ON, C.RULE_OFF, C.AWAY_ON, C.AWAY_OFF, C.PRICE, list(C.C_SW_GRID)]))")
    assert d == [22.0, 24.0, 23.0, "const", "", 30.0, 0.15, 0.15, 4800.0, 4800.0, 23.8, 22.4, 29.8, 29.0,
                 0.18, [0.0, 0.025, 0.05, 0.10, 0.114, 0.15, 0.20, 0.30, 0.60]]


def test_cth_scenario_plumbing():
    """F21: RBRL_CTH reaches final_tables (rule arms, THERM, sim_hyst_batch) and setback_arms;
    a non-default C_th without a tag is refused; --cth on the CLI is the same as RBRL_CTH."""
    code = ("import final_tables as F, setback_arms as SA, json; w = F.EVAL_W[0]; "
            "a = F.rule_run('riyadh', w, 0.18, 23.6, 22.6); b = F.sim_hyst_batch('riyadh', w, 0.18, [23.6], [22.6]); "
            "c = SA.run_rule('riyadh', w, 23.6, 22.6, 4, 28.0); "
            "print(json.dumps([F.C_TH, a['J'], float(b['J'][0]), c['J']]))")
    d0 = _py(code); d1 = _py(code, dict(RBRL_CTH="2400"))
    assert d0[0] == 4800.0 and d1[0] == 2400.0
    assert abs(d1[1] - d1[2]) <= 1e-12 and d1[1] != d0[1] and d1[3] != d0[3]
    r = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "t1_v2.py"), "nojob", "--cth", "2400"],
                       capture_output=True, text=True, env=CLEAN, cwd=ROOT, timeout=120)
    assert r.returncode != 0 and "set RBRL_TAG" in r.stderr


def test_band_shift_propagates():
    """test 3 (F8): the band, R1/R2 and the away limit have one source (config.py)."""
    env = dict(RBRL_BAND_LO="21.5", RBRL_BAND_HI="24.5", RBRL_THERM_SET="24")
    d = _py("import rbrl_ppo as P, mpc_lambda as M, r3_dp as D, t1_v2 as T; import json; print(json.dumps("
            "[P.LO, P.HI, M.RULE_ON, M.RULE_OFF, D.RULE_ON, D.RULE_OFF, T.GUARD_OFF]))", env)
    assert d == [21.5, 24.5, 24.3, 21.9, 24.3, 21.9, 21.9]
    d = _py("import rbrl_ppo as P, setback_arms as SA, mpc_lambda as M, final_tables as F, headroom as H, json; "
            "print(json.dumps([P.AWAY_HI, SA.ENV_MAX, SA.AWAY_ON, SA.AWAY_OFF, H.AWAY_MAX, F.OCC_LO, F.OCC_HI]))",
            dict(RBRL_AWAY_MAX="28", RBRL_BAND_LO="21.5", RBRL_BAND_HI="24.5"))
    assert d == [28.0, 28.0, 27.8, 27.0, 28.0, 21.5, 24.5]


def test_config_is_the_single_source():
    """F8: every protocol module reads band / R1-R2 / c_sw / price / C_th / AWAY_MAX from config.py:
    no module assigns those names a numeric literal."""
    import ast
    NAMES = {"BAND_LO", "BAND_HI", "LO", "HI", "THERM_SET", "AWAY_MAX", "AWAY_HI", "ENV_MAX", "AWAY_ON",
             "AWAY_OFF", "EPS_HOT", "EPS_COLD", "RULE_ON", "RULE_OFF", "GUARD_HOT", "GUARD_OFF", "C_SW",
             "PRICE", "C_TH", "C_TH_DEFAULT", "T0"}
    bad = []
    for f in ("headroom.py", "final_tables.py", "t1_v2.py", "rbrl_ppo.py", "setback_arms.py",
              "mpc_lambda.py", "r3_dp.py", "bound_v2.py"):
        tree = ast.parse(open(os.path.join(ROOT, f)).read())
        for n in tree.body:                                  # module-level assignments only
            if isinstance(n, ast.Assign):
                tg = [t for x in n.targets for t in (x.elts if isinstance(x, ast.Tuple) else [x])]
                vals = n.value.elts if isinstance(n.value, ast.Tuple) else [n.value] * len(tg)
                for t, v in zip(tg, vals):
                    if isinstance(t, ast.Name) and t.id in NAMES and any(
                            isinstance(x, ast.Constant) and isinstance(x.value, (int, float)) for x in ast.walk(v)):
                        bad.append(f"{f}:{n.lineno} {t.id}")
    assert not bad, bad


def test_every_sim_call_passes_c_sw():
    """test 17 (F8): every setback.sim call passes c_sw explicitly (its default binds H.C_SW at
    import, which silently ignored the c_sw sweep once). No exclusions."""
    import ast, glob
    bad = []
    for f in sorted(glob.glob(os.path.join(ROOT, "*.py"))):
        for n in ast.walk(ast.parse(open(f).read())):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "sim"
                    and isinstance(n.func.value, ast.Name) and n.func.value.id in ("S", "setback")
                    and not any(k.arg == "c_sw" for k in n.keywords)):
                bad.append(f"{os.path.basename(f)}:{n.lineno}")
    assert not bad, bad


def test_ppo_env_unchanged_vs_p3_tag(tmp_path):
    """F8 must not change the PPO training env (tag p3-ppo-env is the λ-free arm's env): the same
    action sequence gives bit-identical rewards and observations under HEAD and the tag."""
    old = subprocess.run(["git", "-C", ROOT, "show", "p3-ppo-env:rbrl_ppo.py"], capture_output=True, text=True)
    if old.returncode != 0:
        pytest.skip("tag p3-ppo-env not available")
    (tmp_path / "rbrl_ppo_p3.py").write_text(old.stdout)
    code = ("import sys, json; sys.path.insert(1, TMP); import rbrl_ppo as A, rbrl_ppo_p3 as B\n"
            "out = []\n"
            "for M in (A, B):\n"
            "    e = M.ZoneEnv('riyadh', [135, 163], 0.18, seed=3); o, _ = e.reset(seed=3); tr = []\n"
            "    for i in range(700):\n"
            "        o, r, d, _, _ = e.step(int((i * 7) % 5 < 2))\n"
            "        tr.append([r] + o.tolist())\n"
            "        if d: o, _ = e.reset()\n"
            "    out.append(tr)\n"
            "print(json.dumps(out[0] == out[1]))").replace("TMP", repr(str(tmp_path)))
    assert _py(code) is True


def test_cth_reaches_ppo_evaluate_and_bound():
    """V-code-17: RBRL_CTH reaches rbrl_ppo.evaluate (and equals the rule simulator at the same
    policy) and bound_v2's THERM / DP (one C_th source)."""
    code = ("import rbrl_ppo as P, final_tables as F, bound_v2 as B, r3_dp as D, json; w = F.EVAL_W[0]; "
            "pol = lambda o: int(o[0] > 0.3); "
            "a = P.evaluate(pol, 'riyadh', [w], 0.18, cap=23.9)[0]; "
            "b = B.therm_eval('riyadh', w, 0.18, False); c = F.therm_run('riyadh', w, 0.18); "
            "print(json.dumps([F.C_TH, D.C_TH, a['J'], b['J_energy_terminal'] - c['J']]))")   # O4: bound_v2 J is uniform
    d0 = _py(code); d1 = _py(code, dict(RBRL_CTH="2400", RBRL_TAG="t"))
    assert d0[:2] == [4800.0, 4800.0] and d1[:2] == [2400.0, 2400.0]
    assert d0[2] != d1[2] and d0[3] == 0.0 and d1[3] == 0.0


# ---------------------------------------------------------------- protocol identities
def test_therm_shift_zero_is_therm():
    import final_tables as F
    a = F.therm_run("riyadh", F.EVAL_W[0], 0.18)
    b = F.therm_shift_run("riyadh", F.EVAL_W[0], 0.18, 0.0, 1.0)
    for k in ("J", "E", "f_s", F.MEAN_KEY, "deg_h_occ"):
        assert a[k] == b[k], k


def test_rule_c_identity_zero_saving():
    """THERM scored as an arm against its own equalised comparator (RULING §13 min-J crossing):
    delta = 0 is one crossing, so the comparator is never dearer than THERM (saving <= 0, exactly 0
    where delta = 0 is the cheapest crossing, W1) and the comparator mean matches exactly."""
    import final_tables as F
    for w in (F.TUNE_W[0], F.EVAL_W[0]):
        th = F.therm_run("riyadh", w, 0.18)
        e = F.equalise("riyadh", w, 0.18, th[F.MEAN_KEY])
        assert e["J"] <= th["J"] + 1e-12 and e["resid"] < 1e-9 and e["n_crossings"] >= 1
        assert e["J_eq_max"] >= th["J"] - 1e-12
    assert abs(F.equalise("riyadh", F.TUNE_W[0], 0.18,
                          F.therm_run("riyadh", F.TUNE_W[0], 0.18)[F.MEAN_KEY])["J"]
               - F.therm_run("riyadh", F.TUNE_W[0], 0.18)["J"]) < 1e-12


def test_setback_false_is_all_occupied():
    import final_tables as F
    N, occ, lo, hi = F._ctx("riyadh", F.EVAL_W[0], False)
    assert occ.all() and (lo == F.OCC_LO).all() and (hi == F.OCC_HI).all()


def test_admissible_single_helper():
    """test 7 (F6): condition 1 of Sec. 2.2 -- zero deg_h_over and zero cooling-caused under
    (deg_h_cmd_under); free-float under is allowed; away steps <= AWAY_MAX; no deg-h budget;
    missing metrics raise; batch (array) form agrees with the scalar form."""
    import final_tables as F
    assert not hasattr(F, "DEGH_ALLOW") and not hasattr(F, "_degh_ok")
    base = dict(deg_h_over=0.0, deg_h_cmd_under=0.0, deg_h_ff_under=3.0, deg_h_occ=3.0,
                T_max_away=float("nan"))
    assert F.admissible(base, 121) is True
    assert F.admissible(dict(base, deg_h_over=1e-6)) is False
    assert F.admissible(dict(base, deg_h_cmd_under=1e-6)) is False
    assert F.admissible(dict(base, T_max_away=F.H.AWAY_MAX + 0.01)) is False
    assert F.admissible(dict(base, T_max_away=F.H.AWAY_MAX)) is True
    with pytest.raises(KeyError):
        F.admissible({"deg_h_over": 0.0})
    b = F.sim_hyst_batch("riyadh", F.TUNE_W[0], 0.18, [23.5, 24.3, 23.0], [22.5, 23.0, 21.0])
    got = F.admissible(b)
    assert got.dtype == bool and list(got) == [F.admissible(F.rule_run("riyadh", F.TUNE_W[0], 0.18, a, c))
                                               for a, c in ((23.5, 22.5), (24.3, 23.0), (23.0, 21.0))]
    assert list(got) == [True, False, False]       # 24.3 overshoots HI; 21.0 cools below T_min


def test_fit_status_set_and_fallback():
    """one fallback (pooled 0.10 K) for every arm; the status set is exactly Sec. 2.2 + oracle/fixed."""
    import final_tables as F
    assert F.FIT_STATUSES == ("pooled_0.03", "pooled_0.10", "none", "oracle", "fixed")
    assert (F.POOL_TOL, F.POOL_TOL_FALLBACK) == (0.03, 0.10)
    assert [F.pooled_status(x) for x in (0.0, -0.03, 0.031, 0.1, -0.1001)] == \
        ["pooled_0.03", "pooled_0.03", "pooled_0.10", "pooled_0.10", None]
    T = np.array([[23.0, 23.0], [23.05, 23.05], [23.2, 23.2]])
    # 0.03 met by candidate 0 -> chosen even though 1 is cheaper (fallback only if NONE meets 0.03)
    i, st, _ = F._select_core([2.0, 1.0, 0.5], [2.0, 2.0, 2.0], T, [True, True, True], 23.0)
    assert (i, st) == (0, "pooled_0.03")
    i, st, _ = F._select_core([2.0, 1.0, 0.5], [2.0, 2.0, 2.0], T, [False, True, True], 23.0)
    assert (i, st) == (1, "pooled_0.10")
    i, st, _ = F._select_core([2.0, 1.0, 0.5], [2.0, 2.0, 2.0], T, [False, False, True], 23.0)
    assert (i, st) == (None, "none")
    i, st, _ = F._select_core([1.0, 1.0], [2.0, 2.0], T[:2] * 0 + 23.0, [True, True], 23.0)
    assert i == 0                                   # ties -> lowest candidate index
    with pytest.raises(ValueError):
        F.Fit(1.0, (1,), "per_window_0.03", {})


PROTOCOL_FILES = ("final_tables.py", "t1_v2.py", "rbrl_ppo.py", "rbrl_sb.py", "setback_arms.py",
                  "mpc_lambda.py", "bound_v2.py", "search_audit.py", "r3_dp.py", "shield.py",
                  "mz_r3.py", "mz_mpc.py", "multizone.py", "amy_spread.py", "orientation.py",
                  "clv_refine.py", "clv_ruled.py", "bound_at.py")
# functions allowed to compare the clipped mean with a target (the selection / bracket code itself):
MEAN_CMP_OK = {("r3_dp.py", "clv_fit"), ("r3_dp.py", "dev"), ("r3_dp.py", "run_cap")}


def test_no_admissibility_outside_helper():
    """F6 AST test: no comparison of a comfort metric (deg_h_*, T_max_away) and no |dT| vs
    0.03 / 0.10 tolerance anywhere in the protocol modules except inside final_tables.admissible /
    pooled_status (a line may opt out with '# adm-ok' and a reason: legacy DP oracle only).
    V-code-27: also comparisons through a local variable bound to a comfort metric, through a named
    tolerance (POOL_TOL, POOL_TOL_FALLBACK, ADM_EPS or any module name bound to 0.03 / 0.10), and
    hand-made clipped-mean selections (both sides of a comparison index MEAN_KEY / K) outside the
    selection code itself (MEAN_CMP_OK)."""
    import ast
    KEYS = {"deg_h_over", "deg_h_cmd_under", "deg_h_occ", "deg_h_under", "deg_h_ff_under", "T_max_away"}
    TOL_NAMES = {"POOL_TOL", "POOL_TOL_FALLBACK", "ADM_EPS"}
    bad = []
    for f in PROTOCOL_FILES:
        src = open(os.path.join(ROOT, f)).read(); lines = src.split("\n"); tree = ast.parse(src)
        parent = {c: n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
        def func_of(n):
            while n in parent:
                n = parent[n]
                if isinstance(n, ast.FunctionDef):
                    return n.name
        tolnames = set(TOL_NAMES)
        keyvars = set()          # (function, name) bound to an expression that reads a comfort metric
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign):
                consts = [x.value for x in ast.walk(n.value) if isinstance(x, ast.Constant)]
                for t in n.targets:
                    for nm in [x.id for x in ast.walk(t) if isinstance(x, ast.Name)]:
                        if any(c in KEYS for c in consts if isinstance(c, str)):
                            keyvars.add((func_of(n), nm))
                        if func_of(n) is None and any(isinstance(c, float) and c in (0.03, 0.1) for c in consts):
                            tolnames.add(nm)
        def names(sub):
            return {x.id for x in sub if isinstance(x, ast.Name)} | {x.attr for x in sub if isinstance(x, ast.Attribute)}
        def mean_idx(e):
            return any(isinstance(x, ast.Subscript) and (
                (isinstance(x.slice, ast.Name) and x.slice.id in ("K", "MEAN_KEY")) or
                (isinstance(x.slice, ast.Attribute) and x.slice.attr == "MEAN_KEY") or
                (isinstance(x.slice, ast.Constant) and x.slice.value == "T_mean_occ_clip")) for x in ast.walk(e))
        for n in ast.walk(tree):
            if not isinstance(n, ast.Compare) or all(isinstance(o, (ast.In, ast.NotIn)) for o in n.ops):
                continue
            sub = list(ast.walk(n)); fn = func_of(n)
            key = any(isinstance(x, ast.Constant) and x.value in KEYS for x in sub)
            key = key or any((fn, nm) in keyvars for nm in names(sub))
            has_abs = any((isinstance(x, ast.Name) and x.id == "abs") or
                          (isinstance(x, ast.Attribute) and x.attr == "abs") for x in sub)
            tol = (any(isinstance(x, ast.Constant) and x.value in (0.03, 0.1) and isinstance(x.value, float)
                       for x in sub) and has_abs)
            tol = tol or bool(names(sub) & TOL_NAMES) or (has_abs and bool(names(sub) & tolnames))
            sides = [n.left] + list(n.comparators)
            mean = sum(mean_idx(e) for e in sides) >= 2 and (f, fn) not in MEAN_CMP_OK
            allowed = f == "final_tables.py" and fn in ("admissible", "pooled_status")
            if (key or tol or mean) and not allowed and "adm-ok" not in lines[n.lineno - 1]:
                bad.append(f"{f}:{n.lineno}: {lines[n.lineno - 1].strip()}")
    assert not bad, "\n".join(bad)


def test_fit_status_in_every_arm_row():
    """F6: every arm row an arm script appends (summ/rows/perw/pw lists) carries fit_status."""
    import ast
    bad = []
    for f in ("t1_v2.py", "rbrl_ppo.py", "rbrl_sb.py", "setback_arms.py", "mpc_lambda.py"):
        tree = ast.parse(open(os.path.join(ROOT, f)).read())
        for n in ast.walk(tree):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "append"
                    and isinstance(n.func.value, ast.Name) and n.func.value.id in ("summ", "rows", "perw")
                    and n.args and isinstance(n.args[0], ast.Call) and getattr(n.args[0].func, "id", "") == "dict"):
                kws = {k.arg for k in n.args[0].keywords}
                if "fit_status" not in kws:
                    bad.append(f"{f}:{n.lineno}")
    assert not bad, bad


# ---------------------------------------------------------------- serialisation
def test_writer_handles_heterogeneous_rows_and_numpy(tmp_path, monkeypatch):
    monkeypatch.setenv("RBRL_RESULTS", str(tmp_path))
    IO = pytest.importorskip("rbrl_io")
    monkeypatch.setattr(IO, "R", str(tmp_path))          # restored after the test (isolation)
    monkeypatch.setattr(IO, "_READ", {})
    rows = [dict(a=np.float64(1.0)), dict(a=2.0, b=np.int64(3), c=np.bool_(True))]
    p = IO.write_csv("T_x", rows)
    txt = open(p).read()
    assert txt.splitlines()[0].startswith("a,b,c,prov_code_sha")
    assert os.path.exists(p + ".meta.json")


def _io(tmp_path, monkeypatch, tag=""):
    import rbrl_io as IO
    monkeypatch.setattr(IO, "R", str(tmp_path))
    monkeypatch.setattr(IO, "_READ", {})
    monkeypatch.setenv("RBRL_TAG", tag)
    return IO


def test_writer_refuses_empty_and_none_fit(tmp_path, monkeypatch):
    import csv
    IO = _io(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        IO.write_csv("T_empty", [])
    with pytest.raises(ValueError):
        IO.write_csv("T_emptyrow", [dict(a=1), {}])
    with pytest.raises(ValueError):
        IO.write_csv("T_allnone", [dict(arm="x", fit_status="none")])
    with pytest.raises(ValueError):
        IO.write_csv("T_raise", [dict(arm="x", fit_status="none"), dict(arm="y", fit_status="pooled_0.03")],
                     on_refused="raise")
    p = IO.write_csv("T_mixed", [dict(arm="x", fit_status="none", s=1.0),
                                 dict(arm="y", fit_status="pooled_0.03", s=2.0),
                                 dict(arm="z", fit_status="pooled_0.10", s=3.0)])
    rows = list(csv.DictReader(open(p)))
    assert [r["arm"] for r in rows] == ["y", "z"]
    meta = json.load(open(p + ".meta.json"))
    assert [r["arm"] for r in meta["refused_rows"]] == ["x"]
    assert not [f for f in os.listdir(tmp_path) if f.startswith(".tmp_")]


def test_writer_provenance_tag_and_inputs(tmp_path, monkeypatch):
    import csv
    IO = _io(tmp_path, monkeypatch, tag="_unit")
    monkeypatch.setenv("RBRL_COP", "badescu")
    pj = IO.write_json("params_x", {"riyadh|inforce|TUNED": dict(on=np.float64(23.61), off=22.7)})
    assert pj.endswith("params_x_unit.json") and os.path.exists(pj + ".meta.json")
    d = IO.read_json("params_x")
    assert d == {"riyadh|inforce|TUNED": dict(on=23.61, off=22.7)}         # _provenance stripped
    p = IO.write_csv("T_prov", [dict(a=np.float32(0.1234567891), b=np.int64(7)),
                                dict(a=1.0, c=np.bool_(False))])
    assert p.endswith("T_prov_unit.csv")
    rows = list(csv.DictReader(open(p)))
    assert list(rows[0])[:3] == ["a", "b", "c"] and rows[1]["b"] == "" and rows[1]["c"] == "False"
    assert rows[0]["a"] == "0.123457"
    for r in rows:
        assert r["prov_code_sha"] == IO.code_sha()
        env = json.loads(r["prov_env"])
        assert env["RBRL_TAG"] == "_unit" and env["RBRL_COP"] == "badescu"
        ins = json.loads(r["prov_inputs"])
        assert any(k.endswith("params_x_unit.json") for k in ins) and all(len(v) == 16 for v in ins.values())
    meta = json.load(open(p + ".meta.json"))
    assert meta["code_sha"] == IO.code_sha() and "argv" in meta and "git" in meta
    # sorted header / unrounded variant (final_tables.dump format)
    p2 = IO.write_csv("T_raw", [dict(z=0.1234567891, a=1)], ndigits=None, sort_keys=True)
    r2 = list(csv.DictReader(open(p2)))[0]
    assert list(r2)[:2] == ["a", "z"] and r2["z"] == "0.1234567891"
    with pytest.raises(ValueError):                    # provenance columns are reserved
        IO.write_csv("T_clash", [dict(prov_utc=1)])


def test_writer_locking(tmp_path, monkeypatch):
    IO = _io(tmp_path, monkeypatch)
    path = str(tmp_path / "T_lock.csv")
    open(path + ".lock", "w").write("999999999 dead\n")       # leftover file, no holder -> no wait
    IO.write_csv("T_lock", [dict(a=1)])
    with IO.locked(path):                                       # live holder -> second writer refused
        with pytest.raises(RuntimeError):
            with IO.locked(path, wait_s=0.3):
                pass
    with IO.locked(path, wait_s=0.3):                           # released on exit
        pass
    # meta is written before the table and both carry the same utc stamp
    import csv
    r = list(csv.DictReader(open(path)))[0]
    assert json.load(open(path + ".meta.json"))["utc"] == r["prov_utc"]


def test_code_sha_fixed_at_start():
    """V-code-2: the stamped sha is the one the process started with (RBRL_CODE_SHA from jobq2,
    else computed at import), not the sha at the time of the first write."""
    d = _py("import rbrl_io as IO, json; print(json.dumps([IO._CODE, IO.code_sha_now()]))")
    assert d[0] is not None and d[0] == d[1]
    d = _py("import rbrl_io as IO, json; p = IO.provenance(); "
            "print(json.dumps([IO.code_sha(), p['code_sha'], p['code_changed_during_run'], 'RBRL_CODE_SHA' in p['env']]))",
            dict(RBRL_CODE_SHA="abc123abc123"))
    assert d == ["abc123abc123", "abc123abc123", True, False]


def test_no_direct_result_writes_in_routed_scripts():
    """F2: these scripts write results only through rbrl_io (mpc_lambda: F9; amy_*/orientation/mz_*: F15/F19)."""
    import re
    for f in ("t1_v2.py", "rbrl_ppo.py", "setback_arms.py", "final_tables.py", "bound_v2.py",
              "clv_refine.py", "clv_ruled.py", "search_audit.py", "stats_v3.py", "cycling_energy.py",
              "gen_tables_v3.py"):
        src = open(os.path.join(ROOT, f)).read()
        assert not re.search(r"json\.dump\(|DictWriter\(|open\([^)]*[\"']w[\"']", src), f


# ---------------------------------------------------------------- F3 weather cache (test 13)
def test_series_cache_identical_and_readonly():
    import headroom as H
    from hvac import read_epw, vertical_irradiance
    for city, hours, w in (("riyadh", 168, 121), ("taif", 168, 289), ("jeddah", 24, 200)):
        tdb, dni, dhi = read_epw(f"{ROOT}/{city}.epw")
        irr = vertical_irradiance(dni, dhi, H.CITIES[city], azimuth_deg=180.0)
        spd = int(round(1.0 / H.DT)); N0 = int(round(hours / H.DT)); h0 = w * 24
        t_ref = np.repeat(tdb[h0:h0 + hours], spd)[:N0]; g_ref = np.repeat(irr[h0:h0 + hours], spd)[:N0]
        t, g, N = H.series(city, hours, w)
        t2, g2, _ = H.series(city, float(hours), np.int64(w))      # same cache entry for numpy/float args
        assert N == N0 and t.dtype == t_ref.dtype and g.dtype == g_ref.dtype
        assert np.array_equal(t, t_ref) and np.array_equal(g, g_ref)   # bit-identical
        assert t2 is t and g2 is g
        for a in (t, g):
            assert not a.flags.writeable
            with pytest.raises(ValueError):
                a[0] = 0.0
            with pytest.raises(ValueError):
                a += 1.0
    tdb_c, irr_c = H._epw("riyadh")
    assert not tdb_c.flags.writeable and not irr_c.flags.writeable


# ---------------------------------------------------------------- F4 vectorised hysteresis (test 12)
def _scalar_traj(city, w, on_, off_, policy=None, setback=False):
    """S.sim with a recording policy: returns (sim dict, u list, post-step T list)."""
    import final_tables as F, setback as S, headroom as H
    N, occ, lo, hi = F._ctx(city, w, setback)
    price = H.price_flat(N, 0.18)
    base = policy or S.hyst_abs(on_, off_)
    us, Ts = [], []
    def pol(T, prev, k):
        if k > 0:
            Ts.append(T)
        u = int(base(T, prev, k)); us.append(u); return u
    r = S.sim(pol, city, F.FACES, F.C_TH, price, lo, hi, occ, 168, w, F.T0, c_sw=F.C_SW)
    Ts.append(r["T_end"])
    return r, np.array(us), np.array(Ts), occ, lo, hi


def _ref_metrics(us, Ts, occ, lo, hi, t_min, tol=1e-9):
    """Independent Sec. 2.1 metrics from a recorded trajectory, with setback.sim's 1e-9
    comparison convention (max(0, x - 1e-9))."""
    dt = 0.25
    over = float(np.sum(np.where(occ, np.maximum(0.0, Ts - hi - tol), 0.0)) * dt)
    cmd = float(np.sum(np.where(us == 1, np.maximum(0.0, t_min - Ts - tol), 0.0)) * dt)
    ff = float(np.sum(np.where((us == 0) & occ, np.maximum(0.0, t_min - Ts - tol), 0.0)) * dt)
    under = float(np.sum(np.where(occ, np.maximum(0.0, lo - Ts - tol), 0.0)) * dt)
    tmax_away = float(Ts[~occ].max()) if (~occ).any() else float("nan")
    return dict(deg_h_over=over, deg_h_cmd_under=cmd, deg_h_ff_under=ff, deg_h_under=under,
                T_max_away=tmax_away, starts=float(np.sum((us[1:] == 1) & (us[:-1] == 0)) + us[0]))


LEGACY_KEYS = ("J", "E", "f_s", "deg_h_occ", "T_mean_occ_clip", "T_mean_occ", "T_end")
NEW_KEYS = ("deg_h_over", "deg_h_cmd_under", "deg_h_ff_under", "deg_h_under", "starts")


def test_vectorised_sim_equals_scalar():
    """Test 12: 50 random (on, off) pairs, sim_hyst_batch == S.sim to <= 1e-12 (all-occupied)."""
    import final_tables as F
    rng = np.random.default_rng(12)
    on = np.round(rng.uniform(F.OCC_LO + 0.3, F.OCC_HI + 0.6, 50), 3)   # some above HI: over deg-h occur
    off = np.round(on - rng.uniform(0.1, 1.6, 50), 3)                   # some below LO: cmd-under occurs
    for city, w in (("riyadh", F.TUNE_W[0]), ("taif", 289)):
        R = F.sim_hyst_batch(city, w, 0.18, on, off)
        assert all(R[k].shape == (50,) for k in R)
        hits = dict(over=0, cmd=0)
        for i in range(50):
            r, us, Ts, occ, lo, hi = _scalar_traj(city, w, on[i], off[i])
            ref = _ref_metrics(us, Ts, occ, lo, hi, F.OCC_LO)
            for k in LEGACY_KEYS:
                assert abs(R[k][i] - r[k]) <= 1e-12, (city, i, k, R[k][i], r[k])
            for k in NEW_KEYS:
                assert abs(R[k][i] - ref[k]) <= 1e-12, (city, i, k, R[k][i], ref[k])
                if k in r:                                   # and S.sim itself, where it emits the key
                    assert abs(R[k][i] - r[k]) <= 1e-12, (city, i, k, "vs S.sim")
            assert R["fallback_steps"][i] == 0
            hits["over"] += ref["deg_h_over"] > 0; hits["cmd"] += ref["deg_h_cmd_under"] > 0
            hits["ff"] = hits.get("ff", 0) + (ref["deg_h_ff_under"] > 0)
        assert hits["over"] > 0 and hits["cmd"] > 0      # the comfort metrics are actually exercised


def test_vectorised_setback_equals_scalar():
    """Setback variant (occ/lo/hi vectors, per-candidate lead and away thresholds) == S.sim."""
    import final_tables as F, setback_arms as SA, setback as S
    rng = np.random.default_rng(13)
    P = 12
    on = np.round(rng.uniform(23.3, 24.2, P), 2); off = np.round(on - rng.uniform(0.4, 1.5, P), 2)
    L = rng.integers(0, 25, P); a_on = np.round(rng.uniform(25.0, 29.8, P), 1)
    for city, w in (("riyadh", F.TUNE_W[1]), ("jeddah", F.EVAL_W[2])):
        N, occ, lo, hi, _ = SA.ctx(city, w)
        hi = np.where(occ, hi, SA.ENV_MAX)
        occ_ext = S.occupancy(N + 200)
        mask = F.lead_mask(occ_ext, L, N)
        R = F.sim_hyst_batch(city, w, 0.18, on, off, occ=occ, lo=lo, hi=hi, active=mask,
                             on_away=a_on, off_away=a_on - 0.8)
        for i in range(P):
            pol = SA.sb_policy(on[i], off[i], int(L[i]), occ_ext, a_on[i])
            r = SA.run_rule(city, w, on[i], off[i], int(L[i]), a_on[i])
            _, us, Ts, _, _, _ = _scalar_traj(city, w, 0, 0, policy=pol, setback=True)
            ref = _ref_metrics(us, Ts, occ, lo, hi, F.OCC_LO)
            for k in LEGACY_KEYS:
                assert abs(R[k][i] - r[k]) <= 1e-12, (city, i, k)
            for k in NEW_KEYS + ("T_max_away",):
                assert abs(R[k][i] - ref[k]) <= 1e-12, (city, i, k, R[k][i], ref[k])
                if k in r:
                    assert abs(R[k][i] - r[k]) <= 1e-12, (city, i, k, "vs S.sim")


# ---------------------------------------------------------------- slow equivalences
@pytest.mark.slow
def test_mpc_batch_equals_single():
    import mpc_lambda as M, final_tables as F
    w = F.TUNE_W[0]
    a = M.mpc_lams("riyadh", w, [0.3, 5.0], 1.0, n_grid=101, rule=(23.6, 22.35))
    b = M.mpc_lams("riyadh", w, [0.3], 1.0, n_grid=101, rule=(23.6, 22.35))
    assert a[0].keys() == b[0].keys()
    for k in a[0]:   # NaN-aware (T_max_away is NaN without a setback)
        x, y = a[0][k], b[0][k]
        assert x == y or (isinstance(x, float) and np.isnan(x) and np.isnan(y)), k


@pytest.mark.slow
def test_mz_mpc_batch_invariant():
    import mz_r3 as Z, mz_mpc as MM
    D1 = Z.Dwelling("riyadh", "1x2", 181, None, False); D1.N = 48
    D2 = Z.Dwelling("riyadh", "1x2", 181, None, False); D2.N = 48
    MM.NG = 101
    a = MM.mz_mpc_run(D1, [0.5], 6.0, rule=(23.6, 22.35))[0]
    b = MM.mz_mpc_run(D2, [0.5, 24.0], 6.0, rule=(23.6, 22.35))[0]
    assert a == b


@pytest.mark.slow
def test_numpy_policy_matches_sb3_on_trajectories():
    pytest.importorskip("stable_baselines3")
    from stable_baselines3 import PPO
    import rbrl_ppo as RP, final_tables as F
    m = PPO.load(f"{ROOT}/results/models/rbrl_ppo5_v2_riyadh_riyadh_42.zip", device="cpu")
    f = RP.numpy_policy(m)
    seen = []
    def logger(o):
        a = f(o); seen.append((o.copy(), a)); return a
    RP.evaluate(logger, "riyadh", [F.EVAL_W[0]], 0.18)
    for o, a in seen[::7]:
        assert a == int(m.predict(o, deterministic=True)[0])


# ---------------------------------------------------------------- F7 A4 objective (tests 5, nesting, audit)
W1 = [121 + 14]          # one tuning window (smoke): TUNE_W[0]


def test_therm_as_candidate_saves_zero():
    """test 5 (F7): THERM offered as a candidate scores exactly the comparator: ratio 1, saving 0."""
    import final_tables as F
    assert F.TUNE_W[0] == W1[0]
    f = F.fit_param([(23.5, 22.5)], lambda p, w: F.rule_run("riyadh", w, 0.18, *p), W1,
                    city="riyadh", price_v=0.18)
    assert f.fit_status == "pooled_0.03" and abs(f[0] - 1.0) < 1e-12 and abs(f.info["tune_saving"]) < 1e-10


def test_j_eq_matches_equalise():
    """selection and evaluation use the same Rule C helper (F.j_eq vs F.equalise, both F.rule_c on
    the one cached curve), including on the non-monotone staircase."""
    import final_tables as F
    w = F.TUNE_W[0]
    m, J = F.therm_curve("riyadh", w, 0.18)
    assert np.any(np.diff(m) < 0)                       # the staircase is not monotone
    # (a target exactly ON a grid mean is a tie that the 1e-14 batch/scalar difference may resolve
    # either way; the protocol never evaluates such a target except THERM itself, test 5)
    for T in (m[200] + 0.0013, m[150] + 1e-7, m[0] - 0.1, m[-1] + 0.1, float(np.mean(m))):
        e = F.equalise("riyadh", w, 0.18, T)
        j, clipped = F.j_eq("riyadh", w, 0.18, T)
        assert clipped == e["clipped"] and abs(j - e["J"]) < 1e-9


def test_nesting_deadband_125_tuned_not_worse():
    """E-opt3-3: at comparator deadband 1.25 K THERM_1.25 is in TUNED's family, so TUNED's
    equalised tuning saving is >= 0 (one tuning window smoke)."""
    import final_tables as F
    f = F.tune_rule("riyadh", 0.18, W1, db=1.25)
    assert f is not None and f[0] <= 1.0 + 1e-12 and f.info["tune_saving"] >= -1e-10
    g = F.fit_param([(23.625, 22.375)], lambda p, w: F.rule_run("riyadh", w, 0.18, *p), W1,
                    city="riyadh", price_v=0.18, db=1.25)
    assert abs(g[0] - 1.0) < 1e-12 and f[0] <= g[0] + 1e-12


def test_search_audit_flags_cheaper_neighbour():
    """F7: the audit passes on a tune_rule optimum and fails on a point with a cheaper admissible
    neighbour (THERM itself, one window)."""
    import final_tables as F, search_audit as SA
    f = F.tune_rule("riyadh", 0.18, W1)
    base, better = SA.audit_rule("riyadh", f[1], f[2], windows=W1)
    assert base["status"] == f.fit_status and abs(base["obj"] - f[0]) < 1e-12 and not better
    _, better = SA.audit_rule("riyadh", 23.5, 22.5, windows=W1)
    assert better


def test_fit_lambda_uses_the_helper(monkeypatch):
    """mpc_lambda.fit_lambda selects through F.select_rows (A4, fit_status). The MPC is replaced
    by a cheap stand-in whose 'lam' sets a hysteresis rule, on one tuning window."""
    import final_tables as F, mpc_lambda as M
    monkeypatch.setattr(F, "TUNE_W", W1)
    pair = lambda lam: (23.5 + 0.4 * np.tanh(lam), 22.5 - 0.2 * np.tanh(lam))
    def fake(city, windows, lams, hh, n_grid, rule=None, price_v=0.18, ruled=False, forecast="perfect"):
        return [[dict(F.rule_run(city, w, 0.18, *pair(l)), fallback_steps=0) for l in lams]
                for w in windows]
    monkeypatch.setattr(M, "mpc_batch", fake)
    lam, relaxed, allr, status = M.fit_lambda("riyadh", 6.0, None, 101, lambda m: None, with_status=True)
    rows = [[fake("riyadh", W1, [r["lam"]], 6.0, 101)[0][0]] for r in allr]
    ref = F.select_rows([r["lam"] for r in allr], rows, "riyadh", 0.18, W1)
    assert ref is not None and lam == ref[1] and status == ref.fit_status
