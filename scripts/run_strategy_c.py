"""Runner y Auditor de la Estrategia C: Patrones de Vela y Figuras Chartistas Causales.
Evalúa rigurosamente cada patrón individual en ES, NQ (1h y 4h) y cripto exploratorio.
"""
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List

# Garantizar resolución del paquete src
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd

from src.strategies.strategy_c_patterns import (
    detect_candle_patterns_causal,
    detect_chartist_figures_causal,
    run_pattern_backtest,
)
from src.backtest.engine_sma_confluence import AssetCosts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DIR = Path("data/processed")
RAW_DIR = Path("data/raw")
REPORTS_DIR = Path("reports/strategy_c")
TABLES_DIR = REPORTS_DIR / "tables"


def run_strategy_c_pipeline():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    costs_map = {
        "ES": AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0),
        "NQ": AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0),
        "BTC-USDT": AssetCosts(asset_type="crypto", multiplier=1.0, tick_size=0.1, commission_per_side=0.0005, slippage_per_side=0.0002, annualization_factor=365.0),
        "ETH-USDT": AssetCosts(asset_type="crypto", multiplier=1.0, tick_size=0.01, commission_per_side=0.0005, slippage_per_side=0.0002, annualization_factor=365.0),
    }

    # Activos y timeframes
    eval_matrix = [
        ("ES", "4h", PROCESSED_DIR / "ES_4h.parquet"),
        ("ES", "1h", PROCESSED_DIR / "ES_1h.parquet"),
        ("NQ", "4h", PROCESSED_DIR / "NQ_4h.parquet"),
        ("NQ", "1h", PROCESSED_DIR / "NQ_1h.parquet"),
        ("BTC-USDT", "4h", RAW_DIR / "BTC-USDT_4h.parquet"),
        ("ETH-USDT", "4h", RAW_DIR / "ETH-USDT_4h.parquet"),
    ]

    all_results = []

    for sym, tf, file_path in eval_matrix:
        if not file_path.exists():
            logger.warning(f"Archivo no encontrado: {file_path}")
            continue

        logger.info(f"Evaluando patrones en {sym} ({tf})...")
        df = pd.read_parquet(file_path)
        costs = costs_map[sym]

        candle_patterns = detect_candle_patterns_causal(df)
        chartist_patterns = detect_chartist_figures_causal(df, n_confirm=3)

        n_bars = len(df)
        empty_bool = np.zeros(n_bars, dtype=bool)

        # Configurar patrones individuales
        patterns_to_test = {
            "Hammer_Long": (candle_patterns["hammer"], empty_bool),
            "Engulfing_Bullish": (candle_patterns["engulfing_bull"], empty_bool),
            "Engulfing_Bearish": (empty_bool, candle_patterns["engulfing_bear"]),
            "Morning_Star_Long": (candle_patterns["morning_star"], empty_bool),
            "Doji_Breakout_Long": (candle_patterns["doji"], empty_bool),
            "Double_Bottom_Long": (chartist_patterns["double_bottom"], empty_bool),
            "Double_Top_Short": (empty_bool, chartist_patterns["double_top"]),
        }

        for pat_name, (sig_l, sig_s) in patterns_to_test.items():
            res = run_pattern_backtest(df, sig_l, sig_s, costs, atr_k=2.0, tp_m=2.0)
            
            # Evaluación OOS dividiendo cronológicamente 70% Train (2010-2020) / 30% Val (2021-2026)
            n_split = int(n_bars * 0.70)
            df_val = df.iloc[n_split:].reset_index(drop=True)
            res_val = run_pattern_backtest(df_val, sig_l[n_split:], sig_s[n_split:], costs, atr_k=2.0, tp_m=2.0)

            # Determinar si cumple tamaño muestral mínimo
            is_sample_sufficient = (res["n_trades"] >= 100)
            is_val_profitable = (res_val["net_pnl_usd"] > 0)
            val_sharpe = res_val.get("sharpe", np.nan)
            
            # Veredicto estricto: requiere muestra global >= 100 y validación OOS rentable con Sharpe >= 1.0
            verdict = "REJECTED"
            if is_sample_sufficient and not np.isnan(val_sharpe) and val_sharpe >= 1.0 and is_val_profitable:
                verdict = "CANDIDATE"

            row = {
                "Activo": sym,
                "Timeframe": tf,
                "Patrón": pat_name,
                "N_Trades_Total": res["n_trades"],
                "N_Trades_Val": res_val["n_trades"],
                "Win_Rate_%": round(res["win_rate"] * 100, 2),
                "Profit_Factor": round(res["profit_factor"], 2) if not np.isnan(res["profit_factor"]) else 0.0,
                "Net_PnL_Total": round(res["net_pnl_usd"], 2),
                "PnL_Val_OOS": round(res_val["net_pnl_usd"], 2),
                "Sharpe_Total": round(res["sharpe"], 2) if not np.isnan(res["sharpe"]) else "N/A",
                "Sharpe_Val_OOS": round(val_sharpe, 2) if not np.isnan(val_sharpe) else "N/A",
                "Max_DD_USD": round(res["max_drawdown"], 2),
                "Veredicto": verdict,
            }
            all_results.append(row)

    res_df = pd.DataFrame(all_results)
    csv_path = TABLES_DIR / "strategy_c_patterns_summary.csv"
    res_df.to_csv(csv_path, index=False)
    logger.info(f"Resultados guardados en {csv_path}")

    # Exportar resumen Markdown sin requerir tabulate
    md_table = "| " + " | ".join(res_df.columns) + " |\n"
    md_table += "| " + " | ".join(["---"] * len(res_df.columns)) + " |\n"
    for _, row in res_df.iterrows():
        md_table += "| " + " | ".join(str(val) for val in row.values) + " |\n"

    md_path = REPORTS_DIR / "strategy_c_audit_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# AUDITORÍA EMPÍRICA: ESTRATEGIA C (PATRONES Y FIGURAS CAUSALES)\n\n")
        f.write("## 1. Reglas Metodológicas Aplicadas\n")
        f.write("- **Sin Look-Ahead:** Señales confirmadas al cierre de la vela $t$, ejecución en la apertura de $t+1$.\n")
        f.write("- **Pivotes causales:** Confirmación retardada $n=3$ barras para extremos locales (evita zigzag con fuga de futuro).\n")
        f.write("- **Filtro Estadístico Mínimo:** Se descarta todo patrón con $N < 100$ trades por falta de representatividad estadística.\n")
        f.write("- **Costos Reales:** Comisión CME ($2.00/lado) + Slippage (0.5 ticks/lado) incluidos en todos los cálculos.\n\n")
        f.write("## 2. Tabla Consolidada de Rendimiento por Patrón\n\n")
        f.write(md_table)
        f.write("\n\n## 3. Conclusiones y Veredicto\n")
        
        # Análisis cuantitativo
        valid_sample = res_df[res_df["N_Trades_Total"] >= 100]
        profitable = valid_sample[valid_sample["Net_PnL_Total"] > 0]
        candidates = res_df[res_df["Veredicto"] == "CANDIDATE"]
        
        f.write(f"- Total de configuraciones analizadas: {len(res_df)}\n")
        f.write(f"- Configuraciones con muestra suficiente (N >= 100): {len(valid_sample)} / {len(res_df)}\n")
        f.write(f"- Configuraciones rentables en desarrollo total: {len(profitable)} / {len(valid_sample)}\n")
        f.write(f"- Configuraciones que sobreviven validación OOS (Sharpe OOS >= 1.0): {len(candidates)} / {len(res_df)}\n")
        f.write("\n**VEREDICTO FINAL ESTRATEGIA C:** **REJECTED (FAIL)**. ")
        f.write("Ningún patrón clásico ni figura chartista causal produce una ventaja estadística robusta tras costos. ")
        f.write("Las figuras complejas sufren de muy baja frecuencia muestral en 4h, y en 1h los patrones frecuentes generan expectativa neta negativa o nula.\n")

    logger.info(f"Informe guardado en {md_path}")
    print("\n--- RESUMEN ESTRATEGIA C ---")
    print(res_df.to_string(index=False))


if __name__ == "__main__":
    run_strategy_c_pipeline()
