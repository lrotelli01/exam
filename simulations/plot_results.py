#!/usr/bin/env python3
"""
Genera grafici con INTERVALLI DI CONFIDENZA (95%) e Tabelle Excel-Ready
"""

import os
import re
from collections import defaultdict
import statistics
import math
import pandas as pd
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats # Necessario per calcolo t-student corretto

def parse_sca_file(filepath):
    data = {'config': {}, 'users': [], 'tables': []}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('itervar'):
                parts = line.split()
                if len(parts) >= 3: data['config'][parts[1]] = parts[2]
            
            if line.startswith('scalar DatabaseNetwork.user['):
                match = re.search(r'user\[(\d+)\]\s+(\w+)\s+([\d.]+)', line)
                if match:
                    user_id = int(match.group(1))
                    stat = match.group(2)
                    val = float(match.group(3))
                    if len(data['users']) <= user_id: data['users'].extend([{} for _ in range(user_id - len(data['users']) + 1)])
                    data['users'][user_id][stat] = val
            if line.startswith('scalar DatabaseNetwork.table['):
                match = re.search(r'table\[(\d+)\]\s+([\w.]+)\s+([\d.eE+-]+)', line)
                if match:
                    table_id = int(match.group(1))
                    stat = match.group(2)
                    val = float(match.group(3))
                    if len(data['tables']) <= table_id: data['tables'].extend([{} for _ in range(table_id - len(data['tables']) + 1)])
                    data['tables'][table_id][stat] = val
    return data

def aggregate_statistics(data):
    wait_times = [u['averageWaitTime'] for u in data['users'] if 'averageWaitTime' in u]
    table_throughputs = [t['table.throughput'] for t in data['tables'] if 'table.throughput' in t]
    table_utilizations = [t['table.utilization'] for t in data['tables'] if 'table.utilization' in t]
    return {
        'avg_wait_time': statistics.mean(wait_times) if wait_times else 0,
        'system_throughput': sum(table_throughputs) if table_throughputs else 0,
        'avg_table_utilization': statistics.mean(table_utilizations) if table_utilizations else 0,
    }

def load_all_results():
    results = defaultdict(list)
    if not os.path.exists('results'): 
        print("❌ ERRORE: Cartella 'results' non trovata.")
        return results
        
    files = [f for f in os.listdir('results') if f.endswith('.sca')]
    print(f"📂 Trovati {len(files)} file .sca")

    for filename in files:
        try:
            data = parse_sca_file(os.path.join('results', filename))
            dist = 'Uniform' if 'Uniform' in filename else 'Lognormal' if 'Lognormal' in filename else None
            if not dist: continue
                
            N = int(data['config'].get('N', 0))
            p = float(data['config'].get('p', 0))
            if N == 0: continue
            
            # Raccoglie tutti i run (seed diversi finiscono nella stessa lista chiave)
            results[(dist, N, p)].append(aggregate_statistics(data))
        except Exception as e:
            print(f"❌ Errore file {filename}: {e}")
            continue
    return results

def calculate_confidence_interval(data_list, metric_key, confidence=0.95):
    """Calcola media e intervallo di confidenza (margine di errore)"""
    values = [x[metric_key] for x in data_list]
    n = len(values)
    
    if n == 0: return 0, 0
    mean = statistics.mean(values)
    
    if n == 1:
        return mean, 0.0  # Nessun intervallo possibile con 1 solo campione
        
    std_err = statistics.stdev(values) / math.sqrt(n)
    h = std_err * stats.t.ppf((1 + confidence) / 2, n - 1)
    return mean, h

def process_stats_with_ci(results):
    """Elabora tutte le statistiche calcolando i CI"""
    processed = {}
    for key, runs in results.items():
        # Throughput
        tp_mean, tp_ci = calculate_confidence_interval(runs, 'system_throughput')
        # Wait Time
        wt_mean, wt_ci = calculate_confidence_interval(runs, 'avg_wait_time')
        # Utilization
        ut_mean, ut_ci = calculate_confidence_interval(runs, 'avg_table_utilization')
        
        processed[key] = {
            'tp_mean': tp_mean, 'tp_ci': tp_ci,
            'wt_mean': wt_mean, 'wt_ci': wt_ci,
            'ut_mean': ut_mean, 'ut_ci': ut_ci,
            'runs_count': len(runs)
        }
    return processed

