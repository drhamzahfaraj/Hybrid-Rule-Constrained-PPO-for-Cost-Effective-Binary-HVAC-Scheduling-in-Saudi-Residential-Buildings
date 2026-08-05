# Table schema and provenance

Each CSV mirrors one table in the manuscript. **Values are transcribed from the
published tables, not re-emitted by a run** — see the provenance note below.

| File | Manuscript table | Units |
|---|---|---|
| `consumption_monthly.csv` | Consumption and cost | kWh/zone/day; SAR/zone/**month** |
| `cost_model_comparison.csv` | Results by cost model | SAR/zone/**day**; switches/zone/day |
| `ablation_components.csv` | Component ablation | SAR/zone/day |
| `cost_model_mismatch.csv` | Cost-model mismatch penalty | SAR/zone/day |
| `scalability.csv` | Scalability and latency | %; hours; ms |
| `sensitivity_switching_cost.csv` | Switching-cost sensitivity | SAR; SAR/zone/day |
| `sensitivity_thermal_capacity.csv` | Thermal-capacity sensitivity | kJ/K; % |
| `sota_comparison.csv` | State-of-the-art comparison | % |

## Two evaluation horizons — do not conflate

- `consumption_monthly.csv` reports the **720-hour billing month**.
- `cost_model_comparison.csv` and `scalability.csv` report **168-hour weekly**
  rollouts.

They differ by up to ~1.5 percentage points for the smaller topologies, because
only over a full billing month does cumulative consumption traverse the tariff
tiers, changing the marginal price both controllers face. Jeddah 4x4 under
Model S is 16.8 % monthly and 16.6 % weekly; both are correct on their own basis.

## Column conventions

- `j_bar_sar_zone_day` — mean cost per zone per day (SAR)
- `vc_pct` — percentage of intervals with any zone outside [22, 26] °C
- `switches_zone_day` — compressor start-ups per zone per day
- empty cell — not separately recorded in the manuscript (e.g. SA switching rate)

## Provenance

All runs: Model S unless stated, seeds {42, 43, 44, 45, 46}, mean over all five,
30 held-out test weeks, configurations in `../../configs/`. Weather: IWEC
typical-year files for Riyadh (WMO 404380) and Jeddah (WMO 410240).

These files are a convenience for readers who want the numbers machine-readable.
They are transcribed from the manuscript rather than emitted by the pipeline; to
make the artifact self-verifying, replace them with output written directly by a
run.
