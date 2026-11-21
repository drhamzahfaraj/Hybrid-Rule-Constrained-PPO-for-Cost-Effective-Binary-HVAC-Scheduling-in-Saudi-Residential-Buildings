# Invariant suite

*Moved from the manuscript (main text, Section "Verification and Validity", round-4 revision, 14 Nov 2026).*

Before any table is produced, `code/invariants.py` runs 188 numerical invariants in nine
classes and exits non-zero on any failure. A missing source file is a failure, never a skip.
The run is written to `results/invariants_run.json` (`n_checks`, `n_failed`); the count printed
in the paper is read from that file. At the release used for the paper all 188 pass
(`results/gate_p12.log`, code `5e8bc69a807c`).

| Class | Name | What it checks |
|---|---|---|
| A | Physical sanity | solar geometry and irradiance signs; energy rises as the zone is held cooler |
| B | Bound consistency | no causal arm exceeds the clairvoyant bound under the same terminal condition |
| C | Accounting identities | cost = tariff energy cost + on-command charge; no sentinel values in costs |
| D | Parameter provenance | conductances and infiltration terms derived per city from their stated sources |
| E | Monotonicity | switching frequency falls as the deadband widens |
| F | Decomposition closure | components of a saving sum to the saving |
| G | Feasibility | per-interval excursion Q·Δt/C_th within the band; the band holdable with zero degree-hours |
| H | Deadband actuation condition | condition (8) predicts THERM's feasibility at 15 min (holds) and 1 h (fails) |
| P | Round-4 protocol | fit status, Rule C bracket, comfort metrics, optimiser constraints and fallback, s_a ≤ B_a for every arm, CLV certificate, grid convergence, statistics re-derived |

## Note on class G

The feasibility class retains some checks written for the comfort band of an earlier version of
the model: its "band is holdable" test simulates a hysteresis at 22.5/25.5 °C rather than on the
[22, 24] °C band used in the paper. These checks still pass and are kept as regression tests;
the checks that bear on the paper's band are those of classes H and P.
