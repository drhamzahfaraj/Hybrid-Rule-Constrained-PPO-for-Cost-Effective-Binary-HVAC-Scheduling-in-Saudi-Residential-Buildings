#!/usr/bin/env python3
"""Latent-load study, round 3 (ruling d): fixed-ADP / bypass-factor coil.

Round-3 changes to latent2.py (kept for the record in results/archive_r3):
  * COIL. The fixed-SHR cap min((1-SHR)Q, ...) made latent capacity FALL as the
    entering air got wetter, the wrong direction. Replaced by a fixed apparatus
    dew point / bypass-factor coil at the main model's sensible capacity Q_s:
        m   = Q_s / (c_p (1-BF)(T_in - T_ADP))
        q_l = m h_fg (1-BF) max(0, w_in - w_ADP)
            = Q_s h_fg max(0, w_in - w_ADP) / (c_p (T_in - T_ADP)),
    so latent removal rises with entering humidity (BF cancels). T_ADP = 10 C,
    sensitivity 8 and 12 C; BF = 0.15.
  * INTERNAL MOISTURE. ASHRAE Standard 160 (Addendum b) design moisture
    generation for a 1-bedroom, 2-occupant dwelling, 7 L/day, applied to the
    zone (sensitivity 0 and 3.5 L/day).
  * CONDENSATE HEAT uses the zone's dry-air mass, not the buffered M_w.
  * MATCHING follows the round-3 protocol: rule tuned on the tuning windows
    inside each physics variant, frozen, and evaluated on the held-out windows
    against the comparator THERM(delta_w) equalised per window (Rule C). It is
    NOT matched per held-out window.
  * lat_active_pct is the share of COMPRESSOR RUNTIME during which the coil
    dehumidifies (w_in > w_ADP).
  * Taif is tuned at a 0.02 K step.

Original header (latent2.py) follows.

The study this replaces had three defects, each sufficient to disqualify its
numbers, and all three are repaired here rather than disclosed:

1. SOLAR. It applied global horizontal irradiance (DNI*cos(zenith)+DHI) to the
   glazing, while the adopted model transposes to the plane of the south
   vertical window (`hvac.vertical_irradiance`). At these latitudes in summer
   the horizontal figure is 2.3--2.5x the vertical one, so the old study ran on
   a solar gain more than double the model it claimed to perturb. This rebuild
   imports the SAME transposition the main study uses, so the sensible-only arm
   of this module IS the main model, verified below to machine precision.

2. MATCHING. It compared arms at fixed thresholds with no comfort matching, the
   exact error the matching protocol exists to prevent. Here every arm is
   tuned on the tuning windows and matched per held-out window to that window's
   own baseline mean, the identical admission rule as `final_tables.tune_rule`,
   applied WITHIN each physics variant so the sensible and latent variants each
   carry their own honestly matched pair.

3. SATURATION. Its moisture balance let zone humidity reach 103.8% RH, which no
   zone with surfaces can do. Here the moisture node carries a saturation
   clamp: humidity above saturation condenses, and the condensate's enthalpy of
   vaporisation is returned to the SENSIBLE node, because condensation on a
   surface heats the surface. The clamp is energy-consistent, so RH <= 100% by
   construction rather than by reporting.

Model parameters are the adopted ones throughout (C_th 4800 kJ/K, band
[22,24] occupied, in-force 0.18 SAR/kWh, c_sw 0.15 SAR, 0.6 ACH, the same
envelope conductance), NOT the exploratory values of the superseded script.

Physics added on top of the sensible model
------------------------------------------
Moisture balance on zone humidity ratio w [kg/kg], dry-air mass M_w with a
hygric buffering factor f_hyg for furnishings and surfaces:

    M_w dw/dt = m_inf (w_out - w) - q_lat / h_fg          (moist)

Coil split at rated total capacity Q_tot: latent removal is driven by the zone
state against the apparatus dew point, capped by the rated latent fraction,

    q_lat = min( (1-SHR) Q_tot ,  m_coil (w - w_ADP) h_fg ),   q_sen = Q_tot - q_lat

so in humid air the coil's sensible output falls, runtime rises at equal
electrical draw, and the energy penalty of humidity appears as runtime rather
than as an assumed coefficient.

Comfort on the moisture axis follows ASHRAE 55's humidity-ratio limit of
0.012 kg/kg; the fraction of occupied time above it is reported for both the
outdoor air and the zone.
"""
from __future__ import annotations
import sys, csv, os, argparse
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np

import headroom as H
import final_tables as F
from hvac import read_epw, vertical_irradiance

