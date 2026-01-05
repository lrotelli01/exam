#!/usr/bin/env python3
"""
Analizza i risultati delle simulazioni OMNeT++
"""

import os
import re
from collections import defaultdict
import statistics

def parse_sca_file(filepath):
    """Legge un file .sca e estrae le statistiche"""
    data = {
        'config': {},
        'users': [],
        'tables': []
    }
    
    with open(filepath, 'r') as f:
        current_user = None
        for line in f:
            line = line.strip()
            
            # Parametri configurazione
            if line.startswith('itervar'):
                parts = line.split()
                if len(parts) >= 3:
                    data['config'][parts[1]] = parts[2]
            
            # Parametri per utente
            if line.startswith('par DatabaseNetwork.user['):
                match = re.search(r'user\[(\d+)\]', line)
                if match:
                    user_id = int(match.group(1))
                    current_user = user_id
                    if len(data['users']) <= user_id:
                        data['users'].extend([{} for _ in range(user_id - len(data['users']) + 1)])
            
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
    """Calcola statistiche aggregate su tutti gli utenti e tabelle"""
    total_accesses = 0
    total_reads = 0
    total_writes = 0
    wait_times = []
    throughputs = []
    
    # Statistiche utenti
    for user in data['users']:
        if 'totalAccesses' in user:
            total_accesses += user.get('totalAccesses', 0)
            total_reads += user.get('totalReads', 0)
            total_writes += user.get('totalWrites', 0)
            if 'averageWaitTime' in user:
                wait_times.append(user['averageWaitTime'])
            if 'accessesPerSecond' in user:
                throughputs.append(user['accessesPerSecond'])
    
    # Statistiche tabelle
    table_throughputs = []
    table_utilizations = []
    table_queue_lengths = []
    table_max_queues = []
    table_wait_times = []
    
    for table in data['tables']:
        if 'table.throughput' in table:
            table_throughputs.append(table['table.throughput'])
        if 'table.utilization' in table:
            table_utilizations.append(table['table.utilization'])
        if 'table.avgQueueLength' in table:
            table_queue_lengths.append(table['table.avgQueueLength'])
        if 'table.maxQueueLength' in table:
            table_max_queues.append(table['table.maxQueueLength'])
        if 'table.avgWaitingTime' in table:
            table_wait_times.append(table['table.avgWaitingTime'])
    
    result = {
        'total_accesses': total_accesses,
        'total_reads': total_reads,
        'total_writes': total_writes,
        'avg_wait_time': statistics.mean(wait_times) if wait_times else 0,
        'std_wait_time': statistics.stdev(wait_times) if len(wait_times) > 1 else 0,
        'throughput_per_user': statistics.mean(throughputs) if throughputs else 0,
        # CORRETTO: usa somma throughput tabelle invece di total_accesses/10000
        'system_throughput': sum(table_throughputs) if table_throughputs else (total_accesses / 10000),
        # Statistiche tabelle
        'avg_table_throughput': statistics.mean(table_throughputs) if table_throughputs else 0,
        'max_table_throughput': max(table_throughputs) if table_throughputs else 0,
        'min_table_throughput': min(table_throughputs) if table_throughputs else 0,
        'avg_table_utilization': statistics.mean(table_utilizations) if table_utilizations else 0,
        'max_table_utilization': max(table_utilizations) if table_utilizations else 0,
        'avg_queue_length': statistics.mean(table_queue_lengths) if table_queue_lengths else 0,
        'max_queue_length': max(table_max_queues) if table_max_queues else 0,
        'table_wait_time': statistics.mean(table_wait_times) if table_wait_times else 0
    }
    
    return result

