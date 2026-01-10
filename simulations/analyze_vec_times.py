#!/usr/bin/env python3
"""
Analyze .vec files to see how wait time evolves during simulation
"""

import re
from pathlib import Path
from collections import defaultdict

def analyze_vec_file(vec_path):
    """Extract wait time events from .vec file"""
    wait_times = []
    
    with open(vec_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and metadata lines
            if not line or line.startswith('v ') or line.startswith('vector') or line.startswith('attr') or line.startswith('config') or line.startswith('par') or line.startswith('run') or line.startswith('version'):
                continue
            
            # Data lines format: EventNumber SimTime VectorId Value
            # Example: 0 0.0 0 5.123
            parts = line.split()
            if len(parts) >= 4:
                try:
                    event_num = int(parts[0])
                    sim_time = float(parts[1])
                    vector_id = int(parts[2])
                    value = float(parts[3])
                    
                    # vector_id 0, 2, 4, 6, ... are waitTime vectors
                    # (odd numbers are accessInterval)
                    if vector_id % 2 == 0:  # This is a waitTime vector
                        wait_times.append((sim_time, value))
                except (ValueError, IndexError):
                    pass
    
    return wait_times

# Analyze first replica of 500 and 1000 users
results_dir = Path("results_consistency/results")

vec_500 = results_dir / "Config500Users-#0.vec"
vec_1000 = results_dir / "Config1000Users-#0.vec"

print("="*100)
print("ANALYZING WAIT TIME EVOLUTION OVER TIME")
print("="*100)

if vec_500.exists():
    print(f"\nAnalyzing: {vec_500.name}")
    wait_times_500 = analyze_vec_file(vec_500)
    
    if wait_times_500:
        # Split into time periods: warmup (0-500s) and steady-state (500-1000s)
        warmup_waits = [wt for t, wt in wait_times_500 if t < 500]
        steady_waits = [wt for t, wt in wait_times_500 if t >= 500]
        
        print(f"  Warmup period (0-500s): {len(warmup_waits)} wait events")
        if warmup_waits:
            avg_warmup = sum(warmup_waits) / len(warmup_waits)
            print(f"    Average wait time: {avg_warmup:.2f}s")
        
        print(f"  Steady-state (500-1000s): {len(steady_waits)} wait events")
        if steady_waits:
            avg_steady = sum(steady_waits) / len(steady_waits)
            print(f"    Average wait time: {avg_steady:.2f}s")

if vec_1000.exists():
    print(f"\nAnalyzing: {vec_1000.name}")
    wait_times_1000 = analyze_vec_file(vec_1000)
    
    if wait_times_1000:
        # Split into time periods: warmup (0-500s) and steady-state (500-1000s)
        warmup_waits = [wt for t, wt in wait_times_1000 if t < 500]
        steady_waits = [wt for t, wt in wait_times_1000 if t >= 500]
        
        print(f"  Warmup period (0-500s): {len(warmup_waits)} wait events")
        if warmup_waits:
            avg_warmup = sum(warmup_waits) / len(warmup_waits)
            print(f"    Average wait time: {avg_warmup:.2f}s")
        
        print(f"  Steady-state (500-1000s): {len(steady_waits)} wait events")
        if steady_waits:
            avg_steady = sum(steady_waits) / len(steady_waits)
            print(f"    Average wait time: {avg_steady:.2f}s")

print(f"\n{'='*100}")
print("HYPOTHESIS CHECK:")
print(f"{'='*100}")
print("""
If wait times during WARMUP (0-500s) are similar but STEADY-STATE (500-1000s) differs,
then the warmup-period=500s config is the culprit.

The recordScalar is calculated AFTER finish(), which includes the entire simulation.
If 500-user system spends more time in transient state, that explains the higher avg wait!
""")