CP, H_FG = 1005.0, 2450e3
R_AIR = 287.055
W_LIMIT = 0.012                 # kg/kg, ASHRAE 55 upper humidity-ratio limit
LO, HI = 22.0, 24.0
PRICE = 0.18
DT = H.DT


def p_sat(T):
    return 610.94 * np.exp(17.625 * T / (T + 243.04))


def w_from_rh(T, rh, P=101325.0):
    pv = np.clip(rh, 0.0, 100.0) / 100.0 * p_sat(T)
    return 0.62198 * pv / (P - pv)


def rh_from_w(T, w, P=101325.0):
    pv = w * P / (0.62198 + w)
    return 100.0 * pv / p_sat(T)


def read_epw_humidity(city):
    """RH [%] and station pressure [Pa], hourly, from the same EPW as the
    dry-bulb and irradiance the main study uses."""
    rh, pa = [], []
    with open(f"/home/claude/rbrl/{city}.epw") as f:
        for line in f:
            row = line.split(",")
            if len(row) > 20 and row[0].isdigit():
                rh.append(float(row[8])); pa.append(float(row[9]))
    rh = np.array(rh); pa = np.array(pa)
    pa = np.where(pa > 5e4, pa, H.P_STATION[city])
    return rh, pa


class Zone:
    """Sensible(+moisture) zone on the adopted parameters.

    With latent=False this is EXACTLY the main model: same conductance, same
    exact exponential step, same cost accounting. selftest() verifies that
    equivalence against headroom's own series and setback.sim's arithmetic.
    """

    def __init__(self, city, faces=1, c_th=4800.0, t_adp=10.0, gen_l_day=7.0, f_hyg=4.0,
                 fixed_total=False):
        self.city, self.c_th = city, c_th
        self.lam = H.lam_of(faces, city)
        self.decay = float(np.exp(-DT * 3600.0 * self.lam / (c_th * 1e3)))
        self.p_el = H.Q_HVAC / H.COP_RATED / 1000.0
        tdb, dni, dhi = read_epw(f"/home/claude/rbrl/{city}.epw")
        self.t_out_h = np.asarray(tdb, float)
        self.irr_h = vertical_irradiance(dni, dhi, H.CITIES[city],
                                         azimuth_deg=180.0)
        rh, pa = read_epw_humidity(city)
        self.P = float(np.mean(pa))
        self.w_out_h = w_from_rh(self.t_out_h, rh, pa)
        rho = self.P / (R_AIR * (24.0 + 273.15))
        self.m_inf = H.ACH_Z * H.VOL_Z * rho / 3600.0      # kg/s dry air
        self.M_air = rho * H.VOL_Z                         # kg dry air in the zone
        self.M_w = self.M_air * f_hyg                      # kg, with buffering
        self.t_adp = t_adp
        self.w_adp = float(w_from_rh(self.t_adp, 100.0, self.P))
        self.gen = gen_l_day / 86400.0                     # kg/s internal moisture
        # fixed_total: total coil capacity held at its value at the AHRI 210/240
        # rating point (26.7 C db / 19.4 C wb entering) with the main model's
        # sensible Q there; at other entering states the ADP line splits that
        # total, so sensible output FALLS as humidity rises (an energy penalty).
        self.fixed_total = fixed_total
        w_r = 0.0108
        self.shr_rating = 1.0 / (1.0 + H_FG * (w_r - self.w_adp) / (CP * (26.7 - self.t_adp)))
        self.q_tot = H.Q_HVAC / self.shr_rating

    def run(self, policy, start_day, hours=168, latent=True, T0=23.0):
        spd = int(round(1.0 / DT)); N = int(round(hours / DT))
        h0 = start_day * 24
        t_out = np.repeat(self.t_out_h[h0:h0 + hours], spd)[:N]
        irr = np.repeat(self.irr_h[h0:h0 + hours], spd)[:N]
        w_out = np.repeat(self.w_out_h[h0:h0 + hours], spd)[:N]
        T, w, prev = T0, float(w_from_rh(T0, 50.0, self.P)), 0
        J = E = dh = 0.0; sw = 0
        Tsum = 0.0; wsum = 0.0; rhmax = 0.0
        n_wlim = n_wlim_out = n_capped = n_on = 0
        Tclip = 0.0
        c_J = self.c_th * 1e3
        for k in range(N):
            u = int(policy(T, prev, k))
            if u == 1 and prev == 0:
                J += H.C_SW; sw += 1
            if u == 1:
                n_on += 1
                if latent and w > self.w_adp and T > self.t_adp:
                    ratio = H_FG * (w - self.w_adp) / (CP * (T - self.t_adp))   # q_lat/q_sen
                    if self.fixed_total:
                        q_sen = self.q_tot / (1.0 + ratio); q_lat = self.q_tot - q_sen
                    else:
                        q_sen = H.Q_HVAC; q_lat = H.Q_HVAC * ratio
                    n_capped += 1            # counts dehumidifying runtime
                else:
                    q_lat = 0.0
                    q_sen = self.q_tot if (latent and self.fixed_total) else H.Q_HVAC
                J += PRICE * self.p_el * DT
                E += self.p_el * DT
            else:
                q_lat = q_sen = 0.0
            T_inf = t_out[k] + (H.SHGC * H.A_GL * irr[k] - q_sen) / self.lam
            T = T_inf + (T - T_inf) * self.decay
            if latent:
                dw = (self.m_inf * (w_out[k] - w) + self.gen - q_lat / H_FG) / self.M_w
                w = max(0.0, w + dw * DT * 3600.0)
                # saturation clamp, energy-consistent: condensing the excess
                # releases its enthalpy of vaporisation to the sensible node.
                # Two passes, because the released heat raises T and with it
                # the saturation limit; the second excess is second-order.
                for _ in range(2):
                    w_sat = float(w_from_rh(T, 100.0, self.P))
                    if w <= w_sat:
                        break
                    excess = w - w_sat
                    T += excess * self.M_air * H_FG / c_J
                    w = w_sat
                if w > W_LIMIT:
                    n_wlim += 1
            if w_out[k] > W_LIMIT:
                n_wlim_out += 1
            dh += max(0.0, T - HI) * DT + max(0.0, LO - T) * DT
            Tsum += T; wsum += w; Tclip += max(T, LO)
            rh = rh_from_w(T, w, self.P)
            rhmax = max(rhmax, rh)
            prev = u
        # terminal thermal state, as the main accounting prices it
        J += PRICE * (T - T0) * c_J / 3.6e6 / H.COP_RATED
        days = N * DT / 24.0
        return dict(J=J / days, E=E / days, f_s=sw / days, deg_h=dh,
                    T_mean=Tsum / N, T_mean_occ_clip=Tclip / N, w_mean=wsum / N,
                    rh_max=rhmax, w_over=100.0 * n_wlim / N,
                    w_out_over=100.0 * n_wlim_out / N,
                    lat_active=100.0 * n_capped / max(1, n_on), on_steps=n_on)


