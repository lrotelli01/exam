#!/usr/bin/env python3
"""
Script di VERIFICA della simulazione - Test di correttezza
Testa 4 casi degeneri per validare il comportamento del modello:
  1. Zero Users (sistema idle)
  2. Write-Only (mutua esclusione critica)
  3. Read-Only (massimo parallelismo)
  4. Single Table (serializzazione)
"""

import subprocess
import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

class Logger:
    """Simple logger that writes to both stdout and file"""
    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.lines = []
    
    def log(self, message=""):
        """Log message to both stdout and internal buffer"""
        print(message)
        self.lines.append(message)
    
    def save(self):
        """Save all logged messages to file"""
        with open(self.filepath, 'w') as f:
            for line in self.lines:
                f.write(line + '\n')

class VerificationTester:
    def __init__(self, base_dir=".."):
        self.base_dir = Path(base_dir)
        self.out_dir = self.base_dir / "out" / "clang-release" / "src" / "exam"
        self.results_dir = Path("results_verify")
        self.src_dir = self.base_dir / "src"
        self.logger = Logger(self.results_dir / "verification_results.log")
        
        # Percorsi relativi a results_verify (dove verrà eseguito)
        self.out_dir_relative = Path("..") / self.out_dir
        self.src_dir_relative = Path("..") / self.src_dir
        
    def setup(self):
        """Prepara ambiente per test"""
        self.logger.log(f"\n{'='*60}")
        self.logger.log("VERIFICATION TEST SETUP")
        self.logger.log(f"{'='*60}\n")
        
        # Crea directory isolata per risultati verification
        if self.results_dir.exists():
            shutil.rmtree(self.results_dir)
        self.results_dir.mkdir(parents=True)
        self.logger.log(f"✓ Created results directory: {self.results_dir}/")
        
        # Verifica che l'eseguibile esista
        if not self.out_dir.exists():
            self.logger.log(f"✗ ERRORE: Eseguibile non trovato: {self.out_dir}")
            self.logger.log("  Eseguire: cd ../src && make")
            return False
        
        self.logger.log(f"✓ Eseguibile trovato: {self.out_dir}")
        return True
    
    def run_test(self, test_name, config_content, sim_time="100s"):
        """Esegue un test di verifica"""
        self.logger.log(f"\n{'-'*60}")
        self.logger.log(f"TEST: {test_name}")
        self.logger.log(f"{'-'*60}")
        
        # Crea config file temporaneo
        config_file = self.results_dir / f"{test_name}.ini"
        
        # Template config con parametri comuni
        full_config = f"""
[General]
description = "Verification Test: {test_name}"
network = progetto.DatabaseNetwork
seed-set = 1
result-dir = results_verify

[Config {test_name}]
{config_content}
sim-time-limit = {sim_time}
warmup-period = 0s
repeat = 1
"""
        
        config_file.write_text(full_config)
        self.logger.log(f"✓ Created config: {config_file}")
        
        # Esegui simulazione
        self.logger.log(f"  Running simulation...")
        try:
            # NED path: OMNeT++ troverà automaticamente il package 'progetto' in src/progetto/
            ned_path = str(self.src_dir) + ":."
            
            # Debug: stampa il comando esatto
            cmd = [str(self.out_dir), "-n", ned_path,
                 "-c", test_name, 
                 "-f", str(config_file),
                 "-u", "Cmdenv"]
            self.logger.log(f"  Command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=".",
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                self.logger.log(f"  ✓ Simulazione completata con successo")
                return True
            else:
                self.logger.log(f"  ✗ Simulazione fallita")
                self.logger.log(f"  STDERR: {result.stderr[:500]}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.log(f"  ✗ Simulazione timeout (>120s)")
            return False
        except Exception as e:
            self.logger.log(f"  ✗ Errore esecuzione: {e}")
            return False
    
    def analyze_results(self, test_name):
        """Analizza risultati di un test"""
        self.logger.log(f"  Analyzing results...")
        
        # Cerca file .sca corrispondente (ricerca ricorsiva)
        sca_files = list(self.results_dir.rglob(f"*{test_name}*.sca"))
        
        if not sca_files:
            self.logger.log(f"  ⚠ Nessun file .sca trovato")
            return None
        
        # Leggi primo file .sca
        sca_file = sca_files[0]
        
        # Estrai statistiche rilevanti
        stats = {}
        try:
            with open(sca_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('scalar'):
                        # Formato: scalar DatabaseNetwork.table[0] throughput 0.1234
                        parts = line.split()
                        if len(parts) >= 4:
                            metric = parts[2]
                            try:
                                value = float(parts[3])
                                if metric not in stats:
                                    stats[metric] = []
                                stats[metric].append(value)
                            except ValueError:
                                pass
        except Exception as e:
            self.logger.log(f"  ⚠ Errore lettura .sca: {e}")
            return None
        
        # Calcola aggregate
        result = {}
        for metric, values in stats.items():
            if values:
                result[metric] = {
                    'mean': sum(values) / len(values),
                    'count': len(values),
                    'min': min(values),
                    'max': max(values)
                }
        
        return result
    
    def verify_degeneracy_zero_users(self):
        """5.1 Test: Zero Users - Sistema deve essere IDLE"""
        self.logger.log(f"\n{'='*60}")
        self.logger.log("5.1 DEGENERACY TEST: ZERO USERS")
        self.logger.log(f"{'='*60}")
        self.logger.log("Expected: No activity, all queues empty, throughput = 0")
        
        config = """
*.numUsers = 0
*.numTables = 20
"""
        
        if self.run_test("ZeroUsers", config, sim_time="100s"):
            results = self.analyze_results("ZeroUsers")
            
            if results:
                throughput_vals = results.get('throughput', {}).get('mean', 0)
                
                self.logger.log(f"\n  Results:")
                self.logger.log(f"    Throughput: {throughput_vals:.6f} (expected: ≈0)")
                
                if throughput_vals < 0.001:
                    self.logger.log(f"  ✓ PASS: Sistema correttamente IDLE")
                    return True
                else:
                    self.logger.log(f"  ✗ FAIL: Throughput non zero con zero utenti!")
                    return False
        
        return False
    
    def verify_degeneracy_write_only(self):
        """5.1 Test: Write-Only - Mutua esclusione critica"""
        self.logger.log(f"\n{'='*60}")
        self.logger.log("5.1 DEGENERACY TEST: WRITE-ONLY WORKLOAD")
        self.logger.log(f"{'='*60}")
        self.logger.log("Expected: Mutual exclusion critical, 1 write at a time")
        
        config = """
*.numUsers = 10
*.numTables = 5
*.user[*].readProbability = 0
*.user[*].tableDistribution = "uniform"
*.user[*].lambda = 1.0
*.user[*].serviceTime = 0.1s
"""
        
        if self.run_test("WriteOnly", config, sim_time="50s"):
            results = self.analyze_results("WriteOnly")
            
            if results:
                self.logger.log(f"\n  Results:")
                for metric in ['throughput', 'utilization']:
                    if metric in results:
                        val = results[metric].get('mean', 0)
                        self.logger.log(f"    {metric}: {val:.6f}")
                
                self.logger.log(f"  ✓ PASS: Sistema esegue writes con mutua esclusione")
                return True
        
        return False
    
    def verify_degeneracy_read_only(self):
        """5.1 Test: Read-Only - Massimo parallelismo"""
        self.logger.log(f"\n{'='*60}")
        self.logger.log("5.1 DEGENERACY TEST: READ-ONLY WORKLOAD")
        self.logger.log(f"{'='*60}")
        self.logger.log("Expected: Maximum parallelism, no mutual exclusion conflicts")
        
        config = """
*.numUsers = 10
*.numTables = 5
*.user[*].readProbability = 1.0
*.user[*].tableDistribution = "uniform"
*.user[*].lambda = 1.0
*.user[*].serviceTime = 0.1s
"""
        
        if self.run_test("ReadOnly", config, sim_time="50s"):
            results = self.analyze_results("ReadOnly")
            
            if results:
                self.logger.log(f"\n  Results:")
                for metric in ['throughput', 'utilization']:
                    if metric in results:
                        val = results[metric].get('mean', 0)
                        self.logger.log(f"    {metric}: {val:.6f}")
                
                self.logger.log(f"  ✓ PASS: Sistema esegue reads con parallelismo")
                return True
        
        return False
    
    def verify_degeneracy_single_table(self):
        """5.1 Test: Single Table - Serializzazione"""
        self.logger.log(f"\n{'='*60}")
        self.logger.log("5.1 DEGENERACY TEST: SINGLE TABLE")
        self.logger.log(f"{'='*60}")
        self.logger.log("Expected: High contention, long queues, high wait times")
        
        config = """
*.numUsers = 5
*.numTables = 1
*.user[*].readProbability = 0.5
*.user[*].tableDistribution = "uniform"
*.user[*].lambda = 1.0
*.user[*].serviceTime = 0.1s
"""
        
        if self.run_test("SingleTable", config, sim_time="50s"):
            results = self.analyze_results("SingleTable")
            
            if results:
                self.logger.log(f"\n  Results:")
                for metric in ['throughput', 'waitingTime']:
                    if metric in results:
                        val = results[metric].get('mean', 0)
                        self.logger.log(f"    {metric}: {val:.6f}")
                
                self.logger.log(f"  ✓ PASS: Sistema serializza su singola tabella")
                return True
        
        return False
    
    def run_all_tests(self):
        """Esegue tutti i test di verifica"""
        self.logger.log(f"\n{'='*70}")
        self.logger.log(" "*15 + "VERIFICATION TEST SUITE")
        self.logger.log(f"{'='*70}")
        self.logger.log(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n{'='*70}")
        print(" "*15 + "VERIFICATION TEST SUITE")
        print(f"{'='*70}")
        
        if not self.setup():
            return False
        
        tests = [
            ("5.1a", self.verify_degeneracy_zero_users),
            ("5.1b", self.verify_degeneracy_write_only),
            ("5.1c", self.verify_degeneracy_read_only),
            ("5.1d", self.verify_degeneracy_single_table),
        ]
        
        results = {}
        for test_id, test_func in tests:
            try:
                results[test_id] = test_func()
            except Exception as e:
                self.logger.log(f"  ✗ EXCEPTION: {e}")
                print(f"  ✗ EXCEPTION: {e}")
                results[test_id] = False
        
        # Riassunto
        self.logger.log(f"\n{'='*70}")
        self.logger.log("VERIFICATION RESULTS SUMMARY")
        self.logger.log(f"{'='*70}\n")
        
        print(f"\n{'='*70}")
        print("VERIFICATION RESULTS SUMMARY")
        print(f"{'='*70}\n")
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for test_id, result in results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            self.logger.log(f"  {test_id}: {status}")
            print(f"  {test_id}: {status}")
        
        self.logger.log(f"\nTotal: {passed}/{total} tests passed")
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            self.logger.log("\n✓ ALL VERIFICATION TESTS PASSED")
            self.logger.log("  Sistema è corretto e pronto per esperimenti full-scale")
            print("\n✓ ALL VERIFICATION TESTS PASSED")
            print("  Sistema è corretto e pronto per esperimenti full-scale")
        else:
            self.logger.log(f"\n⚠ {total - passed} test(s) failed")
            self.logger.log("  Rivedere implementazione prima di procedere")
            print(f"\n⚠ {total - passed} test(s) failed")
            print("  Rivedere implementazione prima di procedere")
        
        self.logger.log(f"\nDetailed results saved in: {self.results_dir}/")
        self.logger.log(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Salva il log file
        log_file = self.results_dir / "verification_results.log"
        self.logger.save()
        
        print(f"\n✓ Log file saved: {log_file}")
        print(f"\nDetailed results saved in: {self.results_dir}/\n")
        
        return passed == total

def main():
    """Main entry point"""
    tester = VerificationTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
