#!/usr/bin/env python3
"""
Analizza file .vec per identificare warm-up period
Plotta metriche nel tempo per capire la convergenza a steady-state
"""

import os
import re
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import uniform_filter1d

def parse_vec_file(filepath, metric_filter=None):
    """Legge file .vec di OMNeT++ e estrae le serie temporali per una metrica"""
    data = {}
    current_metric = None
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Estrai definizione vettore (es: "vector 0 DatabaseNetwork.user[0] waitTime:vector ETV")
            if line.startswith('vector'):
                parts = line.split()
                if len(parts) >= 4:
                    vector_id = parts[1]
                    metric_name = parts[3].split(':')[0]
                    
                    # Filtra se richiesto
                    if metric_filter is None or metric_filter in metric_name:
                        current_metric = vector_id
                        data[current_metric] = {'metric': metric_name, 'times': [], 'values': []}
            
            # Leggi dati (formato: vectorID sequence time value)
            elif line and not line.startswith(('version', 'run', 'attr', 'itervar', 'config')):
                try:
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        vector_id = parts[0]
                        if vector_id in data:
                            time = float(parts[2])
                            value = float(parts[3])
                            data[vector_id]['times'].append(time)
                            data[vector_id]['values'].append(value)
                except:
                    continue
    
    return data

def extract_config_from_filename(filename):
    """Estrae numero di utenti (N) dal nome del file .vec"""
    # Formato: results_Uniform-$N=1500-$p=0.5-0.vec
    match = re.search(r'\$N=(\d+)', filename)
    if match:
        return f"N={match.group(1)}"
    # Fallback
    return os.path.basename(filename).replace('.vec', '')

def analyze_warmup(vec_files):
    """Analizza file .vec per identificare warm-up"""
    print(f"\n{'='*60}")
    print(f"ANALISI WARM-UP PERIOD")
    print(f"{'='*60}\n")
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Warm-Up Analysis - Metriche nel Tempo', fontsize=16)
    
    metrics_to_plot = {
        'waitTime': axes[0, 0],
        'queueLength': axes[0, 1],
    }
    
    all_data = {}
    file_configs = {}  # Mappa file -> configurazione
    
    for vec_file in vec_files:
        print(f"Leggendo: {os.path.basename(vec_file)}")
        config_label = extract_config_from_filename(os.path.basename(vec_file))
        file_configs[vec_file] = config_label
        
        # Parsa waitTime e queueLength
        for metric in ['waitTime', 'queueLength']:
            data = parse_vec_file(vec_file, metric_filter=metric)
            if data:
                if metric not in all_data:
                    all_data[metric] = []
                
                # Aggregia tutte le misure (da tutti i vettori di questa metrica)
                all_times = []
                all_vals = []
                for vec_id, vec_data in data.items():
                    if vec_data['times'] and vec_data['values']:
                        all_times.extend(vec_data['times'])
                        all_vals.extend(vec_data['values'])
                
                if all_times and all_vals:
                    all_data[metric].append((np.array(all_times), np.array(all_vals), config_label))
    
    # Plotta i dati
    for metric, ax in metrics_to_plot.items():
        if metric in all_data and all_data[metric]:
            # Plotta media mobile per ogni serie
            for times, vals, config_label in all_data[metric]:
                if len(vals) > 10:
                    # Ordina per tempo
                    idx = np.argsort(times)
                    times_sorted = times[idx]
                    vals_sorted = vals[idx]
                    
                    # Media mobile
                    window = max(1, len(vals_sorted) // 100)
                    smoothed = uniform_filter1d(vals_sorted, size=window, mode='nearest')
                    
                    ax.plot(times_sorted, smoothed, alpha=0.7, linewidth=1.5, label=config_label)
            
            ax.set_xlabel('Simulation Time (s)', fontsize=10)
            ax.set_ylabel(metric, fontsize=10)
            ax.set_title(f'{metric} Over Time', fontsize=12)
            ax.grid(True, alpha=0.3)
            
            # Aggiungi linea warm-up stimato
            ax.axvline(x=500, color='red', linestyle='--', label='Warm-up (500s)', linewidth=2)
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, fontsize=9, frameon=True)
    
    # Pulisci assi vuoti
    axes[1, 0].axis('off')
    axes[1, 1].axis('off')
    
    plt.tight_layout()
    plt.savefig('warmup_analysis.png', dpi=150)
    print("\n✓ Grafico salvato: warmup_analysis.png")
    
    # Analizza convergenza
    print(f"\n{'='*60}")
    print("CONVERGENCE ANALYSIS")
    print(f"{'='*60}\n")
    
    for metric in all_data.keys():
        print(f"\n{metric.upper()}:")
        
        if all_data[metric]:
            for times, vals, config_label in all_data[metric]:
                if len(vals) > 100:
                    # Ordina per tempo
                    idx = np.argsort(times)
                    vals_sorted = vals[idx]
                    
                    # Dividi in 3 parti
                    third = len(vals_sorted) // 3
                    early = np.mean(vals_sorted[:third])
                    middle = np.mean(vals_sorted[third:2*third])
                    late = np.mean(vals_sorted[2*third:])
                    
                    variation = abs(late - early) / (abs(early) + 1e-6) * 100
                    
                    print(f"  {config_label}:")
                    print(f"    Early (0-33%):   {early:.6f}")
                    print(f"    Middle (33-66%): {middle:.6f}")
                    print(f"    Late (66-100%):  {late:.6f}")
                    print(f"    Variation: {variation:.2f}%")
                    
                    if variation < 10:
                        print(f"    → ✓ Sistema CONVERGE")
                    elif variation < 20:
                        print(f"    → ⚠ Convergenza parziale")
                    else:
                        print(f"    → ✗ Sistema NON converge")

