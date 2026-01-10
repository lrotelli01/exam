#!/usr/bin/env python3
"""
Analyze consistency test results and generate plots
"""

import re
import sys
from pathlib import Path
import matplotlib.pyplot as plt

def parse_sca_files(results_dir):
    """Parse all .sca files and extract metrics by configuration"""
    results = {}
    sca_files = list(Path(results_dir).rglob("*.sca"))
    
    if not sca_files:
        print("ERROR: No .sca files found!")
        return results
    
    print(f"Found {len(sca_files)} .sca files")
    
    for sca_file in sorted(sca_files):
        try:
            with open(sca_file, 'r') as f:
                content = f.read()
            
            # Extract run name to identify config: run Config10Users-0-...
            run_match = re.search(r'run (Config\w+)', content)
            if not run_match:
                continue
            
            config_name = run_match.group(1)
            
            # Initialize dict for this config if needed
            if config_name not in results:
                results[config_name] = {
                    'throughput': [],
                    'waitingTime': []
                }
            
            # Extract throughput (accessesPerSecond per user) and average wait time
            throughput_matches = re.findall(
                r'scalar DatabaseNetwork\.user\[\d+\] accessesPerSecond (\d+(?:\.\d+)?)',
                content
            )
            wait_matches = re.findall(
                r'scalar DatabaseNetwork\.user\[\d+\] averageWaitTime (\d+(?:\.\d+)?)',
                content
            )
            
            if throughput_matches:
                # Sum all user throughputs for total system throughput
                total_throughput = sum(float(t) for t in throughput_matches)
                results[config_name]['throughput'].append(total_throughput)
            
            if wait_matches:
                # Average wait time across all users
                avg_wait = sum(float(w) for w in wait_matches) / len(wait_matches)
                results[config_name]['waitingTime'].append(avg_wait)
                    
        except Exception as e:
            print(f"Warning: Could not parse {sca_file}: {e}")
    
    return results

def calculate_ci_95(values):
    """Calculate mean and 95% confidence interval"""
    if not values:
        return None, None, None
    
    import statistics
    from scipy import stats
    
    mean = statistics.mean(values)
    n = len(values)
    
    if n < 2:
        return mean, mean, mean
    
    std = statistics.stdev(values)
    se = std / (n ** 0.5)
    ci = stats.t.ppf(0.975, n-1) * se
    
    return mean, mean - ci, mean + ci

