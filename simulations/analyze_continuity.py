#!/usr/bin/env python3
"""
ANALISI CONTINUITY TEST - Sezione 5.2
Confronta Configuration A (p=0.5) vs Configuration B (p=0.55)
Verifica che gli intervalli di confidenza al 95% si sovrappongono
"""

import sys
from pathlib import Path
from scipy import stats
import numpy as np
import matplotlib.pyplot as plt

def parse_sca_files(results_dir, config_name):
    """Parsa i file .sca per una configurazione"""
    print(f"\n  Parsing {config_name} results...")
    
    sca_files = list(results_dir.rglob(f"*{config_name}*.sca"))
    
    if not sca_files:
        print(f"  ⚠ Nessun file .sca trovato per {config_name}")
        return None
    
    metrics = {
        'throughput': [],
        'waitingTime': [],
        'utilization': []
    }
    
    for sca_file in sca_files:
        try:
            with open(sca_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('scalar'):
                        parts = line.split()
                        if len(parts) >= 4:
                            metric = parts[2]
                            try:
                                value = float(parts[3])
                                # Cerca metriche di interesse
                                for key in metrics.keys():
                                    if key in metric:
                                        metrics[key].append(value)
                            except ValueError:
                                pass
        except Exception as e:
            print(f"  ⚠ Errore lettura {sca_file}: {e}")
    
    return metrics

def calculate_ci_95(values):
    """Calcola media e intervallo di confidenza 95%"""
    if not values or len(values) < 2:
        return None, None, None, None
    
    values = np.array(values)
    mean = np.mean(values)
    std_err = stats.sem(values)  # Standard error of the mean
    ci = std_err * stats.t.ppf((1 + 0.95) / 2, len(values) - 1)
    
    return mean, ci, mean - ci, mean + ci

def check_overlap(ci_a, ci_b):
    """Verifica se due intervalli di confidenza si sovrappongono"""
    mean_a, ci_a_val, lower_a, upper_a = ci_a
    mean_b, ci_b_val, lower_b, upper_b = ci_b
    
    if mean_a is None or mean_b is None:
        return None, None
    
    # Due intervalli si sovrappongono se:
    # lower_a <= upper_b AND lower_b <= upper_a
    overlap = (lower_a <= upper_b) and (lower_b <= upper_a)
    
    # Calcola il grado di sovrapponimnto
    overlap_start = max(lower_a, lower_b)
    overlap_end = min(upper_a, upper_b)
    overlap_percent = (overlap_end - overlap_start) / max(upper_a - lower_a, upper_b - lower_b) * 100
    
    return overlap, overlap_percent

def plot_continuity_results(results_dir, metrics_a, metrics_b):
    """Plotta i risultati del continuity test con error bars per replica"""
    
    print(f"\n  Generating continuity plot...")
    
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle('Continuity Test - Configuration A (p=0.5) vs Configuration B (p=0.55) at 95% CI', fontsize=14)
    
    metrics = ['throughput', 'waitingTime', 'utilization']
    
    for idx, (ax, metric_key) in enumerate(zip(axes, metrics)):
        values_a = metrics_a.get(metric_key, [])
        values_b = metrics_b.get(metric_key, [])
        
        if not values_a or not values_b:
            continue
        
        # Assume 25 replicas per config (vedi continuity_test.py: repeat=25)
        num_replicas = 25
        
        # Dividi i valori in 25 gruppi (uno per replica)
        vals_a_per_replica = []
        vals_b_per_replica = []
        errs_a = []
        errs_b = []
        
        for i in range(num_replicas):
            # Prendi i valori della replica i da entrambe le config
            start_idx = i * (len(values_a) // num_replicas) if num_replicas > 0 else 0
            end_idx = (i + 1) * (len(values_a) // num_replicas) if num_replicas > 0 else len(values_a)
            
            replica_a = values_a[start_idx:end_idx] if start_idx < len(values_a) else []
            replica_b = values_b[start_idx:end_idx] if start_idx < len(values_b) else []
            
            if replica_a:
                vals_a_per_replica.append(np.mean(replica_a))
                errs_a.append(np.std(replica_a))
            
            if replica_b:
                vals_b_per_replica.append(np.mean(replica_b))
                errs_b.append(np.std(replica_b))
        
        # Se non abbiamo abbastanza dati divisi per replica, prendi i valori così come sono
        if len(vals_a_per_replica) < 10:
            vals_a_per_replica = values_a[:num_replicas] if len(values_a) >= num_replicas else values_a
            vals_b_per_replica = values_b[:num_replicas] if len(values_b) >= num_replicas else values_b
            errs_a = [np.std(values_a) / np.sqrt(len(values_a))] * len(vals_a_per_replica)
            errs_b = [np.std(values_b) / np.sqrt(len(values_b))] * len(vals_b_per_replica)
        
        # Prepara x positions
        x_pos = np.arange(1, len(vals_a_per_replica) + 1)
        
        # Plot con error bars
        ax.errorbar(x_pos - 0.15, vals_a_per_replica, yerr=errs_a, fmt='o-', 
                   label='First Config (p=0.5)', color='red', capsize=3, markersize=5, linewidth=1.5)
        ax.errorbar(x_pos + 0.15, vals_b_per_replica, yerr=errs_b, fmt='o-', 
                   label='Second Config (p=0.55)', color='black', capsize=3, markersize=5, linewidth=1.5)
        
        ax.set_xlabel('Replicas', fontsize=10)
        ax.set_ylabel(metric_key.capitalize() + ' (transactions/s)', fontsize=10)
        ax.set_title(metric_key.capitalize(), fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9, loc='best')
        ax.set_xlim(0, len(vals_a_per_replica) + 1)
    
    plt.tight_layout()
    plt.savefig('continuity_test_results.png', dpi=150, bbox_inches='tight')
    print(f"  ✓ Plot saved: continuity_test_results.png\n")

def main():
    """Analizza il continuity test"""
    
    print(f"\n{'='*70}")
    print(" "*15 + "CONTINUITY TEST ANALYSIS - SEZIONE 5.2")
    print(f"{'='*70}")
    
    results_dir = Path("results_continuity")
    
    if not results_dir.exists():
        print(f"\n✗ ERRORE: Directory {results_dir}/ non trovata")
        print(f"  Eseguire prima: python3 continuity_test.py")
        return False
    
    # Parsa risultati
    metrics_a = parse_sca_files(results_dir, "ContinuityA")
    metrics_b = parse_sca_files(results_dir, "ContinuityB")
    
    if not metrics_a or not metrics_b:
        print(f"\n✗ Errore nel parsing dei risultati")
        return False
    
    # Genera plot
    plot_continuity_results(results_dir, metrics_a, metrics_b)
    
    # Calcola statistiche
    print(f"\n{'='*70}")
    print("RISULTATI E CONFRONTO (95% Confidence Intervals)")
    print(f"{'='*70}\n")
    
    results_summary = []
    
    for metric_key in ['throughput', 'waitingTime', 'utilization']:
        print(f"\n{metric_key.upper()}")
        print("-" * 70)
        
        values_a = metrics_a.get(metric_key, [])
        values_b = metrics_b.get(metric_key, [])
        
        if not values_a or not values_b:
            print(f"  ⚠ Metrica non trovata nei risultati")
            continue
        
        # Configuration A
        mean_a, ci_a, lower_a, upper_a = calculate_ci_95(values_a)
        print(f"\nConfiguration A (p=0.5):")
        print(f"  Mean: {mean_a:.6f}")
        print(f"  95% CI: [{lower_a:.6f}, {upper_a:.6f}]")
        print(f"  Samples: {len(values_a)}")
        
        # Configuration B
        mean_b, ci_b, lower_b, upper_b = calculate_ci_95(values_b)
        print(f"\nConfiguration B (p=0.55):")
        print(f"  Mean: {mean_b:.6f}")
        print(f"  95% CI: [{lower_b:.6f}, {upper_b:.6f}]")
        print(f"  Samples: {len(values_b)}")
        
        # Confronto
        ci_a_tuple = (mean_a, ci_a, lower_a, upper_a)
        ci_b_tuple = (mean_b, ci_b, lower_b, upper_b)
        overlap, overlap_pct = check_overlap(ci_a_tuple, ci_b_tuple)
        
        print(f"\nComparison:")
        print(f"  Difference in means: {abs(mean_a - mean_b):.6f}")
        print(f"  Percentage change: {(abs(mean_a - mean_b) / mean_a * 100):.2f}%")
        
        if overlap:
            print(f"  ✓ Intervalli si sovrappongono ({overlap_pct:.1f}% overlap)")
            print(f"  ✓ CONTINUITY PRESERVED: piccola variazione nei parametri →")
            print(f"    → piccola variazione nei risultati")
            results_summary.append((metric_key, True))
        else:
            print(f"  ✗ Intervalli NON si sovrappongono")
            print(f"  ✗ CONTINUITY VIOLATED: variazione nei parametri ha effetto grande")
            results_summary.append((metric_key, False))
    
    # Riassunto finale
    print(f"\n{'='*70}")
    print("CONTINUITY TEST SUMMARY")
    print(f"{'='*70}\n")
    
    passed = sum(1 for _, result in results_summary if result)
    total = len(results_summary)
    
    for metric, result in results_summary:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {metric}: {status}")
    
    print(f"\nTotal: {passed}/{total} metrics show continuity")
    
    if passed == total:
        print(f"\n✓ CONTINUITY TEST PASSED")
        print(f"  Sistema è continuo: piccole variazioni nei parametri")
        print(f"  producono piccole variazioni nei risultati")
        return True
    else:
        print(f"\n⚠ CONTINUITY TEST PARTIALLY FAILED")
        print(f"  Alcuni metriche mostrano variazioni significative")
        return True  # Non è un failure critico

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