def main():
    """Main function"""
    results_dir = 'results'
    
    if not os.path.exists(results_dir):
        print(f"Errore: cartella '{results_dir}' non trovata")
        return
    
    # Cerca tutti i file .vec
    all_vec_files = sorted(glob.glob(os.path.join(results_dir, '*.vec')))
    
    if not all_vec_files:
        print(f"Nessun file .vec trovato in {results_dir}")
        return
    
    # Filtra solo file con N alto (1500, 2000, 2500) per testare carichi pesanti
    heavy_load_files = [f for f in all_vec_files if any(n in f for n in ['$N=1500', '$N=2000', '$N=2500'])]
    
    if not heavy_load_files:
        print("Nessun file con carichi pesanti (N>=1500) trovato. Usando i primi 3 file disponibili...")
        vec_files = all_vec_files[:3]
    else:
        # Prendi primo file per ogni carico pesante
        vec_files = [f for f in heavy_load_files if '$N=1500' in f][:1] + \
                    [f for f in heavy_load_files if '$N=2000' in f][:1] + \
                    [f for f in heavy_load_files if '$N=2500' in f][:1]
    
    print(f"Analizzando {len(vec_files)} file .vec con carichi pesanti:")
    for vf in vec_files:
        print(f"  - {os.path.basename(vf)}")
    
    analyze_warmup(vec_files)
    
    print(f"\n{'='*60}")
    print("RACCOMANDAZIONI")
    print(f"{'='*60}")
    print("""
1. Se la variazione è < 10% dopo 500s → warm-up di 500s è OK
2. Se la variazione è > 20% → aumenta simulation time
3. Se i grafici sono instabili → riduci parametri (meno utenti/tabelle)
4. Una volta individuato warm-up, pulisci results/ e rilancia con:
   - warmup-period = [warm-up identificato]
   - sim-time-limit = [tempo stabilizzato]
   - repeat = 10-30 per intervalli di confidenza
    """)

if __name__ == '__main__':
    main()
