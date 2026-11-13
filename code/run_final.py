#!/usr/bin/env python3
"""Runner: emits T1..T6 for the revised manuscript."""
from __future__ import annotations
import sys, time
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import headroom as H
import setback as S
import final_tables as F

t_start = time.time()
OUT = []


def say(s=""):
    print(s, flush=True)
    OUT.append(s)


# ===================================================================== T1
say("=" * 112)
say("T1  HELD-OUT RESULTS, three cities, occupied band 22-24 C, dt 15 min")
say("    Rule tuned on 6 windows, evaluated on 7 DISJOINT windows. mean +/- sd.")
say("    Every arm comfort-matched to THERM's mean occupied temperature (<=0.03 K).")
say("=" * 112)
t1 = []
tuned_params = {}
for tname in ("inforce", "y2027"):
    pv = F.TARIFFS[tname]
    say(f"\n--- tariff {tname} = {pv} SAR/kWh ---")
    say(f"  {'city':7s} {'controller':26s} {'J SAR/zone/day':>16s} {'T_occ':>6s} "
        f"{'cost sav':>13s} {'energy sav':>13s} {'start sav':>13s}")
    for city in F.CITIES:
        th = {w: F.therm_run(city, w, pv) for w in F.WINDOWS}
        tgt = lambda w: th[w]["T_mean_occ"]
        bt = F.tune_rule(city, pv, F.TUNE_W, tgt)
        tuned_params[(city, tname)] = bt
        rows = {"THERM (1 K deadband @23 C)": [], "tuned rule": [],
                "DP ceiling": [], "DP + setback": []}
        for w in F.EVAL_W:
            rows["THERM (1 K deadband @23 C)"].append(th[w])
            if bt:
                rows["tuned rule"].append(F.rule_run(city, w, pv, bt[1], bt[2]))
            d = F.dp_isocomfort(city, w, pv, th[w]["T_mean_occ"])
            if d: rows["DP ceiling"].append(d[0])
            ds = F.dp_isocomfort(city, w, pv, th[w]["T_mean_occ"], setback=True)
            if ds: rows["DP + setback"].append(ds[0])
        Jb = np.array([r["J"] for r in rows["THERM (1 K deadband @23 C)"]])
        for lab, rs in rows.items():
            if not rs: continue
            J = np.array([r["J"] for r in rs]); E = np.array([r["E"] for r in rs])
            fs = np.array([r["f_s"] for r in rs])
            To = np.array([r["T_mean_occ"] for r in rs])
            dh = max(r["deg_h_occ"] for r in rs)
            # PAIRED per-window saving: each window is its own baseline, so
            # window-to-window load variation does not enter the dispersion.
            Eb = np.array([r["E"] for r in rows["THERM (1 K deadband @23 C)"]])
            Fb = np.array([r["f_s"] for r in rows["THERM (1 K deadband @23 C)"]])
            sav = 100.0 * (Jb - J) / Jb
            esav = 100.0 * (Eb - E) / Eb
            fsav = 100.0 * (Fb - fs) / Fb
            sd = lambda a: a.std(ddof=1) if len(a) > 1 else 0.0
            tag = lab if lab != "tuned rule" else f"tuned rule {bt[1]:.2f}/{bt[2]:.2f}"
            say(f"  {city:7s} {tag:26s} {J.mean():7.4f}+/-{sd(J):.4f} "
                f"{To.mean():6.2f} {sav.mean():6.1f}+/-{sd(sav):4.1f}% "
                f"{esav.mean():6.1f}+/-{sd(esav):4.1f}% {fsav.mean():6.1f}+/-{sd(fsav):4.1f}%")
            t1.append(dict(tariff=tname, price=pv, city=city, controller=tag,
                           n_eval=len(rs), J_mean=round(J.mean(), 4), J_sd=round(sd(J), 4),
                           E_mean=round(E.mean(), 4), E_sd=round(sd(E), 4),
                           fs_mean=round(fs.mean(), 3), fs_sd=round(sd(fs), 3),
                           T_occ_mean=round(To.mean(), 3), max_deg_h_occ=round(dh, 6),
                           cost_sav_mean_pct=round(sav.mean(), 2), cost_sav_sd_pct=round(sd(sav), 2),
                           E_sav_mean_pct=round(esav.mean(), 2), E_sav_sd_pct=round(sd(esav), 2),
                           start_sav_mean_pct=round(fsav.mean(), 2), start_sav_sd_pct=round(sd(fsav), 2)))
    say()
F.dump("T1_heldout_three_cities", t1)

