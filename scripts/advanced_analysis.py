"""Análisis cuantitativo avanzado complementario según las secciones 8 y 14 del Prompt Maestro.
Calcula:
1. Retorno medio de r13 por deciles de r1.
2. Costo de equilibrio (breakeven) por operación para cada hipótesis.
3. Desglose de rendimiento por día de la semana (Lunes a Viernes).
4. Desglose por terciles de volatilidad previa (Baja, Media, Alta).
5. R² fuera de muestra (Campbell-Thompson, 2008).
6. Generación de las figuras adicionales: r13_by_r1_deciles.png, cost_sensitivity_breakeven.png, yearly_results.png.
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.backtest.costs import DEFAULT_COST_CASES, CostSpec
from src.backtest.engine import simulate_trades
from src.analysis.metrics import compute_oos_r_squared

PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports")
FIGURES_DIR = Path("reports/figures")


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    df_es = pd.read_parquet(PROCESSED_DIR / "ES_daily_features.parquet")
    df_nq = pd.read_parquet(PROCESSED_DIR / "NQ_daily_features.parquet")

    # Cargar results.json existente para actualizarlo
    with open(REPORTS_DIR / "results.json", "r", encoding="utf-8") as f:
        results_data = json.load(f)

    advanced_results = {}

    for sym, df, mult, tick_sz, tick_val in [
        ("ES", df_es, 50.0, 0.25, 12.50),
        ("NQ", df_nq, 20.0, 0.25, 5.00),
    ]:
        sym_res = {}

        # 1. Deciles de r1 vs retorno medio de r13 (en toda la muestra y en holdout)
        df_clean = df.dropna(subset=["r1", "r13"]).copy()
        df_clean["r1_decile"] = pd.qcut(df_clean["r1"], q=10, labels=False) + 1
        decile_stats = df_clean.groupby("r1_decile").agg(
            r1_mean=("r1", lambda s: float(s.mean() * 10000)),  # bps
            r13_mean=("r13", lambda s: float(s.mean() * 10000)), # bps
            count=("r13", "count"),
        ).to_dict(orient="index")
        sym_res["r1_deciles_overall_bps"] = decile_stats

        # En Holdout (2024-2026)
        holdout_mask = df_clean["date"] >= "2024-01-01"
        df_ho = df_clean[holdout_mask].copy()
        df_ho["r1_decile"] = pd.qcut(df_ho["r1"], q=10, labels=False) + 1
        decile_ho = df_ho.groupby("r1_decile").agg(
            r1_mean=("r1", lambda s: float(s.mean() * 10000)),
            r13_mean=("r13", lambda s: float(s.mean() * 10000)),
            count=("r13", "count"),
        ).to_dict(orient="index")
        sym_res["r1_deciles_holdout_bps"] = decile_ho

        # 2. Desglose por día de la semana (Lunes=0 a Viernes=4) en Holdout
        df_ho["weekday"] = df_ho["date"].dt.day_name()
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        weekday_stats = {}
        for hyp in ["H1", "H2", "H3", "H4", "B1"]:
            sim = simulate_trades(
                df=df_ho,
                signal_col=f"sig_{hyp}",
                multiplier_usd_per_point=mult,
                tick_size_points=tick_sz,
                tick_value_usd=tick_val,
                cost_spec=DEFAULT_COST_CASES["base"],
            )
            sim["weekday"] = df_ho["weekday"]
            w_pnl = sim.groupby("weekday")["net_pnl_usd"].sum().reindex(weekday_order).to_dict()
            weekday_stats[hyp] = {k: float(v) for k, v in w_pnl.items()}
        sym_res["weekday_net_pnl_holdout_usd"] = weekday_stats

        # 3. Desglose por terciles de volatilidad previa en Holdout
        # Baja: vol <= vol_tercile_low, Media: entre terciles, Alta: vol >= vol_tercile_high
        vol_terciles_stats = {}
        t_low = df_ho["first_30m_vol"] <= df_ho["vol_tercile_low"]
        t_high = df_ho["first_30m_vol"] >= df_ho["vol_tercile_high"]
        t_mid = (~t_low) & (~t_high) & (~df_ho["vol_tercile_low"].isna())

        for hyp in ["H1", "H2", "H3", "H4"]:
            sim = simulate_trades(
                df=df_ho,
                signal_col=f"sig_{hyp}",
                multiplier_usd_per_point=mult,
                tick_size_points=tick_sz,
                tick_value_usd=tick_val,
                cost_spec=DEFAULT_COST_CASES["base"],
            )
            vol_terciles_stats[hyp] = {
                "low_vol_pnl_usd": float(sim.loc[t_low, "net_pnl_usd"].sum()),
                "mid_vol_pnl_usd": float(sim.loc[t_mid, "net_pnl_usd"].sum()),
                "high_vol_pnl_usd": float(sim.loc[t_high, "net_pnl_usd"].sum()),
            }
        sym_res["volatility_terciles_pnl_holdout_usd"] = vol_terciles_stats

        # 4. Costo de equilibrio (breakeven) por operación en Holdout
        # Costo por trade = Gross PnL / n_trades. Si Gross <= 0, el breakeven es $0.00 (o negativo).
        breakevens = {}
        for hyp in ["H1", "H2", "H3", "H4"]:
            sim = simulate_trades(
                df=df_ho,
                signal_col=f"sig_{hyp}",
                multiplier_usd_per_point=mult,
                tick_size_points=tick_sz,
                tick_value_usd=tick_val,
                cost_spec=CostSpec(slippage_ticks_per_side=0.0, commission_usd_per_side=0.0),
            )
            gross_pnl = float(sim["gross_pnl_usd"].sum())
            n_trades = int((sim["trade_signal"] != 0).sum())
            be_per_trade = (gross_pnl / n_trades) if n_trades > 0 else 0.0
            # En ticks (redondeo ida y vuelta): be_per_trade / (2 * tick_value_usd)
            be_ticks_per_side = (be_per_trade - 4.00) / (2.0 * tick_val) if tick_val > 0 else 0.0
            breakevens[hyp] = {
                "gross_pnl_usd": gross_pnl,
                "n_trades": n_trades,
                "breakeven_cost_usd_per_trade": be_per_trade,
                "breakeven_slippage_ticks_per_side_at_comm2": be_ticks_per_side,
            }
        sym_res["breakeven_costs_holdout"] = breakevens

        # 5. R² OOS (Campbell-Thompson) vs Benchmark histórico
        # Dev + Val como in-sample (2018-2023), Holdout como out-of-sample (2024-2026)
        train_df = df_clean[df_clean["date"] < "2024-01-01"]
        test_df = df_clean[df_clean["date"] >= "2024-01-01"]
        r2_oos_r1 = compute_oos_r_squared(
            y_in=train_df["r13"].values,
            x_in=train_df["r1"].values,
            y_out=test_df["r13"].values,
            x_out=test_df["r1"].values,
        )
        r2_oos_r12 = compute_oos_r_squared(
            y_in=train_df["r13"].values,
            x_in=train_df["r12"].values,
            y_out=test_df["r13"].values,
            x_out=test_df["r12"].values,
        )
        sym_res["campbell_thompson_oos_r_squared"] = {
            "r13_from_r1": r2_oos_r1,
            "r13_from_r12": r2_oos_r12,
        }

        advanced_results[sym] = sym_res

    # Actualizar results.json
    results_data["advanced_diagnostics"] = advanced_results
    with open(REPORTS_DIR / "results.json", "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)
    print("Guardados análisis avanzados en reports/results.json")

    # =========================================================================
    # GENERAR FIGURAS ADICIONALES
    # =========================================================================
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # Figura 1: Retorno r13 por decil de r1
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, sym in zip(axes, ["ES", "NQ"]):
        deciles_data = advanced_results[sym]["r1_deciles_holdout_bps"]
        d_keys = sorted(deciles_data.keys(), key=lambda x: int(x))
        r13_bps = [deciles_data[k]["r13_mean"] for k in d_keys]
        colors = ["#d62728" if v < 0 else "#2ca02c" for v in r13_bps]
        ax.bar(d_keys, r13_bps, color=colors, edgecolor="black", alpha=0.8)
        ax.axhline(0, color="black", linestyle="--", linewidth=0.8)
        ax.set_title(f"Retorno Medio de r13 por Decil de r1 (Holdout) - {sym}", fontsize=12, fontweight="bold")
        ax.set_xlabel("Decil de r1 (1: Más negativo, 10: Más positivo)", fontsize=11)
        ax.set_ylabel("Retorno Medio r13 (puntos base)", fontsize=11)
        ax.set_xticks(range(1, 11))
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "r13_by_r1_deciles.png", dpi=300)
    plt.close()
    print("Guardada reports/figures/r13_by_r1_deciles.png")

    # Figura 2: Curva de sensibilidad al deslizamiento y punto de equilibrio
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    slips = [0.0, 0.25, 0.5, 1.0, 2.0]
    for ax, sym, mult, tick_sz, tick_val in [
        (axes[0], "ES", 50.0, 0.25, 12.50),
        (axes[1], "NQ", 20.0, 0.25, 5.00),
    ]:
        df_ho = (df_es if sym == "ES" else df_nq).copy()
        df_ho = df_ho[df_ho["date"] >= "2024-01-01"].reset_index(drop=True)
        for hyp, color in [("H1", "#1f77b4"), ("H2", "#ff7f0e"), ("H3", "#2ca02c"), ("H4", "#d62728")]:
            pnls = []
            for s in slips:
                sim = simulate_trades(
                    df=df_ho,
                    signal_col=f"sig_{hyp}",
                    multiplier_usd_per_point=mult,
                    tick_size_points=tick_sz,
                    tick_value_usd=tick_val,
                    cost_spec=CostSpec(slippage_ticks_per_side=s, commission_usd_per_side=2.00),
                )
                pnls.append(sim["net_pnl_usd"].sum())
            ax.plot(slips, pnls, marker="o", label=hyp, color=color, linewidth=1.5)

        ax.axhline(0, color="red", linestyle="--", linewidth=1.0, label="Breakeven (PnL=0)")
        ax.set_title(f"Sensibilidad al Deslizamiento (Holdout) - {sym}", fontsize=12, fontweight="bold")
        ax.set_xlabel("Deslizamiento (ticks por lado)", fontsize=11)
        ax.set_ylabel("PnL Neto Total (USD)", fontsize=11)
        ax.legend(frameon=True)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "cost_sensitivity_breakeven.png", dpi=300)
    plt.close()
    print("Guardada reports/figures/cost_sensitivity_breakeven.png")

    # Figura 3: PnL Neto anual por hipótesis
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
    for ax, sym, df, mult, tick_sz, tick_val in [
        (axes[0], "ES", df_es, 50.0, 0.25, 12.50),
        (axes[1], "NQ", df_nq, 20.0, 0.25, 5.00),
    ]:
        for hyp in ["H1", "H2", "H3", "H4"]:
            sim = simulate_trades(
                df=df,
                signal_col=f"sig_{hyp}",
                multiplier_usd_per_point=mult,
                tick_size_points=tick_sz,
                tick_value_usd=tick_val,
                cost_spec=DEFAULT_COST_CASES["base"],
            )
            sim["year"] = pd.to_datetime(sim["date"]).dt.year
            y_pnl = sim.groupby("year")["net_pnl_usd"].sum().reindex(years).fillna(0)
            ax.plot(years, y_pnl, marker="s", label=hyp, linewidth=1.5)

        ax.axhline(0, color="black", linestyle="--", linewidth=0.8)
        ax.set_title(f"PnL Neto Anual (2018–2026) - {sym}", fontsize=12, fontweight="bold")
        ax.set_xlabel("Año", fontsize=11)
        ax.set_ylabel("USD / Contrato", fontsize=11)
        ax.legend(frameon=True)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "yearly_results.png", dpi=300)
    plt.close()
    print("Guardada reports/figures/yearly_results.png")


if __name__ == "__main__":
    main()
