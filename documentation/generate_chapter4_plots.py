#!/usr/bin/env python3
"""Generate Chapter 4 plots directly from OMNeT++ .sca results (no synthetic data)."""

from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

OUTPUT_DIR = Path(__file__).parent / "images"
OUTPUT_DIR.mkdir(exist_ok=True)
RESULTS_DIR = Path(__file__).resolve().parents[1] / "simulations" / "results"

plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams["figure.figsize"] = (8, 6)
plt.rcParams["font.size"] = 11


def load_runs_from_sca(results_dir):
    """Read all runs and extract dist, N, p, avg wait (ms), and throughput (req/s)."""
    sca_files = sorted(results_dir.glob("*.sca"))
    if not sca_files:
        raise FileNotFoundError(f"No .sca files found in {results_dir}")

    runs = []
    for filepath in sca_files:
        dist = None
        num_users = None
        read_prob = None
        wait_sum = 0.0
        wait_count = 0
        throughput_sum = 0.0

        with filepath.open("r", encoding="utf-8", errors="ignore") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if line.startswith("attr configname "):
                    dist = line.split()[2]
                elif line.startswith("itervar N "):
                    num_users = int(float(line.split()[2]))
                elif line.startswith("itervar p "):
                    read_prob = float(line.split()[2])
                elif line.startswith("scalar DatabaseNetwork.user["):
                    if " averageWaitTime " in line:
                        wait_sum += float(line.rsplit(" ", 1)[-1])
                        wait_count += 1
                    elif " accessesPerSecond " in line:
                        throughput_sum += float(line.rsplit(" ", 1)[-1])

        if dist and num_users is not None and read_prob is not None and wait_count > 0:
            runs.append(
                {
                    "dist": dist,
                    "N": num_users,
                    "p": read_prob,
                    "wait_ms": (wait_sum / wait_count) * 1000.0,
                    "throughput": throughput_sum,
                }
            )

    return runs


def compute_factor_effects_throughput(runs):
    """Balanced 3-factor ANOVA decomposition for throughput (N, p, distribution)."""
    levels_n = sorted({r["N"] for r in runs})
    levels_p = sorted({r["p"] for r in runs})
    levels_d = sorted({r["dist"] for r in runs})
    a, b, c = len(levels_n), len(levels_p), len(levels_d)

    cells = defaultdict(list)
    for run in runs:
        cells[(run["N"], run["p"], run["dist"])].append(run["throughput"])

    reps = min(len(v) for v in cells.values())
    y = np.array([r["throughput"] for r in runs], dtype=float)
    mu = float(np.mean(y))

    mean_n = {n: np.mean([r["throughput"] for r in runs if r["N"] == n]) for n in levels_n}
    mean_p = {p: np.mean([r["throughput"] for r in runs if r["p"] == p]) for p in levels_p}
    mean_d = {d: np.mean([r["throughput"] for r in runs if r["dist"] == d]) for d in levels_d}
    mean_np = {(n, p): np.mean([r["throughput"] for r in runs if r["N"] == n and r["p"] == p]) for n in levels_n for p in levels_p}
    mean_nd = {(n, d): np.mean([r["throughput"] for r in runs if r["N"] == n and r["dist"] == d]) for n in levels_n for d in levels_d}
    mean_pd = {(p, d): np.mean([r["throughput"] for r in runs if r["p"] == p and r["dist"] == d]) for p in levels_p for d in levels_d}
    mean_npd = {(n, p, d): np.mean(cells[(n, p, d)]) for n in levels_n for p in levels_p for d in levels_d}

    ss_total = np.sum((y - mu) ** 2)
    ss_n = b * c * reps * sum((mean_n[n] - mu) ** 2 for n in levels_n)
    ss_p = a * c * reps * sum((mean_p[p] - mu) ** 2 for p in levels_p)
    ss_d = a * b * reps * sum((mean_d[d] - mu) ** 2 for d in levels_d)
    ss_np = c * reps * sum((mean_np[(n, p)] - mean_n[n] - mean_p[p] + mu) ** 2 for n in levels_n for p in levels_p)
    ss_nd = b * reps * sum((mean_nd[(n, d)] - mean_n[n] - mean_d[d] + mu) ** 2 for n in levels_n for d in levels_d)
    ss_pd = a * reps * sum((mean_pd[(p, d)] - mean_p[p] - mean_d[d] + mu) ** 2 for p in levels_p for d in levels_d)
    ss_npd = reps * sum(
        (
            mean_npd[(n, p, d)]
            - mean_np[(n, p)]
            - mean_nd[(n, d)]
            - mean_pd[(p, d)]
            + mean_n[n]
            + mean_p[p]
            + mean_d[d]
            - mu
        )
        ** 2
        for n in levels_n
        for p in levels_p
        for d in levels_d
    )
    ss_error = sum(np.sum((np.array(vals) - np.mean(vals)) ** 2) for vals in cells.values())

    effects = {
        "N (Users)": ss_n,
        "p (Read Prob)": ss_p,
        "Distribution": ss_d,
        "N × p": ss_np,
        "N × Dist": ss_nd,
        "p × Dist": ss_pd,
        "Residual": ss_npd + ss_error,
    }

    return {name: max(0.0, value) * 100.0 / ss_total for name, value in effects.items()}


