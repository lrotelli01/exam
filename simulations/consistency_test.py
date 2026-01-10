#!/usr/bin/env python3
"""
Consistency Test: Vary numUsers while keeping other parameters constant
Verifies that throughput and wait time change monotonically and predictably
"""

import os
import sys
import subprocess
from pathlib import Path
import time

class ConsistencyTester:
    def __init__(self, base_dir="."):
        self.base_dir = Path(base_dir).resolve()
        self.results_dir = self.base_dir / "results_consistency"
        self.executable = self.base_dir.parent / "out/clang-release/src/exam"
        self.ned_path = str(self.base_dir.parent / "src") + ":."
        
    def setup(self):
        """Create results directory and verify executable exists"""
        self.results_dir.mkdir(exist_ok=True, parents=True)
        if not self.executable.exists():
            print(f"ERROR: Executable not found at {self.executable}")
            return False
        print(f"✓ Executable found: {self.executable}")
        print(f"✓ Results directory: {self.results_dir}")
        return True
    
    def create_config(self, num_users, config_name):
        """Create .ini configuration file for a specific numUsers value"""
        config_path = self.results_dir / f"{config_name}.ini"
        
        config_content = f"""[General]
network = progetto.DatabaseNetwork

# Simulation parameters
sim-time-limit = 4000s
warmup-period = 500s
repeat = 3

# Output
result-dir = {self.results_dir}
output-scalar-file = ${{resultdir}}/${{configname}}-${{iterationvars}}-${{repetition}}.sca

# Network parameters
*.numUsers = {num_users}
*.numTables = 10
*.user[*].readProbability = 0.5
*.user[*].tableDistribution = "uniform"
*.user[*].serviceTime = 0.1s
*.user[*].lambda = 0.05


[Config {config_name}]
"""
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        print(f"✓ Created config: {config_name} (numUsers={num_users})")
        return config_path
    
    def run_test(self, config_path, config_name, timeout=3600):
        """Execute simulation for a specific configuration"""
        print(f"\n{'='*60}")
        print(f"Running: {config_name}")
        print(f"{'='*60}")
        
        try:
            cmd = [
                str(self.executable),
                "-u", "Cmdenv",
                "-c", config_name,
                str(config_path)
            ]
            
            result = subprocess.run(
                cmd,
                timeout=timeout,
                capture_output=True,
                text=True,
                cwd=str(self.base_dir)  # Run from simulations directory where NED files are linked
            )
            
            if result.returncode == 0:
                print(f"✓ {config_name} completed successfully")
                return True
            else:
                print(f"✗ {config_name} failed")
                print("STDERR:", result.stderr[-500:] if result.stderr else "")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"✗ {config_name} timed out after {timeout}s")
            return False
        except Exception as e:
            print(f"✗ {config_name} error: {e}")
            return False
    
    def analyze_results(self):
        """Parse .sca files and extract metrics"""
        import re
        
        results = {}
        sca_files = list(self.results_dir.rglob("*.sca"))
        
        if not sca_files:
            print("ERROR: No .sca files found!")
            return results
        
        print(f"\nFound {len(sca_files)} .sca files")
        
        for sca_file in sorted(sca_files):
            try:
                with open(sca_file, 'r') as f:
                    content = f.read()
                
                # Extract run name to identify config
                run_match = re.search(r'run (\w+)', content)
                if not run_match:
                    continue
                
                run_name = run_match.group(1)
                config_match = re.search(r'Config(\w+)', run_name)
                if not config_match:
                    continue
                
                config_name = config_match.group(1)
                
                # Initialize dict for this config if needed
                if config_name not in results:
                    results[config_name] = {
                        'throughput': [],
                        'waitingTime': [],
                        'utilization': []
                    }
                
                # Extract throughput scalar
                throughput_match = re.search(
                    r'scalar.*?throughput\s+(\d+(?:\.\d+)?)',
                    content
                )
                if throughput_match:
                    results[config_name]['throughput'].append(
                        float(throughput_match.group(1))
                    )
                
                # Extract waiting time scalar
                wait_match = re.search(
                    r'scalar.*?waitingTime\s+(\d+(?:\.\d+)?)',
                    content
                )
                if wait_match:
                    results[config_name]['waitingTime'].append(
                        float(wait_match.group(1))
                    )
                
                # Extract utilization scalar
                util_match = re.search(
                    r'scalar.*?utilization\s+(\d+(?:\.\d+)?)',
                    content
                )
                if util_match:
                    results[config_name]['utilization'].append(
                        float(util_match.group(1))
                    )
                    
            except Exception as e:
                print(f"Warning: Could not parse {sca_file}: {e}")
        
        return results
    
    def run_all_tests(self):
        """Run all consistency test configurations"""
        if not self.setup():
            return False
        
        # Configurations to test
        configs = [
            (10, "Config10Users"),
            (50, "Config50Users"),
            (100, "Config100Users"),
            (500, "Config500Users"),
            (1000, "Config1000Users"),
        ]
        
        print("\n" + "="*60)
        print("CONSISTENCY TEST - Creating configurations")
        print("="*60)
        
        # Create all config files
        config_files = []
        for num_users, config_name in configs:
            config_path = self.create_config(num_users, config_name)
            config_files.append((config_path, config_name, num_users))
        
        print("\n" + "="*60)
        print("CONSISTENCY TEST - Running simulations")
        print("="*60)
        print("Note: Each configuration runs 3 repetitions × 4000s = ~3.3 hours total")
        
        # Run all tests
        results_summary = []
        for config_path, config_name, num_users in config_files:
            start_time = time.time()
            success = self.run_test(config_path, config_name)
            elapsed = time.time() - start_time
            
            results_summary.append({
                'config': config_name,
                'numUsers': num_users,
                'success': success,
                'elapsed': elapsed
            })
        
        # Print summary
        print("\n" + "="*60)
        print("CONSISTENCY TEST - Summary")
        print("="*60)
        
        for result in results_summary:
            status = "✓ PASS" if result['success'] else "✗ FAIL"
            elapsed_min = result['elapsed'] / 60
            print(f"{status}: {result['config']} (numUsers={result['numUsers']}) - {elapsed_min:.1f} min")
        
        # Now analyze all results
        print("\n" + "="*60)
        print("CONSISTENCY TEST - Analysis")
        print("="*60)
        
        results = self.analyze_results()
        
        if not results:
            print("No results to analyze")
            return False
        
        # Print metrics by configuration
        print("\nMetrics by numUsers:")
        print(f"{'Config':<20} {'numUsers':<12} {'Throughput':<15} {'Wait Time':<15} {'Utilization':<15}")
        print("-" * 80)
        
        config_order = [10, 50, 100, 500, 1000]
        for num_users in config_order:
            config_name = f"Config{num_users}Users"
            if config_name in results:
                metrics = results[config_name]
                
                if metrics['throughput']:
                    throughput_avg = sum(metrics['throughput']) / len(metrics['throughput'])
                else:
                    throughput_avg = 0
                
                if metrics['waitingTime']:
                    wait_avg = sum(metrics['waitingTime']) / len(metrics['waitingTime'])
                else:
                    wait_avg = 0
                
                if metrics['utilization']:
                    util_avg = sum(metrics['utilization']) / len(metrics['utilization'])
                else:
                    util_avg = 0
                
                print(f"{config_name:<20} {num_users:<12} {throughput_avg:<15.6f} {wait_avg:<15.6f} {util_avg:<15.6f}")
        
        # Verify consistency
        print("\n" + "="*60)
        print("CONSISTENCY TEST - Verification")
        print("="*60)
        
        throughputs = []
        wait_times = []
        
        for num_users in config_order:
            config_name = f"Config{num_users}Users"
            if config_name in results and results[config_name]['throughput']:
                throughputs.append(sum(results[config_name]['throughput']) / len(results[config_name]['throughput']))
                wait_times.append(sum(results[config_name]['waitingTime']) / len(results[config_name]['waitingTime']))
        
        if len(throughputs) >= 2:
            throughput_increasing = all(throughputs[i] <= throughputs[i+1] for i in range(len(throughputs)-1))
            wait_increasing = all(wait_times[i] <= wait_times[i+1] for i in range(len(wait_times)-1))
            
            print(f"\nThroughput increases with numUsers: {'✓ PASS' if throughput_increasing else '✗ FAIL'}")
            print(f"Wait time increases with numUsers: {'✓ PASS' if wait_increasing else '✗ FAIL'}")
            
            if throughput_increasing and wait_increasing:
                print("\n✓ CONSISTENCY TEST PASSED")
                return True
            else:
                print("\n✗ CONSISTENCY TEST FAILED - Metrics do not increase monotonically")
                return False
        
        return True

if __name__ == "__main__":
    tester = ConsistencyTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
