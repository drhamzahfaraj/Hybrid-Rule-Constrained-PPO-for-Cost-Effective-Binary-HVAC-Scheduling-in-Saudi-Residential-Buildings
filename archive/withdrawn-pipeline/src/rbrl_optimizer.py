"""
RBRL PPO Optimizer for HVAC Scheduling.

This module implements the Rule-Based Reinforcement Learning (RBRL) framework
using Proximal Policy Optimization (PPO) as described in the paper's methodology.

The optimizer integrates with the existing HVACEnvironment and applies:
- Hard rules R1, R2 for comfort constraint enforcement (O1)
- Soft rule R3 for pre-cooling bias (O2)
- PPO agent for cost minimization (O2, O3)
"""

import numpy as np
import gym
from gym import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from typing import Optional, Tuple, Dict, Any

from .environment import HVACEnvironment


class RBRLWrapper(gym.Env):
    """
    Wrapper around HVACEnvironment that adds quadratic comfort penalty during training.
    
    The underlying HVACEnvironment already implements:
    - RC thermal dynamics (eq. RC discretisation in paper)
    - Rules R1, R2, R3 (hard comfort constraint enforcement)
    - Model S step-wise tariff with discrete switching cost
    
    This wrapper only adds the training-time quadratic comfort penalty (eq. reward).
    
    Args:
        Nz: Number of zones
        topology: Zone topology ("1x1", "1x4", "2x2", etc.)
        city: City name ("Riyadh" or "Jeddah")
        horizon_hours: Episode length in hours
        Tmin: Minimum comfort temperature (°C)
        Tmax: Maximum comfort temperature (°C)
        training: If True, adds quadratic comfort penalty; if False, uses base cost only
        penalty_weight: Weight for quadratic comfort penalty (default: 50.0)
    """
    
    metadata = {"render_modes": []}
    
    def __init__(
        self,
        Nz: int = 4,
        topology: str = "1x4",
        city: str = "Riyadh",
        horizon_hours: int = 168,
        Tmin: float = 22.0,
        Tmax: float = 26.0,
        training: bool = True,
        penalty_weight: float = 50.0,
        **env_kwargs
    ):
        super().__init__()
        self.training = training
        self.Tmin = Tmin
        self.Tmax = Tmax
        self.penalty_weight = penalty_weight
        
        # Initialize underlying HVAC environment
        # The HVACEnvironment should already implement RC dynamics, rules, and Model S
        self.env = HVACEnvironment(
            Nz=Nz,
            topology=topology,
            city=city,
            horizon_hours=horizon_hours,
            cost_model="S",  # Use step-wise tariff Model S
            **env_kwargs
        )
        
        # Mirror observation and action spaces
        self.observation_space = self.env.observation_space
        self.action_space = self.env.action_space
        
        # Cache for inspection
        self._last_temperatures = None
    
    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        """Reset environment and return initial observation."""
        obs, info = self.env.reset(seed=seed, options=options)
        self._last_temperatures = info.get("temperatures", None)
        return obs, info
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Execute one step in the environment.
        
        The base environment returns:
        - obs: state observation (eq. state in paper)
        - base_reward: negative interval cost (-c_t) from Model S
        - terminated: episode termination flag
        - truncated: episode truncation flag
        - info: dictionary with 'cost', 'temperatures', 'actions_applied', etc.
        
        During training, we add quadratic comfort penalty to the reward.
        During deployment, we use base reward only (rules guarantee comfort).
        """
        obs, base_reward, terminated, truncated, info = self.env.step(action)
        
        # Extract current temperatures
        temperatures = info.get("temperatures", None)
        if temperatures is not None:
            self._last_temperatures = np.array(temperatures, dtype=float)
        
        # Add quadratic comfort penalty during training (eq. reward in paper)
        if self.training and (temperatures is not None):
            T = np.array(temperatures, dtype=float)
            viol_low = np.maximum(0.0, self.Tmin - T)
            viol_high = np.maximum(0.0, T - self.Tmax)
            comfort_penalty = self.penalty_weight * float(np.sum(viol_low**2 + viol_high**2))
            reward = base_reward - comfort_penalty
            
            # Add penalty info for logging
            info["comfort_penalty"] = comfort_penalty
        else:
            reward = base_reward
            info["comfort_penalty"] = 0.0
        
        return obs, reward, terminated, truncated, info
    
    def render(self):
        """Render environment."""
        return self.env.render()
    
    def close(self):
        """Close environment."""
        return self.env.close()


def make_rbrl_env(
    Nz: int,
    topology: str,
    city: str,
    horizon_hours: int,
    training: bool,
    seed: int,
    **env_kwargs
):
    """
    Factory function for creating RBRL-wrapped environment.
    
    Args:
        Nz: Number of zones
        topology: Zone topology
        city: City name
        horizon_hours: Episode length
        training: Training mode flag
        seed: Random seed
        **env_kwargs: Additional environment kwargs
    """
    def _init():
        env = RBRLWrapper(
            Nz=Nz,
            topology=topology,
            city=city,
            horizon_hours=horizon_hours,
            training=training,
            **env_kwargs
        )
        env.reset(seed=seed)
        return env
    return _init


def train_rbrl_ppo(
    Nz: int = 4,
    topology: str = "1x4",
    city: str = "Riyadh",
    horizon_hours: int = 168,
    total_episodes: int = 2000,
    steps_per_episode: int = 168,
    learning_rate: float = 3e-4,
    seed: int = 0,
    model_save_path: str = "models/ppo_rbrl_hvac",
    verbose: int = 1,
    **env_kwargs
) -> PPO:
    """
    Train PPO agent on RBRL-wrapped HVAC environment.
    
    Implements the training procedure described in Section "Reward Function and PPO Architecture":
    - Two fully connected layers: 256-128 units with ReLU
    - PPO clip coefficient: 0.2
    - Training: 2×10^5 episodes of 168-step rollouts
    - Start dates sampled uniformly from annual EPW profile
    
    Args:
        Nz: Number of zones
        topology: Zone topology ("1x1", "1x4", "2x2", "3x3", "4x4")
        city: City name ("Riyadh" or "Jeddah")
        horizon_hours: Episode length during training (typically 168 = 1 week)
        total_episodes: Total training episodes (default: 2000)
        steps_per_episode: Steps per episode (default: 168)
        learning_rate: PPO learning rate (default: 3e-4)
        seed: Random seed for reproducibility
        model_save_path: Path to save trained model
        verbose: Verbosity level (0: none, 1: info, 2: debug)
        **env_kwargs: Additional environment configuration
    
    Returns:
        Trained PPO model
    """
    print(f"\n{'='*60}")
    print(f"Training RBRL PPO Agent")
    print(f"{'='*60}")
    print(f"Configuration:")
    print(f"  Zones: {Nz} ({topology})")
    print(f"  City: {city}")
    print(f"  Episode length: {horizon_hours} hours")
    print(f"  Total episodes: {total_episodes}")
    print(f"  Total timesteps: {total_episodes * steps_per_episode:,}")
    print(f"{'='*60}\n")
    
    # Create vectorized environment
    vec_env = DummyVecEnv([
        make_rbrl_env(
            Nz=Nz,
            topology=topology,
            city=city,
            horizon_hours=horizon_hours,
            training=True,
            seed=seed,
            **env_kwargs
        )
    ])
    
    # Initialize PPO with architecture from paper
    model = PPO(
        "MlpPolicy",
        vec_env,
        learning_rate=learning_rate,
        n_steps=steps_per_episode,
        batch_size=64,
        gamma=0.99,
        clip_range=0.2,  # PPO clip coefficient
        verbose=verbose,
        seed=seed,
        policy_kwargs=dict(
            net_arch=[256, 128],  # Two FC layers: 256-128 units, ReLU activation
        ),
    )
    
    # Train the model
    total_timesteps = int(total_episodes * steps_per_episode)
    print("Starting training...")
    model.learn(total_timesteps=total_timesteps)
    
    # Save trained model
    print(f"\nTraining complete! Saving model to {model_save_path}")
    model.save(model_save_path)
    
    print(f"{'='*60}\n")
    return model


def extract_monthly_schedule(
    model: PPO,
    Nz: int = 4,
    topology: str = "1x4",
    city: str = "Riyadh",
    month_hours: int = 720,
    seed: int = 0,
    verbose: bool = True,
    **env_kwargs
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Extract optimal monthly schedule using trained PPO model (Algorithm H greedy rollout).
    
    Performs a greedy deterministic rollout over one billing month (H=720 hours)
    to extract the near-optimal binary schedule that satisfies optimality conditions O1-O3.
    
    Args:
        model: Trained PPO model
        Nz: Number of zones
        topology: Zone topology
        city: City name
        month_hours: Monthly horizon in hours (default: 720 = 30 days)
        seed: Random seed for environment initialization
        verbose: Print progress information
        **env_kwargs: Additional environment configuration
    
    Returns:
        schedule: (H, Nz) binary array of HVAC actions u_i^t
        temperatures: (H, Nz) array of zone temperatures T_i^t
        costs: (H,) array of interval costs c_t
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"Extracting Optimal Monthly Schedule")
        print(f"{'='*60}")
        print(f"Configuration:")
        print(f"  Zones: {Nz} ({topology})")
        print(f"  City: {city}")
        print(f"  Horizon: {month_hours} hours (30 days)")
        print(f"{'='*60}\n")
    
    # Create deployment environment (training=False, no comfort penalty)
    env = RBRLWrapper(
        Nz=Nz,
        topology=topology,
        city=city,
        horizon_hours=month_hours,
        training=False,  # Deployment mode: no quadratic comfort penalty
        **env_kwargs
    )
    
    obs, info = env.reset(seed=seed)
    
    # Preallocate result arrays
    schedule = np.zeros((month_hours, Nz), dtype=int)
    temperatures = np.zeros((month_hours, Nz), dtype=float)
    costs = np.zeros(month_hours, dtype=float)
    
    # Greedy rollout
    for t in range(month_hours):
        # Deterministic action selection (no exploration)
        action, _ = model.predict(obs, deterministic=True)
        
        # Execute action
        obs, reward, terminated, truncated, info = env.step(action)
        
        # Extract results from info dict
        # Assumes info contains: 'actions_applied', 'temperatures', 'cost'
        u_applied = info.get("actions_applied", action)
        T_current = info.get("temperatures", None)
        c_t = info.get("cost", -reward)
        
        # Store results
        schedule[t, :] = np.array(u_applied, dtype=int)
        if T_current is not None:
            temperatures[t, :] = np.array(T_current, dtype=float)
        costs[t] = float(c_t)
        
        # Progress indicator
        if verbose and (t + 1) % 168 == 0:
            week = (t + 1) // 168
            total_cost = np.sum(costs[:t+1])
            print(f"  Week {week}/4 complete | Total cost so far: {total_cost:.2f} SAR")
        
        if terminated or truncated:
            if verbose:
                print(f"  Episode ended at t={t+1}")
            break
    
    env.close()
    
    if verbose:
        total_cost = np.sum(costs)
        avg_cost_per_zone = total_cost / (Nz * month_hours)
        total_switches = np.sum(np.diff(schedule, axis=0, prepend=0) == 1)
        avg_switches_per_zone_per_day = total_switches / (Nz * 30)
        
        print(f"\n{'='*60}")
        print(f"Schedule Extraction Complete")
        print(f"{'='*60}")
        print(f"Total monthly cost: {total_cost:.2f} SAR")
        print(f"Average cost per zone per hour: {avg_cost_per_zone:.4f} SAR")
        print(f"Total switches: {total_switches}")
        print(f"Average switches per zone per day: {avg_switches_per_zone_per_day:.2f}")
        print(f"{'='*60}\n")
    
    return schedule, temperatures, costs


def load_and_extract_schedule(
    model_path: str,
    Nz: int = 4,
    topology: str = "1x4",
    city: str = "Riyadh",
    month_hours: int = 720,
    seed: int = 0,
    **env_kwargs
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Load a trained model and extract optimal monthly schedule.
    
    Convenience function that loads a saved model and performs schedule extraction.
    
    Args:
        model_path: Path to saved PPO model (without .zip extension)
        Nz: Number of zones
        topology: Zone topology
        city: City name
        month_hours: Monthly horizon in hours
        seed: Random seed
        **env_kwargs: Additional environment configuration
    
    Returns:
        schedule: (H, Nz) binary array of HVAC actions
        temperatures: (H, Nz) array of zone temperatures
        costs: (H,) array of interval costs
    """
    print(f"Loading trained model from {model_path}...")
    model = PPO.load(model_path)
    
    return extract_monthly_schedule(
        model=model,
        Nz=Nz,
        topology=topology,
        city=city,
        month_hours=month_hours,
        seed=seed,
        **env_kwargs
    )


