#!/usr/bin/env python3
"""Two-state zone model with latent load and an SHR-limited plant.

Why this exists
---------------
The manuscript's model is sensible-only ("captures sensible heat only"), so it
cannot distinguish a hot-arid from a hot-humid climate beyond dry-bulb
amplitude. Measured from the EPW humidity fields over 1 May - 31 Oct:

    Riyadh  mean w_out 0.00572 kg/kg, latent   1.7 W, SHR 0.994
    Jeddah  mean w_out 0.01779 kg/kg, latent 265.2 W, SHR 0.446

so more than half of Jeddah's load is moisture removal and none of it is
represented. This module adds it.

States
------
    T  zone dry-bulb                     [C]
    w  zone humidity ratio               [kg water / kg dry air]

Dynamics (exact exponential on the sensible node, explicit on the moisture node
because its forcing is piecewise constant and its time constant is long):

    C_th dT/dt = -Lam_sen (T - T_out) + q_sol - Q_sen u
    M_w  dw/dt =  m_inf (w_out - w) - Q_lat u / h_fg

    Lam_sen = per_face * faces + m_inf * cp      (fabric + infiltration sensible)
    M_w     = rho * V * f_hyg                    (air plus hygric buffering)

Plant
-----
A coil of fixed total capacity whose split follows the entering air, which is
the mechanism that matters: humid air consumes capacity that is then unavailable
for sensible cooling.

    latent_served   = min(Q_lat_max, latent load presented)
    sensible_served = Q_tot - latent_served        (>= 0)

Q_lat_max = Q_tot (1 - SHR_rated) is the coil's design dehumidification limit.
When the presented latent load exceeds it, humidity rises and the humidity
comfort limit is breached -- a failure a sensible-only model cannot express.

Electrical draw is Q_tot / COP while on, so the energy penalty of a humid
climate appears as longer run time, not as a different instantaneous power.
"""
from __future__ import annotations
import sys, csv, argparse
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np

CP, RHO, H_FG = 1005.0, 1.2, 2450e3
P_ATM = 101325.0


# ----------------------------------------------------------------- psychrometry
def p_sat(T):
    Tk = np.asarray(T, dtype=float) + 273.15
    return np.exp(-5.8002206e3 / Tk + 1.3914993 - 4.8640239e-2 * Tk
                  + 4.1764768e-5 * Tk ** 2 - 1.4452093e-8 * Tk ** 3
                  + 6.5459673 * np.log(Tk))


def w_from_rh(T, rh, P=P_ATM):
    pv = np.clip(rh, 0, 100) / 100.0 * p_sat(T)
    return 0.621945 * pv / np.maximum(P - pv, 1.0)


def rh_from_w(T, w, P=P_ATM):
    pv = w * P / (0.621945 + w)
    return 100.0 * pv / p_sat(T)


def read_epw(path):
    t, rh, pa, dni, dhi = [], [], [], [], []
    with open(path) as f:
        for i, row in enumerate(csv.reader(f)):
            if i < 8 or len(row) < 16:
                continue
            t.append(float(row[6])); rh.append(float(row[8]))
            pa.append(float(row[9])); dni.append(float(row[14]))
            dhi.append(float(row[15]))
    t = np.array(t); pa = np.array(pa)
    return (t, np.array(rh), np.where(pa > 5e4, pa, P_ATM),
            np.array(dni), np.array(dhi))


def ghi_of(dni, dhi, lat_deg, n):
    h = np.arange(n); day = h // 24 + 1; hour = h % 24 + 0.5
    decl = np.radians(23.45) * np.sin(2 * np.pi * (284 + day) / 365.0)
    lat = np.radians(lat_deg); omega = np.radians(15.0 * (hour - 12.0))
    cosz = np.clip(np.sin(lat) * np.sin(decl)
                   + np.cos(lat) * np.cos(decl) * np.cos(omega), 0, 1)
    return dni[:n] * cosz + dhi[:n]