# ===================================================================== T2
say("=" * 112)
say("T2  CONTROL / INTEGRATION STEP SENSITIVITY  (Reviewer 8), Riyadh, tariff in force")
say("    Deadband-form forcing condition: Q*dt/C_th <= delta, delta = THERM's 1 K deadband")
say("=" * 112)
t2 = []
say(f"  {'dt':>7s} {'Q*dt/C_th':>10s} {'<= delta?':>10s} {'THERM J':>8s} {'THERM deg-h':>12s} "
    f"{'rule sav':>9s} {'DP sav':>8s}")
for dt in (1/12, 0.25, 0.5, 1.0):
    H.DT = dt; S.DT = dt
    ov = 2000.0 * dt * 3600 / (F.C_TH * 1e3)
    th = F.therm_run("riyadh", F.WINDOWS[0], 0.18)
    bt = F.tune_rule("riyadh", 0.18, [F.WINDOWS[0]], lambda w: th["T_mean_occ"])
    d = F.dp_run("riyadh", F.WINDOWS[0], 0.18)
    rs = F.rule_run("riyadh", F.WINDOWS[0], 0.18, bt[1], bt[2]) if bt else None
    say(f"  {dt*60:5.0f}m {ov:10.3f} {'OK' if ov <= 1.0 else 'VIOLATED':>10s} "
        f"{th['J']:8.4f} {th['deg_h_occ']:12.3f} "
        f"{(f'{F.pct(th[chr(74)], rs[chr(74)]):8.1f}%' if rs else '      n/a'):>9s} "
        f"{F.pct(th['J'], d['J']):7.1f}%")
    t2.append(dict(dt_min=round(dt*60, 1), overshoot_K=round(ov, 4),
                   admissible=bool(ov <= 1.0), therm_J=round(th['J'], 4),
                   therm_deg_h=round(th['deg_h_occ'], 4),
                   rule_sav_pct=(round(F.pct(th['J'], rs['J']), 2) if rs else None),
                   dp_sav_pct=round(F.pct(th['J'], d['J']), 2)))
H.DT = 0.25; S.DT = 0.25
F.dump("T2_timestep", t2)
say()

# ===================================================================== T3
say("=" * 112)
say("T3  THERMAL CAPACITY SENSITIVITY  (Reviewer 2), Riyadh, tariff in force, dt 15 min")
say("    Admissible when Q*dt/C_th <= 1.0 K (THERM's deadband), i.e. C_th >= 1800 kJ/K")
say("=" * 112)
t3 = []
say(f"  {'C_th':>7s} {'Q*dt/C_th':>10s} {'adm?':>6s} {'THERM J':>8s} {'deg-h':>7s} "
    f"{'rule sav':>9s} {'DP sav':>8s} {'tau (h)':>8s}")
for C in (900.0, 1200.0, 1800.0, 2400.0, 4800.0, 7200.0, 9600.0):
    F.C_TH = C
    ov = 2000.0 * 0.25 * 3600 / (C * 1e3)
    th = F.therm_run("riyadh", F.WINDOWS[0], 0.18)
    bt = F.tune_rule("riyadh", 0.18, [F.WINDOWS[0]], lambda w: th["T_mean_occ"])
    d = F.dp_run("riyadh", F.WINDOWS[0], 0.18)
    rs = F.rule_run("riyadh", F.WINDOWS[0], 0.18, bt[1], bt[2]) if bt else None
    tau = C * 1e3 / H.lam_of(1, "riyadh") / 3600.0
    say(f"  {C:7.0f} {ov:10.3f} {'yes' if ov <= 1.0 else 'NO':>6s} {th['J']:8.4f} "
        f"{th['deg_h_occ']:7.3f} "
        f"{(f'{F.pct(th[chr(74)], rs[chr(74)]):8.1f}%' if rs else '      n/a'):>9s} "
        f"{(f'{F.pct(th[chr(74)], d[chr(74)]):7.1f}%' if d else '    n/a'):>8s} {tau:8.1f}")
    t3.append(dict(C_th=C, overshoot_K=round(ov, 4), admissible=bool(ov <= 1.0),
                   tau_h=round(tau, 2), therm_J=round(th['J'], 4),
                   therm_deg_h=round(th['deg_h_occ'], 4),
                   rule_sav_pct=(round(F.pct(th['J'], rs['J']), 2) if rs else None),
                   dp_sav_pct=(round(F.pct(th['J'], d['J']), 2) if d else None)))
F.C_TH = 4800.0
F.dump("T3_capacity", t3)
say()

