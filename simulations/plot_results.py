#!/usr/bin/env python3
"""
Genera grafici per l'analisi dei risultati delle simulazioni
"""

import os
import re
from collections import defaultdict
import statistics
import matplotlib.pyplot as plt
import numpy as np

def parse_sca_file(filepath):
    """Legge un file .sca e estrae le statistiche"""
    data = {
        'config': {},
        'users': [],
        'tables': []
    }
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Parametri configurazione
            if line.startswith('itervar'):
                parts = line.split()
                if len(parts) >= 3:
                    data['config'][parts[1]] = parts[2]
            
            # Statistiche scalari utenti
            if line.startswith('scalar DatabaseNetwork.user['):
                match = re.search(r'user\[(\d+)\]\s+(\w+)\s+([\d.]+)', line)
                if match:
                    user_id = int(match.group(1))
                    stat_name = match.group(2)
                    value = float(match.group(3))
                    
                    if len(data['users']) <= user_id:
                        data['users'].extend([{} for _ in range(user_id - len(data['users']) + 1)])
                    
                    data['users'][user_id][stat_name] = value
            
            # Statistiche scalari tabelle
            if line.startswith('scalar DatabaseNetwork.table['):
                match = re.search(r'table\[(\d+)\]\s+([\w.]+)\s+([\d.eE+-]+)', line)
                if match:
                    table_id = int(match.group(1))
                    stat_name = match.group(2)
                    value = float(match.group(3))
                    
                    if len(data['tables']) <= table_id:
                        data['tables'].extend([{} for _ in range(table_id - len(data['tables']) + 1)])
                    
                    data['tables'][table_id][stat_name] = value
    
    return data

def aggregate_statistics(data):
    """Calcola statistiche aggregate"""
    total_accesses = sum(user.get('totalAccesses', 0) for user in data['users'])
    total_reads = sum(user.get('totalReads', 0) for user in data['users'])
    total_writes = sum(user.get('totalWrites', 0) for user in data['users'])
    
    wait_times = [user['averageWaitTime'] for user in data['users'] if 'averageWaitTime' in user]
    
    table_throughputs = [table['table.throughput'] for table in data['tables'] if 'table.throughput' in table]
    table_utilizations = [table['table.utilization'] for table in data['tables'] if 'table.utilization' in table]
    
    return {
        'total_accesses': total_accesses,
        'total_reads': total_reads,
        'total_writes': total_writes,
        'avg_wait_time': statistics.mean(wait_times) if wait_times else 0,
        'system_throughput': total_accesses / 10000 if total_accesses > 0 else 0,
        'avg_table_utilization': statistics.mean(table_utilizations) if table_utilizations else 0,
        'max_table_throughput': max(table_throughputs) if table_throughputs else 0,
    }

def load_all_results():
    """Carica tutti i risultati"""
    results_dir = 'results'
    results = defaultdict(list)
    
    for filename in os.listdir(results_dir):
        if filename.endswith('.sca'):
            filepath = os.path.join(results_dir, filename)
            
            try:
                data = parse_sca_file(filepath)
                
                # Estrai nome configurazione
                if 'Uniform' in filename:
                    dist = 'Uniform'
                elif 'Lognormal' in filename:
                    dist = 'Lognormal'
                else:
                    continue
                
                N = data['config'].get('N', '?')
                p = data['config'].get('p', '?')
                
                config_key = (dist, int(N), float(p))
                stats = aggregate_statistics(data)
                results[config_key].append(stats)
                
            except Exception as e:
                print(f"Errore nel processare {filename}: {e}")
    
    return results

def compute_means(results):
    """Calcola medie per ogni configurazione"""
    means = {}
    
    for config_key, runs in results.items():
        means[config_key] = {
            'throughput': statistics.mean([r['system_throughput'] for r in runs]),
            'wait_time': statistics.mean([r['avg_wait_time'] for r in runs]),
            'utilization': statistics.mean([r['avg_table_utilization'] for r in runs]),
            'throughput_std': statistics.stdev([r['system_throughput'] for r in runs]) if len(runs) > 1 else 0,
            'wait_time_std': statistics.stdev([r['avg_wait_time'] for r in runs]) if len(runs) > 1 else 0,
        }
    
    return means

