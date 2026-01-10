#!/usr/bin/env python3
"""
Investigate why wait time decreases from 500 to 1000 users
"""

import re
from pathlib import Path

def analyze_config(config_name):
    """Extract detailed metrics for a specific configuration"""
    results_dir = Path("results_consistency/results")
    
    # Find all .sca files for this config
    sca_files = sorted(results_dir.glob(f"{config_name}-*.sca"))
    
    if not sca_files:
        print(f"No files found for {config_name}")
        return
    
    print(f"\n{'='*100}")
    print(f"Analysis: {config_name}")
    print(f"{'='*100}")
    
    # Aggregate data across all 10 repliche
    all_metrics = {
        'totalAccesses': [],
        'totalReads': [],
        'totalWrites': [],
        'averageWaitTime': [],
        'accessesPerSecond': [],
        'totalServed': [],
        'totalWriteTime': [],
        'totalReadTime': [],
        'utilizationPerTable': [],
        'maxQueueLength': []
    }
    
    for sca_file in sca_files:
        with open(sca_file, 'r') as f:
            content = f.read()
        
        # Extract per-user metrics (sum them up for total)
        total_accesses = sum(float(m) for m in re.findall(r'scalar DatabaseNetwork\.user\[\d+\] totalAccesses (\d+)', content))
        total_reads = sum(float(m) for m in re.findall(r'scalar DatabaseNetwork\.user\[\d+\] totalReads (\d+)', content))
        total_writes = sum(float(m) for m in re.findall(r'scalar DatabaseNetwork\.user\[\d+\] totalWrites (\d+)', content))
        
        # Extract wait time (average across all users)
        wait_times = re.findall(r'scalar DatabaseNetwork\.user\[\d+\] averageWaitTime (\d+(?:\.\d+)?)', content)
        avg_wait = sum(float(w) for w in wait_times) / len(wait_times) if wait_times else 0
        
        # Extract ops per second (sum all users)
        ops_per_sec = sum(float(m) for m in re.findall(r'scalar DatabaseNetwork\.user\[\d+\] accessesPerSecond (\d+(?:\.\d+)?)', content))
        
        # Extract per-table metrics
        total_served = sum(float(m) for m in re.findall(r'scalar DatabaseNetwork\.table\[\d+\] totalServed (\d+)', content))
        
        # Extract queue metrics
        max_queue_lengths = re.findall(r'scalar DatabaseNetwork\.table\[\d+\] maxQueueLength (\d+)', content)
        avg_max_queue = sum(float(m) for m in max_queue_lengths) / len(max_queue_lengths) if max_queue_lengths else 0
        
        all_metrics['totalAccesses'].append(total_accesses)
        all_metrics['totalReads'].append(total_reads)
        all_metrics['totalWrites'].append(total_writes)
        all_metrics['averageWaitTime'].append(avg_wait)
        all_metrics['accessesPerSecond'].append(ops_per_sec)
        all_metrics['totalServed'].append(total_served)
        all_metrics['maxQueueLength'].append(avg_max_queue)
    
    # Print statistics
    print(f"\nPer-User Statistics (summed across users):")
    print(f"  Total Accesses: {sum(all_metrics['totalAccesses'])/len(sca_files):.0f} ± {(max(all_metrics['totalAccesses']) - min(all_metrics['totalAccesses']))/2:.0f}")
    print(f"  Total Reads: {sum(all_metrics['totalReads'])/len(sca_files):.0f}")
    print(f"  Total Writes: {sum(all_metrics['totalWrites'])/len(sca_files):.0f}")
    print(f"  Read/Write Ratio: {(sum(all_metrics['totalReads'])/len(sca_files)) / (sum(all_metrics['totalWrites'])/len(sca_files)):.2f}")
    
    print(f"\nWait Time Metrics:")
    print(f"  Average Wait Time: {sum(all_metrics['averageWaitTime'])/len(sca_files):.2f} ± {(max(all_metrics['averageWaitTime']) - min(all_metrics['averageWaitTime']))/2:.2f}")
    print(f"  Throughput (ops/s): {sum(all_metrics['accessesPerSecond'])/len(sca_files):.2f}")
    
    print(f"\nPer-Table Statistics (averaged across 10 tables):")
    print(f"  Total Served per Table: {sum(all_metrics['totalServed'])/len(sca_files)/10:.0f}")
    print(f"  Avg Max Queue Length: {sum(all_metrics['maxQueueLength'])/len(sca_files):.2f}")
    
    # Calculate service ratio: what % of operations are reads vs writes?
    avg_reads = sum(all_metrics['totalReads'])/len(sca_files)
    avg_writes = sum(all_metrics['totalWrites'])/len(sca_files)
    total_ops = avg_reads + avg_writes
    print(f"\nRead/Write Split:")
    print(f"  Reads: {avg_reads/total_ops*100:.1f}%")
    print(f"  Writes: {avg_writes/total_ops*100:.1f}%")
    
    return all_metrics

