#!/usr/bin/env python3
"""
Generate plots for Chapter 3 (Theoretical Verification)
Creates figures illustrating queueing theory concepts and simulation validation
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import os

# Output directory
OUTPUT_DIR = Path(__file__).parent / "images"
OUTPUT_DIR.mkdir(exist_ok=True)

# Use a clean style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (8, 5)
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['legend.fontsize'] = 10

def plot_kleinrock_function():
    """Plot the Kleinrock function E[N] = rho/(1-rho)"""
    rho = np.linspace(0, 0.99, 500)
    E_N = rho / (1 - rho)
    
    fig, ax = plt.subplots()
    ax.plot(rho, E_N, 'b-', linewidth=2, label=r'$E[N] = \frac{\rho}{1-\rho}$')
    
    # Mark important points
    ax.axhline(y=1, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=0.5, color='gray', linestyle='--', alpha=0.5)
    ax.plot(0.5, 1, 'ro', markersize=8, label=r'$\rho=0.5 \Rightarrow E[N]=1$')
    
    # Highlight danger zone
    ax.fill_between(rho[rho > 0.8], 0, E_N[rho > 0.8], alpha=0.3, color='red', label='Danger zone (ρ > 80%)')
    
    ax.set_xlabel(r'Utilization $\rho$')
    ax.set_ylabel(r'Mean jobs in system $E[N]$')
    ax.set_title('Kleinrock Function (M/M/1 Queue)')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 15)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'kleinrock_function.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'kleinrock_function.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Created: kleinrock_function.pdf/png")

def plot_response_time_vs_utilization():
    """Plot response time E[R] = S/(1-rho) for different service times"""
    rho = np.linspace(0.01, 0.99, 500)
    
    fig, ax = plt.subplots()
    
    S_values = [0.1, 0.2, 0.5]
    colors = ['blue', 'green', 'orange']
    
    for S, color in zip(S_values, colors):
        E_R = S / (1 - rho)
        ax.plot(rho, E_R, color=color, linewidth=2, label=f'S = {S}s')
    
    ax.axvline(x=0.5, color='gray', linestyle='--', alpha=0.5, label='ρ = 50%')
    
    ax.set_xlabel(r'Utilization $\rho$')
    ax.set_ylabel('Mean Response Time E[R] (seconds)')
    ax.set_title('Response Time vs Utilization')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 5)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'response_time_vs_utilization.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'response_time_vs_utilization.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Created: response_time_vs_utilization.pdf/png")

def plot_utilization_vs_users():
    """Plot theoretical utilization vs number of users - OPEN QUEUE MODEL"""
    # System parameters
    M = 10       # Number of tables
    lam = 0.05   # Request rate per user (λ = 1/20 = 0.05 req/s)
    S = 0.1      # Service time (seconds)
    
    N_values = np.arange(1, 1200, 10)
    
    # Theoretical utilization for OPEN queue: U = (N * λ * S) / M
    U_theory = (N_values * lam * S) / M
    
    # Empirical data points (from simulation)
    N_empirical = [10, 50, 100, 500, 1000]
    U_empirical = [0.50, 2.53, 5.00, 24.19, 46.44]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(N_values, U_theory * 100, 'b-', linewidth=2, label='Theoretical (Open Queue)')
    ax.scatter(N_empirical, U_empirical, s=100, c='green', marker='o', zorder=5, 
               edgecolors='black', linewidths=1.5, label='Simulation Results')
    
    ax.set_xlabel('Number of Users (N)')
    ax.set_ylabel('Utilization (%)')
    ax.set_title(f'Utilization vs Users (M={M}, λ={lam} req/s, S={S}s)')
    ax.set_xlim(0, 1200)
    ax.set_ylim(0, 60)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'utilization_vs_users.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'utilization_vs_users.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Created: utilization_vs_users.pdf/png")

def plot_empirical_vs_theoretical():
    """Bar chart comparing empirical vs theoretical utilization - OPEN QUEUE MODEL"""
    N_values = [10, 50, 100, 500, 1000]
    empirical = [0.50, 2.53, 5.00, 24.19, 46.44]
    
    # System parameters for OPEN queue
    M = 10       # Number of tables
    lam = 0.05   # Request rate per user (λ)
    S = 0.1      # Service time
    
    # Theoretical: U = (N * λ * S) / M * 100%
    theoretical = [(N * lam * S) / M * 100 for N in N_values]
    
    x = np.arange(len(N_values))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars1 = ax.bar(x - width/2, empirical, width, label='Empirical (Simulation)', color='steelblue', edgecolor='black')
    bars2 = ax.bar(x + width/2, theoretical, width, label='Theoretical', color='coral', edgecolor='black')
    
    # Add error percentages
    for i, (e, t) in enumerate(zip(empirical, theoretical)):
        error = abs(e - t) / t * 100
        ax.annotate(f'{error:.1f}%', xy=(i, max(e, t) + 1), ha='center', fontsize=9, color='gray')
    
    ax.set_xlabel('Number of Users (N)')
    ax.set_ylabel('Utilization (%)')
    ax.set_title('Empirical vs Theoretical Utilization (Open Queue Model)')
    ax.set_xticks(x)
    ax.set_xticklabels([f'N={n}' for n in N_values])
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'empirical_vs_theoretical.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'empirical_vs_theoretical.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Created: empirical_vs_theoretical.pdf/png")

def plot_per_table_utilization():
    """Plot per-table utilization for N=500"""
    tables = list(range(10))
    table_labels = [f'Table {i}' for i in tables]
    empirical = [23.95, 24.22, 23.90, 24.33, 24.27, 24.46, 24.17, 24.05, 24.31, 24.21]
    
    # Open queue: U = (N * λ * S) / M = (500 * 0.05 * 0.1) / 10 * 100 = 25%
    theoretical = [25.0] * 10
    
    x = np.arange(len(tables))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(12, 5))
    
    bars1 = ax.bar(x - width/2, empirical, width, label='Empirical', color='steelblue', edgecolor='black')
    bars2 = ax.bar(x + width/2, theoretical, width, label='Theoretical', color='coral', edgecolor='black')
    
    ax.axhline(y=np.mean(empirical), color='blue', linestyle='--', alpha=0.7, label=f'Empirical Mean ({np.mean(empirical):.2f}%)')
    ax.axhline(y=25.0, color='red', linestyle='--', alpha=0.7, label='Theoretical (25.0%)')
    
    ax.set_xlabel('Table')
    ax.set_ylabel('Utilization (%)')
    ax.set_title('Per-Table Utilization for N=500 Users')
    ax.set_xticks(x)
    ax.set_xticklabels(table_labels, rotation=45, ha='right')
    ax.set_ylim(20, 28)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'per_table_utilization.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'per_table_utilization.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Created: per_table_utilization.pdf/png")

def plot_throughput_vs_users():
    """Plot system throughput vs number of users - OPEN QUEUE MODEL"""
    # System parameters for OPEN queue
    M = 10       # Number of tables
    lam = 0.05   # Request rate per user (λ)
    S = 0.1      # Service time
    
    N_values = np.arange(1, 1200, 10)
    
    # Theoretical throughput for OPEN queue: γ = N * λ
    gamma_theory = N_values * lam
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(N_values, gamma_theory, 'b-', linewidth=2, label=r'$\gamma = N \cdot \lambda$')
    
    # Add some example points
    N_examples = [100, 500, 1000]
    gamma_examples = [n * lam for n in N_examples]
    ax.scatter(N_examples, gamma_examples, s=100, c='green', marker='o', zorder=5, 
               edgecolors='black', linewidths=1.5)
    
    for n, g in zip(N_examples, gamma_examples):
        ax.annotate(f'N={n}: {g:.0f} req/s', xy=(n, g), xytext=(n+50, g+2),
                   fontsize=10, color='green')
    
    ax.set_xlabel('Number of Users (N)')
    ax.set_ylabel('System Throughput γ (requests/second)')
    ax.set_title('Throughput vs Number of Users (Open Queue)')
    ax.set_xlim(0, 1200)
    ax.set_ylim(0, 70)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'throughput_vs_users.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'throughput_vs_users.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Created: throughput_vs_users.pdf/png")

def plot_interactive_system_model():
    """Create a diagram of the OPEN system model"""
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.axis('off')
    
    # Users box
    users_rect = plt.Rectangle((1, 1), 3, 2, fill=True, facecolor='lightblue', 
                                 edgecolor='black', linewidth=2)
    ax.add_patch(users_rect)
    ax.text(2.5, 2, 'N Users\n(Poisson arrivals)', ha='center', va='center', fontsize=12, fontweight='bold')
    ax.text(2.5, 0.5, 'λ = 0.05 req/s each', ha='center', va='center', fontsize=10)
    
    # Service center box
    service_rect = plt.Rectangle((7, 1), 3, 2, fill=True, facecolor='lightyellow',
                                   edgecolor='black', linewidth=2)
    ax.add_patch(service_rect)
    ax.text(8.5, 2, 'Service\nS = 0.1s', ha='center', va='center', fontsize=12, fontweight='bold')
    ax.text(8.5, 0.5, 'M = 10 tables', ha='center', va='center', fontsize=10)
    
    # Arrows (requests only - no feedback for open queue)
    ax.annotate('', xy=(7, 2), xytext=(4, 2),
                arrowprops=dict(arrowstyle='->', color='green', lw=2))
    ax.text(5.5, 2.3, 'Total rate: N·λ', ha='center', fontsize=10, color='green')
    
    ax.set_title('Open Queueing Network Model', fontsize=14, fontweight='bold', y=1.05)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'interactive_system_model.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'interactive_system_model.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Created: interactive_system_model.pdf/png")

def plot_error_analysis():
    """Plot error percentage vs number of users - OPEN QUEUE MODEL"""
    N_values = [10, 50, 100, 500, 1000]
    empirical = [0.50, 2.53, 5.00, 24.19, 46.44]
    
    # Open queue parameters
    M = 10       # Number of tables
    lam = 0.05   # Request rate per user
    S = 0.1      # Service time
    
    # Open queue: U = (N * λ * S) / M * 100%
    theoretical = [(N * lam * S) / M * 100 for N in N_values]
    errors = [abs(e - t) / t * 100 for e, t in zip(empirical, theoretical)]
    
    fig, ax = plt.subplots(figsize=(8, 5))
    
    bars = ax.bar(range(len(N_values)), errors, color='steelblue', edgecolor='black')
    
    # Color bars based on error threshold
    for bar, err in zip(bars, errors):
        if err < 3:
            bar.set_facecolor('green')
        elif err < 5:
            bar.set_facecolor('orange')
        else:
            bar.set_facecolor('red')
    
    ax.axhline(y=3, color='green', linestyle='--', alpha=0.7, label='Target: < 3%')
    ax.axhline(y=5, color='orange', linestyle='--', alpha=0.7, label='Acceptable: < 5%')
    
    ax.set_xlabel('Number of Users (N)')
    ax.set_ylabel('Relative Error (%)')
    ax.set_title('Model Accuracy: Relative Error vs Number of Users')
    ax.set_xticks(range(len(N_values)))
    ax.set_xticklabels([f'N={n}' for n in N_values])
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'error_analysis.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'error_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Created: error_analysis.pdf/png")


def main():
    print("Generating Chapter 3 plots...")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    
    plot_kleinrock_function()
    plot_response_time_vs_utilization()
    plot_utilization_vs_users()
    plot_empirical_vs_theoretical()
    plot_per_table_utilization()
    plot_throughput_vs_users()
    plot_interactive_system_model()
    plot_error_analysis()
    
    print()
    print("All plots generated successfully!")
    print(f"Files saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
