#!/usr/bin/env python3
"""Full environment disclosure and timing for the computational-cost table.

The table this replaces was withdrawn because its GPU memory figures were
digit-identical to a parameter-count column and the hardware named in its
caption was not available to the author. The remedy is not a better number but
a complete disclosure: every figure below is timed in this process, on the
machine this prints, with the library versions this prints, and anything that
is arithmetic rather than measurement is labelled as such.

Reported separately and never conflated:
  * measured wall-clock, with median and inter-quartile range over many repeats
  * measured peak resident memory, via getrusage
  * parameter counts, in their own column, which are NOT memory
  * analytic state-action counts for the dynamic programme, which are NOT
    timings and are marked as extrapolation beyond the largest size actually run
"""
from __future__ import annotations
import sys, os, time, platform, json, resource, csv
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np


def environment():
    cpu = "unknown"
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass
    cores = os.cpu_count()
    phys = cores
    try:
        import subprocess
        out = subprocess.run(["lscpu"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if line.startswith("Thread(s) per core"):
                tpc = int(line.split(":")[1])
                phys = cores // max(tpc, 1)
    except Exception:
        pass
    mem_gb = None
    try:
        for line in open("/proc/meminfo"):
            if line.startswith("MemTotal"):
                mem_gb = round(int(line.split()[1]) / 1048576.0, 1)
                break
    except Exception:
        pass
    vers = {}
    for mod in ("numpy", "scipy", "torch", "stable_baselines3", "gymnasium"):
        try:
            m = __import__(mod)
            vers[mod] = getattr(m, "__version__", "?")
        except Exception:
            vers[mod] = "not installed"
    blas = "unknown"
    try:
        cfg = np.__config__.show(mode="dicts")
        blas = cfg.get("Build Dependencies", {}).get("blas", {}).get("name",
                                                                    "unknown")
    except Exception:
        try:
            blas = np.__config__.get_info("blas_opt").get("libraries", ["?"])[0]
        except Exception:
            pass
    return dict(
        cpu=cpu, logical_cores=cores, physical_cores=phys,
        threads_used=os.environ.get("OMP_NUM_THREADS", "unset (NumPy default)"),
        omp=os.environ.get("OMP_NUM_THREADS", "unset"),
        mkl=os.environ.get("MKL_NUM_THREADS", "unset"),
        openblas=os.environ.get("OPENBLAS_NUM_THREADS", "unset"),
        ram_gb=mem_gb, os=platform.platform(),
        kernel=platform.release(), python=platform.python_version(),
        blas=blas, gpu="none used", timer="time.perf_counter",
        **{f"v_{k}": v for k, v in vers.items()})


def timed(fn, reps):
    ts = []
    fn()                                   # warm
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    a = np.array(ts)
    return dict(median_ms=float(np.median(a) * 1e3),
                iqr_ms=float((np.percentile(a, 75) - np.percentile(a, 25))
                             * 1e3),
                n=reps)


if __name__ == "__main__":
    env = environment()
    print("ENVIRONMENT DISCLOSURE")
    for k, v in env.items():
        print(f"  {k:16s} {v}")

    import multizone as MZ
    import headroom as H
    import mpc as P

    rows = []
    print("\nMEASURED TIMINGS (median [IQR] over repeats)")

    # --- simulator step, per zone count
    for kind, n in (("single", 1), ("grid", 2), ("grid", 3), ("grid", 4)):
        geo = MZ.build(kind, n, "riyadh")
        steps = int(round(7 * 24 / H.DT))
        r = timed(lambda g=geo: MZ.simulate(g, "riyadh", 121,
                                            MZ.hyst(23.5, 22.5), days=7),
                  reps=5)
        per_step = r["median_ms"] / steps
        print(f"  simulator  N_z={geo['nz']:2d}  {r['median_ms']:8.2f} ms/window"
              f"  [{r['iqr_ms']:.2f}]  -> {per_step*1e3:7.2f} us/step",
              flush=True)
        rows.append(dict(what="simulator window", nz=geo["nz"],
                         median_ms=round(r["median_ms"], 3),
                         iqr_ms=round(r["iqr_ms"], 3), n=r["n"],
                         per_step_us=round(per_step * 1e3, 3), kind="measured"))

    # --- rule layer, the arithmetic a deployed controller does
    for nz in (1, 4, 9, 16):
        T = np.full(nz, 23.0)
        prev = np.zeros(nz, int)

        def rule(T=T, prev=prev):
            u = prev.copy()
            u[T >= 23.8] = 1
            u[T <= 22.4] = 0
            return u
        r = timed(rule, reps=2000)
        print(f"  rule layer N_z={nz:2d}  {r['median_ms']*1e3:8.2f} us/decision"
              f"  [{r['iqr_ms']*1e3:.2f}]", flush=True)
        rows.append(dict(what="rule layer decision", nz=nz,
                         median_ms=round(r["median_ms"], 6),
                         iqr_ms=round(r["iqr_ms"], 6), n=r["n"],
                         per_step_us=round(r["median_ms"] * 1e3, 3),
                         kind="measured"))

    # --- receding-horizon decision, the figure the deployability claim rests on
    steps = int(round(7 * 24 / H.DT))
    for hh in (6.0, 24.0):
        r = timed(lambda h=hh: P.mpc_run("riyadh", 121, 0.18, h, cap=23.70),
                  reps=3)
        per = r["median_ms"] / steps
        print(f"  MPC H={hh:4.0f}h        {per:8.2f} ms/decision "
              f"(window {r['median_ms']/1e3:.2f} s)", flush=True)
        rows.append(dict(what=f"MPC decision H={hh:.0f}h", nz=1,
                         median_ms=round(r["median_ms"], 3),
                         iqr_ms=round(r["iqr_ms"], 3), n=r["n"],
                         per_step_us=round(per * 1e3, 1), kind="measured"))

    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    print(f"\n  peak resident memory of this process: {peak_mb:.1f} MiB "
          f"(getrusage; NOT a parameter count)")

    print("\nANALYTIC (extrapolation, not measurement)")
    # The DP state is (temperatures, PREVIOUS ACTION VECTOR): the switching
    # charge makes each zone's cost depend on its own previous compressor
    # state, so there are 2^N_z previous-action configurations, not one bit.
    G = 1601
    for nz in (1, 2, 3, 4, 16):
        states = float(G) ** nz * 2 ** nz
        print(f"  DP at N_z={nz:2d}: {states:9.3g} states x {2**nz:6d} "
              f"joint actions = {states * 2**nz:9.3g} transitions/interval")

    env["peak_rss_mib"] = round(peak_mb, 1)
    with open("/home/claude/rbrl/results/T18_scalability.csv", "w",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    with open("/home/claude/rbrl/results/T18_environment.json", "w") as f:
        json.dump(env, f, indent=2)
    print("\n-> results/T18_scalability.csv, results/T18_environment.json")