def plot_results(means):
    """Genera grafici"""
    
    # Separa dati per distribuzione
    uniform_data = {k: v for k, v in means.items() if k[0] == 'Uniform'}
    lognormal_data = {k: v for k, v in means.items() if k[0] == 'Lognormal'}
    
    # Valori unici di N e p
    N_values = sorted(set(k[1] for k in means.keys()))
    p_values = sorted(set(k[2] for k in means.keys()))
    
    # Crea figura con 6 subplot (2 righe x 3 colonne)
    fig = plt.figure(figsize=(18, 12))
    
    # --- GRAFICO 1: Throughput vs N (diverse p) - Uniform ---
    ax1 = plt.subplot(2, 3, 1)
    for p in p_values:
        throughputs = [uniform_data.get(('Uniform', N, p), {}).get('throughput', 0) for N in N_values]
        ax1.plot(N_values, throughputs, marker='o', label=f'p={p}', linewidth=2)
    ax1.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax1.set_ylabel('Throughput (req/s)', fontsize=12)
    ax1.set_title('Throughput vs N - Uniform', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # --- GRAFICO 2: Throughput vs N (diverse p) - Lognormal ---
    ax2 = plt.subplot(2, 3, 2)
    for p in p_values:
        throughputs = [lognormal_data.get(('Lognormal', N, p), {}).get('throughput', 0) for N in N_values]
        ax2.plot(N_values, throughputs, marker='s', label=f'p={p}', linewidth=2)
    ax2.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax2.set_ylabel('Throughput (req/s)', fontsize=12)
    ax2.set_title('Throughput vs N - Lognormal', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # --- GRAFICO 3: Confronto Uniform vs Lognormal (p=0.5) ---
    ax3 = plt.subplot(2, 3, 3)
    p_ref = 0.5
    throughputs_u = [uniform_data.get(('Uniform', N, p_ref), {}).get('throughput', 0) for N in N_values]
    throughputs_l = [lognormal_data.get(('Lognormal', N, p_ref), {}).get('throughput', 0) for N in N_values]
    ax3.plot(N_values, throughputs_u, marker='o', label='Uniform', linewidth=2)
    ax3.plot(N_values, throughputs_l, marker='s', label='Lognormal', linewidth=2)
    ax3.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax3.set_ylabel('Throughput (req/s)', fontsize=12)
    ax3.set_title(f'Confronto Throughput (p={p_ref})', fontsize=14, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # --- GRAFICO 4: Tempo Attesa vs N - Uniform ---
    ax4 = plt.subplot(2, 3, 4)
    for p in p_values:
        wait_times = [uniform_data.get(('Uniform', N, p), {}).get('wait_time', 0) * 1000 for N in N_values]
        ax4.plot(N_values, wait_times, marker='o', label=f'p={p}', linewidth=2)
    ax4.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax4.set_ylabel('Tempo Attesa (ms)', fontsize=12)
    ax4.set_title('Tempo Attesa vs N - Uniform', fontsize=14, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # --- GRAFICO 5: Utilization vs N - Entrambe ---
    ax5 = plt.subplot(2, 3, 5)
    p_ref = 0.5
    util_u = [uniform_data.get(('Uniform', N, p_ref), {}).get('utilization', 0) * 100 for N in N_values]
    util_l = [lognormal_data.get(('Lognormal', N, p_ref), {}).get('utilization', 0) * 100 for N in N_values]
    ax5.plot(N_values, util_u, marker='o', label='Uniform', linewidth=2)
    ax5.plot(N_values, util_l, marker='s', label='Lognormal', linewidth=2)
    ax5.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax5.set_ylabel('Utilization (%)', fontsize=12)
    ax5.set_title(f'Utilization Tabelle (p={p_ref})', fontsize=14, fontweight='bold')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    ax5.set_ylim([0, 105])
    
    # --- GRAFICO 6: Throughput vs p (N=100) ---
    ax6 = plt.subplot(2, 3, 6)
    N_ref = 100
    throughputs_u = [uniform_data.get(('Uniform', N_ref, p), {}).get('throughput', 0) for p in p_values]
    throughputs_l = [lognormal_data.get(('Lognormal', N_ref, p), {}).get('throughput', 0) for p in p_values]
    ax6.plot(p_values, throughputs_u, marker='o', label='Uniform', linewidth=2)
    ax6.plot(p_values, throughputs_l, marker='s', label='Lognormal', linewidth=2)
    ax6.set_xlabel('Probabilità Read (p)', fontsize=12)
    ax6.set_ylabel('Throughput (req/s)', fontsize=12)
    ax6.set_title(f'Throughput vs p (N={N_ref})', fontsize=14, fontweight='bold')
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('simulation_results.png', dpi=300, bbox_inches='tight')
    print("✅ Grafico salvato in: simulation_results.png")
    
    # --- GRAFICO AGGIUNTIVO: Heatmap Throughput ---
    fig2, (ax7, ax8) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Heatmap Uniform
    throughput_matrix_u = np.zeros((len(N_values), len(p_values)))
    for i, N in enumerate(N_values):
        for j, p in enumerate(p_values):
            throughput_matrix_u[i, j] = uniform_data.get(('Uniform', N, p), {}).get('throughput', 0)
    
    im1 = ax7.imshow(throughput_matrix_u, aspect='auto', cmap='YlOrRd', origin='lower')
    ax7.set_xticks(range(len(p_values)))
    ax7.set_xticklabels([f'{p:.1f}' for p in p_values])
    ax7.set_yticks(range(len(N_values)))
    ax7.set_yticklabels(N_values)
    ax7.set_xlabel('Probabilità Read (p)', fontsize=12)
    ax7.set_ylabel('Numero Utenti (N)', fontsize=12)
    ax7.set_title('Throughput Heatmap - Uniform', fontsize=14, fontweight='bold')
    
    # Aggiungi valori nella heatmap
    for i in range(len(N_values)):
        for j in range(len(p_values)):
            ax7.text(j, i, f'{throughput_matrix_u[i, j]:.1f}',
                    ha="center", va="center", color="black", fontsize=9)
    
    plt.colorbar(im1, ax=ax7, label='Throughput (req/s)')
    
    # Heatmap Lognormal
    throughput_matrix_l = np.zeros((len(N_values), len(p_values)))
    for i, N in enumerate(N_values):
        for j, p in enumerate(p_values):
            throughput_matrix_l[i, j] = lognormal_data.get(('Lognormal', N, p), {}).get('throughput', 0)
    
    im2 = ax8.imshow(throughput_matrix_l, aspect='auto', cmap='YlOrRd', origin='lower')
    ax8.set_xticks(range(len(p_values)))
    ax8.set_xticklabels([f'{p:.1f}' for p in p_values])
    ax8.set_yticks(range(len(N_values)))
    ax8.set_yticklabels(N_values)
    ax8.set_xlabel('Probabilità Read (p)', fontsize=12)
    ax8.set_ylabel('Numero Utenti (N)', fontsize=12)
    ax8.set_title('Throughput Heatmap - Lognormal', fontsize=14, fontweight='bold')
    
    # Aggiungi valori nella heatmap
    for i in range(len(N_values)):
        for j in range(len(p_values)):
            ax8.text(j, i, f'{throughput_matrix_l[i, j]:.1f}',
                    ha="center", va="center", color="black", fontsize=9)
    
    plt.colorbar(im2, ax=ax8, label='Throughput (req/s)')
    
    plt.tight_layout()
    plt.savefig('throughput_heatmaps.png', dpi=300, bbox_inches='tight')
    print("✅ Heatmap salvata in: throughput_heatmaps.png")

def main():
    print("Caricamento risultati...")
    results = load_all_results()
    print(f"Caricati {len(results)} configurazioni")
    
    print("Calcolo medie...")
    means = compute_means(results)
    
    print("Generazione grafici...")
    plot_results(means)
    
    print("\n✅ Analisi completa!")
    print("📊 Grafici generati:")
    print("   - simulation_results.png (6 grafici principali)")
    print("   - throughput_heatmaps.png (heatmap Uniform e Lognormal)")

if __name__ == '__main__':
    main()
