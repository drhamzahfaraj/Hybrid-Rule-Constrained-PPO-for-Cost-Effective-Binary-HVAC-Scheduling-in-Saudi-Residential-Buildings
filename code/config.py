#!/usr/bin/env python3
"""THE configuration of record (RULING_round4 F8): band, rule thresholds R1/R2, switching cost,
tariff, thermal capacitance, the control interval and the empty-house limit. Every protocol module reads these values
from here (headroom, final_tables, t1_v2, rbrl_ppo, setback_arms, mpc_lambda, r3_dp, bound_v2);
none of them may restate a literal. Scenario controls are environment variables read once, at
import (a scenario run is a separate process with a non-empty RBRL_TAG; headroom.check_scenario_tag).

Defaults reproduce the headline model exactly (tests/test_fast.py::test_default_config_is_headline).
"""
import os as _os

_env = _os.environ.get

# occupied comfort band [BAND_LO, BAND_HI] and THERM's setpoint (THERM cycles THERM_SET +/- 0.5).
# The national 24 C guidance scenario: RBRL_BAND_LO/HI 21.5/24.5, RBRL_THERM_SET 24.
BAND_SHIFT = float(_env("RBRL_BAND_SHIFT", "0"))
BAND_LO = float(_env("RBRL_BAND_LO", 22.0 + BAND_SHIFT))
BAND_HI = float(_env("RBRL_BAND_HI", 24.0 + BAND_SHIFT))
THERM_SET = float(_env("RBRL_THERM_SET", _env("RBRL_THERM_C", 23.0 + BAND_SHIFT)))

# empty-house safety limit (setback only; ruling Sec. 2.1). Rule-arm away thresholds are tied to it:
# on at AWAY_MAX - 0.2, off 0.8 K below that.
AWAY_MAX = float(_env("RBRL_AWAY_MAX", "30.0"))
AWAY_ON = AWAY_MAX - 0.20
AWAY_OFF = AWAY_ON - 0.80
AWAY_FLOOR = 18.0                      # away lower band edge (bands(); no lower limit binds away)

# Hard rule layer (RBRL, guard, in-rules MPC, ruled bound): R1 force ON at T >= cap - EPS_HOT,
# R2 force OFF at T <= BAND_LO + EPS_COLD. RULE_ON/RULE_OFF are R1/R2 at the training ceiling
# (cap = BAND_HI); r3_dp / mpc_lambda take them as arguments with these defaults (F11: the ruled
# bound must use RULE_ON >= and RULE_OFF <= every in-rules arm's R1/R2).
EPS_HOT, EPS_COLD = 0.20, 0.40
RULE_ON = BAND_HI - EPS_HOT
RULE_OFF = BAND_LO + EPS_COLD

# switching cost per compressor start, SAR (headline); the sensitivity grid of T5v3 / J20
C_SW = 0.15
C_SW_GRID = (0.0, 0.025, 0.05, 0.10, 0.114, 0.15, 0.20, 0.30, 0.60)

# flat marginal tariffs, SAR/kWh
PRICE = 0.18                           # in force
TARIFFS = {"historical": 0.05, "inforce": PRICE, "y2027": 0.21}

# effective thermal capacitance, kJ/K (ISO 13786 headline 4800; RBRL_CTH for the J13 sweep)
C_TH_DEFAULT = 4800.0
C_TH = float(_env("RBRL_CTH", C_TH_DEFAULT))

# initial / reference indoor temperature of every 168 h window
T0 = 23.0

# control / actuation interval Delta t, minutes (F23; journal Comment 8, job J24). Headline 15 min;
# RBRL_DT_MIN for the time-step sweep (5 / 30; needs RBRL_TAG, headroom.check_scenario_tag).
# Every step count is derived from it: steps per hour, per day (the MPC persistence offset and the
# 24 h rollout), per 168 h window. Windows (final_tables.WINDOWS / TUNE_W / EVAL_W) stay in days,
# c_sw stays per start and the price per kWh. The plant step is the exact exponential over DT_H.
# 60 / DT_MIN must be an integer (the hourly EPW is held over whole steps).
DT_MIN_DEFAULT = 15.0
DT_MIN = float(_env("RBRL_DT_MIN", DT_MIN_DEFAULT))
if not (DT_MIN > 0 and abs(60.0 / DT_MIN - round(60.0 / DT_MIN)) < 1e-9):
    raise ValueError(f"RBRL_DT_MIN={DT_MIN}: 60 / dt must be a whole number of steps per hour")
DT_H = DT_MIN / 60.0                    # h per step (15/60 == 0.25 exactly: headline bit-identical)
STEPS_PER_HOUR = int(round(60.0 / DT_MIN))
STEPS_PER_DAY = 24 * STEPS_PER_HOUR
STEPS_PER_WINDOW = 168 * STEPS_PER_HOUR     # N = 168 * 60 / dt
