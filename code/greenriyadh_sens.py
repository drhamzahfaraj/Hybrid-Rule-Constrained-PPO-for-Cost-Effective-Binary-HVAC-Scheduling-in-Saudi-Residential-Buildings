"""What a cooler city does to a Riyadh room's cooling (ruling §33): the Green Riyadh project's
stated aim is to lower the city's air temperature by 1.5-2 C. Outdoor dry-bulb is lowered by
d in {0, 1.0, 1.5, 2.0} K at every step of the held-out windows; solar gains, the plant, the band,
the tariff and every controller's thresholds are unchanged (no re-tuning). Reports THERM's and
TUNED's electricity, on-commands and cost, and TUNED's raw saving against THERM at each d.
An outdoor shift on an airport TMYx year is a first-order sensitivity, not a model of the
urban heat island or of the project's realised effect."""
import json
import numpy as np
import config as CFG
import final_tables as F
import headroom as H
import rbrl_io as IO

_orig = H.series


def shifted(d):
    def series(city, hours, start_day):
        t_out, irr, N = _orig(city, hours, start_day)
        return np.asarray(t_out, float) - d, irr, N
    return series


def main():
    tp = json.load(open(f"{IO.R}/tuned_params_v2.json")); IO.note_input(f"{IO.R}/tuned_params_v2.json")
    rows = []
    for city in ("riyadh",):
        on, off = tp[f"{city}|inforce|TUNED"]["on"], tp[f"{city}|inforce|TUNED"]["off"]
        base = None
        for d in (0.0, 1.0, 1.5, 2.0):
            H.series = shifted(d)
            th = [F.therm_run(city, w, CFG.PRICE) for w in F.EVAL_W]
            tu = [F.rule_run(city, w, CFG.PRICE, on, off) for w in F.EVAL_W]
            agg = lambda rs, k: float(sum(r[k] for r in rs))
            r = dict(city=city, dT_out=-d, E_therm=agg(th, "E"), J_therm=agg(th, "J"), f_therm=agg(th, "f_s"),
                     E_tuned=agg(tu, "E"), J_tuned=agg(tu, "J"), f_tuned=agg(tu, "f_s"),
                     Tocc_therm=float(np.mean([x["T_mean_occ_clip"] for x in th])),
                     Tocc_tuned=float(np.mean([x["T_mean_occ_clip"] for x in tu])),
                     over_tuned=agg(tu, "deg_h_over"), on=on, off=off, fit_status="fixed")
            base = base or r
            r.update(dE_therm_pct=100 * (r["E_therm"] / base["E_therm"] - 1),
                     dE_tuned_pct=100 * (r["E_tuned"] / base["E_tuned"] - 1),
                     dJ_therm_pct=100 * (r["J_therm"] / base["J_therm"] - 1),
                     s_raw_tuned_pct=100 * (1 - r["J_tuned"] / r["J_therm"]),
                     starts_avoided_pct=100 * (1 - r["f_tuned"] / r["f_therm"]))
            rows.append(r)
            print(f"{city} dT_out={-d:+.1f} K: THERM energy {r['dE_therm_pct']:+.1f}%  cost {r['dJ_therm_pct']:+.1f}%  "
                  f"TUNED raw saving {r['s_raw_tuned_pct']:.1f}%  on-cmds avoided {r['starts_avoided_pct']:.1f}%  "
                  f"TUNED over-T {r['over_tuned']:.4f}", flush=True)
    H.series = _orig
    IO.write_csv("T34_greenriyadh_sens", rows)


if __name__ == "__main__":
    main()
