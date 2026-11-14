"""THERM's electricity, cost and on-commands against its comfort level (ruling §30 D2).

Reads THERM's own Rule C curve THERM(delta) (final_tables.therm_curve_full) on the held-out
windows and writes, per city, the pooled change relative to delta = 0 at delta = +0.1, +0.2 K
and at the largest delta on the comparator grid whose occupied over-temperature is zero.
No new simulation model: the same plant, tariff and comparator grid as every other arm."""
import numpy as np
import config as CFG
import final_tables as F
import rbrl_io as IO


def main():
    D = F.DELTAS
    i0 = int(np.argmin(np.abs(D)))
    out = []
    for c in F.CITIES:
        cv = [F.therm_curve_full(c, w, CFG.PRICE) for w in F.EVAL_W]
        tot = {k: sum(np.asarray(x[k], float) for x in cv) for k in ("E", "J", "starts")}
        mean = np.mean([np.asarray(x[F.MEAN_KEY], float) for x in cv], axis=0)
        over = sum(np.asarray(x["deg_h_occ"], float) for x in cv)
        for d in (0.1, 0.2, None):
            if d is None:   # largest grid delta with no occupied degree-hours outside the band
                ok = np.flatnonzero(over <= 1e-9); k = int(ok.max()); label = "max_admissible"
            else:
                k = int(np.argmin(np.abs(D - d))); label = f"{d:+.1f}"
            out.append(dict(city=c, point=label, delta=float(D[k]), mean0=float(mean[i0]), mean=float(mean[k]),
                            dmean_K=float(mean[k] - mean[i0]), deg_h_occ=float(over[k]),
                            energy_pct=100 * (tot["E"][k] / tot["E"][i0] - 1),
                            cost_pct=100 * (tot["J"][k] / tot["J"][i0] - 1),
                            starts_pct=100 * (tot["starts"][k] / tot["starts"][i0] - 1),
                            fit_status="fixed"))
            print(f"{c:7s} {label:15s} delta {D[k]:+.3f} dmean {mean[k]-mean[i0]:+.3f} K "
                  f"energy {out[-1]['energy_pct']:+.2f}% cost {out[-1]['cost_pct']:+.2f}%", flush=True)
    IO.write_csv("T32_setpoint_sens", out)


if __name__ == "__main__":
    main()