def build_residual_dataset(runs):
    """
    Residuals are computed per replication against the mean of the same (dist, N, p) config:
    residual% = (wait_i - mean_wait_config) / mean_wait_config * 100.
    """
    grouped = defaultdict(list)
    for run in runs:
        grouped[(run["dist"], run["N"], run["p"])].append(run["wait_ms"])

    mean_wait_by_cfg = {key: float(np.mean(values)) for key, values in grouped.items()}

    predicted_wait_ms = []
    residual_pct = []
    dist = []
    read_p = []

    for run in runs:
        key = (run["dist"], run["N"], run["p"])
        pred = mean_wait_by_cfg[key]
        err_pct = (run["wait_ms"] - pred) / max(pred, 1e-12) * 100.0

        predicted_wait_ms.append(pred)
        residual_pct.append(err_pct)
        dist.append(run["dist"])
        read_p.append(run["p"])

    predicted_wait_ms = np.array(predicted_wait_ms, dtype=float)
    residual_pct = np.array(residual_pct, dtype=float)
    z_residual = (residual_pct - np.mean(residual_pct)) / np.std(residual_pct, ddof=1)

    return {
        "predicted_wait_ms": predicted_wait_ms,
        "residual_pct": residual_pct,
        "abs_residual_pct": np.abs(residual_pct),
        "z_residual": z_residual,
        "dist": np.array(dist, dtype=object),
        "p": np.array(read_p, dtype=float),
    }


def generate_factor_effects_pie(effects):
    labels = list(effects.keys())
    sizes = list(effects.values())
    colors = ["#2ecc71", "#3498db", "#9b59b6", "#e74c3c", "#f39c12", "#1abc9c", "#95a5a6"]
    explode = (0.06, 0, 0, 0, 0, 0, 0)

    def autopct_fmt(value):
        return f"{value:.2f}%" if value >= 0.01 else "<0.01%"

    fig, ax = plt.subplots(figsize=(10, 8))
    wedges, _, autotexts = ax.pie(
        sizes,
        explode=explode,
        labels=labels,
        colors=colors,
        autopct=autopct_fmt,
        startangle=90,
        pctdistance=0.75,
    )

    for autotext in autotexts:
        autotext.set_fontsize(10)
        autotext.set_fontweight("bold")

    ax.set_title("Factor Effects on Throughput (from .sca runs)", fontsize=14, fontweight="bold")
    ax.legend(
        wedges,
        [f"{label}: {value:.4f}%" for label, value in zip(labels, sizes)],
        title="Factors",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
    )

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "factor_effects_pie.pdf", dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / "factor_effects_pie.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Created: factor_effects_pie.pdf/png")


def generate_qq_plot(z_residual):
    fig, ax = plt.subplots(figsize=(8, 8))
    (osm, osr), (slope, intercept, r_value) = stats.probplot(z_residual, dist="norm")
    ax.scatter(osm, osr, s=28, alpha=0.75, color="#3498db", edgecolor="#2980b9")
    ax.plot(osm, slope * osm + intercept, color="#e74c3c", linewidth=2)

    shapiro = stats.shapiro(z_residual)

    ax.set_xlabel("Theoretical Quantiles (Normal)")
    ax.set_ylabel("Sample Quantiles (Standardized residual %)")
    ax.set_title("QQ-Plot of Residual Percentages (from .sca data)", fontsize=14, fontweight="bold")
    ax.text(
        0.03,
        0.96,
        f"R²={r_value**2:.4f}\nShapiro p={shapiro.pvalue:.2e}",
        transform=ax.transAxes,
        va="top",
        fontsize=10,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
    )
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "qq_plot_residuals.pdf", dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / "qq_plot_residuals.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Created: qq_plot_residuals.pdf/png")