def plot_consistency_results(results_dir, metrics):
    """Generate plots showing consistency: throughput and wait time vs numUsers"""
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    config_order = [10, 50, 100, 500, 1000]
    throughputs_mean = []
    throughputs_ci_lower = []
    throughputs_ci_upper = []
    
    wait_times_mean = []
    wait_times_ci_lower = []
    wait_times_ci_upper = []
    
    # Extract statistics for each configuration
    for num_users in config_order:
        config_name = f"Config{num_users}Users"
        
        if config_name in metrics:
            # Throughput
            throughput_mean, throughput_low, throughput_high = calculate_ci_95(
                metrics[config_name]['throughput']
            )
            if throughput_mean is not None:
                throughputs_mean.append(throughput_mean)
                throughputs_ci_lower.append(throughput_low)
                throughputs_ci_upper.append(throughput_high)
            
            # Wait time
            wait_mean, wait_low, wait_high = calculate_ci_95(
                metrics[config_name]['waitingTime']
            )
            if wait_mean is not None:
                wait_times_mean.append(wait_mean)
                wait_times_ci_lower.append(wait_low)
                wait_times_ci_upper.append(wait_high)
    
    # Plot 1: Throughput vs numUsers
    ax1 = axes[0]
    if throughputs_mean:
        errors_throughput = [
            [throughputs_mean[i] - throughputs_ci_lower[i] for i in range(len(throughputs_mean))],
            [throughputs_ci_upper[i] - throughputs_mean[i] for i in range(len(throughputs_mean))]
        ]
        ax1.errorbar(
            config_order[:len(throughputs_mean)],
            throughputs_mean,
            yerr=errors_throughput,
            marker='o',
            color='blue',
            ecolor='lightblue',
            capsize=5,
            label='Throughput (95% CI)'
        )
        ax1.set_xlabel('Number of Users', fontsize=12)
        ax1.set_ylabel('Throughput (ops/s)', fontsize=12)
        ax1.set_title('Consistency Test: Throughput vs numUsers', fontsize=13, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
    
    # Plot 2: Wait time vs numUsers
    ax2 = axes[1]
    if wait_times_mean:
        errors_wait = [
            [wait_times_mean[i] - wait_times_ci_lower[i] for i in range(len(wait_times_mean))],
            [wait_times_ci_upper[i] - wait_times_mean[i] for i in range(len(wait_times_mean))]
        ]
        ax2.errorbar(
            config_order[:len(wait_times_mean)],
            wait_times_mean,
            yerr=errors_wait,
            marker='s',
            color='red',
            ecolor='lightcoral',
            capsize=5,
            label='Wait Time (95% CI)'
        )
        ax2.set_xlabel('Number of Users', fontsize=12)
        ax2.set_ylabel('Wait Time (s)', fontsize=12)
        ax2.set_title('Consistency Test: Wait Time vs numUsers', fontsize=13, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
    
    plt.tight_layout()
    output_path = Path(results_dir) / "consistency_test_results.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ Plot saved: {output_path}")
    plt.close()

def main():
    results_dir = Path("results_consistency")
    
    if not results_dir.exists():
        print(f"ERROR: Results directory not found: {results_dir}")
        return False
    
    print("="*60)
    print("CONSISTENCY TEST - Analysis")
    print("="*60)
    
    # Parse results
    metrics = parse_sca_files(results_dir)
    
    if not metrics:
        print("No metrics found!")
        return False
    
    # Print summary statistics
    print("\nSummary Statistics:")
    print("="*100)
    
    config_order = [10, 50, 100, 500, 1000]
    print(f"{'numUsers':<12} {'Throughput (ops/s)':<40} {'Wait Time (s)':<40}")
    print("-" * 100)
    
    detailed_data = {}
    for num_users in config_order:
        config_name = f"Config{num_users}Users"
        if config_name in metrics:
            throughput_mean, throughput_low, throughput_high = calculate_ci_95(
                metrics[config_name]['throughput']
            )
            wait_mean, wait_low, wait_high = calculate_ci_95(
                metrics[config_name]['waitingTime']
            )
            
            detailed_data[num_users] = {
                'throughput': throughput_mean,
                'wait_time': wait_mean
            }
            
            throughput_str = f"{throughput_mean:.2f} ± {(throughput_high - throughput_mean):.2f}" if throughput_mean else "N/A"
            wait_str = f"{wait_mean:.2f} ± {(wait_high - wait_mean):.2f}" if wait_mean else "N/A"
            
            print(f"{num_users:<12} {throughput_str:<40} {wait_str:<40}")
    
    # Print detailed values
    print("\n" + "="*100)
    print("DETAILED VALUES:")
    print("="*100)
    for num_users in config_order:
        config_name = f"Config{num_users}Users"
        if config_name in metrics:
            print(f"\nConfig: {num_users} Users")
            print(f"  Throughput values (10 repliche): {[f'{x:.2f}' for x in metrics[config_name]['throughput']]}")
            print(f"  Wait Time values (10 repliche): {[f'{x:.2f}' for x in metrics[config_name]['waitingTime']]}")
            
            if metrics[config_name]['throughput']:
                tput_mean = sum(metrics[config_name]['throughput']) / len(metrics[config_name]['throughput'])
                tput_std = (sum((x - tput_mean)**2 for x in metrics[config_name]['throughput']) / len(metrics[config_name]['throughput'])) ** 0.5
                print(f"  Throughput: mean={tput_mean:.2f}, std={tput_std:.2f}")
            
            if metrics[config_name]['waitingTime']:
                wait_mean = sum(metrics[config_name]['waitingTime']) / len(metrics[config_name]['waitingTime'])
                wait_std = (sum((x - wait_mean)**2 for x in metrics[config_name]['waitingTime']) / len(metrics[config_name]['waitingTime'])) ** 0.5
                print(f"  Wait Time: mean={wait_mean:.2f}, std={wait_std:.2f}")
    
    # Generate plots
    print("\nGenerating plots...")
    plot_consistency_results(results_dir, metrics)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
