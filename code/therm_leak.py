"""THERM's comfort leak under the current scenario (ruling §46): occupied degree-hours above
T_max and below T_min of the 1 K-deadband thermostat (on at 23.5, off at 22.5 C) and of a centred
1.5 K deadband (on 23.75, off 22.25 C), Riyadh, at the tariff in force. Run once per scenario
with RBRL_DT_MIN / RBRL_CTH and RBRL_TAG set (jobs J47_*), so the actuation-interval and
capacity rows of the admissibility tables come from stamped round-4 runs. THERM and the fixed
deadband have no fitted parameter; nothing is tuned. Per-step excursion Q dt / C_th is written
beside the leak so the admissibility condition can be read off the same row."""
import config as CFG
import final_tables as F
import headroom as H
import rbrl_io as IO


def main():
    H.check_scenario_tag()
    city = "riyadh"
    cool = H.Q_HVAC * H.DT * 3600.0 / (H.C_TH * 1e3)
    rows = []
    for d in (1.0, 1.5):
        runs = [F.rule_run(city, w, CFG.PRICE, 23.0 + 0.5 * d, 23.0 - 0.5 * d) for w in F.EVAL_W]
        first = runs[0]
        r = dict(city=city, dt_min=CFG.DT_MIN, C_th=H.C_TH, deadband=d, step_excursion_K=cool,
                 first_window=F.EVAL_W[0],
                 over_first=first["deg_h_over"], under_first=first["deg_h_under"],
                 over_all7=float(sum(x["deg_h_over"] for x in runs)),
                 under_all7=float(sum(x["deg_h_under"] for x in runs)),
                 fs_mean=float(sum(x["f_s"] for x in runs) / len(runs)))
        rows.append(r)
        print(f"dt={CFG.DT_MIN:g} min C_th={H.C_TH:g} d={d}: excursion {cool:.3f} K  "
              f"first window over/under {r['over_first']:.4f}/{r['under_first']:.4f}  "
              f"all 7 {r['over_all7']:.4f}/{r['under_all7']:.4f}", flush=True)
    IO.write_csv("T37_therm_leak", rows)


if __name__ == "__main__":
    main()
