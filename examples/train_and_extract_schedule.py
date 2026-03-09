#!/usr/bin/env python3
"""
Example: Train RBRL PPO Agent and Extract Optimal Monthly Schedule

This script demonstrates the complete workflow:
1. Train a PPO agent using the RBRL framework
2. Extract the optimal monthly HVAC schedule
3. Save and visualize the results

Usage:
    python examples/train_and_extract_schedule.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Add parent directory to path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rbrl_optimizer import train_rbrl_ppo, extract_monthly_schedule


def plot_schedule_summary(schedule, temps, costs, city, topology, save_path=None):
    """
    Create visualization of the extracted schedule.
    
    Args:
        schedule: (H, Nz) binary HVAC actions
        temps: (H, Nz) zone temperatures
        costs: (H,) interval costs
        city: City name
        topology: Zone topology
        save_path: Optional path to save figure
    """
    H, Nz = schedule.shape
    hours = np.arange(H)
    days = hours / 24.0
    
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))
    fig.suptitle(f'Optimal HVAC Schedule - {city}, {topology} ({Nz} zones)', 
                 fontsize=14, fontweight='bold')
    
    # Plot 1: HVAC Schedule (binary heatmap)
    ax1 = axes[0]
    im1 = ax1.imshow(schedule.T, aspect='auto', cmap='RdYlGn_r', 
                     interpolation='nearest', vmin=0, vmax=1)
    ax1.set_ylabel('Zone', fontsize=10)
    ax1.set_title('HVAC Schedule (Red=ON, Green=OFF)', fontsize=11)
    ax1.set_xticks(np.arange(0, H, 24))
    ax1.set_xticklabels(np.arange(0, H//24 + 1))
    ax1.set_yticks(np.arange(Nz))
    ax1.set_yticklabels([f'Zone {i+1}' for i in range(Nz)])
    cbar1 = plt.colorbar(im1, ax=ax1)
    cbar1.set_label('HVAC State', rotation=270, labelpad=15)
    
    # Plot 2: Zone Temperatures
    ax2 = axes[1]
    for i in range(Nz):
        ax2.plot(days, temps[:, i], label=f'Zone {i+1}', alpha=0.7, linewidth=1.5)
    ax2.axhline(22, color='blue', linestyle='--', linewidth=1, alpha=0.5, label='T_min')
    ax2.axhline(26, color='red', linestyle='--', linewidth=1, alpha=0.5, label='T_max')
    ax2.fill_between(days, 22, 26, color='green', alpha=0.1, label='Comfort Band')
    ax2.set_ylabel('Temperature (°C)', fontsize=10)
    ax2.set_title('Zone Temperatures Over Time', fontsize=11)
    ax2.legend(loc='upper right', fontsize=8, ncol=min(Nz+3, 5))
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, H/24)
    
    # Plot 3: Cumulative Cost
    ax3 = axes[2]
    cumulative_cost = np.cumsum(costs)
    ax3.plot(days, cumulative_cost, color='darkblue', linewidth=2)
    ax3.fill_between(days, 0, cumulative_cost, color='lightblue', alpha=0.3)
    ax3.set_xlabel('Day', fontsize=10)
    ax3.set_ylabel('Cumulative Cost (SAR)', fontsize=10)
    ax3.set_title(f'Total Monthly Cost: {cumulative_cost[-1]:.2f} SAR', fontsize=11)
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(0, H/24)
    
    plt.tight_layout()
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved to {save_path}")
    
    plt.show()


def main():
    """
    Main execution: Train RBRL agent and extract optimal schedule.
    """
    # Configuration
    CONFIG = {
        "Nz": 4,
        "topology": "1x4",
        "city": "Riyadh",
        "training_episodes": 2000,
        "horizon_hours": 168,  # 1 week episodes
        "learning_rate": 3e-4,
        "seed": 42,
    }
    
    print("="*70)
    print(" RBRL HVAC SCHEDULER - Training and Schedule Extraction")
    print("="*70)
    print(f"\nConfiguration:")
    for key, value in CONFIG.items():
        print(f"  {key:20s}: {value}")
    print("\n" + "="*70)
    
    # Create output directories
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"experiments/run_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/models", exist_ok=True)
    os.makedirs(f"{output_dir}/schedules", exist_ok=True)
    os.makedirs(f"{output_dir}/figures", exist_ok=True)
    
    model_path = f"{output_dir}/models/ppo_{CONFIG['city'].lower()}_{CONFIG['topology']}"
    
    # Step 1: Train PPO Agent
    print("\n" + "="*70)
    print(" STEP 1: Training PPO Agent")
    print("="*70 + "\n")
    
    model = train_rbrl_ppo(
        Nz=CONFIG["Nz"],
        topology=CONFIG["topology"],
        city=CONFIG["city"],
        horizon_hours=CONFIG["horizon_hours"],
        total_episodes=CONFIG["training_episodes"],
        steps_per_episode=CONFIG["horizon_hours"],
        learning_rate=CONFIG["learning_rate"],
        seed=CONFIG["seed"],
        model_save_path=model_path,
        verbose=1,
    )
    
    # Step 2: Extract Optimal Monthly Schedule
    print("\n" + "="*70)
    print(" STEP 2: Extracting Optimal Monthly Schedule")
    print("="*70 + "\n")
    
    schedule, temps, costs = extract_monthly_schedule(
        model=model,
        Nz=CONFIG["Nz"],
        topology=CONFIG["topology"],
        city=CONFIG["city"],
        month_hours=720,  # 30 days
        seed=0,
        verbose=True,
    )
    
    # Step 3: Save Results
    print("\n" + "="*70)
    print(" STEP 3: Saving Results")
    print("="*70 + "\n")
    
    schedule_prefix = f"{output_dir}/schedules/{CONFIG['city']}_{CONFIG['topology']}"
    np.save(f"{schedule_prefix}_schedule.npy", schedule)
    np.save(f"{schedule_prefix}_temps.npy", temps)
    np.save(f"{schedule_prefix}_costs.npy", costs)
    print(f"Schedule data saved to {output_dir}/schedules/")
    
    # Step 4: Compute and Display Metrics
    print("\n" + "="*70)
    print(" STEP 4: Performance Metrics")
    print("="*70 + "\n")
    
    total_cost = np.sum(costs)
    avg_cost_per_zone_per_hour = total_cost / (CONFIG["Nz"] * 720)
    avg_cost_per_zone_per_day = total_cost / (CONFIG["Nz"] * 30)
    
    # Count switches (0→1 transitions)
    switches = np.diff(schedule, axis=0, prepend=0)
    total_switches = np.sum(switches == 1)
    avg_switches_per_zone_per_day = total_switches / (CONFIG["Nz"] * 30)
    
    # Check comfort violations (should be zero)
    temp_violations = np.sum((temps < 22.0) | (temps > 26.0))
    
    print(f"Cost Metrics:")
    print(f"  Total monthly cost:              {total_cost:.2f} SAR")
    print(f"  Average cost per zone per hour:  {avg_cost_per_zone_per_hour:.4f} SAR")
    print(f"  Average cost per zone per day:   {avg_cost_per_zone_per_day:.2f} SAR")
    print(f"\nSwitching Metrics:")
    print(f"  Total switches (30 days):        {total_switches}")
    print(f"  Average switches per zone/day:   {avg_switches_per_zone_per_day:.2f}")
    print(f"\nComfort Metrics:")
    print(f"  Temperature violations:          {temp_violations} (should be 0)")
    print(f"  Min temperature observed:        {np.min(temps):.2f}°C")
    print(f"  Max temperature observed:        {np.max(temps):.2f}°C")
    
    # Step 5: Visualize Results
    print("\n" + "="*70)
    print(" STEP 5: Generating Visualizations")
    print("="*70 + "\n")
    
    figure_path = f"{output_dir}/figures/schedule_{CONFIG['city']}_{CONFIG['topology']}.png"
    plot_schedule_summary(
        schedule=schedule,
        temps=temps,
        costs=costs,
        city=CONFIG["city"],
        topology=CONFIG["topology"],
        save_path=figure_path,
    )
    
    # Save summary report
    report_path = f"{output_dir}/summary_report.txt"
    with open(report_path, 'w') as f:
        f.write("RBRL HVAC Scheduler - Summary Report\n")
        f.write("="*70 + "\n\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Configuration:\n")
        for key, value in CONFIG.items():
            f.write(f"  {key:20s}: {value}\n")
        f.write(f"\nPerformance Metrics:\n")
        f.write(f"  Total monthly cost:              {total_cost:.2f} SAR\n")
        f.write(f"  Average cost per zone per hour:  {avg_cost_per_zone_per_hour:.4f} SAR\n")
        f.write(f"  Average cost per zone per day:   {avg_cost_per_zone_per_day:.2f} SAR\n")
        f.write(f"  Total switches:                  {total_switches}\n")
        f.write(f"  Average switches per zone/day:   {avg_switches_per_zone_per_day:.2f}\n")
        f.write(f"  Temperature violations:          {temp_violations}\n")
    
    print(f"Summary report saved to {report_path}")
    
    print("\n" + "="*70)
    print(" COMPLETED SUCCESSFULLY")
    print("="*70)
    print(f"\nAll results saved to: {output_dir}/")
    print(f"  - Model:     {output_dir}/models/")
    print(f"  - Schedules: {output_dir}/schedules/")
    print(f"  - Figures:   {output_dir}/figures/")
    print(f"  - Report:    {report_path}")
    print("\n")


if __name__ == "__main__":
    main()
