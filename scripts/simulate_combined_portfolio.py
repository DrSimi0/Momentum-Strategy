"""Simulación de Cartera Multiactivo Combinada (50% Futuros, 50% Cripto)
Evaluando correlación, sinergia, diversificación y reducción de drawdown
en el periodo fuera de muestra (Test Final).
"""
import json
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.backtest.engine_sma_confluence import StrategyParams, AssetCosts, run_sma_confluence_backtest
from src.analysis.grid_search import partition_data_60_20_20

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPORTS_DIR = Path("reports")
TABLES_DIR = REPORTS_DIR / "tables"
FIGURES_DIR = REPORTS_DIR / "figures"


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Configuración de Costos
    costs_es = AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5)
    costs_nq = AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5)
    costs_btc = AssetCosts(asset_type="crypto", multiplier=1.0, commission_per_side=0.0005, slippage_per_side=0.0002, funding_rate_8h=0.0001)
    costs_eth = AssetCosts(asset_type="crypto", multiplier=1.0, commission_per_side=0.0005, slippage_per_side=0.0003, funding_rate_8h=0.0001)

    # 2. Cargar datos en 4h y obtener partición Test
    df_es = pd.read_parquet("data/processed/ES_4h.parquet")
    df_nq = pd.read_parquet("data/processed/NQ_4h.parquet")
    df_btc = pd.read_parquet("data/processed/BTC_USDT_4h.parquet")
    df_eth = pd.read_parquet("data/processed/ETH_USDT_4h.parquet")

    _, _, test_es = partition_data_60_20_20(df_es)
    _, _, test_nq = partition_data_60_20_20(df_nq)
    _, _, test_btc = partition_data_60_20_20(df_btc)
    _, _, test_eth = partition_data_60_20_20(df_eth)

    # 3. Definir Estrategias Especializadas
    # Subcartera Futuros: Confluencia 3 SMAs (20, 100, 150) + MACD (16,35,9) + RSI 14
    p_fut = StrategyParams(num_smas=3, fast_sma=20, mid_sma=100, slow_sma=150, macd_fast=16, macd_slow=35, macd_signal=9, rsi_period=14, atr_k=2.0, tp_m=2.0)

    # Subcartera Cripto: Tendencia Pura 2 SMAs (21, 200) sin osciladores
    p_cry = StrategyParams(num_smas=2, fast_sma=21, slow_sma=200, use_macd=False, use_rsi=False, atr_k=3.0, tp_m=2.0)

    # 4. Ejecutar Backtests Individuales en Test
    res_es = run_sma_confluence_backtest(test_es, p_fut, costs_es)
    res_nq = run_sma_confluence_backtest(test_nq, p_fut, costs_nq)
    res_btc = run_sma_confluence_backtest(test_btc, p_cry, costs_btc)
    res_eth = run_sma_confluence_backtest(test_eth, p_cry, costs_eth)

    # 5. Sincronizar fechas y construir retornos diarios sobre el periodo común de Test
    # Normalizamos a naive UTC para evitar discordancias de timezone
    raw_start = max(test_es["ts_event"].min(), test_btc["ts_event"].min())
    raw_end = min(test_es["ts_event"].max(), test_btc["ts_event"].max())
    common_start = pd.to_datetime(raw_start).tz_localize(None) if pd.to_datetime(raw_start).tz is not None else pd.to_datetime(raw_start)
    common_end = pd.to_datetime(raw_end).tz_localize(None) if pd.to_datetime(raw_end).tz is not None else pd.to_datetime(raw_end)
    logger.info(f"Periodo de prueba común sincronizado: {common_start.date()} a {common_end.date()}")

    all_dates = pd.date_range(start=common_start.floor("D"), end=common_end.ceil("D"), freq="D")
    daily_df = pd.DataFrame(index=all_dates)
    daily_df["pnl_es"] = 0.0
    daily_df["pnl_nq"] = 0.0
    daily_df["pnl_btc"] = 0.0
    daily_df["pnl_eth"] = 0.0

    def add_trades_to_daily(trades_list, col_name):
        count = 0
        for t in trades_list:
            dt = pd.to_datetime(t["exit_date"])
            if dt.tz is not None:
                dt = dt.tz_localize(None)
            exit_d = dt.floor("D")
            if exit_d in daily_df.index:
                daily_df.loc[exit_d, col_name] += t["net_pnl_usd"]
                count += 1
        logger.info(f"Asignados {count}/{len(trades_list)} trades en periodo común para {col_name}")

    add_trades_to_daily(res_es["trades"], "pnl_es")
    add_trades_to_daily(res_nq["trades"], "pnl_nq")
    add_trades_to_daily(res_btc["trades"], "pnl_btc")
    add_trades_to_daily(res_eth["trades"], "pnl_eth")

    # 6. Ponderación de Cartera Equilibrada 50% Futuros / 50% Cripto
    # Normalización: Para balancear el tamaño de los contratos futuros con cripto,
    # escalamos la contribución de futuros al 50% del peso monetario conjunto
    # Sub-cartera Futuros: (ES + NQ) / 2
    # Sub-cartera Cripto: (BTC + ETH) / 2
    # Para comparar en escala equiponderada de riesgo unitario:
    daily_df["futuros_subportfolio"] = 0.5 * daily_df["pnl_es"] + 0.5 * daily_df["pnl_nq"]
    daily_df["crypto_subportfolio"] = 0.5 * daily_df["pnl_btc"] + 0.5 * daily_df["pnl_eth"]

    # Cartera combinada 50% Futuros y 50% Cripto
    # Escalamos Cripto x3 para equiparar la exposición de nocional a un tamaño institucional equivalente
    crypto_scaling = 3.0
    daily_df["crypto_subportfolio_scaled"] = daily_df["crypto_subportfolio"] * crypto_scaling
    daily_df["combined_portfolio"] = 0.5 * daily_df["futuros_subportfolio"] + 0.5 * daily_df["crypto_subportfolio_scaled"]

    # 7. Cálculo de Métricas y Drawdowns
    def compute_stats(series: pd.Series, annualization: float = 365.0):
        cum = series.cumsum()
        peak = cum.cummax()
        dd = peak - cum
        max_dd = float(dd.max())
        total_pnl = float(cum.iloc[-1])
        std = float(series.std())
        mean = float(series.mean())
        sharpe = float((mean / std) * np.sqrt(annualization)) if std > 1e-9 else 0.0
        calmar = (total_pnl / max_dd) if max_dd > 0 else np.nan
        return {
            "total_pnl": total_pnl,
            "mean_daily": mean,
            "std_daily": std,
            "sharpe": sharpe,
            "max_dd": max_dd,
            "calmar": calmar,
        }

    stats_es = compute_stats(daily_df["pnl_es"], 252)
    stats_nq = compute_stats(daily_df["pnl_nq"], 252)
    stats_fut = compute_stats(daily_df["futuros_subportfolio"], 252)

    stats_btc = compute_stats(daily_df["pnl_btc"], 365)
    stats_eth = compute_stats(daily_df["pnl_eth"], 365)
    stats_cry = compute_stats(daily_df["crypto_subportfolio"], 365)

    stats_combined = compute_stats(daily_df["combined_portfolio"], 365)

    # 8. Matriz de Correlación
    corr_matrix = daily_df[["pnl_es", "pnl_nq", "pnl_btc", "pnl_eth"]].corr()
    logger.info("Matriz de correlación diaria:\n" + corr_matrix.to_string())

    # Reducción de Drawdown
    avg_individual_dd = (stats_fut["max_dd"] + stats_cry["max_dd"] * crypto_scaling) / 2.0
    combined_dd = stats_combined["max_dd"]
    dd_reduction_pct = ((avg_individual_dd - combined_dd) / avg_individual_dd) * 100.0 if avg_individual_dd > 0 else 0.0

    # 9. Generar Gráfico de Equity Curves
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, gridspec_kw={"height_ratios": [2.5, 1]})

    # Curvas acumuladas
    ax1.plot(daily_df.index, daily_df["futuros_subportfolio"].cumsum(), label=f"Sub-cartera Futuros (Sharpe {stats_fut['sharpe']:.2f})", color="#1f77b4", linewidth=2)
    ax1.plot(daily_df.index, daily_df["crypto_subportfolio_scaled"].cumsum(), label=f"Sub-cartera Cripto Solo-SMA (Sharpe {stats_cry['sharpe']:.2f})", color="#ff7f0e", linewidth=2)
    ax1.plot(daily_df.index, daily_df["combined_portfolio"].cumsum(), label=f"CARTERA COMBINADA 50/50 (Sharpe {stats_combined['sharpe']:.2f})", color="#2ca02c", linewidth=3)
    ax1.set_ylabel("PnL Acumulado (USD)", fontsize=12, fontweight="bold")
    ax1.set_title("Simulación de Cartera Multiactivo: Futuros CME + Criptoactivos (Test Final Fuera de Muestra)", fontsize=14, fontweight="bold")
    ax1.legend(loc="upper left", fontsize=11, frameon=True)
    ax1.grid(True, linestyle="--", alpha=0.6)

    # Drawdown de la cartera combinada
    cum_comb = daily_df["combined_portfolio"].cumsum()
    peak_comb = cum_comb.cummax()
    dd_comb = peak_comb - cum_comb
    ax2.fill_between(daily_df.index, -dd_comb, 0, color="#d62728", alpha=0.4, label=f"Drawdown Cartera Combinada (Max: -${stats_combined['max_dd']:,.0f})")
    ax2.set_ylabel("Drawdown (USD)", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Fecha", fontsize=12, fontweight="bold")
    ax2.legend(loc="lower left", fontsize=11, frameon=True)
    ax2.grid(True, linestyle="--", alpha=0.6)

    fig_out = FIGURES_DIR / "portfolio_combined_equity.png"
    plt.tight_layout()
    plt.savefig(fig_out, dpi=300)
    plt.close()
    logger.info(f"Gráfico de cartera guardado en: {fig_out}")

    # 10. Guardar Tablas y JSON
    summary_data = [
        {"Activo / Cartera": "ES (E-mini S&P 500)", "Estrategia": "Confluencia 3 SMAs (20,100,150) + MACD + RSI", "PnL_USD": stats_es["total_pnl"], "Sharpe": stats_es["sharpe"], "Max_Drawdown_USD": stats_es["max_dd"], "Calmar": stats_es["calmar"]},
        {"Activo / Cartera": "NQ (E-mini Nasdaq)", "Estrategia": "Confluencia 3 SMAs (20,100,150) + MACD + RSI", "PnL_USD": stats_nq["total_pnl"], "Sharpe": stats_nq["sharpe"], "Max_Drawdown_USD": stats_nq["max_dd"], "Calmar": stats_nq["calmar"]},
        {"Activo / Cartera": "Sub-cartera Futuros", "Estrategia": "50% ES + 50% NQ", "PnL_USD": stats_fut["total_pnl"], "Sharpe": stats_fut["sharpe"], "Max_Drawdown_USD": stats_fut["max_dd"], "Calmar": stats_fut["calmar"]},
        {"Activo / Cartera": "BTC-USDT", "Estrategia": "Solo-SMA 21/200 Tendencial", "PnL_USD": stats_btc["total_pnl"], "Sharpe": stats_btc["sharpe"], "Max_Drawdown_USD": stats_btc["max_dd"], "Calmar": stats_btc["calmar"]},
        {"Activo / Cartera": "ETH-USDT", "Estrategia": "Solo-SMA 21/200 Tendencial", "PnL_USD": stats_eth["total_pnl"], "Sharpe": stats_eth["sharpe"], "Max_Drawdown_USD": stats_eth["max_dd"], "Calmar": stats_eth["calmar"]},
        {"Activo / Cartera": "Sub-cartera Cripto", "Estrategia": "50% BTC + 50% ETH", "PnL_USD": stats_cry["total_pnl"], "Sharpe": stats_cry["sharpe"], "Max_Drawdown_USD": stats_cry["max_dd"], "Calmar": stats_cry["calmar"]},
        {"Activo / Cartera": "CARTERA COMBINADA 50/50", "Estrategia": "50% Futuros + 50% Cripto", "PnL_USD": stats_combined["total_pnl"], "Sharpe": stats_combined["sharpe"], "Max_Drawdown_USD": stats_combined["max_dd"], "Calmar": stats_combined["calmar"]},
    ]

    df_summary = pd.DataFrame(summary_data)
    csv_out = TABLES_DIR / "portfolio_combined_results.csv"
    df_summary.to_csv(csv_out, index=False)

    corr_out = TABLES_DIR / "portfolio_correlation_matrix.csv"
    corr_matrix.to_csv(corr_out)

    results_payload = {
        "common_test_start": str(common_start),
        "common_test_end": str(common_end),
        "summary": summary_data,
        "correlation_matrix": corr_matrix.to_dict(),
        "drawdown_reduction_pct": dd_reduction_pct,
    }
    with open(REPORTS_DIR / "portfolio_combined.json", "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)

    logger.info(f"Resultados guardados en {csv_out} y {REPORTS_DIR / 'portfolio_combined.json'}")


if __name__ == "__main__":
    main()
