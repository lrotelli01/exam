#!/usr/bin/env python3
"""
CONTINUITY TEST - Sezione 5.2 della Documentazione
Verifica che piccole variazioni nei parametri producono piccole variazioni nei risultati
Confronta due configurazioni leggermente diverse (readProbability 0.5 vs 0.55)
"""

import subprocess
import os
import sys
from pathlib import Path
from datetime import datetime

def run_continuity_test():
    """Esegue il continuity test con due configurazioni"""
    
    print(f"\n{'='*70}")
    print(" "*15 + "CONTINUITY TEST - SEZIONE 5.2")
    print(f"{'='*70}\n")
    
    # Directories
    base_dir = Path("..")
    out_dir = base_dir / "out" / "clang-release" / "src" / "exam"
    src_dir = base_dir / "src"
    results_dir = Path("results_continuity")
    
    # Crea directory risultati
    if results_dir.exists():
        import shutil
        shutil.rmtree(results_dir)
    results_dir.mkdir(parents=True)
    print(f"✓ Created results directory: {results_dir}/\n")
    
    # Verifiche
    if not out_dir.exists():
        print(f"✗ ERRORE: Eseguibile non trovato: {out_dir}")
        print("  Eseguire: cd ../src && make")
        return False
    
    print(f"✓ Eseguibile trovato: {out_dir}\n")
    
    # Configurazione A: p = 0.5 (baseline)
    config_a = """[General]
description = "Continuity Test - Configuration A (p=0.5)"
network = DatabaseNetwork
seed-set = 1
result-dir = results_continuity

[Config ContinuityA]
*.numUsers = 100
*.numTables = 20
*.user[*].lambda = 1.0
*.user[*].readProbability = 0.5
*.user[*].serviceTime = 0.1s
*.user[*].tableDistribution = "uniform"
sim-time-limit = 1000s
warmup-period = 500s
repeat = 25
"""
    
    # Configurazione B: p = 0.55 (variazione piccola)
    config_b = """[General]
description = "Continuity Test - Configuration B (p=0.55)"
network = DatabaseNetwork
seed-set = 1
result-dir = results_continuity

[Config ContinuityB]
*.numUsers = 100
*.numTables = 20
*.user[*].lambda = 1.0
*.user[*].readProbability = 0.55
*.user[*].serviceTime = 0.1s
*.user[*].tableDistribution = "uniform"
sim-time-limit = 1000s
warmup-period = 500s
repeat = 25
"""
    
    # Salva config files
    config_a_file = results_dir / "ContinuityA.ini"
    config_b_file = results_dir / "ContinuityB.ini"
    
    config_a_file.write_text(config_a)
    config_b_file.write_text(config_b)
    
    print(f"Configuration A (readProbability = 0.5):")
    print(f"  ✓ Salvato: {config_a_file}")
    print(f"\nConfiguration B (readProbability = 0.55):")
    print(f"  ✓ Salvato: {config_b_file}\n")
    
    # Esegui simulazione A
    print(f"{'='*70}")
    print("Lanciando CONFIGURATION A (p=0.5) con 25 repetizioni...")
    print(f"{'='*70}\n")
    
    cmd_a = [str(out_dir), "-n", str(src_dir) + ":.",
             "-c", "ContinuityA",
             "-f", str(config_a_file),
             "-u", "Cmdenv"]
    
    try:
        result_a = subprocess.run(cmd_a, cwd=".", capture_output=True, text=True, timeout=3600)
        
        if result_a.returncode == 0:
            print(f"✓ CONFIGURATION A completata con successo\n")
        else:
            print(f"✗ CONFIGURATION A fallita")
            print(f"STDERR: {result_a.stderr[:500]}\n")
            return False
    except subprocess.TimeoutExpired:
        print(f"✗ CONFIGURATION A timeout (>60 min)\n")
        return False
    except Exception as e:
        print(f"✗ Errore esecuzione A: {e}\n")
        return False
    
    # Esegui simulazione B
    print(f"{'='*70}")
    print("Lanciando CONFIGURATION B (p=0.55) con 25 repetizioni...")
    print(f"{'='*70}\n")
    
    cmd_b = [str(out_dir), "-n", str(src_dir) + ":.",
             "-c", "ContinuityB",
             "-f", str(config_b_file),
             "-u", "Cmdenv"]
    
    try:
        result_b = subprocess.run(cmd_b, cwd=".", capture_output=True, text=True, timeout=3600)
        
        if result_b.returncode == 0:
            print(f"✓ CONFIGURATION B completata con successo\n")
        else:
            print(f"✗ CONFIGURATION B fallita")
            print(f"STDERR: {result_b.stderr[:500]}\n")
            return False
    except subprocess.TimeoutExpired:
        print(f"✗ CONFIGURATION B timeout (>60 min)\n")
        return False
    except Exception as e:
        print(f"✗ Errore esecuzione B: {e}\n")
        return False
    
    # Riassunto
    print(f"\n{'='*70}")
    print("CONTINUITY TEST COMPLETED")
    print(f"{'='*70}\n")
    
    print(f"✓ Both configurations executed successfully!")
    print(f"✓ Results saved in: {results_dir}/")
    print(f"\nNext step:")
    print(f"  - Analyze .sca files from both configurations")
    print(f"  - Compare 95% confidence intervals")
    print(f"  - Verify overlap to confirm continuity\n")
    
    return True

def main():
    """Main entry point"""
    success = run_continuity_test()
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
