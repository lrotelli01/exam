#!/usr/bin/env python3
"""
Real Warm-Up Period Analysis using Welch's Graphical Procedure
Analyzes .vec files from simulation results to determine warm-up period
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict
import re

# Directories
RESULTS_DIR = Path(__file__).parent / "results_consistency"
OUTPUT_DIR = Path(__file__).parent.parent / "documentation" / "images"
OUTPUT_DIR.mkdir(exist_ok=True)

def parse_vec_file(filepath):
    """Parse a .vec file and extract time series data"""
    vectors = {}  # vector_id -> {'name': ..., 'data': [(time, value), ...]}
    config = {}
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Parse config
            if line.startswith('config '):
                parts = line.split(' ', 2)
                if len(parts) >= 3:
                    config[parts[1]] = parts[2]
            
            # Parse vector definition
            elif line.startswith('vector '):
                parts = line.split()
                if len(parts) >= 4:
                    vec_id = int(parts[1])
                    module = parts[2]
                    name = parts[3]
                    vectors[vec_id] = {'name': name, 'module': module, 'data': []}
            
            # Parse data lines (format: vector_id event_num time value)
            elif line and line[0].isdigit() and '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 4:
                    try:
                        vec_id = int(parts[0])
                        time = float(parts[2])
                        value = float(parts[3])
                        if vec_id in vectors:
                            vectors[vec_id]['data'].append((time, value))
                    except (ValueError, IndexError):
                        pass
    
    return vectors, config

def aggregate_metric_series(vectors, metric_pattern='waitingTime|waitTime', bin_size=50.0, max_time=4000):
    """Aggregate metric vectors into time bins"""
    # Collect all matching data from tables
    all_data = []
    pattern = re.compile(metric_pattern)
    
    for vec_id, vec_info in vectors.items():
        if pattern.search(vec_info['name']) and 'table' in vec_info['module'].lower():
            all_data.extend(vec_info['data'])
    
    if not all_data:
        return None, None
    
    # Sort by time
    all_data.sort(key=lambda x: x[0])
    
    # Limit time range
    max_time = min(max(t for t, v in all_data), max_time)
    
    # Create bins
    num_bins = int(max_time / bin_size) + 1
    bins = [[] for _ in range(num_bins)]
    
    for time, value in all_data:
        if time <= max_time:
            bin_idx = min(int(time / bin_size), num_bins - 1)
            # Convert to ms and use max of 0 to ignore negative values
            bins[bin_idx].append(max(0, value * 1000))
    
    # Calculate mean for each bin (require minimum samples)
    times = []
    means = []
    for i, bin_data in enumerate(bins):
        if len(bin_data) >= 3:
            times.append((i + 0.5) * bin_size)
            means.append(np.mean(bin_data))
    
    return np.array(times), np.array(means)

def welch_procedure(replications_data, window_size=5):
    """Apply Welch's graphical procedure to multiple replications"""
    valid_data = [(t, m) for t, m in replications_data if t is not None and len(t) > 0]
    
    if not valid_data:
        return None, None, None
    
    # Find common time range
    min_len = min(len(t) for t, m in valid_data)
    if min_len == 0:
        return None, None, None
    
    # Align all replications
    times = valid_data[0][0][:min_len]
    aligned_data = [m[:min_len] for t, m in valid_data]
    
    # Calculate ensemble average
    ensemble_avg = np.mean(aligned_data, axis=0)
    ensemble_std = np.std(aligned_data, axis=0) if len(aligned_data) > 1 else np.zeros_like(ensemble_avg)
    
    # Apply moving average for smoothing
    if len(ensemble_avg) > 2 * window_size:
        smoothed = np.convolve(ensemble_avg, np.ones(window_size)/window_size, mode='valid')
        offset = (window_size - 1) // 2
        times_smooth = times[offset:offset+len(smoothed)]
        std_smooth = ensemble_std[offset:offset+len(smoothed)]
    else:
        smoothed = ensemble_avg
        times_smooth = times
        std_smooth = ensemble_std
    
    return times_smooth, smoothed, std_smooth

