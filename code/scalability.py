#!/usr/bin/env python3
"""Computational scalability, measured on stated hardware.

Replaces the table withdrawn from an earlier version of this study, whose GPU
memory figures were digit-identical to a parameter-count column and whose named
hardware was not available to the author. Nothing here is taken from a prior
run: every figure is timed in this process, on the machine named in the output,
and the analytic counts are derived from the formulation rather than measured.

What is reported
----------------
  * SIMULATION throughput per zone-step, which is what an evaluation costs.
  * RULE-LAYER decision time per step, which is what a deployed RBRL controller
    costs at inference (the rule layer and a trained policy's forward pass are
    the two terms; the policy term is reported separately where a trained model
    is available).
  * The CLAIRVOYANT DP's state and action counts, which are analytic and are
    the reason a multi-zone optimum is not computed in this paper: the joint
    action set is 2^N_z per step and the state grid is G^N_z, so the DP that
    supplies the single-zone reference is intractable beyond two zones on any
    hardware. This is a property of the formulation, not of the machine, and it
    is the honest form of the scalability claim the earlier version tried to
    make with timings.

What is NOT reported, and why
-----------------------------
No training time and no GPU memory. Training was run once per seed on a
container whose allocation is not a stable basis for a published figure, and a
number that cannot be reproduced on stated hardware is worth less than its
absence. The deployability claim is correspondingly narrow: inference is cheap,
which is measured; training cost is not claimed.
"""
from __future__ import annotations
import sys, time, platform, csv
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import multizone as MZ
import headroom as H

GRID = 1601          # state-grid points per zone, as the single-zone DP uses
CONTROL_STEP_S = H.DT * 3600.0


def hardware():
    name = "unknown"
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name"):
                name = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass
    return (f"{name}, {platform.machine()}, single-threaded NumPy "
            f"{np.__version__}, Python {platform.python_version()}")


def time_sim(geo, city, start_day, reps=1):
    pol = MZ.hyst(23.5, 22.5)
    t0 = time.perf_counter()
    for _ in range(reps):
        MZ.simulate(geo, city, start_day, pol, days=7)
    dt = (time.perf_counter() - t0) / reps
    steps = int(round(7 * 24 / H.DT))
    return dt, dt / steps, dt / steps / geo["nz"]


def time_rule_layer(nz, reps=20000):
    """The guard layer alone: the arithmetic a deployed controller must do."""
    T = np.full(nz, 23.0)
    prev = np.zeros(nz, int)
    hi, lo = 23.8, 22.4
    t0 = time.perf_counter()
    for _ in range(reps):
        u = prev.copy()
        u[T >= hi] = 1
        u[T <= lo] = 0
    return (time.perf_counter() - t0) / reps


if __name__ == "__main__":
    hw = hardware()
    print("COMPUTATIONAL SCALABILITY")
    print(f"hardware: {hw}")
    print(f"control step: {CONTROL_STEP_S:.0f} s\n")
    rows = []
    print(f"{'topo':6s} {'Nz':>3} {'sim/window':>11} {'sim/step':>10} "
          f"{'rule/step':>10} {'DP states':>14} {'DP actions':>11}")
    for kind, n in (("single", 1), ("linear", 2), ("grid", 2), ("linear", 4),
                    ("linear", 6), ("grid", 3), ("grid", 4)):
        geo = MZ.build(kind, n, "riyadh")
        nz = geo["nz"]
        reps = 3 if nz <= 4 else 1
        tw, ts, tsz = time_sim(geo, "riyadh", 121, reps=reps)
        tr = time_rule_layer(nz)
        states = float(GRID) ** nz
        actions = 2 ** nz
        rows.append(dict(topo=geo["label"], nz=nz,
                         sim_window_s=round(tw, 4),
                         sim_step_ms=round(ts * 1e3, 4),
                         sim_step_per_zone_ms=round(tsz * 1e3, 5),
                         rule_step_us=round(tr * 1e6, 3),
                         dp_states=f"{states:.3g}", dp_actions=actions,
                         hardware=hw))
        print(f"{geo['label']:6s} {nz:3d} {tw:10.3f}s {ts*1e3:9.3f}ms "
              f"{tr*1e6:9.2f}us {states:14.3g} {actions:11d}", flush=True)

    with open("/home/claude/rbrl/results/T18_scalability.csv", "w",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

    print("\nMARGIN AT DEPLOYMENT")
    for r in rows:
        margin = CONTROL_STEP_S / (r["rule_step_us"] * 1e-6)
        print(f"  {r['topo']:6s} rule layer is {margin:.3g}x faster than the "
              f"control step")

    print("\nWHY NO MULTI-ZONE CLAIRVOYANT OPTIMUM IS REPORTED")
    g1 = float(GRID)
    for nz in (1, 2, 3, 4, 16):
        states = g1 ** nz
        # one backward pass touches states x actions x 2 (previous-action bit)
        work = states * (2 ** nz) * 2
        print(f"  N_z={nz:2d}: {states:9.3g} states x {2**nz:6d} actions "
              f"= {work:9.3g} transitions per interval")
    print("  At N_z = 2 this is already ~2e7 transitions per interval and "
          "~1e10 per week;\n  at N_z = 3 it exceeds 1e13. The obstruction is "
          "the formulation, not the machine.")
    print("\n-> results/T18_scalability.csv")
