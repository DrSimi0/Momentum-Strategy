"""Genera gráfico comparativo de Equity Curve Train (3 Años) vs Test Virgen (2 Años)
para la estrategia EMA 200 en NQ 5m, NQ 15m, ES 15m y ES 5m.
"""
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.strategies.intraday_ema200_strategy import (
    IntradayEma200Params,
    run_ema200_backtest,
)
from src.backtest.engine_sma_confluence import AssetCosts

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR = Path("C:/Users/leono/.gemini/antigravity/brain/bad9add8-21bd-44f6-a0bb-469902521894")

DATE_START_5Y = pd.Timestamp("2021-10-20", tz="UTC")
DATE_SPLIT_3Y = pd.Timestamp("2024-10-20", tz="UTC")
DATE_END_5Y = pd.Timestamp("2026-10-19 23:59:59", tz="UTC")
INITIAL_CAPITAL = 50000.0


def plot_train_test_curves():
    costs_nq = AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0)
    costs_es = AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0)

    configs = [
        ("NQ 5m (EMA 200 Cross, k=2.5, m=3.0)", "NQ_5m.parquet", costs_nq, IntradayEma200Params(trend_ema_period=200, atr_k=2.5, tp_m=3.0, trigger_type="price_cross", moc_close_time="15:50")),
        ("NQ 15m (EMA 200 Cross, k=2.0, m=1.5)", "NQ_15m.parquet", costs_nq, IntradayEma200Params(trend_ema_period=200, atr_k=2.0, tp_m=1.5, trigger_type="price_cross", moc_close_time="15:45")),
        ("ES 15m (EMA 200 Vela, k=2.0, m=1.5)", "ES_15m.parquet", costs_es, IntradayEma200Params(trend_ema_period=200, atr_k=2.0, tp_m=1.5, trigger_type="candle_pattern", moc_close_time="15:45")),
        ("ES 5m (EMA 200 Cross, k=2.0, m=3.0)", "ES_5m.parquet", costs_es, IntradayEma200Params(trend_ema_period=200, atr_k=2.0, tp_m=3.0, trigger_type="price_cross", moc_close_time="15:50")),
    ]

    fig, axes = plt.subplots(4, 1, figsize=(14, 16), sharex=True)
    plt.subplots_adjust(hspace=0.28)

    for ax, (title, f_name, costs, params) in zip(axes, configs):
        df = pd.read_parquet(PROCESSED_DIR / f_name)
        df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
        df = df[df["ts_event"] >= DATE_START_5Y - pd.Timedelta(days=30)].copy().reset_index(drop=True)

        res = run_ema200_backtest(df, params, costs, INITIAL_CAPITAL)
        trades = res["trades"]

        # Filtrar trades dentro de los 5 años
        trades_5y = [t for t in trades if DATE_START_5Y <= pd.to_datetime(t["entry_date"], utc=True) <= DATE_END_5Y]
        
        # Serie diaria de equity
        daily_pnl = {}
        for t in trades_5y:
            d = pd.to_datetime(t["exit_date"], utc=True).date()
            daily_pnl[d] = daily_pnl.get(d, 0.0) + t["net_pnl_usd"]

        all_dates = pd.date_range(DATE_START_5Y.date(), DATE_END_5Y.date(), freq="B")
        cum_s = pd.Series([daily_pnl.get(d.date(), 0.0) for d in all_dates], index=all_dates).cumsum()

        split_date = pd.Timestamp("2024-10-20")

        # Pintar curva Train e In-Sample vs Test
        train_mask = cum_s.index < split_date
        test_mask = cum_s.index >= split_date

        ax.plot(cum_s.index[train_mask], cum_s[train_mask], label="Train In-Sample (3 Años: 2021-2024)", color="#2b5c8f", lw=2)
        ax.plot(cum_s.index[test_mask], cum_s[test_mask], label="Test Virgen Out-of-Sample (2 Años: 2024-2026)", color="#d95f02", lw=2.5)

        ax.axvline(split_date, color="black", linestyle="--", lw=1.5, alpha=0.8, label="Límite Holdout Virgen (2024-10-20)")
        ax.axhline(0, color="gray", linestyle=":", lw=1)

        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_ylabel("PnL Acumulado ($ USD)", fontsize=10)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="upper left", fontsize=9)
        ax.yaxis.set_major_formatter("${x:,.0f}")

    axes[-1].set_xlabel("Fecha (2021 - 2026)", fontsize=11)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    plt.suptitle("ESTUDIO DE VALIDACIÓN CIEGA: ESTRATEGIA INTRADÍA EMA 200\nEntrenamiento In-Sample (3 Años) vs Holdout Virgen Out-of-Sample (2 Años)", fontsize=14, fontweight="bold", y=0.995)
    plt.tight_layout()

    out_file = FIGURES_DIR / "ema200_train_vs_test_equity_curves.png"
    plt.savefig(out_file, dpi=150)
    plt.close()
    print("Gráfica guardada en:", out_file)

    # Copiar al directorio de artefactos si existe
    if ARTIFACT_DIR.exists():
        import shutil
        shutil.copy(out_file, ARTIFACT_DIR / "ema200_train_vs_test_equity_curves.png")
        print("Copiada gráfica a directorio de artefactos:", ARTIFACT_DIR)


if __name__ == "__main__":
    plot_train_test_curves()
