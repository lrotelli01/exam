#!/usr/bin/env python3
"""
Genera grafici AVANZATI, CSV e Report Testuale (Fusione Plot + Analyze)
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
from scipy import stats

def parse_sca_file(filepath):
    """Parsing esteso per catturare code e statistiche dettagliate"""
    data = {'config': {}, 'users': [], 'tables': []}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('itervar'):
                parts = line.split()
                if len(parts) >= 3: data['config'][parts[1]] = parts[2]
            
            # User Stats (Wait Time, Reads, Writes)
            if line.startswith('scalar DatabaseNetwork.user['):
                match = re.search(r'user\[(\d+)\]\s+(\w+)\s+([\d.]+)', line)
                if match:
                    user_id = int(match.group(1))
                    stat = match.group(2)
                    val = float(match.group(3))
                    if len(data['users']) <= user_id: data['users'].extend([{} for _ in range(user_id - len(data['users']) + 1)])
                    data['users'][user_id][stat] = val
            
            # Table Stats (Throughput, Util, Queue)
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
    """Aggregazione estesa con metriche di Analyze"""
    # User Metrics
    wait_times = [u.get('averageWaitTime', 0) for u in data['users']]
    total_reads = sum(u.get('totalReads', 0) for u in data['users'])
    total_writes = sum(u.get('totalWrites', 0) for u in data['users'])
    total_ops = total_reads + total_writes
    read_pct = (total_reads / total_ops * 100) if total_ops > 0 else 0

    # Table Metrics
    table_throughputs = [t.get('table.throughput', 0) for t in data['tables']]
    table_utils = [t.get('table.utilization', 0) for t in data['tables']]
    table_queues = [t.get('table.avgQueueLength', 0) for t in data['tables']]
    table_max_queues = [t.get('table.maxQueueLength', 0) for t in data['tables']]

    return {
        'system_throughput': sum(table_throughputs),
        'avg_wait_time': statistics.mean(wait_times) if wait_times else 0,
        
        # Utilization
        'avg_table_utilization': statistics.mean(table_utils) if table_utils else 0,
        'max_table_utilization': max(table_utils) if table_utils else 0, # Hotspot detection
        
        # Queues
        'avg_queue_len': statistics.mean(table_queues) if table_queues else 0,
        'max_queue_len': max(table_max_queues) if table_max_queues else 0, # Bottleneck detection
        
        # Verification
        'read_pct': read_pct
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
            
            results[(dist, N, p)].append(aggregate_statistics(data))
        except Exception as e:
            print(f"❌ Errore file {filename}: {e}")
            continue
    return results

def calculate_ci(values, confidence=0.95):
    """Helper per Intervallo di Confidenza"""
    n = len(values)
    if n <= 1: return statistics.mean(values) if values else 0, 0
    mean = statistics.mean(values)
    std_err = statistics.stdev(values) / math.sqrt(n)
    h = std_err * stats.t.ppf((1 + confidence) / 2, n - 1)
    return mean, h

def process_stats(results):
    processed = {}
    for key, runs in results.items():
        # Estrai vettori
        tps = [r['system_throughput'] for r in runs]
        waits = [r['avg_wait_time'] for r in runs]
        avg_utils = [r['avg_table_utilization'] for r in runs]
        max_utils = [r['max_table_utilization'] for r in runs]
        queues = [r['avg_queue_len'] for r in runs]
        max_queues = [r['max_queue_len'] for r in runs]
        read_pcts = [r['read_pct'] for r in runs]

        # Calcola Medie e CI
        processed[key] = {
            'tp_mean': statistics.mean(tps), 'tp_ci': calculate_ci(tps)[1],
            'wt_mean': statistics.mean(waits), 'wt_ci': calculate_ci(waits)[1],
            'ut_mean': statistics.mean(avg_utils), 
            'ut_max_mean': statistics.mean(max_utils), # Media dei massimi
            'q_mean': statistics.mean(queues),
            'q_max_mean': statistics.mean(max_queues),
            'read_pct': statistics.mean(read_pcts),
            'runs': len(runs)
        }
    return processed

def export_tables(stats_data):
    print("\n" + "="*50)
    print("GENERAZIONE DATI AVANZATI (CSV)")
    print("="*50)
    data_list = []
    for key, val in stats_data.items():
        dist, N, p = key
        data_list.append({
            'Distribuzione': dist, 'N': N, 'p': p, 'Runs': val['runs'],
            'Throughput': round(val['tp_mean'], 2), '+/-': round(val['tp_ci'], 2),
            'Wait_Time': round(val['wt_mean'], 4),
            'Avg_Util_%': round(val['ut_mean']*100, 2),
            'Max_Util_%': round(val['ut_max_mean']*100, 2), # Hotspot Detection
            'Avg_Queue': round(val['q_mean'], 2),
            'Max_Queue': round(val['q_max_mean'], 0), # Bottleneck Detection
            'Real_Read_%': round(val['read_pct'], 1)
        })
    
    if not data_list: return
    df = pd.DataFrame(data_list).sort_values(by=['Distribuzione', 'p', 'N'])
    df.to_csv('simulation_data_advanced.csv', index=False, sep=';', decimal=',')
    print("✅ Tabella salvata: simulation_data_advanced.csv (Include Code e Max Util)")

def print_text_report(stats_data):
    """Stampa un report stile 'analyze' nel terminale"""
    print("\n" + "="*50)
    print("REPORT ANALISI TESTUALE")
    print("="*50)
    
    # Ordina per stampa
    keys = sorted(stats_data.keys(), key=lambda x: (x[0], x[2], x[1]))
    
    current_dist = ""
    for k in keys:
        dist, N, p = k
        d = stats_data[k]
        
        if dist != current_dist:
            print(f"\n--- {dist.upper()} ---")
            current_dist = dist
            
        print(f"N={N:<4} p={p:<3} | TP: {d['tp_mean']:>6.1f} | Wait: {d['wt_mean']:>7.3f}s | "
              f"Q_Max: {d['q_max_mean']:>4.0f} | Util: {d['ut_mean']*100:>4.1f}% (Max: {d['ut_max_mean']*100:>4.1f}%)")

def plot_advanced(stats_data):
    uniform_data = {k: v for k, v in stats_data.items() if k[0] == 'Uniform'}
    lognormal_data = {k: v for k, v in stats_data.items() if k[0] == 'Lognormal'}
    N_values = sorted(list(set(k[1] for k in stats_data.keys())))
    p_values = sorted(list(set(k[2] for k in stats_data.keys())))
    
    if not N_values: return

    # Helper per vettori
    def get_vec(dataset, dist, p, metric):
        x, y = [], []
        for n in N_values:
            if (dist, n, p) in dataset:
                x.append(n)
                y.append(dataset[(dist, n, p)][metric])
        return x, y

    fig = plt.figure(figsize=(24, 12))
    fig.suptitle(f'Analisi Completa (Performance + Code + Hotspots)', fontsize=18)

    # 1. Throughput Comparison (p=0.5)
    ax1 = plt.subplot(2, 4, 1)
    x_u, y_u = get_vec(uniform_data, 'Uniform', 0.5, 'tp_mean')
    x_l, y_l = get_vec(lognormal_data, 'Lognormal', 0.5, 'tp_mean')
    ax1.plot(x_u, y_u, marker='o', label='Uniform')
    ax1.plot(x_l, y_l, marker='s', label='Lognormal', linestyle='--')
    ax1.set_title('Confronto Throughput (p=0.5)')
    ax1.set_xlabel('N Utenti')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. Wait Time Lognormal (Il crollo)
    ax2 = plt.subplot(2, 4, 2)
    for p in p_values:
        x, y = get_vec(lognormal_data, 'Lognormal', p, 'wt_mean')
        ax2.plot(x, y, marker='s', label=f'p={p}')
    ax2.axhline(y=50, color='r', linestyle=':', label='Timeout')
    ax2.set_title('Wait Time Lognormal (Collasso)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. Queue Length (NUOVO!)
    ax3 = plt.subplot(2, 4, 3)
    for p in p_values:
        # Mostriamo la coda MASSIMA, che è quella che conta per il bottleneck
        x, y = get_vec(lognormal_data, 'Lognormal', p, 'q_max_mean')
        ax3.plot(x, y, marker='s', label=f'Lognormal p={p}')
    ax3.set_title('Max Queue Length (Code Lognormal)')
    ax3.set_ylabel('N Richieste in Coda')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. Hotspot Detection (NUOVO!)
    # Confronta Avg Util vs Max Util per Lognormal p=0.3
    ax4 = plt.subplot(2, 4, 4)
    x_avg, y_avg = get_vec(lognormal_data, 'Lognormal', 0.3, 'ut_mean')
    x_max, y_max = get_vec(lognormal_data, 'Lognormal', 0.3, 'ut_max_mean')
    
    ax4.plot(x_avg, [v*100 for v in y_avg], marker='o', label='Media Sistema', color='green')
    ax4.plot(x_max, [v*100 for v in y_max], marker='x', label='Disco Hotspot (Max)', color='red', linestyle='--')
    
    ax4.set_title('Hotspot Analysis (Lognormal p=0.3)')
    ax4.set_ylabel('Utilization (%)')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim([0, 105])

    # 5-8: Standard Graphs (Throughput per p, etc.)
    # Throughput Uniform
    ax5 = plt.subplot(2, 4, 5)
    for p in p_values:
        x, y = get_vec(uniform_data, 'Uniform', p, 'tp_mean')
        ax5.plot(x, y, marker='o', label=f'p={p}')
    ax5.set_title('Throughput Uniform')
    ax5.grid(True, alpha=0.3)
    
    # Throughput Lognormal
    ax6 = plt.subplot(2, 4, 6)
    for p in p_values:
        x, y = get_vec(lognormal_data, 'Lognormal', p, 'tp_mean')
        ax6.plot(x, y, marker='s', label=f'p={p}')
    ax6.set_title('Throughput Lognormal')
    ax6.grid(True, alpha=0.3)
    
    # Wait Time Uniform
    ax7 = plt.subplot(2, 4, 7)
    for p in p_values:
        x, y = get_vec(uniform_data, 'Uniform', p, 'wt_mean')
        ax7.plot(x, y, marker='o', label=f'p={p}')
    ax7.set_title('Wait Time Uniform')
    ax7.grid(True, alpha=0.3)

    # Utilization Comparison (p=0.5)
    ax8 = plt.subplot(2, 4, 8)
    x_u, y_u = get_vec(uniform_data, 'Uniform', 0.5, 'ut_mean')
    x_l, y_l = get_vec(lognormal_data, 'Lognormal', 0.5, 'ut_mean')
    ax8.plot(x_u, [v*100 for v in y_u], marker='o', label='Uniform')
    ax8.plot(x_l, [v*100 for v in y_l], marker='s', label='Lognormal')
    ax8.set_title('Avg Utilization (p=0.5)')
    ax8.set_ylim([0, 105])
    ax8.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('simulation_results_advanced.png', dpi=300)
    print("✅ Grafico salvato: simulation_results_advanced.png")

def main():
    print("Caricamento risultati...")
    results = load_all_results()
    if not results: return

    processed = process_stats(results)
    
    # 1. Stampa Report Console
    print_text_report(processed)
    
    # 2. Esporta CSV Ricco
    export_tables(processed)
    
    # 3. Genera Grafici Avanzati
    plot_advanced(processed)

if __name__ == '__main__':
    main()