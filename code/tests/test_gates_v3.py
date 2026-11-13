"""Tests for the v3 consumers (RULING_round4 F16-F18): cycling_energy, gen_tables_v3, invariants
class P (v3), verify_numbers, build_registry and the test-18 manifest. The v3 CSVs do not exist yet,
so every test builds small SYNTHETIC v3 tables with the documented column schema (v3_names
docstring; t1_v2.evaluate, mpc_lambda.main, rbrl_ppo, shield, bound_v2) in a tmp results dir.
Fast tier (no simulation).
"""
import csv, importlib, json, os, sys
import numpy as np
import pytest

ROOT = os.environ.get("RBRL_ROOT", "/home/claude/rbrl")
sys.path.insert(0, ROOT)
import rbrl_io as IO
import v3_names as V

EVAL_W = (121, 149, 177, 205, 233, 261, 289)
C_TH, COP, T0, PRICE, CSW = 4800.0, 2.985, 23.0, 0.18, 0.15


# ------------------------------------------------------------------ synthetic v3 results
def _write(d, name, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(os.path.join(d, name + ".csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys + ["prov_code_sha"], restval="")
        w.writeheader()
        for r in rows:
            w.writerow({**r, "prov_code_sha": "synthetic"})


def pw_rows(rng, n_start_cut, dT=0.0, base_fs=4.0, base_E=2.8, price=PRICE, extra=None):
    """per-window rows obeying the duty-cycle identity: equal terminal-priced energy, fewer starts."""
    out = []
    for i, w in enumerate(EVAL_W):
        fq = base_fs + 0.3 * rng.standard_normal()
        fa = fq * (1 - n_start_cut) + 0.05 * rng.standard_normal()
        Etp = base_E + 0.2 * rng.standard_normal()
        T_end = 23.0 + 0.3 * rng.standard_normal()
        E_arm = Etp - (T_end - T0) * C_TH * 1e3 / 3.6e6 / COP / 7.0
        Ja, Jq = CSW * fa + price * Etp, CSW * fq + price * Etp
        out.append(dict(window=w, J_arm=Ja, J_therm0=Jq * 1.001, J_eq=Jq, delta_w=0.0,
                        bracket_gap=0.01, eq_resid=0.0, eq_clipped=False, T_arm=22.95 + dT,
                        T_therm0=22.95, dT_w=dT, fs_arm=fa, fs_eq=fq, E_arm=E_arm, E_eq=Etp,
                        deg_h_over=0.0, deg_h_under=0.0, deg_h_cmd_under=0.0, deg_h_ff_under=0.0,
                        T_end=T_end, fallback_steps=0, **(extra or {})))
    return out


def summ_of(pw, **kw):
    Ja = np.array([r["J_arm"] for r in pw]); Jq = np.array([r["J_eq"] for r in pw])
    J0 = np.array([r["J_therm0"] for r in pw])
    return dict(n_eval=len(pw), fit_windows="TUNE_W", s_pooled_eq=100 * (1 - Ja.sum() / Jq.sum()),
                s_raw=100 * (1 - Ja.sum() / J0.sum()), dT_pooled=float(np.mean([r["dT_w"] for r in pw])),
                max_abs_dT_w=float(max(abs(r["dT_w"]) for r in pw)),
                start_sav_eq=100 * (1 - sum(r["fs_arm"] for r in pw) / sum(r["fs_eq"] for r in pw)),
                energy_sav_eq=0.0, J_arm_mean=Ja.mean(), J_eq_mean=Jq.mean(), J_therm0_mean=J0.mean(),
                deg_h_over=0.0, deg_h_under=0.0, deg_h_cmd_under=0.0, deg_h_ff_under=0.0,
                T_end_mean=float(np.mean([r["T_end"] for r in pw])), fallback_steps=0, n_eq_clipped=0,
                max_bracket_gap=0.01, **kw)


CUTS = dict(TUNED=0.16, guard=0.10, MPC=0.25, MPCp=0.20, MPCr=0.05, RBRL=0.10, D1=0.08, E2=0.12)


def make_v3(d, seed=0):
    """write a complete synthetic v3 result set into directory d."""
    rng = np.random.default_rng(seed)
    t1s, t1p, t7, t5, t4b = [], [], [], [], []
    for c in V.CITIES:
        for tname, pv in (("inforce", 0.18), ("y2027", 0.21), ("historical", 0.05)):
            arms = ("TUNED", "guard") if tname == "inforce" else ("TUNED",)
            for arm in arms:
                pw = pw_rows(rng, CUTS[arm], price=pv)
                prm = {"on": 23.6, "off": 22.35} if arm == "TUNED" else {"cap": 23.8, "on": 23.6, "off": 22.4}
                t1s.append(dict(tariff=tname, price=pv, city=c, arm=arm, params=json.dumps(prm),
                                fit_status="pooled_0.03", **summ_of(pw)))
                t1p += [dict(tariff=tname, city=c, arm=arm, fit_status="pooled_0.03", **r) for r in pw]
        for db in (0.5, 0.75, 1.0, 1.25):
            pw = pw_rows(rng, 0.16 * db)
            t7.append(dict(city=c, deadband=db, on=23.6, off=22.35, fit_status="pooled_0.03",
                           therm_fs=4.0, guard_fit_status="pooled_0.03", guard_s_eq=5.0, guard_s_raw=5.1,
                           **summ_of(pw)))
        for cs in (0.0, 0.025, 0.05, 0.10, 0.114, 0.15, 0.30, 0.60):
            pw = pw_rows(rng, 0.16)
            t5.append(dict(c_sw=cs, city=c, on=23.6, off=22.35, fit_status="pooled_0.03", **summ_of(pw)))
        # MPC perfect / persistence / in-rules
        for key, cut, fc, hs in (("MPC", CUTS["MPC"], "perfect", (0.25, 1, 2, 6, 24, 48)),
                                 ("MPC_PERS", CUTS["MPCp"], "persistence", (6, 24)),
                                 ("MPC_RULED", CUTS["MPCr"], "perfect", (1, 6, 24)),
                                 ("MPC_GUARD", CUTS["MPCr"], "perfect", (1, 6, 24))):
            ss, pp = [], []
            for h in hs:
                pw = pw_rows(rng, cut * min(1.0, h / 24.0) + 0.02)
                ex = dict(city=c, horizon_h=float(h), forecast=fc, n_grid=801, c_sw=CSW, c_th=C_TH,
                          lam=0.2, lam_over_lam_star=1.02, fit_status="pooled_0.03")
                ss.append(dict(**ex, grid_h_min=0.004, grid_h_max=0.005, lam_star=0.196, **summ_of(pw)))
                pp += [dict(**ex, grid_h=0.0045, **r) for r in pw]
            _write(d, V.name(key, c), ss); _write(d, V.name(key, c) + "_perwindow", pp)
        conv = [dict(city=c, horizon_h=24.0, forecast="perfect", n_grid=1601, fit_status="pooled_0.03",
                     s_pooled_eq=[r for r in csv.DictReader(open(os.path.join(d, V.name("MPC", c) + ".csv")))
                                  if float(r["horizon_h"]) == 24.0][0]["s_pooled_eq"])]
        _write(d, V.name("MPC_CONV", c), conv)
        # RBRL 5 seeds, D1 sigma family
        rs, rp = [], []
        for seed in range(42, 47):
            pw = pw_rows(rng, CUTS["RBRL"])
            rs.append(dict(city=c, seed=seed, steps=200000, cap=23.8, fit_status="pooled_0.03", **summ_of(pw)))
            rp += [dict(city=c, seed=seed, cap=23.8, fit_status="pooled_0.03", **r) for r in pw]
        _write(d, V.name("RBRL", c), rs); _write(d, V.name("RBRL_PW", c), rp)
        ds, dp = [], []
        for sg, tr in ((0.0, 0.92), (0.05, 0.90), (0.10, 0.93)):
            pw = pw_rows(rng, CUTS["D1"])
            ds.append(dict(city=c, arm="D1-latch", sigma=sg, cap=23.8, fit_status="pooled_0.03",
                           tune_ratio=tr, **summ_of(pw)))
            dp += [dict(city=c, arm="D1-latch", sigma=sg, cap=23.8, **r) for r in pw]
        _write(d, V.name("D1", c), ds); _write(d, V.name("D1_PW", c), dp)
        # CLV + bound (bound_v2 main): bound_reported is B*, dual curves give B_a
        clv_pw = pw_rows(rng, 0.20)
        Jb = float(np.mean([r["J_therm0"] for r in clv_pw]))
        bd = dict(city=c, price=0.18, c_sw=CSW, setback=False, therm_J=Jb, bound_reported=40.0,
                  bound_rel6401=39.95, bound_unrel6401=39.0, clv_s_pooled=20.0, clv_dT_pooled=0.0,
                  clv_s_raw=20.5, clv_B_a=30.0,
                  clv_start_sav=25.0, clv_le_bound_all_windows=True, clv_le_bound_pooled=True,
                  fit_status="oracle")
        _write(d, V.name("CLV", c), [bd])
        _write(d, V.name("CLV_PW", c), [dict(city=c, setback=False, **r) for r in clv_pw])
        # dual curve: L(lam) - lam*T/7 <= 0.6 Jb for every T near 23 -> B_a ~ 40 %
        pts = [[lam, 0.6 * Jb + lam * 22.95 / 7.0] for lam in (0.0, 0.05, 0.1, 0.2)]
        json.dump({f"{c}|0.18|0.15|False": {"rel6401": pts}},
                  open(os.path.join(d, V.name("DUAL", c) + ".json"), "w"))
        _write(d, V.name("T5_BOUND", c), [dict(city=c, price=0.18, c_sw=cs, setback=False, therm_J=1.1,
                                               bound_reported=b) for cs, b in ((0.025, 33.0), (0.114, 38.0))])
    # J20: MPC-24 on the c_sw grid (Riyadh), J-MZ (Riyadh, mz_r3 / mz_mpc schema)
    for cs in (0.0, 0.025, 0.05, 0.10, 0.114, 0.30, 0.60):
        pw = pw_rows(rng, 0.25)
        _write(d, f"T21v3_csw{cs:g}_riyadh", [dict(city="riyadh", horizon_h=24.0, forecast="perfect", c_sw=cs,
                                                    fit_status="pooled_0.03", **summ_of(pw))])
    for topo, lijs in V.MZ_LAYOUTS:
        for lij in lijs:
            ss, pp = [], []
            for arm in ("THERM", "TUNED", "guard"):
                pw = pw_rows(rng, {"THERM": 0.0, "TUNED": 0.16, "guard": 0.1}[arm])
                ss.append(dict(city="riyadh", topology=topo, lam_ij=lij, arm=arm,
                               fit_status="reference" if arm == "THERM" else "pooled_0.03",
                               T_zone_spread_mean=0.3, **summ_of(pw)))
                pp += [dict(city="riyadh", topology=topo, lam_ij=lij, arm=arm, **r) for r in pw]
            stem = V.MZ_RULES.format(topo=topo, lij=lij)
            _write(d, stem, ss); _write(d, stem + "_perwindow", pp)
            pw = pw_rows(rng, 0.2)
            stem = V.MZ_MPC.format(topo=topo, lij=lij, h=V.MZ_MPC_H)
            _write(d, stem, [dict(city="riyadh", topology=topo, lam_ij=lij, arm="MPC-MZ24", lam=0.2,
                                  fit_status="pooled_0.10", **summ_of(pw))])
            _write(d, stem + "_perwindow", [dict(city="riyadh", topology=topo, lam_ij=lij, **r) for r in pw])
    _write(d, V.name("T1"), t1s); _write(d, V.name("T1_PW"), t1p)
    _write(d, V.name("T7"), t7); _write(d, V.name("T5"), t5)
    _write(d, V.name("T4_BOUND"), [dict(city="riyadh", price=p, c_sw=CSW, setback=False, therm_J=1.1,
                                        bound_reported=b) for p, b in ((0.05, 55.0), (0.21, 37.0))])
    pw = pw_rows(rng, CUTS["E2"], extra=dict(city="riyadh"))
    _write(d, V.name("E2"), [dict(city="riyadh", seed=s, fit_status="pooled_0.03", **summ_of(pw)) for s in (1, 2, 3)])
    _write(d, V.name("E2_PW"), [dict(seed=s, fit_status="pooled_0.03", **r) for s in (1, 2, 3) for r in pw])
    # C_th sweep (Riyadh): T1 and MPC under the scenario tags
    for tg in sorted(t for t in V.CTH_TAGS.values() if t):          # _cth2400/_cth7200/_cth9600
        for key in ("T1", "T1_PW", "MPC", "MPC_PW"):
            src = os.path.join(d, V.name(key, "riyadh") + ".csv")
            rows = list(csv.DictReader(open(src)))
            _write(d, V.name(key, "riyadh") + tg, [{k: v for k, v in r.items() if k != "prov_code_sha"} for r in rows])
    return d


@pytest.fixture
def v3dir(tmp_path, monkeypatch):
    monkeypatch.setattr(IO, "R", str(tmp_path))
    monkeypatch.setattr(IO, "_READ", {})
    return make_v3(str(tmp_path))


# ------------------------------------------------------------------ F16 cycling energy
def test_cycling_reproduces_E_hvac2_2_from_T5v2_summary():
    """E-hvac2-2 / H2-7: Riyadh +0.23/+0.56/+1.08/+2.0 % at 10/25/50/100 Wh, Taif +0.11/+0.27 at
    10/25 Wh, derived from the T5v2 c_sw = 0.15 rows under Rule C with the store priced."""
    import cycling_energy as C
    riy = (1.017006, 1.113673, 15.821344)       # T5v2_switchcost_tuned.csv c_sw 0.15 riyadh
    tai = (0.588122, 0.612432, 6.969202)
    got = [round(C.from_summary(*riy, 0.18, 0.15, wh), 2) for wh in (10, 25, 50, 100)]
    assert got[:3] == [0.23, 0.56, 1.08] and round(got[3], 1) == 2.0
    assert [round(C.from_summary(*tai, 0.18, 0.15, wh), 2) for wh in (10, 25)] == [0.11, 0.27]


def test_cycling_perwindow_equals_summary_method_and_identity(v3dir):
    import cycling_energy as C
    rows = C.arm_rows("TUNED", "riyadh")
    pw = V.perwindow("TUNED", "riyadh")
    s = summ_of([{k: float(v) if k not in ("eq_clipped", "fit_status", "tariff", "city", "arm",
                                           "prov_code_sha") else v for k, v in r.items()} for r in pw.values()])
    for r in rows:
        if r["tau_eff_min"] == "":
            ref = C.from_summary(s["J_arm_mean"], s["J_eq_mean"], s["start_sav_eq"], PRICE, CSW, r["wh_per_start"])
            assert abs(r["energy_saving_pct"] - ref) < 1e-9
    assert abs(rows[0]["energy_identity_rel"]) < 1e-9 and rows[0]["energy_saving_pct"] == pytest.approx(0.0, abs=1e-9)
    assert all(b["energy_saving_pct"] > a["energy_saving_pct"] for a, b in zip(rows[:6], rows[1:7]))


def test_cycling_refuses_metered_energy_and_missing_file(v3dir):
    import cycling_energy as C
    r = dict(V.perwindow("TUNED", "riyadh")[121])
    r["E_arm"] = float(r["E_arm"]) + 0.01          # not terminal-priced -> stop
    with pytest.raises(ValueError, match="terminal"):
        C.window_energy(r)
    os.remove(V.path("MPC_PW", "taif"))
    with pytest.raises(FileNotFoundError):
        C.main(["--arms", "MPC24", "--cities", "taif"])


def test_cycling_main_writes_v3_table(v3dir):
    import cycling_energy as C
    p = C.main([])
    rows = list(csv.DictReader(open(p)))
    assert os.path.basename(p) == "T25v3_cycling_energy.csv"
    assert {r["arm"] for r in rows} == {"TUNED", "guard", "MPC24"} and len(rows) == 3 * 3 * 11
    assert all(r["prov_code_sha"] for r in rows)


# ------------------------------------------------------------------ F18 gates on the synthetic v3 set
def _pipeline(d, tmp):
    import stats_v3, cycling_energy, gen_tables_v3 as T
    stats_v3.main(); cycling_energy.main([])
    out = os.path.join(tmp, "tex", "tables"); os.makedirs(out, exist_ok=True)
    T.main(["--out", out])
    return out


def test_gen_tables_v3_from_v3_files(v3dir, tmp_path):
    out = _pipeline(v3dir, str(tmp_path))
    body = {fn: open(os.path.join(out, fn)).read() for fn in os.listdir(out) if fn.endswith(".tex")}
    assert set(body) == {"tab_main.tex", "tab_sensitivity.tex", "tab_stats.tex", "tab_s_mz.tex"}
    for fn, b in body.items():
        assert b.startswith("% generated by") and "nan" not in b.lower(), fn
        assert b.count(r"\begin{tabularx}") == 1 and b.count(r"\end{tabularx}") == 1, fn
    m = body["tab_main.tex"]
    assert "THERM" in m and r"\emph{Bound}" in m and "CLV" in m and "E2-PPO" in m and r"\sigma=0.05" in m
    assert r"\label{tab:stats}" in body["tab_stats.tex"] and "0.047" in body["tab_stats.tex"]
    # every fitted cell carries its fit_status mark; a 'none' row can never be tabulated
    import gen_tables_v3 as T
    with pytest.raises(ValueError):
        T.fit_mark("none")
    os.remove(V.path("MPC_RULED_PW", "jeddah"))
    with pytest.raises(FileNotFoundError):
        T.tab_main()


def test_latex_tables_compile(v3dir, tmp_path):
    import shutil, subprocess
    if not shutil.which("pdflatex"):
        pytest.skip("no pdflatex")
    out = _pipeline(v3dir, str(tmp_path))
    doc = (r"\documentclass{article}\usepackage[a4paper,landscape,margin=1cm]{geometry}"
           r"\usepackage{booktabs,tabularx,amsmath}\begin{document}\section{x}\label{subsec:protocol}"
           r"\begin{table*}\small\input{tab_main}\end{table*}\begin{table*}\small\input{tab_sensitivity}\end{table*}"
           r"\input{tab_stats}\begin{table}\small\input{tab_s_mz}\end{table}\end{document}")
    open(os.path.join(out, "t.tex"), "w").write(doc)
    r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "t.tex"], cwd=out,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout[-1500:]


def test_invariants_class_P_passes_and_fails_on_missing_file(v3dir, tmp_path):
    import invariants as I, stats_v3
    stats_v3.main()
    assert I.main(["--classes", "P"]) == 0
    run = json.load(open(os.path.join(v3dir, "invariants_run.json")))
    assert run["n_failed"] == 0 and run["n_checks"] > 100 and run["full_gate"] is False
    os.remove(V.path("MPC_CONV", "taif"))                 # P11 must FAIL, not skip
    os.remove(V.path("DUAL", "jeddah", ext=".json"))       # B_a needs the dual curves
    assert I.main(["--classes", "P"]) == 1
    failed = json.load(open(os.path.join(v3dir, "invariants_run.json")))["failed"]
    assert any("P11 taif" in f for f in failed) and any("jeddah" in f for f in failed)


def test_invariants_B_a_violation_detected(v3dir):
    import invariants as I, stats_v3
    stats_v3.main()
    d = os.path.join(v3dir, V.name("DUAL", "riyadh") + ".json")
    cv = json.load(open(d))
    for k in cv:
        cv[k]["rel6401"] = [[lam, L * 1.55] for lam, L in cv[k]["rel6401"]]   # bound below every arm
    json.dump(cv, open(d, "w"))
    assert I.main(["--classes", "P"]) == 1
    assert any(f.startswith("P10 riyadh") for f in I.FAILS)


def test_verify_numbers_v3(v3dir, tmp_path):
    import verify_numbers as VN, shutil
    out = _pipeline(v3dir, str(tmp_path))
    tex = os.path.dirname(out)
    open(os.path.join(tex, "main.tex"), "w").write("x \\input{tables/tab_main} \\pend{a, T1v3}\n")
    open(os.path.join(tex, "supplement.tex"), "w").write("\\input{tables/tab_s_mz}\n")
    assert VN.main(["--tex", tex, "--tables", out]) == 0
    assert VN.main(["--tex", tex, "--tables", out, "--final"]) == 1            # a \pend left at G2
    # a summary that no longer matches its per-window rows, and a stale table, both fail
    p = V.path("T1"); rows = list(csv.DictReader(open(p)))
    rows[0]["s_pooled_eq"] = str(float(rows[0]["s_pooled_eq"]) + 0.5)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    assert VN.main(["--tex", tex, "--tables", out]) == 1
    assert any(x.startswith("A TUNED riyadh") for x in VN.FAILS)
    assert any(x.startswith("E tab_main") for x in VN.FAILS)                   # T1v3 bytes changed
    src = open(os.path.join(ROOT, "verify_numbers.py")).read()
    assert "7.62" not in src and "9.25" not in src and "19.8" not in src     # no typed result values


def test_build_registry_auto_status(v3dir, tmp_path, monkeypatch):
    import build_registry as B
    monkeypatch.setattr(B, "record_sha", lambda: ("synthetic", "test"))
    out = str(tmp_path / "REG.md")
    rc = B.main(out)
    txt = open(out).read()
    assert rc == 1                                    # synthetic files have no .meta.json
    assert "| `T1v3_heldout.csv` | UNSTAMPED |" in txt and "| `T2v3_timestep.csv` | MISSING |" in txt
    assert "Riyadh: TUNED pooled equalised saving s (%)" in txt and "**MISSING**" not in txt.split("## 2.")[0].split("RBRL")[0]
    for n in ("T1v3_heldout.csv", "T1v3_perwindow.csv"):
        json.dump(dict(code_sha="synthetic", code_changed_during_run=False), open(os.path.join(v3dir, n + ".meta.json"), "w"))
    assert "| `T1v3_heldout.csv` | CURRENT |" in open(out).read() or B.main(out) == 1
    assert "| `T1v3_heldout.csv` | CURRENT |" in open(out).read()
