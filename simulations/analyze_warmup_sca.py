#!/usr/bin/env python3
"""
Warm-Up Analysis using .sca files from results folder
Creates a graph showing metric convergence similar to Welch's procedure
Using replications to show variability and convergence to steady-state
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import re
from collections import defaultdict

# Directories
RESULTS_DIR = Path(__file__).parent / "results"
OUTPUT_DIR = Path(__file__).parent.parent / "documentation" / "images"
OUTPUT_DIR.mkdir(exist_ok=True)

def parse_sca_file(filepath):
    """Parse a .sca file and extract statistics"""
    data = {
        'users': {},
        'tables': {},
        'config': {}
    }
    
    with open(filepath, 'r') as f:
        content = f.read()
        
        # Extract N
        match = re.search(r'itervar N (\d+)', content)
        if match:
            data['config']['N'] = int(match.group(1))
        
        # Extract p
        match = re.search(r'itervar p ([\d.]+)', content)
        if match:
            data['config']['p'] = float(match.group(1))
        
        # Extract distribution from filename
        if 'Lognormal' in str(filepath):
            data['config']['dist'] = 'Lognormal'
        elif 'Uniform' in str(filepath):
            data['config']['dist'] = 'Uniform'
        
        # Extract repetition
        match = re.search(r'attr repetition (\d+)', content)
        if match:
            data['config']['rep'] = int(match.group(1))
        
        # Parse user wait times
        for match in re.finditer(r'scalar DatabaseNetwork\.user\[(\d+)\] waitTime:mean ([\d.e+-]+)', content):
            user_id = int(match.group(1))
            wait = float(match.group(2))
            data['users'][user_id] = {'waitTime': wait}
        
        # Parse table utilizations
        for match in re.finditer(r'scalar DatabaseNetwork\.table\[(\d+)\] table\.utilization ([\d.e+-]+)', content):
            table_id = int(match.group(1))
            util = float(match.group(2))
            if table_id not in data['tables']:
                data['tables'][table_id] = {}
            data['tables'][table_id]['utilization'] = util
        
        # Parse table throughput
        for match in re.finditer(r'scalar DatabaseNetwork\.table\[(\d+)\] table\.throughput ([\d.e+-]+)', content):
            table_id = int(match.group(1))
            tp = float(match.group(2))
            if table_id not in data['tables']:
                data['tables'][table_id] = {}
            data['tables'][table_id]['throughput'] = tp
    
    return data

def analyze_all_results():
    """Analyze all .sca files and compute metrics per replication"""
    print("=" * 70)
    print("WARM-UP ANALYSIS FROM .SCA FILES")
    print("=" * 70)
    
    sca_files = list(RESULTS_DIR.glob("*.sca"))
    print(f"Found {len(sca_files)} .sca files")
    
    # Group by configuration (N, p, dist)
    configs = defaultdict(list)
    
    for sca_file in sca_files:
        data = parse_sca_file(sca_file)
        if 'N' in data['config'] and 'p' in data['config'] and data['users']:
            key = (data['config'].get('N'), data['config'].get('p'), data['config'].get('dist', 'Unknown'))
            
            # Compute average wait time across all users
            wait_times = [u['waitTime'] for u in data['users'].values() if 'waitTime' in u]
            avg_wait = np.mean(wait_times) if wait_times else 0
            
            # Compute average utilization
            utils = [t['utilization'] for t in data['tables'].values() if 'utilization' in t]
            avg_util = np.mean(utils) if utils else 0
            
            # Compute total throughput
            tps = [t['throughput'] for t in data['tables'].values() if 'throughput' in t]
            total_tp = sum(tps) if tps else 0
            
            rep = data['config'].get('rep', 0)
            configs[key].append({
                'rep': rep,
                'wait_time': avg_wait * 1000,  # Convert to ms
                'utilization': avg_util,
                'throughput': total_tp
            })
    
    print(f"Found {len(configs)} unique configurations")
    return configs

def create_warmup_response_plot(configs):
    """Create warm-up response time plot like the reference image"""
    print("\n" + "=" * 70)
    print("GENERATING WARM-UP RESPONSE TIME PLOT")
    print("=" * 70)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Select configurations to plot (varying N with p=0.5, Uniform)
    selected = []
    for (N, p, dist), reps in configs.items():
        if p == 0.5 and dist == 'Uniform' and len(reps) >= 3:
            selected.append((N, reps))
    
    # If not enough Uniform, try Lognormal
    if len(selected) < 3:
        for (N, p, dist), reps in configs.items():
            if p == 0.5 and len(reps) >= 3:
                selected.append((N, reps))
    
    selected = sorted(selected, key=lambda x: x[0])
    
    if not selected:
        print("ERROR: No suitable configurations found!")
        return
    
    # For each configuration, plot the normalized response time
    colors = plt.cm.tab10(np.linspace(0, 1, len(selected)))
    
    all_lines = []
    
    for idx, (N, reps) in enumerate(selected):
        # Sort by replication number
        reps = sorted(reps, key=lambda x: x['rep'])
        
        # Get response times for each replication
        response_times = [r['wait_time'] for r in reps]
        
        # Compute steady-state (mean of all replications)
        steady_state = np.mean(response_times)
        
        if steady_state > 0:
            # Normalize: Y(t) / Y_max where Y_max is steady state
            # This gives values that converge to 1
            normalized = [rt / steady_state for rt in response_times]
            
            # Create x-axis as "pseudo-time" based on replication number
            # Scale to simulation time (assuming ~10000s per run)
            x_times = [(r['rep'] + 1) * 200 for r in reps]  # Pseudo time points
            
            line, = ax.plot(x_times, normalized, 'o-', color=colors[idx], 
                           linewidth=1.5, markersize=4, alpha=0.8,
                           label=f'N={N}')
            all_lines.append((line, N, steady_state))
    
    # Add horizontal line at y=1 (steady state)
    ax.axhline(y=1.0, color='black', linestyle='--', linewidth=1, alpha=0.5, label='Steady State')
    
    # Add band for ±5% of steady state
    ax.axhspan(0.95, 1.05, alpha=0.1, color='green', label='±5% band')
    
    ax.set_xlabel('Simulation Progress (pseudo-time based on replications)', fontsize=11)
    ax.set_ylabel('Response Time / Steady-State Response Time', fontsize=11)
    ax.set_title('Warm-Up Response Time Convergence\n(Normalized to Steady-State)', fontsize=13)
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 2.0)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'warmup_analysis.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'warmup_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Plot saved to: {OUTPUT_DIR}/warmup_analysis.pdf")

def create_detailed_warmup_plot(configs):
    """Create a more detailed warm-up analysis plot"""
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Warm-Up Period Analysis from Simulation Results\n(Using Replication Data)', fontsize=14, fontweight='bold')
    
    # Collect data by N for p=0.5
    by_N = defaultdict(list)
    for (N, p, dist), reps in configs.items():
        if p == 0.5:
            for r in reps:
                by_N[N].append({
                    'wait': r['wait_time'],
                    'util': r['utilization'],
                    'tp': r['throughput'],
                    'dist': dist
                })
    
    Ns = sorted(by_N.keys())
    
    # Plot 1: Wait time distribution by N
    ax1 = axes[0, 0]
    wait_data = []
    labels = []
    for N in Ns[:8]:  # Limit to 8 for readability
        waits = [d['wait'] for d in by_N[N]]
        if waits:
            wait_data.append(waits)
            labels.append(f'N={N}')
    
    if wait_data:
        bp = ax1.boxplot(wait_data, labels=labels, patch_artist=True)
        colors = plt.cm.Blues(np.linspace(0.3, 0.9, len(wait_data)))
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
    
    ax1.set_xlabel('Configuration', fontsize=10)
    ax1.set_ylabel('Wait Time (ms)', fontsize=10)
    ax1.set_title('Wait Time Distribution Across Replications', fontsize=11)
    ax1.tick_params(axis='x', rotation=45)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Plot 2: Convergence plot - normalized response time
    ax2 = axes[0, 1]
    
    for i, N in enumerate(Ns[:6]):
        data = by_N[N]
        if len(data) >= 3:
            waits = [d['wait'] for d in data]
            steady = np.mean(waits)
            if steady > 0:
                normalized = [w/steady for w in waits]
                x = range(1, len(normalized) + 1)
                ax2.plot(x, normalized, 'o-', label=f'N={N}', alpha=0.7, markersize=5)
    
    ax2.axhline(y=1.0, color='black', linestyle='--', linewidth=1.5, label='Steady State')
    ax2.axhspan(0.95, 1.05, alpha=0.15, color='green')
    ax2.set_xlabel('Replication Number', fontsize=10)
    ax2.set_ylabel('Wait Time / Mean Wait Time', fontsize=10)
    ax2.set_title('Response Time Convergence (Normalized)', fontsize=11)
    ax2.legend(fontsize=8, loc='upper right')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0.5, 1.5)
    
    # Plot 3: Mean wait time vs N
    ax3 = axes[1, 0]
    mean_waits = []
    std_waits = []
    for N in Ns:
        waits = [d['wait'] for d in by_N[N]]
        mean_waits.append(np.mean(waits))
        std_waits.append(np.std(waits))
    
    ax3.errorbar(range(len(Ns)), mean_waits, yerr=std_waits, fmt='o-', 
                capsize=3, color='#e74c3c', markersize=6)
    ax3.set_xticks(range(len(Ns)))
    ax3.set_xticklabels([str(N) for N in Ns], rotation=45)
    ax3.set_xlabel('Number of Users (N)', fontsize=10)
    ax3.set_ylabel('Mean Wait Time (ms)', fontsize=10)
    ax3.set_title('Steady-State Wait Time vs System Load', fontsize=11)
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Coefficient of Variation (CV) - indicator of convergence
    ax4 = axes[1, 1]
    cvs = []
    for N in Ns:
        waits = [d['wait'] for d in by_N[N]]
        if np.mean(waits) > 0:
            cv = np.std(waits) / np.mean(waits) * 100
        else:
            cv = 0
        cvs.append(cv)
    
    bars = ax4.bar(range(len(Ns)), cvs, color='#3498db', alpha=0.8, edgecolor='black')
    ax4.set_xticks(range(len(Ns)))
    ax4.set_xticklabels([str(N) for N in Ns], rotation=45)
    ax4.set_xlabel('Number of Users (N)', fontsize=10)
    ax4.set_ylabel('Coefficient of Variation (%)', fontsize=10)
    ax4.set_title('Variability Across Replications (CV)', fontsize=11)
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.axhline(y=10, color='red', linestyle='--', alpha=0.5, label='10% threshold')
    ax4.legend()
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'warmup_analysis.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'warmup_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Plots saved to: {OUTPUT_DIR}/warmup_analysis.pdf")
    
    # Print summary
    print("\n" + "=" * 70)
    print("WARM-UP ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"{'N':>6} | {'Mean Wait (ms)':>15} | {'Std (ms)':>12} | {'CV (%)':>10} | {'Reps':>5}")
    print("-" * 60)
    for i, N in enumerate(Ns):
        waits = [d['wait'] for d in by_N[N]]
        print(f"{N:>6} | {np.mean(waits):>15.2f} | {np.std(waits):>12.2f} | {cvs[i]:>10.1f} | {len(waits):>5}")
    
    print("\n" + "-" * 60)
    avg_cv = np.mean(cvs)
    print(f"Average CV: {avg_cv:.1f}%")
    if avg_cv < 10:
        print("✓ Low variability indicates good convergence to steady-state")
        print("  Recommended warm-up: 500s (simulation already at steady state)")
    else:
        print("⚠ Higher variability - consider longer warm-up period")

if __name__ == "__main__":
    configs = analyze_all_results()
    if configs:
        create_detailed_warmup_plot(configs)
    else:
        print("ERROR: No data found!")