def detect_warmup_point(times, smoothed, threshold_pct=5):
    """Detect warm-up point where series stabilizes"""
    if smoothed is None or len(smoothed) < 10:
        return 0
    
    # Calculate steady-state as mean of last 25% of data
    last_quarter = smoothed[int(0.75 * len(smoothed)):]
    steady_state = np.mean(last_quarter)
    
    if steady_state == 0:
        return times[0]  # No warm-up needed if steady state is 0
    
    # Find first point within threshold of steady state
    threshold = max(steady_state * threshold_pct / 100, 0.1)  # Min threshold 0.1ms
    
    for i, val in enumerate(smoothed):
        if abs(val - steady_state) < threshold:
            return times[i]
    
    return times[len(times)//4]  # Default to first quarter

def analyze_configurations():
    """Analyze warm-up for multiple configurations"""
    print("=" * 70)
    print("WARM-UP ANALYSIS USING WELCH'S PROCEDURE")
    print("Analyzing .vec files from simulation results")
    print("=" * 70)
    
    # Find all .vec files
    vec_files = list(RESULTS_DIR.glob("*.vec"))
    print(f"\nFound {len(vec_files)} .vec files")
    
    # Group by configuration
    configs = defaultdict(list)
    for vf in vec_files:
        match = re.match(r'(Config\d+Users)-#(\d+)\.vec', vf.name)
        if match:
            config_name = match.group(1)
            rep_num = int(match.group(2))
            configs[config_name].append((rep_num, vf))
    
    print(f"Found {len(configs)} configurations:")
    for cfg in sorted(configs.keys(), key=lambda x: int(re.search(r'\d+', x).group())):
        print(f"  - {cfg}: {len(configs[cfg])} replications")
    
    results = {}
    
    # Analyze selected configurations
    selected = ['Config10Users', 'Config50Users', 'Config100Users', 'Config500Users', 'Config1000Users']
    selected = [c for c in selected if c in configs]
    
    for config_name in selected:
        print(f"\n--- Analyzing {config_name} ---")
        
        replications_data = []
        for rep_num, vf in sorted(configs[config_name]):
            vectors, cfg = parse_vec_file(vf)
            times, means = aggregate_metric_series(vectors, bin_size=50.0)
            if times is not None and len(times) > 0:
                replications_data.append((times, means))
                print(f"    Rep {rep_num}: {len(times)} bins, wait range: {means.min():.2f}-{means.max():.2f}ms")
        
        if replications_data:
            times, smoothed, std = welch_procedure(replications_data, window_size=3)
            if times is not None and len(times) > 0:
                warmup = detect_warmup_point(times, smoothed)
                steady_state = np.mean(smoothed[int(0.75*len(smoothed)):])
                results[config_name] = {
                    'times': times,
                    'smoothed': smoothed,
                    'std': std,
                    'warmup': warmup,
                    'steady_state': steady_state,
                    'raw_data': replications_data
                }
                print(f"    Warm-up: {warmup:.0f}s, Steady-state: {steady_state:.2f}ms")
    
    return results

def create_warmup_plots(results):
    """Create comprehensive warm-up analysis plots"""
    print("\n" + "=" * 70)
    print("GENERATING WARM-UP PLOTS")
    print("=" * 70)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.suptitle('Warm-Up Period Analysis (Welch\'s Procedure)\nUsing Real Simulation Data from .vec Files', 
                 fontsize=14, fontweight='bold')
    
    colors = ['#2ecc71', '#3498db', '#e74c3c', '#9b59b6', '#f39c12']
    
    # Sort results by N
    sorted_results = sorted(results.items(), key=lambda x: int(re.search(r'\d+', x[0]).group()))
    
    # Plot 1: Smoothed ensemble average for all configurations
    ax1 = axes[0, 0]
    for i, (config_name, data) in enumerate(sorted_results):
        N = int(re.search(r'(\d+)', config_name).group(1))
        ax1.plot(data['times'], data['smoothed'], label=f'N={N}', 
                color=colors[i % len(colors)], linewidth=2)
        ax1.axvline(data['warmup'], color=colors[i % len(colors)], linestyle='--', alpha=0.5)
    
    ax1.set_xlabel('Simulation Time (s)', fontsize=11)
    ax1.set_ylabel('Average Wait Time (ms)', fontsize=11)
    ax1.set_title('Ensemble Average Wait Time Over Time', fontsize=12)
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, None)
    
    # Plot 2: Individual replications vs ensemble for largest config
    ax2 = axes[0, 1]
    if sorted_results:
        config_name, data = sorted_results[-1]  # Largest N
        N = int(re.search(r'(\d+)', config_name).group(1))
        
        for i, (times, means) in enumerate(data['raw_data']):
            ax2.plot(times, means, alpha=0.4, linewidth=1, label=f'Rep {i+1}')
        
        ax2.plot(data['times'], data['smoothed'], 'k-', linewidth=2.5, label='Ensemble Avg')
        ax2.axvline(data['warmup'], color='red', linestyle='--', linewidth=2, label=f'Warm-up={data["warmup"]:.0f}s')
        ax2.axvspan(0, data['warmup'], alpha=0.15, color='red')
        
        ax2.set_xlabel('Simulation Time (s)', fontsize=11)
        ax2.set_ylabel('Wait Time (ms)', fontsize=11)
        ax2.set_title(f'Individual Replications (N={N})', fontsize=12)
        ax2.legend(loc='upper right', fontsize=9)
        ax2.grid(True, alpha=0.3)
    
    # Plot 3: Warm-up period vs N
    ax3 = axes[1, 0]
    Ns = [int(re.search(r'(\d+)', cfg).group(1)) for cfg, _ in sorted_results]
    warmups = [data['warmup'] for _, data in sorted_results]
    
    bars = ax3.bar(range(len(Ns)), warmups, color='#3498db', alpha=0.8, edgecolor='black')
    ax3.set_xticks(range(len(Ns)))
    ax3.set_xticklabels([f'N={n}' for n in Ns])
    ax3.set_xlabel('Configuration', fontsize=11)
    ax3.set_ylabel('Warm-Up Period (s)', fontsize=11)
    ax3.set_title('Detected Warm-Up Period', fontsize=12)
    ax3.grid(True, alpha=0.3, axis='y')
    
    for i, w in enumerate(warmups):
        ax3.text(i, w + max(warmups)*0.02, f'{w:.0f}s', ha='center', va='bottom', fontsize=10)
    
    # Plot 4: Steady-state wait time vs N
    ax4 = axes[1, 1]
    steady_states = [data['steady_state'] for _, data in sorted_results]
    
    ax4.bar(range(len(Ns)), steady_states, color='#e74c3c', alpha=0.8, edgecolor='black')
    ax4.set_xticks(range(len(Ns)))
    ax4.set_xticklabels([f'N={n}' for n in Ns])
    ax4.set_xlabel('Configuration', fontsize=11)
    ax4.set_ylabel('Steady-State Wait Time (ms)', fontsize=11)
    ax4.set_title('Steady-State Average Wait Time', fontsize=12)
    ax4.grid(True, alpha=0.3, axis='y')
    
    for i, ss in enumerate(steady_states):
        ax4.text(i, ss + max(steady_states)*0.02, f'{ss:.2f}ms', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'warmup_analysis.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'warmup_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Plots saved to: {OUTPUT_DIR}/warmup_analysis.pdf")
    
    # Print summary
    print("\n" + "=" * 70)
    print("WARM-UP ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"{'Config':<20} | {'N':>6} | {'Warm-Up':>10} | {'Steady-State':>15}")
    print("-" * 60)
    for config_name, data in sorted_results:
        N = int(re.search(r'(\d+)', config_name).group(1))
        print(f"{config_name:<20} | {N:>6} | {data['warmup']:>9.0f}s | {data['steady_state']:>14.2f}ms")
    
    max_warmup = max(d['warmup'] for _, d in sorted_results) if sorted_results else 0
    print("-" * 60)
    print(f"RECOMMENDED WARM-UP: {max_warmup:.0f}s")

if __name__ == "__main__":
    results = analyze_configurations()
    if results:
        create_warmup_plots(results)
    else:
        print("ERROR: No valid data found!")