# Analyze both critical configurations
print("\nComparing 500 vs 1000 Users Behavior")
print("="*100)

metrics_500 = analyze_config("Config500Users")
metrics_1000 = analyze_config("Config1000Users")

# Calculate difference
print(f"\n{'='*100}")
print("COMPARISON: 500 Users vs 1000 Users")
print(f"{'='*100}")

avg_wait_500 = sum(metrics_500['averageWaitTime']) / len(metrics_500['averageWaitTime'])
avg_wait_1000 = sum(metrics_1000['averageWaitTime']) / len(metrics_1000['averageWaitTime'])

print(f"\nWait Time:")
print(f"  500 users: {avg_wait_500:.2f}s")
print(f"  1000 users: {avg_wait_1000:.2f}s")
print(f"  Difference: {avg_wait_500 - avg_wait_1000:.2f}s ({(1 - avg_wait_1000/avg_wait_500)*100:.1f}% LOWER)")

throughput_500 = sum(metrics_500['accessesPerSecond']) / len(metrics_500['accessesPerSecond'])
throughput_1000 = sum(metrics_1000['accessesPerSecond']) / len(metrics_1000['accessesPerSecond'])

print(f"\nThroughput:")
print(f"  500 users: {throughput_500:.2f} ops/s")
print(f"  1000 users: {throughput_1000:.2f} ops/s")
print(f"  Ratio: {throughput_1000/throughput_500:.2f}x")

queue_500 = sum(metrics_500['maxQueueLength']) / len(metrics_500['maxQueueLength'])
queue_1000 = sum(metrics_1000['maxQueueLength']) / len(metrics_1000['maxQueueLength'])

print(f"\nMax Queue Length (avg per table):")
print(f"  500 users: {queue_500:.2f}")
print(f"  1000 users: {queue_1000:.2f}")
print(f"  Difference: {queue_1000 - queue_500:.2f}")

print(f"\n{'='*100}")
print("HYPOTHESIS:")
print(f"{'='*100}")
print("""
Con 500 utenti (50 per tabella):
  - Coda media al massimo ~25-30 operazioni per tabella
  - Ogni operazione aspetta ~100s in coda
  
Con 1000 utenti (100 per tabella):
  - Coda POTREBBE essere più grande in termini assoluti
  - MA il throughput RADDOPPIA (500 → 1000 ops/s)
  - Meno "residuo" in coda perché vengono processate più velocemente
  - Il sistema raggiunge un equilibrio di regime diverso
  
La metrica "averageWaitTime" potrebbe essere calcolata come:
  averageWaitTime = somma(tempi d'attesa) / numero_operazioni
  
Con 1000 utenti, anche se la coda è fisicamente più grande,
il numero TOTALE di operazioni è 2x, quindi il tempo medio potrebbe scendere!
""")