if __name__ == "__main__":
    """
    Example usage: Train RBRL PPO agent and extract optimal monthly schedule.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Train RBRL PPO optimizer for HVAC scheduling")
    parser.add_argument("--Nz", type=int, default=4, help="Number of zones")
    parser.add_argument("--topology", type=str, default="1x4", help="Zone topology")
    parser.add_argument("--city", type=str, default="Riyadh", choices=["Riyadh", "Jeddah"], help="City")
    parser.add_argument("--episodes", type=int, default=2000, help="Training episodes")
    parser.add_argument("--horizon", type=int, default=168, help="Episode horizon (hours)")
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default="models/ppo_rbrl_hvac", help="Model save path")
    
    args = parser.parse_args()
    
    # Train PPO agent
    model = train_rbrl_ppo(
        Nz=args.Nz,
        topology=args.topology,
        city=args.city,
        horizon_hours=args.horizon,
        total_episodes=args.episodes,
        steps_per_episode=args.horizon,
        learning_rate=args.lr,
        seed=args.seed,
        model_save_path=args.output,
        verbose=1,
    )
    
    # Extract optimal monthly schedule
    schedule, temperatures, costs = extract_monthly_schedule(
        model=model,
        Nz=args.Nz,
        topology=args.topology,
        city=args.city,
        month_hours=720,
        seed=0,
    )
    
    # Save results
    output_dir = "experiments/schedules"
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    np.save(f"{output_dir}/optimal_schedule_{args.city}_{args.topology}.npy", schedule)
    np.save(f"{output_dir}/optimal_temps_{args.city}_{args.topology}.npy", temperatures)
    np.save(f"{output_dir}/optimal_costs_{args.city}_{args.topology}.npy", costs)
    
    print(f"\nSchedule data saved to {output_dir}/")
