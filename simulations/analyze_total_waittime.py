#!/usr/bin/env python3
"""
Calculate totalWaitTime from known averageWaitTime and totalAccesses
"""

import re
from pathlib import Path

def extract_sca_data(sca_file):
    """Extract key metrics from .sca file"""
    with open(sca_file, 'r') as f:
        content = f.read()
    
    data = {
        'totalAccesses': [],
        'averageWaitTime': [],
    }
    
    # Extract per-user totalAccesses and averageWaitTime
    accesses = re.findall(r'scalar DatabaseNetwork\.user\[\d+\] totalAccesses (\d+)', content)
    waits = re.findall(r'scalar DatabaseNetwork\.user\[\d+\] averageWaitTime (\d+(?:\.\d+)?)', content)
    
    data['totalAccesses'] = [float(a) for a in accesses]
    data['averageWaitTime'] = [float(w) for w in waits]
    
    return data

results_dir = Path("results_consistency/results")

# Analyze first replica of 500 and 1000
sca_500 = results_dir / "Config500Users-#0.sca"
sca_1000 = results_dir / "Config1000Users-#0.sca"

print("="*100)
print("CALCULATING totalWaitTime FROM RECORDED SCALARS")
print("="*100)

if sca_500.exists():
    print(f"\nConfig500Users-#0:")
    data_500 = extract_sca_data(sca_500)
    
    if data_500['totalAccesses'] and data_500['averageWaitTime']:
        total_accesses_500 = sum(data_500['totalAccesses'])
        avg_wait_500 = sum(data_500['averageWaitTime']) / len(data_500['averageWaitTime'])
        calc_total_wait_500 = total_accesses_500 * avg_wait_500
        
        print(f"  Total Accesses (sum across users): {total_accesses_500:.0f}")
        print(f"  Average Wait Time (mean across users): {avg_wait_500:.2f}s")
        print(f"  Calculated Total Wait Time: {calc_total_wait_500:.0f}s ({calc_total_wait_500/3600:.1f} hours)")

if sca_1000.exists():
    print(f"\nConfig1000Users-#0:")
    data_1000 = extract_sca_data(sca_1000)
    
    if data_1000['totalAccesses'] and data_1000['averageWaitTime']:
        total_accesses_1000 = sum(data_1000['totalAccesses'])
        avg_wait_1000 = sum(data_1000['averageWaitTime']) / len(data_1000['averageWaitTime'])
        calc_total_wait_1000 = total_accesses_1000 * avg_wait_1000
        
        print(f"  Total Accesses (sum across users): {total_accesses_1000:.0f}")
        print(f"  Average Wait Time (mean across users): {avg_wait_1000:.2f}s")
        print(f"  Calculated Total Wait Time: {calc_total_wait_1000:.0f}s ({calc_total_wait_1000/3600:.1f} hours)")

print(f"\n{'='*100}")
print("COMPARISON:")
print(f"{'='*100}")

if sca_500.exists() and sca_1000.exists():
    total_accesses_500 = sum(data_500['totalAccesses'])
    avg_wait_500 = sum(data_500['averageWaitTime']) / len(data_500['averageWaitTime'])
    calc_total_wait_500 = total_accesses_500 * avg_wait_500
    
    total_accesses_1000 = sum(data_1000['totalAccesses'])
    avg_wait_1000 = sum(data_1000['averageWaitTime']) / len(data_1000['averageWaitTime'])
    calc_total_wait_1000 = total_accesses_1000 * avg_wait_1000
    
    print(f"\nTotal Accesses:")
    print(f"  500 users: {total_accesses_500:.0f}")
    print(f"  1000 users: {total_accesses_1000:.0f}")
    print(f"  Ratio (1000/500): {total_accesses_1000/total_accesses_500:.2f}x")
    
    print(f"\nAverage Wait Time per Access:")
    print(f"  500 users: {avg_wait_500:.2f}s")
    print(f"  1000 users: {avg_wait_1000:.2f}s")
    print(f"  Difference: {avg_wait_500 - avg_wait_1000:.2f}s ({(1 - avg_wait_1000/avg_wait_500)*100:.1f}% LOWER)")
    
    print(f"\nTotal Wait Time Accumulated:")
    print(f"  500 users: {calc_total_wait_500:.0f}s ({calc_total_wait_500/3600:.1f} hours)")
    print(f"  1000 users: {calc_total_wait_1000:.0f}s ({calc_total_wait_1000/3600:.1f} hours)")
    print(f"  Ratio (1000/500): {calc_total_wait_1000/calc_total_wait_500:.2f}x")
    
    print(f"\n{'='*100}")
    print("KEY INSIGHT:")
    print(f"{'='*100}")
    print(f"""
Total Accesses raddoppia (2.00x), ma
Average Wait Time per Access SCENDE (0.59x),
Quindi Total Wait Time CRESCE ma MENO del doppio ({calc_total_wait_1000/calc_total_wait_500:.2f}x).

Questo significa che il sistema con 1000 utenti elabora operazioni più velocemente
perché raggiunge un equilibrio diverso dove la contention è distribuita meglio.

La metrica "average wait time" riflette il TEMPO MEDIO che ogni operazione attende,
non il TOTALE. Con più operazioni elaborate in parallelo, il tempo medio diminuisce.
""")
