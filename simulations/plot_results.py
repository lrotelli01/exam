#!/usr/bin/env python3
"""
Analisi Completa con SCALABILITÀ RISORSE (Confronto M=5, 10, 20)
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
    """Parsing che rileva automaticamente anche il numero di tabelle (M)"""
    data = {'config': {}, 'users': [], 'tables': []}
    
    # Set per contare le tabelle uniche trovate
    found_table_ids = set()
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('itervar'):
                parts = line.split()
                if len(parts) >= 3: data['config'][parts[1]] = parts[2]
            
            # User Stats
            if line.startswith('scalar DatabaseNetwork.user['):
                match = re.search(r'user\[(\d+)\]\s+(\w+)\s+([\d.]+)', line)
                if match:
                    user_id = int(match.group(1))
                    stat = match.group(2)
                    val = float(match.group(3))
                    if len(data['users']) <= user_id: data['users'].extend([{} for _ in range(user_id - len(data['users']) + 1)])
                    data['users'][user_id][stat] = val
            
            # Table Stats
            if line.startswith('scalar DatabaseNetwork.table['):
                match = re.search(r'table\[(\d+)\]\s+([\w.]+)\s+([\d.eE+-]+)', line)
                if match:
                    table_id = int(match.group(1))
                    found_table_ids.add(table_id) # Tracciamo l'ID
                    stat = match.group(2)
                    val = float(match.group(3))
                    if len(data['tables']) <= table_id: data['tables'].extend([{} for _ in range(table_id - len(data['tables']) + 1)])
                    data['tables'][table_id][stat] = val
    
    # Calcola M basandosi sugli indici trovati (es. 0..19 -> M=20)
    data['detected_M'] = len(found_table_ids)
    return data

def aggregate_statistics(data):
    wait_times = [u.get('averageWaitTime', 0) for u in data['users']]
    total_reads = sum(u.get('totalReads', 0) for u in data['users'])
    total_writes = sum(u.get('totalWrites', 0) for u in data['users'])
    total_ops = total_reads + total_writes
    read_pct = (total_reads / total_ops * 100) if total_ops > 0 else 0

    table_throughputs = [t.get('table.throughput', 0) for t in data['tables']]
    table_utils = [t.get('table.utilization', 0) for t in data['tables']]
    table_queues = [t.get('table.avgQueueLength', 0) for t in data['tables']]
    table_max_queues = [t.get('table.maxQueueLength', 0) for t in data['tables']]

    return {
        'system_throughput': sum(table_throughputs),
        'avg_wait_time': statistics.mean(wait_times) if wait_times else 0,
        'avg_table_utilization': statistics.mean(table_utils) if table_utils else 0,
        'max_table_utilization': max(table_utils) if table_utils else 0,
        'avg_queue_len': statistics.mean(table_queues) if table_queues else 0,
        'max_queue_len': max(table_max_queues) if table_max_queues else 0,
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
            
            # Parametri chiave
            N = int(data['config'].get('N', 0))
            p = float(data['config'].get('p', 0))
            M = int(data.get('detected_M', 0)) # M rilevato automaticamente
            
            if N == 0 or M == 0: continue
            
            # Chiave include M ora!
            results[(dist, M, N, p)].append(aggregate_statistics(data))
        except Exception as e:
            print(f"❌ Errore file {filename}: {e}")
            continue
    return results

def calculate_ci(values, confidence=0.95):
    n = len(values)
    if n <= 1: return statistics.mean(values) if values else 0, 0
    mean = statistics.mean(values)
    std_err = statistics.stdev(values) / math.sqrt(n)
    h = std_err * stats.t.ppf((1 + confidence) / 2, n - 1)
    return mean, h

def process_stats(results):
    processed = {}
    for key, runs in results.items():
        tps = [r['system_throughput'] for r in runs]
        waits = [r['avg_wait_time'] for r in runs]
        avg_utils = [r['avg_table_utilization'] for r in runs]
        max_utils = [r['max_table_utilization'] for r in runs]
        queues = [r['avg_queue_len'] for r in runs]
        max_queues = [r['max_queue_len'] for r in runs]
        read_pcts = [r['read_pct'] for r in runs]

        processed[key] = {
            'tp_mean': statistics.mean(tps), 'tp_ci': calculate_ci(tps)[1],
            'wt_mean': statistics.mean(waits), 'wt_ci': calculate_ci(waits)[1],
            'ut_mean': statistics.mean(avg_utils), 
            'ut_max_mean': statistics.mean(max_utils),
            'q_mean': statistics.mean(queues),
            'q_max_mean': statistics.mean(max_queues),
            'read_pct': statistics.mean(read_pcts),
            'runs': len(runs)
        }
    return processed

def export_tables(stats_data):
    print("\n" + "="*50)
    print("GENERAZIONE DATI (Include M)")
    print("="*50)
    data_list = []
    for key, val in stats_data.items():
        dist, M, N, p = key
        data_list.append({
            'Distribuzione': dist, 'M_Tabelle': M, 'N_Utenti': N, 'p': p,
            'Runs': val['runs'],
            'Throughput': round(val['tp_mean'], 2),
            'Wait_Time': round(val['wt_mean'], 4),
            'Avg_Util_%': round(val['ut_mean']*100, 2),
            'Max_Util_%': round(val['ut_max_mean']*100, 2),
            'Max_Queue': round(val['q_max_mean'], 0)
        })
    
    if not data_list: return
    df = pd.DataFrame(data_list).sort_values(by=['Distribuzione', 'M_Tabelle', 'p', 'N_Utenti'])
    df.to_csv('simulation_data_scalability.csv', index=False, sep=';', decimal=',')
    print("✅ Tabella salvata: simulation_data_scalability.csv")

def plot_scalability(stats_data):
    """Genera grafici specifici per il confronto tra diversi M"""
    
    # Estrai i valori unici di M, N, p presenti
    M_values = sorted(list(set(k[1] for k in stats_data.keys())))
    N_values = sorted(list(set(k[2] for k in stats_data.keys())))
    p_values = sorted(list(set(k[3] for k in stats_data.keys())))
    
    if not M_values: return
    print(f"📊 Generazione grafici scalabilità per M = {M_values}")

    fig = plt.figure(figsize=(24, 12))
    fig.suptitle(f'Analisi Scalabilità Risorse (M={M_values})', fontsize=18)

    # Helper function
    def get_curve(dist, m_val, p_val, metric):
        x, y = [], []
        for n in N_values:
            if (dist, m_val, n, p_val) in stats_data:
                x.append(n)
                y.append(stats_data[(dist, m_val, n, p_val)][metric])
        return x, y

    # 1. Throughput Uniform (Confronto M) - p=0.3
    ax1 = plt.subplot(2, 3, 1)
    p_target = 0.3
    for m in M_values:
        x, y = get_curve('Uniform', m, p_target, 'tp_mean')
        if x: ax1.plot(x, y, marker='o', label=f'M={m}', linewidth=2)
    ax1.set_title(f'Throughput Uniform (p={p_target})')
    ax1.set_ylabel('Req/s')
    ax1.set_xlabel('N Utenti')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. Throughput Lognormal (Confronto M) - p=0.3
    ax2 = plt.subplot(2, 3, 2)
    for m in M_values:
        x, y = get_curve('Lognormal', m, p_target, 'tp_mean')
        if x: ax2.plot(x, y, marker='s', label=f'M={m}', linewidth=2)
    ax2.set_title(f'Throughput Lognormal (p={p_target})')
    ax2.set_xlabel('N Utenti')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. Wait Time Lognormal (Confronto M) - p=0.3
    ax3 = plt.subplot(2, 3, 3)
    for m in M_values:
        x, y = get_curve('Lognormal', m, p_target, 'wt_mean')
        if x: ax3.plot(x, y, marker='s', label=f'M={m}', linewidth=2)
    ax3.axhline(y=50, color='r', linestyle=':', label='Timeout')
    ax3.set_title(f'Wait Time Lognormal (p={p_target})')
    ax3.set_ylabel('Secondi')
    ax3.set_xlabel('N Utenti')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. Max Queue Length (Confronto M)
    ax4 = plt.subplot(2, 3, 4)
    for m in M_values:
        x, y = get_curve('Lognormal', m, p_target, 'q_max_mean')
        if x: ax4.plot(x, y, marker='x', label=f'M={m}')
    ax4.set_title(f'Max Queue Length Lognormal (p={p_target})')
    ax4.set_ylabel('Lunghezza Coda')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 5. Throughput per M (Efficiency Check a N=2500)
    # Mostra quanto aumenta il TP all'aumentare di M fissando N
    ax5 = plt.subplot(2, 3, 5)
    n_fixed = 2500 if 2500 in N_values else (max(N_values) if N_values else 0)
    
    tp_u, tp_l = [], []
    valid_ms = []
    for m in M_values:
        val_u = stats_data.get(('Uniform', m, n_fixed, p_target), {}).get('tp_mean', None)
        val_l = stats_data.get(('Lognormal', m, n_fixed, p_target), {}).get('tp_mean', None)
        if val_u is not None:
            tp_u.append(val_u)
            tp_l.append(val_l if val_l else 0)
            valid_ms.append(m)
            
    if valid_ms:
        ax5.plot(valid_ms, tp_u, marker='o', label='Uniform', color='blue')
        ax5.plot(valid_ms, tp_l, marker='s', label='Lognormal', color='orange')
        
    ax5.set_title(f'Efficienza Scalabilità (N={n_fixed}, p={p_target})')
    ax5.set_xlabel('Numero Tabelle (M)')
    ax5.set_ylabel('Throughput')
    ax5.legend()
    ax5.grid(True)

    # 6. Confronto Letture (p=0.8)
    ax6 = plt.subplot(2, 3, 6)
    p_high = 0.8
    for m in M_values:
        x, y = get_curve('Lognormal', m, p_high, 'wt_mean')
        if x: ax6.plot(x, y, marker='^', label=f'M={m}')
    ax6.set_title(f'Wait Time Lognormal (p={p_high})')
    ax6.legend()
    ax6.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('simulation_scalability_analysis.png', dpi=300)
    print("✅ Grafico salvato: simulation_scalability_analysis.png")

def main():
    print("Caricamento risultati (Auto-detect M)...")
    results = load_all_results()
    if not results: return

    processed = process_stats(results)
    
    # Stampa M rilevati
    ms = set(k[1] for k in processed.keys())
    print(f"🔹 Configurazioni M rilevate: {sorted(list(ms))}")
    
    # CSV
    export_tables(processed)
    
    # Plot Scalabilità
    plot_scalability(processed)

if __name__ == '__main__':
    main()