#!/usr/bin/env python3
"""Round-3 clairvoyant bracket (ruling c; C5, C6-bound/CLV, C7-bound/CLV).

For each configuration (city, tariff, c_sw, setback):
  * THERM (unshifted) on the 7 held-out windows, clipped occupied mean.
  * BOUND: pooled relaxed Lagrangian dual (provable), at the grids the ruling
    names; unrelaxed values kept as a convergence row only. Saving upper bound
    rounded OUTWARD (up) to 0.1 point.
  * BOUND per window (relaxed, lam_w), for the CLV <= bound invariant.
  * CLV (F10): per window, r3_dp.clv_fit -- lam_w refined by bisection (plus the occupied-cap
    knob) to |T~_w - T~_THERM,w| <= 0.002 K two-sided where attainable (clv_tol_met), admissible
    through F.admissible, fallback_steps = 0; scored by Rule C (F.equalise at its own mean),
    fit_status "oracle"; T_end recorded. Invariants: per-window certificate margin >= 0
    (r3_dp.certificate_margin), s_CLV <= B_CLV and s_CLV <= B* (pooled).
  * The dual curve L_raw(lam) (pooled and per window) is stored so B(T_a) can be evaluated at
    any arm's own pooled mean (bound_at.py).
  * Terminal (O4, ruling §21.3): every J here -- THERM, the DP / bound, the CLV and its Rule C
    comparator -- uses the uniform terminal value r3_dp.uniform_J (energy at rated COP +
    c_sw / DELTA_CYCLE per K of T_N - T0); bound_at rescores the arms onto it. Outward rounding
    (up01) unchanged.
  * Grids: Taif/Jeddah spacing capped at Riyadh's (r3_dp.h_ref, F-4); relaxed <= unrelaxed is
    asserted pointwise in lam.

Usage: python3 bound_v2.py main|sb|ruled [city,...] | tariff | csw   (names: v3_names.py)
"""
from __future__ import annotations
import sys, csv, json, math, time
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import config as CFG
import headroom as H
import setback as S
import final_tables as F
import r3_dp as D
import rbrl_io as IO

R = "/home/claude/rbrl/results"
K = F.MEAN_KEY


def therm_eval(city, w, pv, setback):
    """THERM (unshifted) on window w; J under the uniform O4 terminal (r3_dp.uniform_J, the
    terminal of the bound and the CLV), the simulator's J kept as J_energy_terminal."""
    N, occ, lo, hi = F._ctx(city, w, setback)
    price = H.price_flat(N, pv)
    r = S.sim(S.hyst_abs(H.THERM_SET + 0.5, H.THERM_SET - 0.5), city, F.FACES, F.C_TH, price, lo, hi, occ,
              168, w, F.T0, c_sw=F.C_SW)
    r["J_energy_terminal"] = r["J"]
    r["J"] = D.uniform_J(r["J"], r["T_end"], F.C_SW)
    return r


def up01(x):
    """outward (upward) rounding of a saving bound to 0.1 point; floating-point noise errs
    outward (F-7: no -1e-9)."""
    return math.ceil(x * 10) / 10


def config(city, pv, setback, c_sw, grids_rel, grids_unrel, do_clv=True, perwindow=True,
           ruled=False, rule_on=None, rule_off=None):
    """C_th: F.C_TH == D.C_TH == H.C_TH (config.C_TH / RBRL_CTH; asserted). c_sw set for this
    configuration and restored afterwards, even on error."""
    assert F.C_TH == D.C_TH == H.C_TH, "C_th must have one source (config.py)"
    c_sw0 = F.C_SW
    F.C_SW = c_sw
    try:
        return _config(city, pv, setback, c_sw, grids_rel, grids_unrel, do_clv, perwindow,
                       ruled, rule_on, rule_off)
    finally:
        F.C_SW = c_sw0


def lower_cost_curves(curves, T, days=7.0):
    """L*(T) per day from stored relaxed dual curves {tag: [(lam, L_raw)]}: max over every relaxed
    grid and every stored lam of L_raw(lam) - lam T / days (each is a valid lower bound)."""
    return max(L - lam * T / days for tag, pts in curves.items() if tag.startswith("rel")
               for lam, L in pts)


