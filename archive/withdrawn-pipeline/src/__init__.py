"""HVAC Scheduling with Hybrid RBRL Framework.

This package implements the constrained optimal binary HVAC scheduling
system for Saudi residential buildings under a four-tier step-wise tariff.
"""

__version__ = "1.0.0"
__author__ = "Hamzah Faraj"
__email__ = "[email removed]"

from .thermal_model import ThermalModel, Zone
from .cost_models import LinearCostModel, ExponentialCostModel, StepwiseCostModel
from .rbrl_agent import RBRLAgent
from .rules import HardConstraintRules
from .environment import HVACEnvironment
from .rbrl_optimizer import (
    RBRLWrapper,
    train_rbrl_ppo,
    extract_monthly_schedule,
    load_and_extract_schedule,
)

__all__ = [
    "ThermalModel",
    "Zone",
    "LinearCostModel",
    "ExponentialCostModel",
    "StepwiseCostModel",
    "RBRLAgent",
    "HardConstraintRules",
    "HVACEnvironment",
    "RBRLWrapper",
    "train_rbrl_ppo",
    "extract_monthly_schedule",
    "load_and_extract_schedule",
]
