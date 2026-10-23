"""Script para generar la suite de gráficas de Drawdown vs Tiempo y Porcentaje.
Produce:
1. Gráfica Submarina (Underwater Chart) de series temporales continuas (2010 - 2026):
   Drawdown en % de capital inicial ($50,000 USD) para H4, H1, M15 y M5.
2. Gráfica de Dispersión: Max Drawdown % vs Duración Máxima del Drawdown en días de mercado.
3. Copia las figuras en reports/figures/ y en el directorio de artefactos para visualización directa.
"""
from pathlib import Path
import shutil
import sys
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from src.strategies.intraday_unified_strategy import (
    IntradayStrategyParams,
    run_intraday_backtest,
)
from src.strategies.unified_strategy import (
    UnifiedStrategyParams,
    run_unified_backtest,
)
from src.analysis.daily_equity_audit import build_daily_equity_curve
from src.backtest.engine_sma_confluence import AssetCosts

PROCESSED_DIR = Path("data/processed")
FIGURES_DIR = Path("reports/figures")
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR = Path("C:/Users/leono/.gemini/antigravity/brain/bad9add8-21bd-44f6-a0bb-469902521894")


def get_costs(symbol: str) -> AssetCosts:
    if symbol == "ES":
        return AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0)
    elif symbol == "NQ":
        return AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0)
    raise ValueError(f"Símbolo {symbol} no reconocido")