def _config(city, pv, setback, c_sw, grids_rel, grids_unrel, do_clv=True, perwindow=True,
            ruled=False, rule_on=None, rule_off=None):
    t0 = time.time()
    rk = dict(ruled=ruled, rule_on=rule_on, rule_off=rule_off)
    th = {w: therm_eval(city, w, pv, setback) for w in F.EVAL_W}
    Jb = np.array([th[w]["J"] for w in F.EVAL_W])
    tgt = float(np.mean([th[w][K] for w in F.EVAL_W]))
    out = dict(city=city, price=pv, c_sw=c_sw, setback=setback, therm_J=float(Jb.mean()),
               terminal=f"uniform: energy at rated COP + c_sw/{D.DELTA_CYCLE:g} K per K (O4)",
               target=tgt, ruled=ruled, rule_on=rk["rule_on"] if ruled else "",
               rule_off=rk["rule_off"] if ruled else "")
    curves = {}
    for ng, rel in [(g, True) for g in grids_rel] + [(g, False) for g in grids_unrel]:
        # F11 (F-4): every city's grid at least as fine as Riyadh's at the same node count
        hR = D.h_ref(ng, setback)
        Tgs = {w: D.grid_for(city, w, setback, ng, h_max=hR) for w in F.EVAL_W}
        def Lfun(lam):
            rs = [D.lagrangian(city, w, pv, lam, setback, ng, rel, c_sw, Tg=Tgs[w], **rk) for w in F.EVAL_W]
            return float(np.mean([r["L"] for r in rs])), rs[0]["days"]
        v, lam, curve = D.dual_max(Lfun, tgt)
        s = 100.0 * (1 - v / Jb.mean())
        tag = f"{'rel' if rel else 'unrel'}{ng}"
        out[f"bound_{tag}"] = s
        out[f"lam_{tag}"] = lam
        out[f"h_max_{tag}"] = max(float(Tg[1] - Tg[0]) for Tg in Tgs.values())
        curves[tag] = sorted(curve.items())            # L_raw(lam), per day, pooled over EVAL_W
    # invariant: relaxed <= unrelaxed (pointwise in lam, same grid): theorem of the relaxation
    for g in set(grids_rel) & set(grids_unrel):
        cr, cu = dict(curves[f"rel{g}"]), dict(curves[f"unrel{g}"])
        common = sorted(set(cr) & set(cu))
        gap = min(cu[l] - cr[l] for l in common)
        out[f"rel_le_unrel_{g}_min_gap"] = gap
        assert gap >= -1e-12, f"{city}: relaxed L > unrelaxed L at grid {g} (gap {gap})"
    rel_main = f"rel{max(grids_rel)}"
    # every relaxed grid gives a valid bound; the tightest is the smallest saving
    out["bound_reported"] = up01(min(out[f"bound_rel{g}"] for g in grids_rel))
    out["bound_reported_grid"] = min(grids_rel, key=lambda g: out[f"bound_rel{g}"])
    pw, pw_curves = [], {}
    if perwindow or do_clv:
        ng = max(grids_rel)                       # tightest per-window bound
        ngc = 3201 if not setback else 6401       # CLV replay grid (achievable)
        hR = D.h_ref(ng, setback)
        for w in F.EVAL_W:
            Tg = D.grid_for(city, w, setback, ng, h_max=hR)
            row = dict(city=city, price=pv, c_sw=c_sw, setback=setback, ruled=ruled, window=w,
                       therm_J=th[w]["J"], therm_T=th[w][K], therm_T_end=th[w]["T_end"])
            if perwindow:
                v, lam, cw = D.dual_max(lambda l: (D.lagrangian(city, w, pv, l, setback, ng, True, c_sw,
                                                                Tg=Tg, **rk)["L"], 7.0), th[w][K])
                row.update(bound_J_w=v, bound_s_w=100.0 * (1 - v / th[w]["J"]), lam_w=lam,
                           grid_h_w=float(Tg[1] - Tg[0]))
                pw_curves[str(w)] = sorted(cw.items())
            if do_clv:
                row.update(clv_row(city, w, pv, setback, c_sw, ngc, th[w], **rk))
                if perwindow:
                    row["clv_cert_margin"] = D.certificate_margin(row["clv_J"], row["clv_T"], row["bound_J_w"],
                                                                  row["lam_w"], th[w][K])
            pw.append(row)
        if do_clv:
            Jc = [r["clv_J"] for r in pw]; Jq = [r["clv_J_eq"] for r in pw]
            out["clv_fit_status"] = "oracle"
            out["clv_s_pooled"] = F.pooled_saving(Jc, Jq)                 # Rule C (Sec. 2.3)
            out["clv_s_raw"] = F.pooled_saving(Jc, Jb)
            out["clv_dT_pooled"] = float(np.mean([r["clv_T"] - r["therm_T"] for r in pw]))
            out["clv_max_abs_dT_w"] = float(max(abs(r["clv_T"] - r["therm_T"]) for r in pw))
            out["clv_n_tol_met"] = int(sum(bool(r["clv_tol_met"]) for r in pw))
            out["clv_start_sav"] = F.pooled_saving([r["clv_fs"] for r in pw], [r["clv_fs_eq"] for r in pw])
            out["clv_T_end_mean"] = float(np.mean([r["clv_T_end"] for r in pw]))
            out["therm_T_end_mean"] = float(np.mean([r["therm_T_end"] for r in pw]))
            out["clv_fallback_steps"] = int(sum(r["clv_fallback_steps"] for r in pw))
            # B_clv: the bound at CLV's own pooled mean against CLV's own comparator (s_a <= B_a)
            Tc = float(np.mean([r["clv_T"] for r in pw]))
            out["clv_B_a"] = 100.0 * (1.0 - lower_cost_curves(curves, Tc) / float(np.mean(Jq)))
            out["clv_le_B_a"] = out["clv_s_pooled"] <= out["clv_B_a"] + 1e-9
            out["clv_le_bound_pooled"] = out["clv_s_pooled"] <= out["bound_reported"] + 1e-9
            if perwindow:
                out["clv_cert_min_margin"] = float(min(r["clv_cert_margin"] for r in pw))
                out["clv_le_bound_all_windows"] = out["clv_cert_min_margin"] >= -1e-9
    print(f"{city:7s} p={pv:.2f} csw={c_sw:.3f} sb={setback!s:5s} ruled={ruled!s:5s} " +
          " ".join(f"{k}={v:.3f}" for k, v in out.items()
                   if k.startswith(("bound", "clv_s", "lam_rel", "clv_cert", "clv_B")) and not isinstance(v, bool)) +
          f"  ok={out.get('clv_le_bound_all_windows')}/{out.get('clv_le_B_a')}/{out.get('clv_le_bound_pooled')}"
          f"  ({time.time()-t0:.0f}s)", flush=True)
    return out, pw, curves, pw_curves


