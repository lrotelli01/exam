#!/usr/bin/env python3
"""
Analisi risultati Consistency Test - Confronto scalabilità utenti
"""

import os
import re
from collections import defaultdict
import statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def parse_consistency_file(filepath):
    """Parse file .sca dal consistency test"""
    data = {'config': {}, 'users': [], 'tables': []}
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Config params
            if line.startswith('config *.numUsers'):
                data['config']['N'] = int(line.split()[-1])
            elif line.startswith('config *.numTables'):
                data['config']['M'] = int(line.split()[-1])
            elif line.startswith('config *.user[*].readProbability'):
                data['config']['p'] = float(line.split()[-1])
            elif line.startswith('config sim-time-limit'):
                # Estrai tempo simulazione (es: "4000s" -> 4000)
                time_str = line.split()[-1]
                data['config']['sim_time'] = float(time_str.rstrip('s'))
            
            # User Stats
            if line.startswith('scalar DatabaseNetwork.user['):
                match = re.search(r'user\[(\d+)\]\s+(\w+)\s+([\d.]+)', line)
                if match:
                    user_id = int(match.group(1))
                    stat = match.group(2)
                    val = float(match.group(3))
                    if len(data['users']) <= user_id:
                        data['users'].extend([{} for _ in range(user_id - len(data['users']) + 1)])
                    data['users'][user_id][stat] = val
            
            # Table Stats
            if line.startswith('scalar DatabaseNetwork.table['):
                match = re.search(r'table\[(\d+)\]\s+([\w.:]+)\s+([\d.eE+-]+)', line)
                if match:
                    table_id = int(match.group(1))
                    stat = match.group(2).replace(':last', '')  # Rimuovi suffisso :last
                    val = float(match.group(3))
                    if len(data['tables']) <= table_id:
                        data['tables'].extend([{} for _ in range(table_id - len(data['tables']) + 1)])
                    data['tables'][table_id][stat] = val
    
    return data

def aggregate_stats(data):
    """Calcola statistiche aggregate"""
    # Wait time dalle statistiche
    wait_times = [u.get('averageWaitTime', 0) for u in data['users']]
    total_accesses = sum(u.get('totalAccesses', 0) for u in data['users'])
    
    # Usa 'throughput' invece di 'table.throughput'
    table_throughputs = [t.get('throughput', 0) for t in data['tables']]
    table_utils = [t.get('table.utilization', 0) for t in data['tables']]
    table_queues = [t.get('table.avgQueueLength', 0) for t in data['tables']]
    max_queues = [t.get('table.maxQueueLength', 0) for t in data['tables']]
    total_served = sum(t.get('table.totalServed', 0) for t in data['tables'])
    
    # Richieste in coda = generate ma non completate
    requests_in_queue = total_accesses - total_served
    
    # Wait time medio delle richieste completate
    avg_wait_completed = statistics.mean(wait_times) if wait_times else 0
    
    # Per le richieste in coda, assumiamo che stiano aspettando da un tempo pari
    # al tempo medio della coda diviso per il throughput (Little's Law inverso)
    # Inoltre aggiungiamo il tempo rimanente della simulazione come penalità
    avg_queue_len = statistics.mean(table_queues) if table_queues else 0
    max_queue_len = max(max_queues) if max_queues else 0
    total_throughput = sum(table_throughputs)
    sim_time = data.get('config', {}).get('sim_time', 4000)
    
    # Stima conservativa: le richieste in coda hanno aspettato almeno
    # il tempo medio necessario per elaborare la coda attuale
    if total_throughput > 0 and requests_in_queue > 0:
        # Tempo per elaborare la coda massima rimanente
        estimated_wait_queued = max_queue_len / total_throughput if total_throughput > 0 else sim_time
        
        # Aggiungiamo anche una penalità per non completamento
        # Le richieste non completate sono peggiori - usiamo almeno la max queue time
        if estimated_wait_queued < avg_wait_completed:
            estimated_wait_queued = avg_wait_completed * 2
        
        # Wait time complessivo pesato:
        # (completate * wait_completate + in_coda * wait_stimato) / totale
        total_wait_time = (total_served * avg_wait_completed + 
                          requests_in_queue * estimated_wait_queued)
        overall_wait = total_wait_time / total_accesses if total_accesses > 0 else avg_wait_completed
    else:
        overall_wait = avg_wait_completed
    
    return {
        'throughput': sum(table_throughputs),
        'wait_time': overall_wait,
        'wait_time_completed': avg_wait_completed,
        'avg_util': statistics.mean(table_utils) if table_utils else 0,
        'max_util': max(table_utils) if table_utils else 0,
        'avg_queue': avg_queue_len,
        'max_queue': max_queue_len,
        'total_accesses': total_accesses,
        'total_served': total_served,
        'requests_in_queue': requests_in_queue
    }

