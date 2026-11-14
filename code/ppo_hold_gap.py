"""How far is each trained PPO policy from the hold policy, on the weeks it trained on and on the
held-out weeks? (the training-length question, ruling §32)

Scores every saved headline model (results/models/rbrl_ppo5_v2_<city>_<city>_<seed>) and the hold
policy (keep the previous action until R1/R2 fires) at the TRAINING rules (cap = BAND_HI), on the
same simulator and windows as every other arm, with the training reward's cost J (no comfort term).
gap = J_policy / J_hold - 1. A policy at hold on TUNE_W cannot gain from longer training on TUNE_W
by more than E1's DP margin; a gap that appears only on EVAL_W is a generalisation gap."""
import numpy as np
from stable_baselines3 import PPO
import config as CFG
import final_tables as F
import rbrl_ppo as R
import rbrl_io as IO


def hold(obs):
    return int(obs[1] > 0.5)


def J(pol, city, windows):
    return float(sum(r["J"] for r in R.evaluate(pol, city, windows, CFG.PRICE)))


def main():
    rows = []
    for c in F.CITIES:
        Jh = {"TUNE_W": J(hold, c, F.TUNE_W), "EVAL_W": J(hold, c, F.EVAL_W)}
        for s in range(42, 47):
            p = f"{IO.R}/models/rbrl_ppo5_v2_{c}_{c}_{s}.zip"
            IO.note_input(p)
            m = PPO.load(p, device="cpu")
            jt, je = J(m, c, F.TUNE_W), J(m, c, F.EVAL_W)
            rows.append(dict(city=c, seed=s, J_tune=jt, J_hold_tune=Jh["TUNE_W"], gap_tune_pct=100 * (jt / Jh["TUNE_W"] - 1),
                             J_eval=je, J_hold_eval=Jh["EVAL_W"], gap_eval_pct=100 * (je / Jh["EVAL_W"] - 1),
                             cap=R.HI, fit_status="fixed"))
            print(f"{c:7s} {s}: tune {rows[-1]['gap_tune_pct']:+.2f}%  eval {rows[-1]['gap_eval_pct']:+.2f}%", flush=True)
    IO.write_csv("T33_ppo_hold_gap", rows)


if __name__ == "__main__":
    main()