def hyst(on, off):
    return lambda T, prev, k: 1 if T >= on else (0 if T <= off else prev)


def selftest():
    """latent=False must reproduce the main model exactly."""
    z = Zone("riyadh")
    r = z.run(hyst(23.5, 22.5), 121, latent=False)
    th = F.therm_run("riyadh", 121, PRICE)
    dj = abs(r["J"] - th["J"]); dT = abs(r["T_mean"] - th["T_mean_occ"])
    print(f"  selftest vs therm_run: dJ={dj:.2e} SAR/day, dT={dT:.2e} K "
          f"({'PASS' if dj < 1e-9 and dT < 1e-9 else 'FAIL'})")
    return dj < 1e-9 and dT < 1e-9


def tune(z, latent, windows, targets, tol=0.03, step=0.05):
    """The paper's own admission rule (Rule A, clipped mean), inside this physics
    variant. The 0.02 K step searches on 23.0-24.0 / 22.0-23.0 only."""
    best = None
    on_rng = np.arange(LO + 0.3, HI + 1e-9, step) if step >= 0.05 else np.arange(23.0, HI + 1e-9, step)
    for on_ in on_rng:
        for off_ in np.arange(LO, min(on_ - 0.09, 23.0 + 1e-9), step):
            Js, ok = [], True
            for w in windows:
                r = z.run(hyst(on_, off_), w, latent=latent)
                if r["deg_h"] > 1e-9 or abs(r["T_mean_occ_clip"] - targets[w]) > tol:
                    ok = False; break
                Js.append(r["J"])
            if ok:
                m = float(np.mean(Js))
                if best is None or m < best[0]:
                    best = (m, float(on_), float(off_))
    return best