def generate_residuals_vs_predicted(predicted_wait_ms, residual_pct, dist):
    fig, ax = plt.subplots(figsize=(10, 6))

    mask_uniform = dist == "Uniform"
    mask_lognormal = dist == "Lognormal"

    ax.scatter(
        predicted_wait_ms[mask_uniform],
        residual_pct[mask_uniform],
        alpha=0.65,
        s=28,
        color="#1f77b4",
        label="Uniform",
    )
    ax.scatter(
        predicted_wait_ms[mask_lognormal],
        residual_pct[mask_lognormal],
        alpha=0.65,
        s=28,
        color="#d62728",
        label="Lognormal",
    )

    ax.axhline(0.0, color="black", linewidth=1.5)
    ax.set_xscale("log")
    ax.set_xlabel("Predicted waiting time per configuration (ms, log scale)")
    ax.set_ylabel("Residual percentage (%)")
    ax.set_title("Residuals vs Predicted Waiting Time (.sca replications)", fontsize=14, fontweight="bold")

    rho, p_value = stats.spearmanr(np.log10(predicted_wait_ms + 1.0), np.abs(residual_pct))
    ax.text(
        0.02,
        0.96,
        f"Spearman rho(|residual%|, pred) = {rho:.3f}\np = {p_value:.2e}",
        transform=ax.transAxes,
        va="top",
        fontsize=10,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
    )
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "residuals_vs_predicted.pdf", dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / "residuals_vs_predicted.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Created: residuals_vs_predicted.pdf/png")


def generate_residual_magnitude(abs_residual_pct, dist, read_p):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax1 = axes[0]
    ax1.hist(abs_residual_pct, bins=35, color="#4c78a8", alpha=0.8, edgecolor="white")
    median = float(np.median(abs_residual_pct))
    p90 = float(np.quantile(abs_residual_pct, 0.90))
    ax1.axvline(median, color="#2ca02c", linewidth=2, label=f"Median = {median:.3f}%")
    ax1.axvline(p90, color="#ff7f0e", linewidth=2, linestyle="--", label=f"P90 = {p90:.3f}%")
    ax1.set_xlabel("|Residual| (%)")
    ax1.set_ylabel("Count")
    ax1.set_title("Absolute Residual Magnitude (all replications)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    group_order = [
        ("Uniform", 0.3),
        ("Uniform", 0.5),
        ("Uniform", 0.8),
        ("Lognormal", 0.3),
        ("Lognormal", 0.5),
        ("Lognormal", 0.8),
    ]
    group_data = []
    labels = []
    for dist_name, p_value in group_order:
        mask = (dist == dist_name) & np.isclose(read_p, p_value)
        group_data.append(abs_residual_pct[mask])
        labels.append(f"{dist_name[0]} p={p_value}")

    box = ax2.boxplot(group_data, tick_labels=labels, patch_artist=True, showfliers=True)
    colors = ["#1f77b4", "#6baed6", "#9ecae1", "#d62728", "#ff9896", "#fcbba1"]
    for patch, color in zip(box["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)

    ax2.set_xlabel("Configuration group")
    ax2.set_ylabel("|Residual| (%)")
    ax2.set_title("Residual Magnitude by Distribution and p")
    ax2.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "residual_magnitude.pdf", dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / "residual_magnitude.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Created: residual_magnitude.pdf/png")


def print_residual_summary(abs_residual_pct, dist, read_p):
    median = float(np.median(abs_residual_pct))
    p90 = float(np.quantile(abs_residual_pct, 0.90))
    p99 = float(np.quantile(abs_residual_pct, 0.99))
    max_v = float(np.max(abs_residual_pct))
    print(f"Residual magnitude summary: median={median:.4f}%, p90={p90:.4f}%, p99={p99:.4f}%, max={max_v:.4f}%")
    for dist_name in ("Uniform", "Lognormal"):
        for p_value in (0.3, 0.5, 0.8):
            mask = (dist == dist_name) & np.isclose(read_p, p_value)
            values = abs_residual_pct[mask]
            print(
                f"  {dist_name:9s} p={p_value}: median={np.median(values):.4f}% "
                f"p90={np.quantile(values, 0.90):.4f}%"
            )


if __name__ == "__main__":
    print("Generating Chapter 4 plots from .sca data...")
    print(f"Results directory: {RESULTS_DIR}")
    print(f"Output directory: {OUTPUT_DIR}\n")

    all_runs = load_runs_from_sca(RESULTS_DIR)
    print(f"Loaded {len(all_runs)} runs.")

    effects = compute_factor_effects_throughput(all_runs)
    residual_data = build_residual_dataset(all_runs)

    generate_factor_effects_pie(effects)
    generate_qq_plot(residual_data["z_residual"])
    generate_residuals_vs_predicted(
        residual_data["predicted_wait_ms"],
        residual_data["residual_pct"],
        residual_data["dist"],
    )
    generate_residual_magnitude(
        residual_data["abs_residual_pct"],
        residual_data["dist"],
        residual_data["p"],
    )
    print_residual_summary(
        residual_data["abs_residual_pct"],
        residual_data["dist"],
        residual_data["p"],
    )

    print("\nAll Chapter 4 plots generated successfully.")
