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
        'system_throughput': sum(table_throughputs) if table_throughputs else 0,  # CORRETTO: usa throughput tabelle
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
    
    # Crea figura con 8 subplot (2 righe x 4 colonne)
    fig = plt.figure(figsize=(24, 12))
    
    # --- GRAFICO 1: Throughput vs N (diverse p) - Uniform ---
    ax1 = plt.subplot(2, 4, 1)
    for p in p_values:
        throughputs = [uniform_data.get(('Uniform', N, p), {}).get('throughput', 0) for N in N_values]
        ax1.plot(N_values, throughputs, marker='o', label=f'p={p}', linewidth=2)
    ax1.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax1.set_ylabel('Throughput (req/s)', fontsize=12)
    ax1.set_title('Throughput vs N - Uniform', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # --- GRAFICO 2: Throughput vs N (diverse p) - Lognormal ---
    ax2 = plt.subplot(2, 4, 2)
    for p in p_values:
        throughputs = [lognormal_data.get(('Lognormal', N, p), {}).get('throughput', 0) for N in N_values]
        ax2.plot(N_values, throughputs, marker='s', label=f'p={p}', linewidth=2)
    ax2.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax2.set_ylabel('Throughput (req/s)', fontsize=12)
    ax2.set_title('Throughput vs N - Lognormal', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # --- GRAFICO 3: Confronto Throughput Uniform vs Lognormal ---
    ax3 = plt.subplot(2, 4, 3)
    p_ref = 0.5
    throughputs_u = [uniform_data.get(('Uniform', N, p_ref), {}).get('throughput', 0) for N in N_values]
    throughputs_l = [lognormal_data.get(('Lognormal', N, p_ref), {}).get('throughput', 0) for N in N_values]
    
    # Plot con annotazioni della differenza
    line_u = ax3.plot(N_values, throughputs_u, marker='o', label='Uniform', linewidth=2.5, markersize=8)
    line_l = ax3.plot(N_values, throughputs_l, marker='s', label='Lognormal', linewidth=2.5, markersize=8, linestyle='--')
    
    # Aggiungi annotazioni con differenza percentuale
    for i, N in enumerate(N_values):
        if throughputs_u[i] > 0 and throughputs_l[i] > 0:
            diff_pct = ((throughputs_u[i] - throughputs_l[i]) / throughputs_l[i]) * 100
            if abs(diff_pct) > 1:  # Mostra solo se differenza > 1%
                ax3.annotate(f'{diff_pct:+.1f}%', 
                           xy=(N, (throughputs_u[i] + throughputs_l[i])/2),
                           fontsize=8, ha='center', color='red', fontweight='bold')
    
    ax3.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax3.set_ylabel('Throughput (req/s)', fontsize=12)
    ax3.set_title(f'Confronto Throughput (p={p_ref})', fontsize=14, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # --- GRAFICO 4: Wait Time Uniform only ---
    ax4 = plt.subplot(2, 4, 4)
    for p in p_values:
        wait_times = [uniform_data.get(('Uniform', N, p), {}).get('wait_time', 0) for N in N_values]
        ax4.plot(N_values, wait_times, marker='o', label=f'p={p}', linewidth=2)
    ax4.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax4.set_ylabel('Tempo Attesa (s)', fontsize=12)
    ax4.set_title('Wait Time vs N - Uniform', fontsize=14, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # --- GRAFICO 5: Wait Time Lognormal only (con soglia) ---
    ax5 = plt.subplot(2, 4, 5)
    THRESHOLD_S = 50  # 50 secondi soglia
    
    for p in p_values:
        wait_times_l = [lognormal_data.get(('Lognormal', N, p), {}).get('wait_time', 0) for N in N_values]
        wait_l_plot = [min(w, THRESHOLD_S) for w in wait_times_l]
        
        line = ax5.plot(N_values, wait_l_plot, marker='s', label=f'p={p}', linewidth=2, linestyle='--')
        color = line[0].get_color()
        
        # Annota valori sopra soglia
        for i, N in enumerate(N_values):
            if wait_times_l[i] > THRESHOLD_S:
                ax5.text(N, THRESHOLD_S * 0.95, f'{wait_times_l[i]:.0f}↑', ha='center', va='top', fontsize=8, color=color, fontweight='bold')
    
    ax5.axhline(y=THRESHOLD_S, color='red', linestyle=':', linewidth=2, alpha=0.7, label=f'Soglia {THRESHOLD_S}s')
    ax5.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax5.set_ylabel('Tempo Attesa (s)', fontsize=12)
    ax5.set_title('Wait Time vs N - Lognormal (saturazione)', fontsize=14, fontweight='bold')
    ax5.legend(fontsize=9)
    ax5.grid(True, alpha=0.3)
    ax5.set_ylim([0, THRESHOLD_S * 1.05])
    
    # --- GRAFICO 6: Utilization vs N - Entrambe ---
    ax6 = plt.subplot(2, 4, 6)
    p_ref = 0.5
    util_u = [uniform_data.get(('Uniform', N, p_ref), {}).get('utilization', 0) * 100 for N in N_values]
    util_l = [lognormal_data.get(('Lognormal', N, p_ref), {}).get('utilization', 0) * 100 for N in N_values]
    ax6.plot(N_values, util_u, marker='o', label='Uniform', linewidth=2)
    ax6.plot(N_values, util_l, marker='s', label='Lognormal', linewidth=2)
    ax6.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax6.set_ylabel('Utilization (%)', fontsize=12)
    ax5.set_title(f'Utilization Tabelle (p={p_ref})', fontsize=14, fontweight='bold')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    ax6.set_title(f'Utilization Tabelle (p={p_ref})', fontsize=14, fontweight='bold')
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    ax6.set_ylim([0, 105])
    
    # --- GRAFICO 7: Throughput vs p - Uniform ---
    ax7 = plt.subplot(2, 4, 7)
    N_ref = 1000
    throughputs_u = [uniform_data.get(('Uniform', N_ref, p), {}).get('throughput', 0) for p in p_values]
    ax7.plot(p_values, throughputs_u, marker='o', linewidth=2.5, markersize=10, color='blue')
    ax7.set_xlabel('Probabilità Read (p)', fontsize=12)
    ax7.set_ylabel('Throughput (req/s)', fontsize=12)
    ax7.set_title(f'Throughput vs p - Uniform (N={N_ref})', fontsize=14, fontweight='bold')
    ax7.grid(True, alpha=0.3)
    
    # --- GRAFICO 8: Throughput vs p - Lognormal ---
    ax8 = plt.subplot(2, 4, 8)
    throughputs_l = [lognormal_data.get(('Lognormal', N_ref, p), {}).get('throughput', 0) for p in p_values]
    ax8.plot(p_values, throughputs_l, marker='s', linewidth=2.5, markersize=10, color='red', linestyle='--')
    ax8.set_xlabel('Probabilità Read (p)', fontsize=12)
    ax8.set_ylabel('Throughput (req/s)', fontsize=12)
    ax8.set_title(f'Throughput vs p - Lognormal (N={N_ref})', fontsize=14, fontweight='bold')
    ax8.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('simulation_results.png', dpi=300, bbox_inches='tight')
    print("✅ Grafico salvato in: simulation_results.png")
    
    # --- GRAFICO AGGIUNTIVO: Heatmap Throughput ---
    fig2, (ax9, ax10) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Heatmap Uniform
    throughput_matrix_u = np.zeros((len(N_values), len(p_values)))
    for i, N in enumerate(N_values):
        for j, p in enumerate(p_values):
            throughput_matrix_u[i, j] = uniform_data.get(('Uniform', N, p), {}).get('throughput', 0)
    
    im1 = ax9.imshow(throughput_matrix_u, aspect='auto', cmap='YlOrRd', origin='lower')
    ax9.set_xticks(range(len(p_values)))
    ax9.set_xticklabels([f'{p:.1f}' for p in p_values])
    ax9.set_yticks(range(len(N_values)))
    ax9.set_yticklabels(N_values)
    ax9.set_xlabel('Probabilità Read (p)', fontsize=12)
    ax9.set_ylabel('Numero Utenti (N)', fontsize=12)
    ax9.set_title('Throughput Heatmap - Uniform', fontsize=14, fontweight='bold')
    
    # Aggiungi valori nella heatmap
    for i in range(len(N_values)):
        for j in range(len(p_values)):
            ax9.text(j, i, f'{throughput_matrix_u[i, j]:.1f}',
                    ha="center", va="center", color="black", fontsize=9)
    
    plt.colorbar(im1, ax=ax9, label='Throughput (req/s)')
    
    # Heatmap Lognormal
    throughput_matrix_l = np.zeros((len(N_values), len(p_values)))
    for i, N in enumerate(N_values):
        for j, p in enumerate(p_values):
            throughput_matrix_l[i, j] = lognormal_data.get(('Lognormal', N, p), {}).get('throughput', 0)
    
    im2 = ax10.imshow(throughput_matrix_l, aspect='auto', cmap='YlOrRd', origin='lower')
    ax10.set_xticks(range(len(p_values)))
    ax10.set_xticklabels([f'{p:.1f}' for p in p_values])
    ax10.set_yticks(range(len(N_values)))
    ax10.set_yticklabels(N_values)
    ax10.set_xlabel('Probabilità Read (p)', fontsize=12)
    ax10.set_ylabel('Numero Utenti (N)', fontsize=12)
    ax10.set_title('Throughput Heatmap - Lognormal', fontsize=14, fontweight='bold')
    
    # Aggiungi valori nella heatmap
    for i in range(len(N_values)):
        for j in range(len(p_values)):
            ax10.text(j, i, f'{throughput_matrix_l[i, j]:.1f}',
                    ha="center", va="center", color="black", fontsize=9)
    
    plt.colorbar(im2, ax=ax10, label='Throughput (req/s)')
    
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