# ----------------------------------------------------------------- the model
class LatentZone:
    def __init__(self, city, faces=1, dt=0.25, c_th=2400.0, ach=0.6, vol=64.0,
                 per_face=11.90, shgc=0.25, a_gl=2.0, q_tot=2000.0,
                 shr_rated=0.75, cop=2.985, f_hyg=4.0,
                 t_min=22.0, t_max=26.0, rh_max=60.0, price=0.05, c_sw=0.15):
        self.__dict__.update(locals()); del self.self
        lat = {"riyadh": 24.7, "jeddah": 21.5, "taif": 21.483}[city]
        t, rh, pa, dni, dhi = read_epw(f"/home/claude/rbrl/{city}.epw")
        n = len(t)
        self.t_out = t
        self.w_out = w_from_rh(t, rh, pa)
        self.ghi = ghi_of(dni, dhi, lat, n)
        self.m_inf = ach * vol * RHO / 3600.0            # kg/s dry air
        self.lam_sen = per_face * faces + self.m_inf * CP  # W/K
        self.M_w = RHO * vol * f_hyg                      # kg, moisture capacitance
        self.q_lat_max = q_tot * (1.0 - shr_rated)
        self.p_el = q_tot / cop / 1000.0                  # kW while on
        self.decay = float(np.exp(-dt * 3600.0 * self.lam_sen / (c_th * 1e3)))
        self.w_set = w_from_rh(24.0, 50.0)                # reference indoor state
        # coil: apparatus dew point and supply airflow
        self.t_adp = 11.0                                 # C, typical DX coil ADP
        self.w_adp = float(w_from_rh(self.t_adp, 100.0))   # saturated at ADP
        # supply airflow from the rated sensible capacity over a 10 K coil rise
        self.m_coil = (q_tot * shr_rated) / (CP * 10.0)    # kg/s dry air

    def run(self, policy, start_day=181, days=7, T0=24.0, w0=None, latent=True):
        dt = self.dt; spd = int(round(1.0 / dt)); N = int(days * 24 * spd)
        h0 = start_day * 24
        T = T0
        w = self.w_set if w0 is None else w0
        prev = 0
        cost = e = 0.0; sw = 0
        v_T = v_rh = 0; dh_T = 0.0
        w_hist = []; T_hist = []; rh_hist = []; lat_served = []
        for k in range(N):
            h = (h0 + k // spd) % len(self.t_out)
            t_out = self.t_out[h]; w_out = self.w_out[h]; g = self.ghi[h]
            u = int(policy(T, prev, k, rh_from_w(T, w)))
            if u == 1 and prev == 0:
                cost += self.c_sw; sw += 1
            # --- plant capacity split follows the entering air -----------------
            if u == 1:
                # Coil dehumidification is driven by the ZONE humidity against the
                # apparatus dew point, not by the infiltration gradient: as w rises
                # the coil removes more, which is the stabilising feedback a real
                # coil provides. Capped at the design latent capacity.
                if latent:
                    drive = max(0.0, self.m_coil * (w - self.w_adp) * H_FG)
                    q_lat = min(self.q_lat_max, drive)
                else:
                    q_lat = 0.0
                q_sen = max(0.0, self.q_tot - q_lat)
                cost += self.price * self.p_el * dt
                e += self.p_el * dt
            else:
                q_lat = q_sen = 0.0
            # --- sensible node, exact over the step ---------------------------
            T_inf = t_out + (self.shgc * self.a_gl * g - q_sen) / self.lam_sen
            T = T_inf + (T - T_inf) * self.decay
            # --- moisture node ------------------------------------------------
            if latent:
                dw = (self.m_inf * (w_out - w) - q_lat / H_FG) / self.M_w
                w = max(0.0, w + dw * dt * 3600.0)
            rh = rh_from_w(T, w)
            if T > self.t_max or T < self.t_min:
                v_T += 1
                dh_T += max(0.0, T - self.t_max) * dt + max(0.0, self.t_min - T) * dt
            if latent and rh > self.rh_max:
                v_rh += 1
            T_hist.append(T); w_hist.append(w); rh_hist.append(rh)
            lat_served.append(q_lat)
            prev = u
        return dict(J=cost / days, E=e / days, f_s=sw / days,
                    v_T=100.0 * v_T / N, v_rh=100.0 * v_rh / N, dh_T=dh_T,
                    T_mean=float(np.mean(T_hist)), rh_mean=float(np.mean(rh_hist)),
                    rh_max=float(np.max(rh_hist)),
                    lat_mean=float(np.mean(lat_served)),
                    lat_capped=100.0 * float(np.mean(
                        np.isclose(lat_served, self.q_lat_max, rtol=1e-6)
                        & (np.array(lat_served) > 0))))


def hyst(lo, hi):
    def pol(T, prev, k, rh):
        return 1 if T >= hi else (0 if T <= lo else prev)
    return pol


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shr", type=float, default=0.75)
    ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args()
    print(f"Two-state zone, SHR_rated = {a.shr}, 0.6 ACH, hygric factor 4.0, "
          f"{a.days}-day run from day 181\n")
    rows = []
    for city in ("riyadh", "jeddah"):
        z = LatentZone(city, shr_rated=a.shr)
        print(f"=== {city.upper()}  Lam_sen={z.lam_sen:.2f} W/K  "
              f"Q_lat_max={z.q_lat_max:.0f} W ===")
        print(f"  {'model':16s} {'J':>7s} {'E':>7s} {'f_s':>5s} {'T_mean':>7s} "
              f"{'RH_mean':>8s} {'RH_max':>7s} {'v_T%':>6s} {'v_RH%':>6s} {'lat W':>7s} {'capped%':>8s}")
        for lab, latflag in (("sensible only", False), ("with latent", True)):
            r = z.run(hyst(22.7, 25.8), days=a.days, latent=latflag)
            rows.append(dict(city=city, model=lab, shr=a.shr,
                             **{k: round(v, 4) for k, v in r.items()}))
            print(f"  {lab:16s} {r['J']:7.4f} {r['E']:7.3f} {r['f_s']:5.2f} "
                  f"{r['T_mean']:7.2f} {r['rh_mean']:8.1f} {r['rh_max']:7.1f} "
                  f"{r['v_T']:6.2f} {r['v_rh']:6.2f} {r['lat_mean']:7.1f} "
                  f"{r['lat_capped']:8.1f}")
        print()
    import os
    os.makedirs("/home/claude/rbrl/results", exist_ok=True)
    with open("/home/claude/rbrl/results/latent.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
    print("-> results/latent.csv")