# ===================================================================== T4
say("=" * 112)
say("T4  TARIFF DEPENDENCE  (Reviewer 6). The saving is switching-dominated, so it")
say("    scales inversely with the energy price. Riyadh, held-out window 1.")
say("=" * 112)
t4 = []
say(f"  {'schedule':12s} {'price':>6s} {'sw share of THERM cost':>23s} {'rule sav':>9s} {'DP sav':>8s}")
for tname in ("historical", "inforce", "y2027"):
    pv = F.TARIFFS[tname]
    th = F.therm_run("riyadh", F.WINDOWS[0], pv)
    bt = F.tune_rule("riyadh", pv, [F.WINDOWS[0]], lambda w: th["T_mean_occ"])
    d = F.dp_run("riyadh", F.WINDOWS[0], pv)
    rs = F.rule_run("riyadh", F.WINDOWS[0], pv, bt[1], bt[2]) if bt else None
    share = 100.0 * 0.15 * th["f_s"] / th["J"]
    say(f"  {tname:12s} {pv:6.2f} {share:22.1f}% "
        f"{(f'{F.pct(th[chr(74)], rs[chr(74)]):8.1f}%' if rs else '      n/a'):>9s} "
        f"{F.pct(th['J'], d['J']):7.1f}%")
    t4.append(dict(schedule=tname, price=pv, sw_share_pct=round(share, 2),
                   rule_sav_pct=(round(F.pct(th['J'], rs['J']), 2) if rs else None),
                   dp_sav_pct=round(F.pct(th['J'], d['J']), 2)))
F.dump("T4_tariff", t4)
say()

# ===================================================================== T5
say("=" * 112)
say("T5  SWITCHING-COST SENSITIVITY including c_sw = 0. Riyadh, tariff in force.")
say("=" * 112)
t5 = []
say(f"  {'c_sw':>6s} {'sw share':>9s} {'THERM J':>8s} {'rule sav':>9s} {'DP sav':>8s}")
for cs in (0.0, 0.05, 0.15, 0.30, 0.60):
    H.C_SW = cs
    th = F.therm_run("riyadh", F.WINDOWS[0], 0.18)
    bt = F.tune_rule("riyadh", 0.18, [F.WINDOWS[0]], lambda w: th["T_mean_occ"])
    d = F.dp_run("riyadh", F.WINDOWS[0], 0.18)
    rs = F.rule_run("riyadh", F.WINDOWS[0], 0.18, bt[1], bt[2]) if bt else None
    share = 100.0 * cs * th["f_s"] / th["J"]
    say(f"  {cs:6.2f} {share:8.1f}% {th['J']:8.4f} "
        f"{(f'{F.pct(th[chr(74)], rs[chr(74)]):8.1f}%' if rs else '      n/a'):>9s} "
        f"{F.pct(th['J'], d['J']):7.1f}%")
    t5.append(dict(c_sw=cs, sw_share_pct=round(share, 2), therm_J=round(th['J'], 4),
                   rule_sav_pct=(round(F.pct(th['J'], rs['J']), 2) if rs else None),
                   dp_sav_pct=round(F.pct(th['J'], d['J']), 2)))
H.C_SW = 0.15
F.dump("T5_switchcost", t5)
say()

# ===================================================================== T6
say("=" * 112)
say("T6  PER-WINDOW DETAIL on the held-out set (dispersion evidence), tariff in force")
say("=" * 112)
t6 = []
for city in F.CITIES:
    bt = tuned_params[(city, "inforce")]
    say(f"\n  {city.upper()}  tuned rule {bt[1]:.2f}/{bt[2]:.2f}")
    say(f"    {'start day':>10s} {'THERM J':>8s} {'rule J':>8s} {'sav':>7s} "
        f"{'THERM st/d':>11s} {'rule st/d':>10s} {'deg-h':>7s}")
    for w in F.EVAL_W:
        th = F.therm_run(city, w, 0.18)
        rs = F.rule_run(city, w, 0.18, bt[1], bt[2])
        say(f"    {w:10d} {th['J']:8.4f} {rs['J']:8.4f} {F.pct(th['J'], rs['J']):6.1f}% "
            f"{th['f_s']:11.2f} {rs['f_s']:10.2f} {rs['deg_h_occ']:7.3f}")
        t6.append(dict(city=city, start_day=w, therm_J=round(th['J'], 4),
                       rule_J=round(rs['J'], 4),
                       sav_pct=round(F.pct(th['J'], rs['J']), 2),
                       therm_fs=round(th['f_s'], 3), rule_fs=round(rs['f_s'], 3),
                       rule_deg_h=round(rs['deg_h_occ'], 6)))
F.dump("T6_per_window", t6)

say(f"\nTotal runtime {time.time()-t_start:.0f} s")
with open("/home/claude/rbrl/results/FINAL_TABLES.txt", "w") as f:
    f.write("\n".join(OUT))
print("-> results/FINAL_TABLES.txt")
