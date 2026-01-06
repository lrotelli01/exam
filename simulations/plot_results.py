#!/usr/bin/env python3
"""
Genera grafici E TABELLE DATI (Formato Excel Italia Compatibile)
"""

import os
import re
from collections import defaultdict
import statistics
import pandas as pd
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

def parse_sca_file(filepath):
    data = {'config': {}, 'users': [], 'tables': []}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            # Legge configurazione
            if line.startswith('itervar'):
                parts = line.split()
                if len(parts) >= 3: data['config'][parts[1]] = parts[2]
            
            # Legge statistiche user
            if line.startswith('scalar DatabaseNetwork.user['):
                match = re.search(r'user\[(\d+)\]\s+(\w+)\s+([\d.]+)', line)
                if match:
                    user_id = int(match.group(1))
                    stat = match.group(2)
                    val = float(match.group(3))
                    if len(data['users']) <= user_id: data['users'].extend([{} for _ in range(user_id - len(data['users']) + 1)])
                    data['users'][user_id][stat] = val
                    
            # Legge statistiche table
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
            
            results[(dist, N, p)].append(aggregate_statistics(data))
        except Exception as e:
            print(f"❌ Errore file {filename}: {e}")
            continue
    return results

def export_tables(means):
    """Genera e salva le tabelle dei dati in formato ITALIANO"""
    print("\n" + "="*50)
    print("GENERAZIONE TABELLE DATI")
    print("="*50)
    
    data_list = []
    
    for key, val in means.items():
        dist, N, p = key
        row = {
            'Distribuzione': dist,
            'N_Utenti': N,
            'Prob_Read (p)': p,
            'Throughput (req/s)': round(val['system_throughput'], 2),
            'Wait_Time (s)': round(val['avg_wait_time'], 4),
            'Utilization (%)': round(val['avg_table_utilization'] * 100, 2)
        }
        data_list.append(row)
    
    if not data_list:
        print("❌ Nessun dato da tabellare.")
        return

    df = pd.DataFrame(data_list)
    df = df.sort_values(by=['Distribuzione', 'Prob_Read (p)', 'N_Utenti'])
    
    # --- SALVATAGGIO CSV FORMATO ITALIA ---
    csv_filename = 'simulation_data_table.csv'
    
    # sep=';' -> Colonne divise da punto e virgola
    # decimal=',' -> Decimali con la virgola (es. 12,5 invece di 12.5)
    df.to_csv(csv_filename, index=False, sep=';', decimal=',')
    
    print(f"✅ Tabella salvata in: {csv_filename}")
    print("   (Formato: Separatore ';', Decimale ',') -> Pronto per Excel Italiano")
    
    # Stampa a video (lasciamo il punto per leggibilità terminale)
    print("\n--- ANTEPRIMA DATI (Terminal usa punto, CSV usa virgola) ---")
    print(df.head(10).to_string(index=False)) 
    print("... (vedi CSV per lista completa)")

def plot_results(means):
    uniform_data = {k: v for k, v in means.items() if k[0] == 'Uniform'}
    lognormal_data = {k: v for k, v in means.items() if k[0] == 'Lognormal'}
    N_values = sorted(list(set(k[1] for k in means.keys())))
    p_values = sorted(list(set(k[2] for k in means.keys())))
    
    if not N_values: return

    fig = plt.figure(figsize=(24, 12))
    fig.suptitle(f'Analisi Database - N Max: {max(N_values)}', fontsize=18)
    
    def get_y(data, dist, p, metric):
        res = []
        for n in N_values:
            val = data.get((dist, n, p), {}).get(metric, None)
            res.append(val)
        return res

    # 1. Throughput Uniform
    ax1 = plt.subplot(2, 4, 1)
    for p in p_values:
        y = get_y(uniform_data, 'Uniform', p, 'system_throughput')
        clean = [(n, v) for n, v in zip(N_values, y) if v is not None]
        if clean: ax1.plot([x[0] for x in clean], [x[1] for x in clean], marker='o', label=f'p={p}')
    ax1.set_title('Throughput Uniform')
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # 2. Throughput Lognormal
    ax2 = plt.subplot(2, 4, 2)
    for p in p_values:
        y = get_y(lognormal_data, 'Lognormal', p, 'system_throughput')
        clean = [(n, v) for n, v in zip(N_values, y) if v is not None]
        if clean: ax2.plot([x[0] for x in clean], [x[1] for x in clean], marker='s', label=f'p={p}')
    ax2.set_title('Throughput Lognormal')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # 5. Wait Time Lognormal
    ax5 = plt.subplot(2, 4, 5)
    for p in p_values:
        y = get_y(lognormal_data, 'Lognormal', p, 'avg_wait_time')
        clean = [(n, v) for n, v in zip(N_values, y) if v is not None]
        if clean: ax5.plot([x[0] for x in clean], [x[1] for x in clean], marker='s', label=f'p={p}')
    ax5.axhline(y=50, color='r', linestyle=':', label='Timeout')
    ax5.set_title('Wait Time Lognormal')
    ax5.grid(True, alpha=0.3)
    ax5.legend()
    
    # (Mettiamo qui solo i grafici essenziali richiesti per brevità script, 
    # ma puoi incollare il blocco completo dei grafici precedente se vuoi tutti gli 8 pannelli)
    
    plt.tight_layout()
    plt.savefig('simulation_results_tables.png', dpi=300)
    print("✅ Grafico salvato: simulation_results_tables.png")

def main():
    print("Caricamento risultati...")
    results = load_all_results()
    
    if not results:
        print("Nessun risultato trovato!")
        return

    means = {}
    for k, v in results.items():
        means[k] = {
            'system_throughput': statistics.mean([x['system_throughput'] for x in v]),
            'avg_wait_time': statistics.mean([x['avg_wait_time'] for x in v]),
            'avg_table_utilization': statistics.mean([x['avg_table_utilization'] for x in v]),
        }
    
    export_tables(means)
    plot_results(means)

if __name__ == '__main__':
    main()