#!/usr/bin/env python3
"""Latent-load study, rebuilt from scratch on the adopted model.

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

    def __init__(self, city, faces=1, c_th=4800.0, shr_rated=0.75, f_hyg=4.0):
        self.city, self.c_th, self.shr = city, c_th, shr_rated
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
        self.M_w = rho * H.VOL_Z * f_hyg                   # kg, with buffering
        self.q_lat_max = H.Q_HVAC * (1.0 - shr_rated)
        self.t_adp = 11.0
        self.w_adp = float(w_from_rh(self.t_adp, 100.0, self.P))
        self.m_coil = (H.Q_HVAC * shr_rated) / (CP * 10.0)  # kg/s over 10 K rise

    def run(self, policy, start_day, hours=168, latent=True, T0=23.0):
        spd = int(round(1.0 / DT)); N = int(round(hours / DT))
        h0 = start_day * 24
        t_out = np.repeat(self.t_out_h[h0:h0 + hours], spd)[:N]
        irr = np.repeat(self.irr_h[h0:h0 + hours], spd)[:N]
        w_out = np.repeat(self.w_out_h[h0:h0 + hours], spd)[:N]
        T, w, prev = T0, float(w_from_rh(T0, 50.0, self.P)), 0
        J = E = dh = 0.0; sw = 0
        Tsum = 0.0; wsum = 0.0; rhmax = 0.0
        n_wlim = n_wlim_out = n_capped = 0
        c_J = self.c_th * 1e3
        for k in range(N):
            u = int(policy(T, prev, k))
            if u == 1 and prev == 0:
                J += H.C_SW; sw += 1
            if u == 1:
                if latent:
                    drive = max(0.0, self.m_coil * (w - self.w_adp) * H_FG)
                    q_lat = min(self.q_lat_max, drive)
                    if q_lat >= self.q_lat_max - 1e-9 and drive > 0:
                        n_capped += 1
                else:
                    q_lat = 0.0
                q_sen = H.Q_HVAC - q_lat
                J += PRICE * self.p_el * DT
                E += self.p_el * DT
            else:
                q_lat = q_sen = 0.0
            T_inf = t_out[k] + (H.SHGC * H.A_GL * irr[k] - q_sen) / self.lam
            T = T_inf + (T - T_inf) * self.decay
            if latent:
                dw = (self.m_inf * (w_out[k] - w) - q_lat / H_FG) / self.M_w
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
                    T += excess * self.M_w * H_FG / c_J
                    w = w_sat
                if w > W_LIMIT:
                    n_wlim += 1
            if w_out[k] > W_LIMIT:
                n_wlim_out += 1
            dh += max(0.0, T - HI) * DT + max(0.0, LO - T) * DT
            Tsum += T; wsum += w
            rh = rh_from_w(T, w, self.P)
            rhmax = max(rhmax, rh)
            prev = u
        # terminal thermal state, as the main accounting prices it
        J += PRICE * (T - T0) * c_J / 3.6e6 / H.COP_RATED
        days = N * DT / 24.0
        return dict(J=J / days, E=E / days, f_s=sw / days, deg_h=dh,
                    T_mean=Tsum / N, w_mean=wsum / N,
                    rh_max=rhmax, w_over=100.0 * n_wlim / N,
                    w_out_over=100.0 * n_wlim_out / N,
                    lat_capped=100.0 * n_capped / N)


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
    """The paper's own admission rule, inside this physics variant."""
    best = None
    for on_ in np.arange(LO + 0.3, HI + 1e-9, step):
        for off_ in np.arange(LO, on_ - 0.09, step):
            Js, ok = [], True
            for w in windows:
                r = z.run(hyst(on_, off_), w, latent=latent)
                if r["deg_h"] > 1e-9 or abs(r["T_mean"] - targets[w]) > tol:
                    ok = False; break
                Js.append(r["J"])
            if ok:
                m = float(np.mean(Js))
                if best is None or m < best[0]:
                    best = (m, float(on_), float(off_))
    return best


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shr", type=float, default=0.75)
    ap.add_argument("--cities", default="riyadh,jeddah,taif")
    a = ap.parse_args()
    print("Latent study on the adopted model (POA solar, saturation clamp, "
          f"per-window matching), SHR_rated={a.shr}\n")
    ok = selftest()
    rows = []
    for city in a.cities.split(","):
        z = Zone(city, shr_rated=a.shr)
        print(f"\n=== {city.upper()}  Lam={z.lam:.2f} W/K  "
              f"Q_lat_max={z.q_lat_max:.0f} W  P={z.P/1000:.1f} kPa ===")
        for lab, lat in (("sensible", False), ("latent", True)):
            # baseline and target means inside THIS physics variant
            th = {w: z.run(hyst(23.5, 22.5), w, latent=lat) for w in F.EVAL_W}
            tune_t = {w: z.run(hyst(23.5, 22.5), w, latent=lat)["T_mean"]
                      for w in F.TUNE_W}
            got = tune(z, lat, F.TUNE_W, tune_t)
            if got is None:
                print(f"  {lab}: NO admissible tuned rule"); continue
            _, on_, off_ = got
            sav, degs = [], []
            agg = dict(E_t=0.0, E_r=0.0, fs_t=0.0, fs_r=0.0, wo=0.0, cap=0.0,
                       woo=0.0, rhm=0.0)
            for w in F.EVAL_W:
                r = z.run(hyst(on_, off_), w, latent=lat)
                sav.append(100.0 * (th[w]["J"] - r["J"]) / th[w]["J"])
                degs.append(r["deg_h"])
                agg["E_t"] += th[w]["E"]; agg["E_r"] += r["E"]
                agg["fs_t"] += th[w]["f_s"]; agg["fs_r"] += r["f_s"]
                agg["wo"] += r["w_over"]; agg["cap"] += r["lat_capped"]
                agg["woo"] += r["w_out_over"]
                agg["rhm"] = max(agg["rhm"], r["rh_max"])
            n = len(F.EVAL_W)
            sv = float(np.mean(sav)); sd = float(np.std(sav, ddof=1))
            dE = 100.0 * (agg["E_t"] - agg["E_r"]) / agg["E_t"]
            print(f"  {lab:9s} rule {on_:.2f}/{off_:.2f}  "
                  f"sav {sv:+.2f}+/-{sd:.2f}%  dE {dE:+.2f}%  "
                  f"f_s {agg['fs_r']/n:.2f} (TH {agg['fs_t']/n:.2f})  "
                  f"w>limit {agg['wo']/n:.1f}% (out {agg['woo']/n:.1f}%)  "
                  f"RH_max {agg['rhm']:.1f}%  coil capped {agg['cap']/n:.1f}%")
            rows.append(dict(city=city, model=lab, shr=a.shr,
                             on=round(on_, 2), off=round(off_, 2),
                             sav=round(sv, 3), sav_sd=round(sd, 3),
                             dE_pct=round(dE, 3),
                             fs=round(agg["fs_r"] / n, 3),
                             fs_therm=round(agg["fs_t"] / n, 3),
                             w_over_pct=round(agg["wo"] / n, 2),
                             w_out_over_pct=round(agg["woo"] / n, 2),
                             rh_max=round(agg["rhm"], 1),
                             lat_capped_pct=round(agg["cap"] / n, 2),
                             max_deg_h=round(max(degs), 5)))
    os.makedirs("/home/claude/rbrl/results", exist_ok=True)
    with open("/home/claude/rbrl/results/T22_latent2.csv", "w", newline="") as f:
        wcsv = csv.DictWriter(f, fieldnames=list(rows[0]))
        wcsv.writeheader(); wcsv.writerows(rows)
    print(f"\nselftest {'PASSED' if ok else 'FAILED'}  "
          f"-> results/T22_latent2.csv")
