"""One-day operating traces for the manuscript figure (ruling §36): THERM, TUNED and the 24 h
MPC (perfect forecast, the fitted headline lambda and grid read from T21v3_riyadh.csv) on the
hottest held-out Riyadh window, recorded at every 15-min step; the plotted span is fixed in
advance as days 1-2 of that window (day 0 is the warm-up from T0), so no day is selected by result. No fitting here: thresholds come from tuned_params_v2.json and
lambda from the headline MPC row, so the traces are those of the reported arms."""
import csv
import json
import numpy as np
import config as CFG
import final_tables as F
import headroom as H
import mpc_lambda as M
import setback as S
import rbrl_io as IO

CITY = "riyadh"


def playback(acts):
    def pol(T, prev, k):
        return acts[k]
    return pol


def main():
    tp = json.load(open(f"{IO.R}/tuned_params_v2.json")); IO.note_input(f"{IO.R}/tuned_params_v2.json")
    on, off = tp[f"{CITY}|inforce|TUNED"]["on"], tp[f"{CITY}|inforce|TUNED"]["off"]
    src = f"{IO.R}/T21v3_{CITY}.csv"; IO.note_input(src)
    row = [r for r in csv.DictReader(open(src)) if float(r["horizon_h"]) == 24][0]
    lam, ngrid = float(row["lam"]), int(float(row.get("n_grid") or M.HEADLINE_NGRID))
    tout = {w: float(np.mean(H.series(CITY, 168, w)[0])) for w in F.EVAL_W}
    w = max(tout, key=tout.get)
    t_out = np.asarray(H.series(CITY, 168, w)[0], float)
    N, occ, lo, hi = F._ctx(CITY, w, False)
    price = H.price_flat(N, CFG.PRICE)
    th = S.sim(S.hyst_abs(H.THERM_SET + 0.5, H.THERM_SET - 0.5), CITY, F.FACES, F.C_TH, price,
               lo, hi, occ, 168, w, F.T0, c_sw=F.C_SW, record=True)
    tu = S.sim(S.hyst_abs(on, off), CITY, F.FACES, F.C_TH, price, lo, hi, occ, 168, w, F.T0,
               c_sw=F.C_SW, record=True)
    mp = M.mpc_lams(CITY, w, [lam], 24.0, n_grid=ngrid, return_actions=True)[0]
    acts = [int(a) for a in mp["actions"]]
    mr = S.sim(playback(acts), CITY, F.FACES, F.C_TH, price, lo, hi, occ, 168, w, F.T0,
               c_sw=F.C_SW, record=True)
    spd = int(round(24 / S.DT))
    day, ndays = 1, 2
    k0 = day * spd
    st = lambda u: int(sum(1 for a, b in zip([0] + list(u[:-1]), u) if b == 1 and a == 0))
    wk = {n: st(list(r["u"])) for n, r in (("therm", th), ("tuned", tu), ("mpc", mr))}
    rows = []
    for k in range(k0, k0 + ndays * spd):
        rows.append(dict(city=CITY, start_day=w, day=day, step=k, hour=(k - k0) * S.DT,
                         t_out=float(t_out[k]), occupied=int(occ[k]), lo=float(lo[k]), hi=float(hi[k]),
                         T_therm=float(th["T_next"][k]), u_therm=int(th["u"][k]),
                         T_tuned=float(tu["T_next"][k]), u_tuned=int(tu["u"][k]),
                         T_mpc=float(mr["T_next"][k]), u_mpc=int(mr["u"][k]),
                         lam=lam, n_grid=ngrid, tuned_on=on, tuned_off=off, week_on_therm=wk['therm'],
                         week_on_tuned=wk['tuned'], week_on_mpc=wk['mpc'], fit_status="fixed"))
    for name, r in (("THERM", th), ("TUNED", tu), ("MPC24", mr)):
        u = list(r["u"][k0:k0 + ndays * spd]); T = np.asarray(r["T_next"][k0:k0 + ndays * spd])
        print(f"{name:6s} days {day}-{day + ndays - 1} of window {w}: on-commands {st(u)}, on-steps {sum(u)}, "
              f"T {T.min():.2f}-{T.max():.2f} C; week J {r['J']:.3f}", flush=True)
    IO.write_csv("T35_day_traces", rows)


if __name__ == "__main__":
    main()