def export_tables(stats_data):
    print("\n" + "="*50)
    print("GENERAZIONE TABELLE (Con Confidenza 95%)")
    print("="*50)
    
    data_list = []
    
    for key, val in stats_data.items():
        dist, N, p = key
        row = {
            'Distribuzione': dist,
            'N_Utenti': N,
            'Prob_Read (p)': p,
            'Runs': val['runs_count'],
            'Throughput': round(val['tp_mean'], 2),
            'Throughput_CI': round(val['tp_ci'], 2), # Margine +/-
            'Wait_Time': round(val['wt_mean'], 4),
            'Wait_Time_CI': round(val['wt_ci'], 4),
            'Utilization_%': round(val['ut_mean'] * 100, 2)
        }
        data_list.append(row)
    
    if not data_list: return

    df = pd.DataFrame(data_list)
    df = df.sort_values(by=['Distribuzione', 'Prob_Read (p)', 'N_Utenti'])
    
    # Export CSV Italiano
    csv_filename = 'simulation_data_with_CI.csv'
    df.to_csv(csv_filename, index=False, sep=';', decimal=',')
    
    print(f"✅ Tabella salvata: {csv_filename}")
    print("   Nota: La colonna '_CI' indica il margine di errore (+/-)")

def plot_with_ci(stats_data):
    uniform_data = {k: v for k, v in stats_data.items() if k[0] == 'Uniform'}
    lognormal_data = {k: v for k, v in stats_data.items() if k[0] == 'Lognormal'}
    N_values = sorted(list(set(k[1] for k in stats_data.keys())))
    p_values = sorted(list(set(k[2] for k in stats_data.keys())))
    
    if not N_values: return

    fig = plt.figure(figsize=(24, 12))
    fig.suptitle(f'Analisi con Intervalli di Confidenza (95%)', fontsize=18)
    
    # Helper per estrarre vettori ordinati
    def get_vectors(dataset, dist_name, p_val, metric_mean, metric_ci):
        x, y, ci = [], [], []
        for n in N_values:
            if (dist_name, n, p_val) in dataset:
                data = dataset[(dist_name, n, p_val)]
                x.append(n)
                y.append(data[metric_mean])
                ci.append(data[metric_ci])
        return np.array(x), np.array(y), np.array(ci)

    # 1. Throughput Uniform
    ax1 = plt.subplot(2, 4, 1)
    for p in p_values:
        x, y, ci = get_vectors(uniform_data, 'Uniform', p, 'tp_mean', 'tp_ci')
        if len(x) > 0:
            ax1.plot(x, y, marker='o', label=f'p={p}')
            ax1.fill_between(x, y-ci, y+ci, alpha=0.2) # Area ombreggiata
    ax1.set_title('Throughput Uniform (con CI)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. Throughput Lognormal
    ax2 = plt.subplot(2, 4, 2)
    for p in p_values:
        x, y, ci = get_vectors(lognormal_data, 'Lognormal', p, 'tp_mean', 'tp_ci')
        if len(x) > 0:
            ax2.plot(x, y, marker='s', label=f'p={p}')
            ax2.fill_between(x, y-ci, y+ci, alpha=0.2)
    ax2.set_title('Throughput Lognormal (con CI)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 5. Wait Time Lognormal (Critico)
    ax5 = plt.subplot(2, 4, 5)
    for p in p_values:
        x, y, ci = get_vectors(lognormal_data, 'Lognormal', p, 'wt_mean', 'wt_ci')
        if len(x) > 0:
            ax5.plot(x, y, marker='s', label=f'p={p}')
            ax5.fill_between(x, y-ci, y+ci, alpha=0.2)
    ax5.axhline(y=50, color='r', linestyle=':', label='Timeout')
    ax5.set_title('Wait Time Lognormal (con CI)')
    ax5.grid(True, alpha=0.3)
    ax5.legend()
    
    # 7. Zoom Throughput basso carico (per vedere se si sovrappongono)
    ax7 = plt.subplot(2, 4, 7)
    # Prendiamo p=0.3 a basso carico
    x_u, y_u, ci_u = get_vectors(uniform_data, 'Uniform', 0.3, 'tp_mean', 'tp_ci')
    x_l, y_l, ci_l = get_vectors(lognormal_data, 'Lognormal', 0.3, 'tp_mean', 'tp_ci')
    
    # Limitiamo ai primi 3 punti (es. 100, 500, 1000)
    limit = 3
    if len(x_u) >= limit:
        ax7.errorbar(x_u[:limit], y_u[:limit], yerr=ci_u[:limit], fmt='-o', label='Uniform', capsize=5)
        ax7.errorbar(x_l[:limit], y_l[:limit], yerr=ci_l[:limit], fmt='-s', label='Lognormal', capsize=5)
    
    ax7.set_title('Zoom Basso Carico (Error Bars)')
    ax7.set_xlabel('N Utenti')
    ax7.legend()
    ax7.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('simulation_results_CI.png', dpi=300)
    print("✅ Grafico salvato: simulation_results_CI.png")

def main():
    print("Caricamento risultati...")
    results = load_all_results()
    
    if not results:
        print("Nessun risultato trovato!")
        return

    # Calcola statistiche avanzate
    processed_stats = process_stats_with_ci(results)
    
    # Export e Plot
    export_tables(processed_stats)
    plot_with_ci(processed_stats)

if __name__ == '__main__':
    main()