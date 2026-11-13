#!/usr/bin/env python3
"""F23 golden values: the headline-step (Delta t = 15 min) outputs of the simulator paths that the
actuation-interval sweep (J24) touches, encoded bit-exactly (float.hex).

tests/f23_golden_p9.json was written by this script on the tag p9 tree (HEAD == p9, clean) BEFORE
the F23 change:   cd /home/claude/rbrl && python3 -I tests/f23_golden.py --write
tests/test_f23_timestep.py::test_headline_dt_bit_identical_to_p9 recomputes them with the current
code and requires exact equality. To re-derive the file from the tag itself:
    git archive p9 | tar -x -C /tmp/p9 && python3 -I tests/f23_golden.py --root /tmp/p9 --print
(--root runs the computation on that tree; the modules' own sys.path.insert of the repo is ignored).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(HERE, "f23_golden_p9.json")


class _PinnedPath(list):
    """sys.path that ignores the modules' sys.path.insert(0, '/home/claude/rbrl') (--root runs)."""
    def insert(self, i, p):
        if p == "/home/claude/rbrl":
            return
        super().insert(i, p)


def _enc(x):
    import numpy as np
    if isinstance(x, dict):
        return {k: _enc(v) for k, v in sorted(x.items())}
    if isinstance(x, (list, tuple)):
        return [_enc(v) for v in x]
    if isinstance(x, np.ndarray):
        return [_enc(v) for v in x.tolist()]
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return float(x).hex()
    return x


def compute():
    import numpy as np
    import final_tables as F
    import mpc_lambda as M
    import r3_dp as D
    out = {}
    out["rule_run"] = F.rule_run("riyadh", 121, 0.18, 23.71, 22.36)
    out["therm_run"] = F.therm_run("riyadh", 135, 0.18)
    out["sim_hyst_batch"] = F.sim_hyst_batch("riyadh", 149, 0.18, np.array([23.5, 23.71, 23.9]),
                                             np.array([22.5, 22.36, 22.2]))
    out["mpc_perfect"] = M.mpc_lams("riyadh", 121, [0.0, 0.24, 1.0], 24.0, n_grid=201,
                                    rule=(23.71, 22.36), N=96, return_actions=True)
    out["mpc_persistence"] = M.mpc_lams("riyadh", 121, [0.24], 6.0, n_grid=201, rule=(23.71, 22.36),
                                        N=48, forecast="persistence")
    for rel in (False, True):
        # terminal="energy": the p9 terminal (O4, ruling §21.3, changed the DEFAULT on purpose; this
        # golden checks the dt plumbing, so it compares like with like)
        d = D.lagrangian("riyadh", 121, 0.18, 0.24, n_grid=401, relaxed=rel, terminal="energy")
        out[f"lagrangian_rel{int(rel)}"] = {k: d[k] for k in d if k in ("L", "h")}
    return _enc(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--root" in a:
        root = a[a.index("--root") + 1]
        sys.path = _PinnedPath([root] + [p for p in sys.path if p not in ("", HERE)])
        os.environ["RBRL_ROOT"] = root
    else:
        sys.path.insert(0, os.path.dirname(HERE))
    for k in [k for k in os.environ if k.startswith("RBRL_") and k not in ("RBRL_ROOT",)]:
        del os.environ[k]
    res = compute()
    if "--write" in a:
        json.dump(res, open(GOLDEN, "w"), indent=0, sort_keys=True)
        print("wrote", GOLDEN)
    else:
        print(json.dumps(res, sort_keys=True))
