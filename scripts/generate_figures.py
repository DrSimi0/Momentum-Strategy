"""Generación de figuras científicas para el informe final de Momentum Intradía (ES / NQ).
"""
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.backtest.costs import DEFAULT_COST_CASES
from src.backtest.engine import simulate_trades
from src.analysis.inference import bootstrap_sharpe_distribution

FIGURES_DIR = Path("reports/figures")
PROCESSED_DIR = Path("data/processed")


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    df_es = pd.read_parquet(PROCESSED_DIR / "ES_daily_features.parquet")
    df_nq = pd.read_parquet(PROCESSED_DIR / "NQ_daily_features.parquet")

    # 1. Curva de PnL acumulado a lo largo de todo el periodo (2018–2026)
    fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    
    for ax, df, sym, mult, tick_sz, tick_val in [
        (axes[0], df_es, "ES (E-mini S&P 500)", 50.0, 0.25, 12.50),
        (axes[1], df_nq, "NQ (E-mini Nasdaq-100)", 20.0, 0.25, 5.00),
    ]:
        for hyp, col, color, ls in [
            ("H1 (r1)", "sig_H1", "#1f77b4", "-"),
            ("H2 (r12)", "sig_H2", "#ff7f0e", "-"),
            ("H3 (r1 & r12)", "sig_H3", "#2ca02c", "-"),
            ("H4 (Vol Filt)", "sig_H4", "#d62728", "-"),
            ("B1 (Buy & Hold)", "sig_B1", "#7f7f7f", "--"),
        ]:
            sim = simulate_trades(
                df=df,
                signal_col=col,
                multiplier_usd_per_point=mult,
                tick_size_points=tick_sz,
                tick_value_usd=tick_val,
                cost_spec=DEFAULT_COST_CASES["base"],
            )
            cum_pnl = sim["net_pnl_usd"].cumsum()
            ax.plot(df["date"], cum_pnl, label=hyp, color=color, linestyle=ls, linewidth=1.5)

        # Líneas verticales divisorias de particiones
        ax.axvline(pd.Timestamp("2022-01-01"), color="black", linestyle=":", alpha=0.7, label="Inicio Validación")
        ax.axvline(pd.Timestamp("2024-01-01"), color="red", linestyle="--", alpha=0.8, label="Inicio Holdout (Lock)")
        ax.set_title(f"PnL Neto Acumulado (USD) - {sym}", fontsize=14, fontweight="bold")
        ax.set_ylabel("PnL Neto Acumulado (USD)", fontsize=11)
        ax.legend(loc="upper left", frameon=True)

    axes[1].set_xlabel("Fecha de Sesión", fontsize=12)
    plt.tight_layout()
    fig_path1 = FIGURES_DIR / "cumulative_pnl.png"
    plt.savefig(fig_path1, dpi=300)
    plt.close()
    print(f"Guardada {fig_path1}")

    # 2. Descomposición PnL Bruto vs. Costos en Holdout
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    holdout_es = df_es[df_es["date"] >= "2024-01-01"].copy().reset_index(drop=True)
    holdout_nq = df_nq[df_nq["date"] >= "2024-01-01"].copy().reset_index(drop=True)

    for ax, df, sym, mult, tick_sz, tick_val in [
        (axes[0], holdout_es, "ES (Holdout 2024–2026)", 50.0, 0.25, 12.50),
        (axes[1], holdout_nq, "NQ (Holdout 2024–2026)", 20.0, 0.25, 5.00),
    ]:
        hyps = ["H1", "H2", "H3", "H4", "B1"]
        gross_vals = []
        cost_vals = []
        net_vals = []
        for h in hyps:
            sim = simulate_trades(
                df=df,
                signal_col=f"sig_{h}",
                multiplier_usd_per_point=mult,
                tick_size_points=tick_sz,
                tick_value_usd=tick_val,
                cost_spec=DEFAULT_COST_CASES["base"],
            )
            gross_vals.append(sim["gross_pnl_usd"].sum())
            cost_vals.append(sim["total_cost_usd"].sum())
            net_vals.append(sim["net_pnl_usd"].sum())

        x = np.arange(len(hyps))
        w = 0.25
        ax.bar(x - w, gross_vals, width=w, label="PnL Bruto", color="#1f77b4")
        ax.bar(x, cost_vals, width=w, label="Costos Totales", color="#d62728")
        ax.bar(x + w, net_vals, width=w, label="PnL Neto", color="#2ca02c")
        ax.set_xticks(x)
        ax.set_xticklabels(hyps, fontsize=11)
        ax.set_title(f"Descomposición de Retorno - {sym}", fontsize=13, fontweight="bold")
        ax.set_ylabel("USD", fontsize=11)
        ax.axhline(0, color="gray", linewidth=0.8)
        ax.legend(frameon=True)

    plt.tight_layout()
    fig_path2 = FIGURES_DIR / "costs_breakdown_holdout.png"
    plt.savefig(fig_path2, dpi=300)
    plt.close()
    print(f"Guardada {fig_path2}")


if __name__ == "__main__":
    main()