def clv_row(city, w, pv, setback, c_sw, ngc, th_w, ruled=False, rule_on=None, rule_off=None):
    """THE CLV of one held-out window (F10): r3_dp.clv_fit (two-sided lam refinement to
    CLV_TOL, admissibility through F.admissible inside it), scored by Rule C at the CLV's own
    clipped mean, both sides under the uniform O4 terminal (r3_dp.comparator_uniform; ruling
    §21.3). fit_status "oracle"."""
    lam, r, info = D.clv_fit(city, w, pv, th_w[K], setback, ngc, c_sw, ruled=ruled,
                             rule_on=rule_on, rule_off=rule_off)
    e = D.comparator_uniform(city, w, pv, r[K], setback, c_sw)     # Rule C, uniform O4 terminal
    return dict(clv_fit_status="oracle", clv_lam=lam, clv_cap=info["cap"], clv_J=r["J"], clv_T=r[K],
                clv_resid=info["resid"], clv_tol_met=info["tol_met"], clv_fs=r["f_s"], clv_E=r["E"],
                clv_T_end=r["T_end"], clv_fallback_steps=int(r["fallback_steps"]),
                clv_deg_h_over=r["deg_h_over"], clv_deg_h_cmd_under=r["deg_h_cmd_under"],
                clv_deg_h_ff_under=r["deg_h_ff_under"],
                clv_J_eq=float(e["J"]), clv_fs_eq=float(e["f_s"]), clv_E_eq=float(e["E"]),
                clv_eq_clipped=bool(e["clipped"]), clv_s_w=100.0 * (1 - r["J"] / float(e["J"])))