def equalise(z, lat, w, target, lo=-0.4, hi=0.4, step=0.002):
    """Rule C inside the physics variant (bisection on the staircase, then
    linear interpolation of J and the moisture metrics)."""
    ds = np.round(np.arange(lo, hi + 1e-12, step), 6)
    cache = {}
    def run(d):
        if d not in cache:
            cache[d] = z.run(hyst(23.5 + d, 22.5 + d), w, latent=lat)
        return cache[d]
    a, b = 0, len(ds) - 1
    if run(ds[a])["T_mean_occ_clip"] > target:
        return run(ds[a])
    if run(ds[b])["T_mean_occ_clip"] < target:
        return run(ds[b])
    while b - a > 1:
        m = (a + b) // 2
        if run(ds[m])["T_mean_occ_clip"] <= target: a = m
        else: b = m
    ra, rb = run(ds[a]), run(ds[b])
    sp = rb["T_mean_occ_clip"] - ra["T_mean_occ_clip"]
    t = 0.0 if sp <= 1e-12 else (target - ra["T_mean_occ_clip"]) / sp
    return {k: (ra[k] + t * (rb[k] - ra[k]) if isinstance(ra[k], float) else ra[k]) for k in ra}


VARIANTS = [("sensible", False, 10.0, 7.0), ("latent", True, 10.0, 7.0),
            ("latent_adp8", True, 8.0, 7.0), ("latent_adp12", True, 12.0, 7.0),
            ("latent_gen0", True, 10.0, 0.0), ("latent_gen3.5", True, 10.0, 3.5),
            ("latent_fixedtotal", True, 10.0, 7.0)]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cities", default="riyadh,jeddah,taif")
    ap.add_argument("--variants", default="all")
    ap.add_argument("--out", default="T22v2_latent")
    a = ap.parse_args()
    ok = selftest()
    rows = []
    for city in a.cities.split(","):
        for lab, lat, tadp, gen in VARIANTS:
            if a.variants != "all" and lab not in a.variants.split(","):
                continue
            z = Zone(city, t_adp=tadp, gen_l_day=gen, fixed_total=(lab == "latent_fixedtotal"))
            th = {w: z.run(hyst(23.5, 22.5), w, latent=lat) for w in F.WINDOWS}
            tg = {w: th[w]["T_mean_occ_clip"] for w in F.WINDOWS}
            got = tune(z, lat, F.TUNE_W, tg, step=0.02 if city == "taif" else 0.05)
            if got is None:
                print(f"  {city} {lab}: NO admissible tuned rule", flush=True); continue
            _, on_, off_ = got
            Ja, Jq, J0, fa, fq, Ea, Eq = [], [], [], [], [], [], []
            wo_r, wo_t, woo, act, rhm, degs, dT = [], [], [], [], 0.0, [], []
            for w in F.EVAL_W:
                r = z.run(hyst(on_, off_), w, latent=lat)
                q = equalise(z, lat, w, r["T_mean_occ_clip"])
                Ja.append(r["J"]); Jq.append(q["J"]); J0.append(th[w]["J"])
                fa.append(r["f_s"]); fq.append(q["f_s"]); Ea.append(r["E"]); Eq.append(q["E"])
                wo_r.append(r["w_over"]); wo_t.append(q["w_over"]); woo.append(r["w_out_over"])
                act.append(r["lat_active"]); rhm = max(rhm, r["rh_max"], q["rh_max"])
                degs.append(r["deg_h"]); dT.append(r["T_mean_occ_clip"] - th[w]["T_mean_occ_clip"])
            sv = F.pooled_saving(Ja, Jq)
            row = dict(city=city, model=lab, t_adp=tadp, gen_l_day=gen,
                       shr_at_rating=round(z.shr_rating, 3), on=round(on_, 2),
                       off=round(off_, 2), fit_windows="TUNE_W",
                       s_pooled_eq=round(sv, 3), s_raw=round(F.pooled_saving(Ja, J0), 3),
                       energy_sav_eq=round(F.pooled_saving(Ea, Eq), 3),
                       start_sav_eq=round(F.pooled_saving(fa, fq), 3),
                       dT_pooled=round(float(np.mean(dT)), 4),
                       w_over_pct_tuned=round(float(np.mean(wo_r)), 2),
                       w_over_pct_therm=round(float(np.mean(wo_t)), 2),
                       w_out_over_pct=round(float(np.mean(woo)), 2),
                       rh_max=round(rhm, 1),
                       lat_active_pct_of_runtime=round(float(np.mean(act)), 2),
                       max_deg_h=round(max(degs), 5))
            rows.append(row)
            print("  " + " ".join(f"{k}={v}" for k, v in row.items()), flush=True)
            with open(f"/home/claude/rbrl/results/{a.out}.csv", "w", newline="") as f:
                wcsv = csv.DictWriter(f, fieldnames=list(rows[0]))
                wcsv.writeheader(); wcsv.writerows(rows)
    print(f"\nselftest {'PASSED' if ok else 'FAILED'}  -> results/T22v2_latent.csv")