def main():
    results_dir = 'results'
    
    # Raggruppa i risultati per configurazione
    results = defaultdict(list)
    
    print("Analisi dei risultati delle simulazioni\n")
    print("=" * 80)
    
    for filename in os.listdir(results_dir):
        if filename.endswith('.sca'):
            filepath = os.path.join(results_dir, filename)
            
            try:
                data = parse_sca_file(filepath)
                config_key = f"{data['config'].get('N', '?')}u_p{data['config'].get('p', '?')}"
                
                # Estrai nome configurazione (Uniform o Lognormal)
                if 'Uniform' in filename:
                    dist = 'Uniform'
                elif 'Lognormal' in filename:
                    dist = 'Lognormal'
                else:
                    dist = 'Unknown'
                
                config_full = f"{dist}_{config_key}"
                
                stats = aggregate_statistics(data)
                stats['config'] = data['config']
                results[config_full].append(stats)
                
            except Exception as e:
                print(f"Errore nel processare {filename}: {e}")
    
    # Stampa risultati aggregati
    for config_name in sorted(results.keys()):
        runs = results[config_name]
        
        if not runs:
            continue
        
        # Calcola medie su tutte le ripetizioni
        avg_accesses = statistics.mean([r['total_accesses'] for r in runs])
        avg_reads = statistics.mean([r['total_reads'] for r in runs])
        avg_writes = statistics.mean([r['total_writes'] for r in runs])
        avg_wait = statistics.mean([r['avg_wait_time'] for r in runs])
        avg_throughput = statistics.mean([r['system_throughput'] for r in runs])
        
        std_wait = statistics.stdev([r['avg_wait_time'] for r in runs]) if len(runs) > 1 else 0
        std_throughput = statistics.stdev([r['system_throughput'] for r in runs]) if len(runs) > 1 else 0
        
        # Statistiche tabelle
        avg_table_util = statistics.mean([r['avg_table_utilization'] for r in runs])
        max_table_util = statistics.mean([r['max_table_utilization'] for r in runs])
        avg_queue = statistics.mean([r['avg_queue_length'] for r in runs])
        max_queue = statistics.mean([r['max_queue_length'] for r in runs])
        
        # Estrai parametri
        N = runs[0]['config'].get('N', '?')
        p = runs[0]['config'].get('p', '?')
        
        print(f"\n{config_name}")
        print(f"  N={N} utenti, p={p} (prob. read)")
        print(f"  Ripetizioni: {len(runs)}")
        print(f"  ─────────────────────────────────")
        print(f"  Accessi totali (media): {avg_accesses:.0f}")
        print(f"  Letture: {avg_reads:.0f} ({avg_reads/avg_accesses*100:.1f}%)")
        print(f"  Scritture: {avg_writes:.0f} ({avg_writes/avg_accesses*100:.1f}%)")
        print(f"  Throughput sistema: {avg_throughput:.4f} ± {std_throughput:.4f} req/s")
        print(f"  Tempo attesa medio: {avg_wait*1000:.2f} ± {std_wait*1000:.2f} ms")
        print(f"  Utilization tabelle: {avg_table_util*100:.1f}% (max: {max_table_util*100:.1f}%)")
        print(f"  Lunghezza coda: {avg_queue:.2f} (max: {max_queue:.0f})")
    
    print("\n" + "=" * 80)
    print("\nRiepilogo confronto Uniform vs Lognormal:")
    print("─" * 80)
    
    # Confronto per ogni combinazione N,p
    for config_key in sorted(set([k.split('_', 1)[1] for k in results.keys()])):
        uniform_key = f"Uniform_{config_key}"
        lognormal_key = f"Lognormal_{config_key}"
        
        if uniform_key in results and lognormal_key in results:
            u_runs = results[uniform_key]
            l_runs = results[lognormal_key]
            
            u_throughput = statistics.mean([r['system_throughput'] for r in u_runs])
            l_throughput = statistics.mean([r['system_throughput'] for r in l_runs])
            
            u_wait = statistics.mean([r['avg_wait_time'] for r in u_runs])
            l_wait = statistics.mean([r['avg_wait_time'] for r in l_runs])
            
            diff_throughput = ((l_throughput - u_throughput) / u_throughput * 100) if u_throughput > 0 else 0
            diff_wait = ((l_wait - u_wait) / u_wait * 100) if u_wait > 0 else 0
            
            print(f"\n{config_key}:")
            print(f"  Throughput: Uniform={u_throughput:.4f} req/s, Lognormal={l_throughput:.4f} req/s ({diff_throughput:+.1f}%)")
            print(f"  Attesa:     Uniform={u_wait*1000:.2f} ms, Lognormal={l_wait*1000:.2f} ms ({diff_wait:+.1f}%)")

if __name__ == '__main__':
    main()