def load_consistency_results():
    """Carica tutti i risultati dal consistency test"""
    results = defaultdict(list)
    result_dir = 'results_consistency'
    
    if not os.path.exists(result_dir):
        print(f"❌ Cartella '{result_dir}' non trovata")
        return results
    
    files = [f for f in os.listdir(result_dir) if f.endswith('.sca')]
    print(f"📂 Trovati {len(files)} file .sca in {result_dir}")
    
    for filename in files:
        try:
            # Estrai N dal nome file (es: Config1000Users--0.sca)
            match = re.search(r'Config(\d+)Users', filename)
            if not match:
                continue
            
            N = int(match.group(1))
            data = parse_consistency_file(os.path.join(result_dir, filename))
            
            # Usa N dal nome file se non trovato nel config
            if 'N' not in data['config'] or data['config']['N'] == 0:
                data['config']['N'] = N
            
            stats = aggregate_stats(data)
            results[N].append(stats)
            
        except Exception as e:
            print(f"⚠ Errore file {filename}: {e}")
            continue
    
    return results

def plot_consistency_analysis(results):
    """Genera grafici per l'analisi di consistenza"""
    if not results:
        print("❌ Nessun dato da plottare")
        return
    
    # Ordina per N
    N_values = sorted(results.keys())
    
    # Calcola medie e deviazioni
    throughputs_mean = []
    throughputs_std = []
    wait_times_mean = []
    wait_times_std = []
    avg_utils_mean = []
    max_utils_mean = []
    max_queues_mean = []
    requests_queued_mean = []
    completion_rate_mean = []
    
    for N in N_values:
        runs = results[N]
        
        tps = [r['throughput'] for r in runs]
        wts = [r['wait_time'] for r in runs]
        avg_ut = [r['avg_util'] for r in runs]
        max_ut = [r['max_util'] for r in runs]
        max_q = [r['max_queue'] for r in runs]
        queued = [r['requests_in_queue'] for r in runs]
        comp_rate = [r['total_served'] / r['total_accesses'] * 100 if r['total_accesses'] > 0 else 0 for r in runs]
        
        throughputs_mean.append(statistics.mean(tps))
        throughputs_std.append(statistics.stdev(tps) if len(tps) > 1 else 0)
        
        wait_times_mean.append(statistics.mean(wts))
        wait_times_std.append(statistics.stdev(wts) if len(wts) > 1 else 0)
        
        avg_utils_mean.append(statistics.mean(avg_ut) * 100)
        max_utils_mean.append(statistics.mean(max_ut) * 100)
        max_queues_mean.append(statistics.mean(max_q))
        requests_queued_mean.append(statistics.mean(queued))
        completion_rate_mean.append(statistics.mean(comp_rate))
    
    # Crea figura con 6 subplot
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle('Consistency Test: Analisi Scalabilità Utenti', fontsize=16, fontweight='bold')
    
    # 1. Throughput vs N
    ax1 = axes[0, 0]
    ax1.errorbar(N_values, throughputs_mean, yerr=throughputs_std, 
                 marker='o', linewidth=2, capsize=5, label='Throughput')
    ax1.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax1.set_ylabel('Throughput (req/s)', fontsize=12)
    ax1.set_title('Throughput Sistema vs Numero Utenti')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # 2. Wait Time vs N
    ax2 = axes[0, 1]
    ax2.errorbar(N_values, wait_times_mean, yerr=wait_times_std,
                 marker='s', linewidth=2, capsize=5, color='orange', label='Wait Time')
    ax2.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax2.set_ylabel('Tempo di Attesa (s)', fontsize=12)
    ax2.set_title('Tempo di Attesa Medio vs Numero Utenti')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # 3. Utilization vs N
    ax3 = axes[0, 2]
    ax3.plot(N_values, avg_utils_mean, marker='o', linewidth=2, label='Avg Utilization')
    ax3.plot(N_values, max_utils_mean, marker='^', linewidth=2, label='Max Utilization')
    ax3.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax3.set_ylabel('Utilizzo (%)', fontsize=12)
    ax3.set_title('Utilizzo Tabelle vs Numero Utenti')
    ax3.axhline(y=100, color='r', linestyle='--', alpha=0.5, label='Saturazione')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # 4. Richieste in Coda
    ax4 = axes[1, 0]
    ax4.plot(N_values, requests_queued_mean, marker='D', linewidth=2, color='red')
    ax4.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax4.set_ylabel('Richieste in Coda (non completate)', fontsize=12)
    ax4.set_title('Richieste Rimaste in Coda a Fine Simulazione')
    ax4.grid(True, alpha=0.3)
    
    # 5. Completion Rate
    ax5 = axes[1, 1]
    ax5.plot(N_values, completion_rate_mean, marker='o', linewidth=2, color='green')
    ax5.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax5.set_ylabel('Completion Rate (%)', fontsize=12)
    ax5.set_title('Percentuale Richieste Completate')
    ax5.axhline(y=100, color='g', linestyle='--', alpha=0.5)
    ax5.grid(True, alpha=0.3)
    ax5.set_ylim([0, 105])
    
    # 6. Max Queue Length
    ax6 = axes[1, 2]
    ax6.plot(N_values, max_queues_mean, marker='x', linewidth=2, color='purple')
    ax6.set_xlabel('Numero Utenti (N)', fontsize=12)
    ax6.set_ylabel('Max Queue Length', fontsize=12)
    ax6.set_title('Lunghezza Massima Coda')
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('consistency_analysis.png', dpi=300, bbox_inches='tight')
    print("✅ Grafico salvato: consistency_analysis.png")
    
    # Stampa statistiche
    print("\n" + "="*90)
    print("STATISTICHE CONSISTENCY TEST")
    print("="*90)
    print(f"{'N Users':<10} {'Throughput':<15} {'Wait Time':<15} {'Avg Util %':<12} {'In Queue':<12} {'Compl %':<10}")
    print("-"*90)
    for i, N in enumerate(N_values):
        print(f"{N:<10} {throughputs_mean[i]:>8.2f} ±{throughputs_std[i]:>4.2f}   "
              f"{wait_times_mean[i]:>8.2f} ±{wait_times_std[i]:>4.2f}   "
              f"{avg_utils_mean[i]:>8.2f}       "
              f"{requests_queued_mean[i]:>8.0f}      "
              f"{completion_rate_mean[i]:>6.2f}")
    print("\n⚠ NOTA: Richieste 'In Queue' = generate ma non completate a fine simulazione")

def main():
    print("Caricamento risultati Consistency Test...")
    results = load_consistency_results()
    
    if not results:
        print("❌ Nessun risultato trovato")
        return
    
    print(f"✓ Caricati dati per {len(results)} configurazioni diverse di N")
    plot_consistency_analysis(results)

if __name__ == '__main__':
    main()