def calculate_drawdown_series_and_durations():
    configs = [
        # TF, Label, Symbol, Timeframe, Type, Params, Color, LineStyle
        ("H4", "NQ 4h Swing", "NQ", "4h", "unified", UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0), "#1f77b4", "-"),
        ("H4", "ES 4h Swing", "ES", "4h", "unified", UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0), "#aec7e8", "--"),
        ("H1", "NQ 1h Swing", "NQ", "1h", "unified", UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0), "#d62728", "-"),
        ("H1", "ES 1h Swing", "ES", "1h", "unified", UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0), "#ff9896", "--"),
        ("M15", "NQ 15m MOC Fix", "NQ", "15m", "intraday", IntradayStrategyParams(fast_ema=20, slow_ema=80, atr_k=2.0, tp_m=2.0, rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:45", use_volatility_filter=True), "#2ca02c", "-"),
        ("M15", "NQ 15m Pre-Fix", "NQ", "15m", "intraday", IntradayStrategyParams(fast_ema=20, slow_ema=80, atr_k=2.0, tp_m=2.0, rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50", use_volatility_filter=True), "#98df8a", ":"),
        ("M15", "ES 15m Base", "ES", "15m", "intraday", IntradayStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0, rth_start_time="00:00", rth_end_time="23:59", moc_close_time="23:59", use_volatility_filter=False), "#8c564b", "--"),
        ("M5", "ES 5m Agresiva", "ES", "5m", "intraday", IntradayStrategyParams(fast_ema=10, slow_ema=50, atr_k=1.5, tp_m=2.0, rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50", use_volatility_filter=True), "#9467bd", "-"),
        ("M5", "NQ 5m Opt", "NQ", "5m", "intraday", IntradayStrategyParams(fast_ema=20, slow_ema=80, atr_k=2.0, tp_m=2.0, rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50", use_volatility_filter=True), "#ff7f0e", "--"),
        ("M5", "NQ 5m Sin Vol (Quiebra)", "NQ", "5m", "intraday", IntradayStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0, rth_start_time="00:00", rth_end_time="23:59", moc_close_time="15:50", use_volatility_filter=False), "#7f7f7f", "-."),
    ]

    results = []

    for tf_group, label, sym, tf, engine_type, params, color, lstyle in configs:
        df = pd.read_parquet(PROCESSED_DIR / f"{sym}_{tf}.parquet")
        costs = get_costs(sym)
        if engine_type == "unified":
            res = run_unified_backtest(df, params, costs)
        else:
            res = run_intraday_backtest(df, params, costs)

        daily = build_daily_equity_curve(res["trades"], df, initial_capital=50000.0)
        d_df = daily["daily_df"]
        d_df["date"] = pd.to_datetime(d_df["date"])

        # Drawdown en % del capital inicial fijo ($50,000 USD)
        # Se expresa como valor negativo para el gráfico submarino: - (peak - equity) / 50000 * 100
        d_df["dd_pct_init"] = - ((d_df["peak"] - d_df["equity"]) / 50000.0) * 100.0
        max_dd_pct_init = float(((d_df["peak"] - d_df["equity"]) / 50000.0).max() * 100.0)

        # Cálculo de la duración máxima de drawdown (en días de mercado consecutivos en DD)
        in_dd = (d_df["peak"] - d_df["equity"]) > 1e-4
        dd_durations = []
        cur_dur = 0
        for val in in_dd:
            if val:
                cur_dur += 1
            else:
                if cur_dur > 0:
                    dd_durations.append(cur_dur)
                cur_dur = 0
        if cur_dur > 0:
            dd_durations.append(cur_dur)

        max_dd_days = max(dd_durations) if dd_durations else 0
        avg_dd_days = float(np.mean(dd_durations)) if dd_durations else 0.0

        results.append({
            "group": tf_group,
            "label": label,
            "symbol": sym,
            "tf": tf,
            "color": color,
            "lstyle": lstyle,
            "daily_df": d_df[["date", "dd_pct_init", "equity", "peak"]],
            "max_dd_pct_init": max_dd_pct_init,
            "max_dd_days": max_dd_days,
            "avg_dd_days": avg_dd_days,
        })

    return results


def plot_drawdown_underwater_charts(results: List[Dict[str, Any]]):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 11), sharex=True, gridspec_kw={"height_ratios": [1, 1]})

    # Panel 1: Swing (H4 y H1)
    swing_res = [r for r in results if r["group"] in ["H4", "H1"]]
    for r in swing_res:
        df = r["daily_df"]
        ax1.plot(df["date"], df["dd_pct_init"], label=f"{r['label']} (Max DD: {r['max_dd_pct_init']:.1f}%)", color=r["color"], linestyle=r["lstyle"], linewidth=1.5, alpha=0.85)

    ax1.set_title("Evolución Temporal del Drawdown (% Capital Inicial $50k) - Temporalidades Mayores Swing (H4 y H1)", fontsize=13, fontweight="bold", pad=10)
    ax1.set_ylabel("Drawdown (% del Capital)", fontsize=11, fontweight="bold")
    ax1.axhline(0, color="black", linestyle="-", linewidth=0.8, alpha=0.7)
    ax1.axhline(-50, color="orange", linestyle=":", linewidth=1.2, alpha=0.8, label="Umbral de Alerta (-50%)")
    ax1.axhline(-100, color="red", linestyle="--", linewidth=1.5, alpha=0.9, label="Umbral de Quiebra Total (-100%)")
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.legend(loc="lower left", fontsize=9, framealpha=0.9)
    ax1.set_ylim(-160, 5)

    # Panel 2: Menor Temporalidad (M15 y M5)
    intra_res = [r for r in results if r["group"] in ["M15", "M5"]]
    for r in intra_res:
        df = r["daily_df"]
        ax2.plot(df["date"], df["dd_pct_init"], label=f"{r['label']} (Max DD: {r['max_dd_pct_init']:.1f}%)", color=r["color"], linestyle=r["lstyle"], linewidth=1.5, alpha=0.85)

    ax2.set_title("Evolución Temporal del Drawdown (% Capital Inicial $50k) - Menor Temporalidad Intradía (M15 y M5)", fontsize=13, fontweight="bold", pad=10)
    ax2.set_xlabel("Línea Temporal (2010 - 2026)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Drawdown (% del Capital)", fontsize=11, fontweight="bold")
    ax2.axhline(0, color="black", linestyle="-", linewidth=0.8, alpha=0.7)
    ax2.axhline(-50, color="orange", linestyle=":", linewidth=1.2, alpha=0.8, label="Umbral de Alerta (-50%)")
    ax2.axhline(-100, color="red", linestyle="--", linewidth=1.5, alpha=0.9, label="Umbral de Quiebra Total (-100%)")
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.legend(loc="lower left", fontsize=9, framealpha=0.9)
    ax2.set_ylim(-160, 5)

    ax2.xaxis.set_major_locator(mdates.YearLocator(2))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    plt.tight_layout()
    out_path = FIGURES_DIR / "drawdown_temporal_series_comparative.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print("Guardada gráfica temporal en:", out_path)

    # Copiar al directorio de artefactos para renderizado
    if ARTIFACT_DIR.exists():
        shutil.copy(out_path, ARTIFACT_DIR / "drawdown_temporal_series_comparative.png")


def plot_max_drawdown_vs_duration_scatter(results: List[Dict[str, Any]]):
    fig, ax = plt.subplots(figsize=(12, 8))

    for r in results:
        # Convertir días de mercado a meses aproximados (21 días hábiles por mes)
        dur_months = r["max_dd_days"] / 21.0
        dd_pct = r["max_dd_pct_init"]
        
        # Tamaño del punto según timeframe
        size = 180 if r["group"] in ["H4", "H1"] else 140
        marker = "o" if r["group"] == "H4" else ("s" if r["group"] == "H1" else ("^" if r["group"] == "M15" else "D"))

        ax.scatter(dur_months, dd_pct, color=r["color"], s=size, marker=marker, edgecolors="black", linewidth=1.2, zorder=4, label=f"[{r['group']}] {r['label']}")
        
        # Etiqueta de texto al lado del punto
        offset_x = 0.5
        offset_y = 1.5 if dd_pct < 120 else -4.0
        ax.annotate(r["label"], (dur_months + offset_x, dd_pct + offset_y), fontsize=9, fontweight="bold", alpha=0.9)

    ax.axhline(100, color="red", linestyle="--", linewidth=1.5, alpha=0.8, label="Límite de Quiebra (100% de la Cuenta)")
    ax.axhline(50, color="orange", linestyle=":", linewidth=1.2, alpha=0.8, label="Umbral de Peligro (50%)")
    ax.axvline(12, color="gray", linestyle=":", linewidth=1.0, alpha=0.6, label="1 Año de Recuperación")
    ax.axvline(24, color="gray", linestyle="--", linewidth=1.0, alpha=0.6, label="2 Años de Recuperación")

    ax.set_title("Relación Bidimensional: Máximo Drawdown (%) vs Tiempo Máximo en Recuperarse (Meses)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Duración Máxima del Drawdown (Meses de Mercado)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Máximo Drawdown (% sobre Capital Inicial $50,000 USD)", fontsize=11, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.set_ylim(10, 160)
    ax.set_xlim(0, 50)

    # Cuadrantes explicativos
    ax.text(3, 140, "CUADRANTE CRÍTICO\nQuiebra Severa / Dilatada", fontsize=10, color="red", fontweight="bold", bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))
    ax.text(3, 20, "ZONA DE MENOR EROSIÓN\nBajo Drawdown (< 30%)", fontsize=10, color="green", fontweight="bold", bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

    plt.tight_layout()
    out_path = FIGURES_DIR / "max_drawdown_vs_duracion_scatter.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print("Guardada gráfica de dispersión en:", out_path)

    if ARTIFACT_DIR.exists():
        shutil.copy(out_path, ARTIFACT_DIR / "max_drawdown_vs_duracion_scatter.png")


def main():
    print("Calculando series de drawdown y duraciones...")
    results = calculate_drawdown_series_and_durations()
    plot_drawdown_underwater_charts(results)
    plot_max_drawdown_vs_duration_scatter(results)
    print("Proceso de visualización completado con éxito.")


if __name__ == "__main__":
    main()