def write(name, rows):
    """through rbrl_io: atomic, locked, RBRL_TAG-aware, key union, provenance (F2)."""
    return IO.write_csv(name, rows)


def ruled_rules():
    """(R1, R2) of every in-rules arm the ruled bound must cover (F-10): the training rules
    23.80/22.40 and each city's fitted guard (on at cap - GUARD_HOT, off at GUARD_OFF), read from
    the tuned-parameter file when it exists (stated, never silent)."""
    import t1_v2 as T1V2
    rules = [(CFG.RULE_ON, CFG.RULE_OFF)]
    try:
        prm = IO.read_json(T1V2.PARAMS_NAME if hasattr(T1V2, "PARAMS_NAME") else "tuned_params_v2")
    except FileNotFoundError:
        print("ruled bound: no tuned-parameter file; covering the training rules only", flush=True)
        return rules
    for k, v in prm.items():
        if k.endswith("|guard") and "on" in v:
            rules.append((float(v["on"]), float(v.get("off", CFG.RULE_OFF))))
    return rules


def main(mode, cities=F.CITIES):
    """main: per city T17v3_<city> (+ _perwindow, _dualcurves.json): relaxed bound pooled and per
    window, L_raw(lam) curves, CLV (F10). sb: T17v3sb_<city>. ruled: T17v3_ruled_<city> (ruled
    relaxed bound + CLV in rules, RULE_ON/RULE_OFF covering every in-rules arm). tariff / csw:
    T4v3_bound / T5v3_bound."""
    import v3_names as V
    if mode in ("main", "sb", "ruled"):
        ron, roff = D.ruled_cover(ruled_rules()) if mode == "ruled" else (None, None)
        for city in cities:
            sb = mode == "sb"
            gr, gu = ((6401, 25601), (6401,)) if sb else ((1601, 3201, 6401, 12801), (1601, 3201, 12801))
            if mode == "ruled":
                gr, gu = (12801,), ()
            o, pw, cv, pwc = config(city, CFG.PRICE, sb, CFG.C_SW, gr, gu, ruled=mode == "ruled",
                                    rule_on=ron, rule_off=roff)
            stem = {"main": V.name("CLV", city), "sb": V.name("CLV_SB", city),
                    "ruled": V.name("BOUND_RULED", city)}[mode]
            write(stem, [o]); write(f"{stem}_perwindow", pw)
            key = f"{city}|{CFG.PRICE}|{CFG.C_SW}|{sb}" + ("|ruled" if mode == "ruled" else "")
            IO.write_json(f"{stem}{IO.tag()}_dualcurves",
                          {key: cv, key + "|perwindow": pwc}, apply_tag=False, embed=False)
        return
    summ, perw, curves = [], [], {}
    if mode == "tariff":
        jobs = [("riyadh", CFG.TARIFFS[t], False, CFG.C_SW) for t in ("historical", "y2027")]
    else:
        jobs = [(c, CFG.PRICE, False, cs) for cs in (0.025, 0.114) for c in F.CITIES]
    for city, pv, sb, cs in jobs:
        o, pw, cv, pwc = config(city, pv, sb, cs, (12801,), ())
        summ.append(o); perw += pw
        curves[f"{city}|{pv}|{cs}|{sb}"] = cv
        curves[f"{city}|{pv}|{cs}|{sb}|perwindow"] = pwc
    name = {"tariff": V.name("T4_BOUND"), "csw": V.name("T5_BOUND")}[mode]
    write(name, summ)
    write(f"{name}_perwindow", perw)
    IO.write_json(f"{name}{IO.tag()}_dualcurves", curves, apply_tag=False, embed=False)


if __name__ == "__main__":
    H.check_scenario_tag()          # a C_th / dt scenario must carry RBRL_TAG (F21/F23)
    main(sys.argv[1], sys.argv[2].split(",") if len(sys.argv) > 2 else F.CITIES)
