#!/usr/bin/env python3
"""
Generate plots for:
1. Warm-up analysis - single configuration with replications
2. Continuity test - bar chart comparing two configurations (like consistency test)
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import re
from collections import defaultdict
from scipy import stats

# Directories
RESULTS_DIR = Path(__file__).parent / "results"
CONTINUITY_DIR = Path(__file__).parent / "results_continuity" / "results_continuity"
CONSISTENCY_DIR = Path(__file__).parent / "results_consistency"
OUTPUT_DIR = Path(__file__).parent.parent / "documentation" / "images"
OUTPUT_DIR.mkdir(exist_ok=True)

def parse_sca_file(filepath):
    """Parse a .sca file and extract statistics"""
    data = {'users': {}, 'tables': {}, 'config': {}}
    
    with open(filepath, 'r') as f:
        content = f.read()
        
        # Extract throughput from tables
        total_throughput = 0
        for match in re.finditer(r'scalar DatabaseNetwork\.table\[(\d+)\] throughput:last (\d+)', content):
            total_throughput += int(match.group(2))
        
        data['throughput'] = total_throughput
        
        # Extract utilization
        utils = []
        for match in re.finditer(r'scalar DatabaseNetwork\.table\[(\d+)\] utilization:last ([\d.e+-]+)', content):
            utils.append(float(match.group(2)))
        data['utilization'] = np.mean(utils) if utils else 0
        
        # Extract wait time
        wait_times = []
        for match in re.finditer(r'scalar DatabaseNetwork\.table\[(\d+)\] waitingTime:mean ([\d.e+-]+)', content):
            wait_times.append(float(match.group(2)))
        data['waitTime'] = np.mean(wait_times) * 1000 if wait_times else 0  # Convert to ms
        
    return data

def create_continuity_barchart():
    """Create bar chart for continuity test comparing Config A and Config B"""
    print("=" * 70)
    print("CONTINUITY TEST - BAR CHART")
    print("=" * 70)
    
    # Parse all files for ContinuityA and ContinuityB
    config_a_data = {'throughput': [], 'utilization': [], 'waitTime': []}
    config_b_data = {'throughput': [], 'utilization': [], 'waitTime': []}
    
    for sca_file in CONTINUITY_DIR.glob("ContinuityA-*.sca"):
        data = parse_sca_file(sca_file)
        config_a_data['throughput'].append(data['throughput'])
        config_a_data['utilization'].append(data['utilization'])
        config_a_data['waitTime'].append(data['waitTime'])
    
    for sca_file in CONTINUITY_DIR.glob("ContinuityB-*.sca"):
        data = parse_sca_file(sca_file)
        config_b_data['throughput'].append(data['throughput'])
        config_b_data['utilization'].append(data['utilization'])
        config_b_data['waitTime'].append(data['waitTime'])
    
    print(f"Config A: {len(config_a_data['throughput'])} replications")
    print(f"Config B: {len(config_b_data['throughput'])} replications")
    
    # Create figure with 3 subplots
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.suptitle('Continuity Test: Configuration A (N=100) vs Configuration B (N=101)', 
                 fontsize=13, fontweight='bold')
    
    metrics = ['throughput', 'utilization', 'waitTime']
    titles = ['Throughput (transactions/s)', 'Utilization (%)', 'Wait Time (ms)']
    
    for ax, metric, title in zip(axes, metrics, titles):
        a_vals = config_a_data[metric]
        b_vals = config_b_data[metric]
        
        if metric == 'utilization':
            a_vals = [v * 100 for v in a_vals]
            b_vals = [v * 100 for v in b_vals]
        
        # Calculate means and 95% CI
        a_mean = np.mean(a_vals)
        b_mean = np.mean(b_vals)
        
        a_ci = stats.sem(a_vals) * stats.t.ppf((1 + 0.95) / 2, len(a_vals) - 1) if len(a_vals) > 1 else 0
        b_ci = stats.sem(b_vals) * stats.t.ppf((1 + 0.95) / 2, len(b_vals) - 1) if len(b_vals) > 1 else 0
        
        # Bar chart
        x = np.arange(2)
        bars = ax.bar(x, [a_mean, b_mean], yerr=[a_ci, b_ci], 
                     color=['#e74c3c', '#2c3e50'], alpha=0.8, 
                     capsize=5, edgecolor='black', linewidth=1.2)
        
        ax.set_xticks(x)
        ax.set_xticklabels(['Config A\n(N=100)', 'Config B\n(N=101)'])
        ax.set_ylabel(title, fontsize=10)
        ax.set_title(title.split('(')[0].strip(), fontsize=11)
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar, val, ci in zip(bars, [a_mean, b_mean], [a_ci, b_ci]):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + ci + 0.02*max(a_mean, b_mean),
                   f'{val:.1f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'continuity_test_results.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'continuity_test_results.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\nContinuity test plot saved to: {OUTPUT_DIR}/continuity_test_results.pdf")
    
    # Print summary
    print("\nSummary:")
    print(f"  Throughput A: {np.mean(config_a_data['throughput']):.1f} ± {a_ci:.1f}")
    print(f"  Throughput B: {np.mean(config_b_data['throughput']):.1f} ± {b_ci:.1f}")

def create_warmup_single_config():
    """Create warm-up plot for a single configuration using replications"""
    print("\n" + "=" * 70)
    print("WARM-UP ANALYSIS - SINGLE CONFIGURATION")
    print("=" * 70)
    
    # Use consistency test data for N=1000 (has multiple replications)
    config_data = []
    
    for sca_file in CONSISTENCY_DIR.glob("Config1000Users--*.sca"):
        data = parse_sca_file(sca_file)
        rep_match = re.search(r'--(\d+)\.sca', str(sca_file))
        rep = int(rep_match.group(1)) if rep_match else 0
        config_data.append({
            'rep': rep,
            'throughput': data['throughput'],
            'utilization': data['utilization'] * 100,
            'waitTime': data['waitTime']
        })
    
    config_data = sorted(config_data, key=lambda x: x['rep'])
    print(f"Found {len(config_data)} replications for N=1000")
    
    # Also get data for other N values to show convergence pattern
    all_configs = {}
    for pattern in ['Config10Users', 'Config50Users', 'Config100Users', 'Config500Users', 'Config1000Users']:
        all_configs[pattern] = []
        for sca_file in CONSISTENCY_DIR.glob(f"{pattern}--*.sca"):
            data = parse_sca_file(sca_file)
            all_configs[pattern].append(data['waitTime'])
    
    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('Warm-Up Period Analysis\nConfiguration: N=1000, M=10, p=0.5, λ=0.05', 
                 fontsize=13, fontweight='bold')
    
    # Plot 1: Wait time across replications for N=1000
    ax1 = axes[0, 0]
    reps = [d['rep'] + 1 for d in config_data]
    waits = [d['waitTime'] for d in config_data]
    steady_state = np.mean(waits)
    
    ax1.plot(reps, waits, 'o-', color='#3498db', markersize=8, linewidth=2, label='Wait Time')
    ax1.axhline(y=steady_state, color='red', linestyle='--', linewidth=2, label=f'Mean = {steady_state:.2f}ms')
    ax1.fill_between(reps, steady_state * 0.95, steady_state * 1.05, alpha=0.2, color='green', label='±5% band')
    
    ax1.set_xlabel('Replication Number', fontsize=10)
    ax1.set_ylabel('Wait Time (ms)', fontsize=10)
    ax1.set_title('Wait Time Across Replications (N=1000)', fontsize=11)
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Normalized convergence
    ax2 = axes[0, 1]
    normalized = [w / steady_state for w in waits]
    
    ax2.plot(reps, normalized, 'o-', color='#e74c3c', markersize=8, linewidth=2)
    ax2.axhline(y=1.0, color='black', linestyle='--', linewidth=2, label='Steady State')
    ax2.fill_between(reps, 0.95, 1.05, alpha=0.2, color='green', label='±5% band')
    
    ax2.set_xlabel('Replication Number', fontsize=10)
    ax2.set_ylabel('Wait Time / Mean', fontsize=10)
    ax2.set_title('Normalized Convergence (N=1000)', fontsize=11)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0.5, 1.5)
    
    # Plot 3: Comparison across all N values
    ax3 = axes[1, 0]
    N_values = [10, 50, 100, 500, 1000]
    means = []
    stds = []
    for pattern in ['Config10Users', 'Config50Users', 'Config100Users', 'Config500Users', 'Config1000Users']:
        vals = all_configs[pattern]
        means.append(np.mean(vals))
        stds.append(np.std(vals))
    
    x = np.arange(len(N_values))
    bars = ax3.bar(x, means, yerr=stds, color='#3498db', alpha=0.8, capsize=5, edgecolor='black')
    ax3.set_xticks(x)
    ax3.set_xticklabels([f'N={n}' for n in N_values])
    ax3.set_xlabel('Configuration', fontsize=10)
    ax3.set_ylabel('Wait Time (ms)', fontsize=10)
    ax3.set_title('Steady-State Wait Time by Configuration', fontsize=11)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Plot 4: Coefficient of Variation
    ax4 = axes[1, 1]
    cvs = [(s / m * 100) if m > 0 else 0 for m, s in zip(means, stds)]
    
    bars = ax4.bar(x, cvs, color='#9b59b6', alpha=0.8, edgecolor='black')
    ax4.set_xticks(x)
    ax4.set_xticklabels([f'N={n}' for n in N_values])
    ax4.set_xlabel('Configuration', fontsize=10)
    ax4.set_ylabel('CV (%)', fontsize=10)
    ax4.set_title('Coefficient of Variation (Stability Indicator)', fontsize=11)
    ax4.axhline(y=10, color='red', linestyle='--', alpha=0.7, label='10% threshold')
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'warmup_analysis.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'warmup_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\nWarm-up analysis plot saved to: {OUTPUT_DIR}/warmup_analysis.pdf")
    
    # Print summary
    print("\nWarm-Up Analysis Summary (N=1000):")
    print(f"  Replications: {len(config_data)}")
    print(f"  Mean Wait Time: {steady_state:.2f}ms")
    print(f"  Std Dev: {np.std(waits):.2f}ms")
    print(f"  CV: {np.std(waits)/steady_state*100:.1f}%")
    
    if np.std(waits)/steady_state*100 < 10:
        print("  ✓ Low variability - system converges quickly")
        print("  Recommended warm-up: 500s")
    else:
        print("  ⚠ Higher variability detected")

if __name__ == "__main__":
    create_continuity_barchart()
    create_warmup_single_config()
    print("\n" + "=" * 70)
    print("ALL PLOTS GENERATED SUCCESSFULLY")
    print("=" * 70)
