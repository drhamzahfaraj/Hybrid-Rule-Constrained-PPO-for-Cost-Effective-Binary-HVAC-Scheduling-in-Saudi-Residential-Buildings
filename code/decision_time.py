"""Wall-clock decision time of the 24 h MPC at the headline grid (ruling §42): one held-out
Riyadh window at the fitted headline lambda, single process, timed around mpc_lams; reports
seconds per 15-min decision (total / steps). Machine description is recorded in the meta."""
import csv
import os
import platform
import time
import final_tables as F
import mpc_lambda as M
import rbrl_io as IO


def main():
    src = f"{IO.R}/T21v3_riyadh.csv"; IO.note_input(src)
    row = [r for r in csv.DictReader(open(src)) if float(r["horizon_h"]) == 24][0]
    lam = float(row["lam"])
    rows = []
    for h in (6.0, 24.0):
        w = F.EVAL_W[0]
        t0 = time.perf_counter()
        r = M.mpc_lams("riyadh", w, [lam], h, n_grid=M.HEADLINE_NGRID, return_actions=True)[0]
        dt = time.perf_counter() - t0
        n = len(r["actions"])
        rows.append(dict(city="riyadh", window=w, horizon_h=h, n_grid=M.HEADLINE_NGRID, steps=n,
                         total_s=dt, ms_per_decision=1000 * dt / n, step_s=900,
                         cpu=platform.processor() or platform.machine(), ncpu=os.cpu_count(),
                         fit_status="fixed"))
        print(f"H={h:g} h: {n} decisions in {dt:.1f} s -> {1000*dt/n:.1f} ms/decision", flush=True)
    IO.write_csv("T36_decision_time", rows)


if __name__ == "__main__":
    main()
