#!/usr/bin/env python3
"""
Analizza file .vec e plotta waitTime nel tempo.
Taglia automaticamente l'ultima parte della simulazione (98%) per evitare artefatti di terminazione.

MODIFICHE:
- Solo 1 plot (waitTime)
- Niente max_time
- Niente warmup_time
- Taglio finale al 98% (END_CUTOFF)
"""

import os
import re
import glob
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import uniform_filter1d


END_CUTOFF = 0.98          # usa solo fino al 98% del tempo (taglia l'ultimo 2%)
OUTPUT_PNG = "waittime_98pct.png"


def parse_vec_file(filepath, metric_filter=None):
    """Legge file .vec di OMNeT++ e estrae le serie temporali per una metrica"""
    data = {}

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()

            # Definizione vettore: "vector <id> <module> <metric>:vector ..."
            if line.startswith("vector"):
                parts = line.split()
                if len(parts) >= 4:
                    vector_id = parts[1]
                    metric_name = parts[3].split(":")[0]

                    if metric_filter is None or metric_filter in metric_name:
                        data[vector_id] = {"metric": metric_name, "times": [], "values": []}

            # Dati: vectorID \t seq \t time \t value
            elif line and not line.startswith(("version", "run", "attr", "itervar", "config")):
                try:
                    parts = line.split("\t")
                    if len(parts) >= 4:
                        vector_id = parts[0]
                        if vector_id in data:
                            time = float(parts[2])
                            value = float(parts[3])
                            data[vector_id]["times"].append(time)
                            data[vector_id]["values"].append(value)
                except Exception:
                    continue

    return data


def extract_config_from_filename(filename):
    """Estrae numero di utenti (N) dal nome del file .vec"""
    match = re.search(r"\$N=(\d+)", filename)
    if match:
        return f"N={match.group(1)}"
    return os.path.basename(filename).replace(".vec", "")


def analyze_and_plot(vec_files):
    print(f"\n{'='*60}")
    print("PLOT waitTime (con taglio finale al 98%)")
    print(f"{'='*60}\n")

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.suptitle("waitTime Over Time (end-cut 98%)", fontsize=16)

    plotted_any = False

    for vec_file in vec_files:
        config_label = extract_config_from_filename(os.path.basename(vec_file))
        print(f"Leggendo: {os.path.basename(vec_file)}  -> {config_label}")

        data = parse_vec_file(vec_file, metric_filter="waitTime")
        if not data:
            continue

        # Aggrega tutte le serie waitTime in un'unica serie (times, values)
        all_times, all_vals = [], []
        for vec_data in data.values():
            if vec_data["times"] and vec_data["values"]:
                all_times.extend(vec_data["times"])
                all_vals.extend(vec_data["values"])

        if not all_times or not all_vals:
            continue

        times = np.array(all_times)
        vals = np.array(all_vals)

        # Ordina per tempo
        idx = np.argsort(times)
        times_sorted = times[idx]
        vals_sorted = vals[idx]

        # Taglio finale al 98% per togliere artefatti di terminazione
        tmax = times_sorted.max()
        mask = times_sorted <= (END_CUTOFF * tmax)
        times_sorted = times_sorted[mask]
        vals_sorted = vals_sorted[mask]

        if len(vals_sorted) < 2:
            continue

        # Smooth (media mobile)
        window = max(1, len(vals_sorted) // 100)
        smoothed = uniform_filter1d(vals_sorted, size=window, mode="nearest")

        ax.plot(times_sorted, smoothed, alpha=0.7, linewidth=1.5, label=config_label)
        plotted_any = True

    if not plotted_any:
        ax.text(
            0.5, 0.5,
            "Nessun dato waitTime trovato nei file selezionati",
            ha="center", va="center",
            transform=ax.transAxes
        )

    ax.set_xlabel("Simulation Time (s)", fontsize=10)
    ax.set_ylabel("waitTime", fontsize=10)
    ax.set_title("waitTime Over Time", fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9, frameon=True)

    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, dpi=150)
    print(f"\n✓ Grafico salvato: {OUTPUT_PNG}")


def main():
    results_dir = "results"

    if not os.path.exists(results_dir):
        print(f"Errore: cartella '{results_dir}' non trovata")
        return

    all_vec_files = sorted(glob.glob(os.path.join(results_dir, "*.vec")))
    if not all_vec_files:
        print(f"Nessun file .vec trovato in {results_dir}")
        return

    # Seleziona carichi pesanti (1500, 2000, 2500) se presenti
    heavy_load_files = [
        f for f in all_vec_files
        if any(n in f for n in ["$N=1500", "$N=2000", "$N=2500"])
    ]

    if not heavy_load_files:
        print("Nessun file con carichi pesanti trovato. Uso i primi 3 file disponibili...")
        vec_files = all_vec_files[:3]
    else:
        vec_files = (
            [f for f in heavy_load_files if "$N=1500" in f][:1]
            + [f for f in heavy_load_files if "$N=2000" in f][:1]
            + [f for f in heavy_load_files if "$N=2500" in f][:1]
        )

        # Se per caso qualche lista è vuota (es. manca N=2500), ripulisci dai None
        vec_files = [f for f in vec_files if f]

    print(f"\nAnalizzando {len(vec_files)} file .vec:")
    for vf in vec_files:
        print(f"  - {os.path.basename(vf)}")

    analyze_and_plot(vec_files)


if __name__ == "__main__":
    main()
