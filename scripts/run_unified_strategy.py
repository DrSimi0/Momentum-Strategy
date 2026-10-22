"""Script de Evaluación y Auditoría de la Estrategia Cuantitativa Unificada.
Compara la confluencia EMA 30/200 + MACD/RSI + Price Action frente a componentes individuales y Buy & Hold.
"""
from dataclasses import asdict
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

from src.strategies.unified_strategy import (
    UnifiedStrategyParams,
    run_unified_backtest,
)
from src.backtest.engine_sma_confluence import AssetCosts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DIR = Path("data/processed")
RAW_DIR = Path("data/raw")
REPORTS_DIR = Path("reports/unified_strategy")
TABLES_DIR = REPORTS_DIR / "tables"


def compute_buy_and_hold(df: pd.DataFrame, costs: AssetCosts) -> Dict[str, float]:
    """Calcula el rendimiento neto de Buy & Hold en el periodo evaluado."""
    if len(df) < 2:
        return {"bnh_pnl_usd": 0.0, "bnh_ret_pct": 0.0}
    
    first_open = float(df["open"].iloc[0])
    last_close = float(df["close"].iloc[-1])
    is_futures = (costs.asset_type == "futures")
    
    if is_futures:
        gross_pnl = (last_close - first_open) * costs.multiplier
        fixed_cost = 2.0 * costs.commission_per_side + 2.0 * costs.slippage_per_side * costs.tick_size * costs.multiplier
        net_pnl = gross_pnl - fixed_cost
        ret_pct = (last_close / first_open - 1.0) * 100.0
    else:
        ret_pct = (last_close / first_open - 1.0) * 100.0
        net_pnl = (ret_pct / 100.0) * 10000.0

    return {"bnh_pnl_usd": net_pnl, "bnh_ret_pct": ret_pct}


def run_unified_evaluation():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    costs_map = {
        "ES": AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0),
        "NQ": AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0),
        "BTC-USDT": AssetCosts(asset_type="crypto", multiplier=1.0, tick_size=0.1, commission_per_side=0.0005, slippage_per_side=0.0002, annualization_factor=365.0),
        "ETH-USDT": AssetCosts(asset_type="crypto", multiplier=1.0, tick_size=0.01, commission_per_side=0.0005, slippage_per_side=0.0002, annualization_factor=365.0),
    }

    eval_matrix = [
        ("ES", "4h", PROCESSED_DIR / "ES_4h.parquet"),
        ("ES", "1h", PROCESSED_DIR / "ES_1h.parquet"),
        ("NQ", "4h", PROCESSED_DIR / "NQ_4h.parquet"),
        ("NQ", "1h", PROCESSED_DIR / "NQ_1h.parquet"),
        ("BTC-USDT", "4h", RAW_DIR / "BTC-USDT_4h.parquet"),
        ("ETH-USDT", "4h", RAW_DIR / "ETH-USDT_4h.parquet"),
    ]

    variants = [
        ("UNIFIED_LONG_ONLY", UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0, long_only=True, use_candle_trigger=True)),
        ("UNIFIED_LONG_SHORT", UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0, long_only=False, use_candle_trigger=True)),
        ("UNIFIED_NO_TRIGGER", UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0, long_only=True, use_candle_trigger=False)),
    ]

    all_results = []

    for sym, tf, file_path in eval_matrix:
        if not file_path.exists():
            logger.warning(f"Archivo no disponible: {file_path}")
            continue

        logger.info(f"Evaluando Estrategia Unificada en {sym} ({tf})...")
        df = pd.read_parquet(file_path)
        costs = costs_map[sym]
        bnh = compute_buy_and_hold(df, costs)

        for v_name, params in variants:
            # Evaluación en el historial completo de desarrollo (2010-2026)
            res_full = run_unified_backtest(df, params, costs)

            # Evaluación en validación fuera de muestra (2021-2026, últimos 30%)
            n_val = int(len(df) * 0.70)
            df_val = df.iloc[n_val:].reset_index(drop=True)
            res_val = run_unified_backtest(df_val, params, costs)

            row = {
                "Activo": sym,
                "Timeframe": tf,
                "Variante": v_name,
                "N_Trades_Total": res_full["n_trades"],
                "WinRate_Total_%": round(res_full["win_rate"] * 100, 2),
                "ProfitFactor_Total": round(res_full["profit_factor"], 2) if not np.isnan(res_full["profit_factor"]) else 0.0,
                "Net_PnL_Total_USD": round(res_full["net_pnl_usd"], 2),
                "Sharpe_Total": round(res_full["sharpe"], 2) if not np.isnan(res_full["sharpe"]) else "N/A",
                "Max_DD_Total_USD": round(res_full["max_drawdown"], 2),
                "N_Trades_Val": res_val["n_trades"],
                "Net_PnL_Val_USD": round(res_val["net_pnl_usd"], 2),
                "Sharpe_Val_OOS": round(res_val["sharpe"], 2) if not np.isnan(res_val["sharpe"]) else "N/A",
                "BuyAndHold_PnL_USD": round(bnh["bnh_pnl_usd"], 2),
                "BuyAndHold_Ret_%": round(bnh["bnh_ret_pct"], 2),
            }
            all_results.append(row)

    res_df = pd.DataFrame(all_results)
    csv_path = TABLES_DIR / "unified_strategy_summary.csv"
    res_df.to_csv(csv_path, index=False)
    logger.info(f"Resultados guardados en {csv_path}")

    # Generar tabla Markdown
    md_table = "| " + " | ".join(res_df.columns) + " |\n"
    md_table += "| " + " | ".join(["---"] * len(res_df.columns)) + " |\n"
    for _, r in res_df.iterrows():
        md_table += "| " + " | ".join(str(val) for val in r.values) + " |\n"

    # Redactar informe de auditoría de la estrategia unificada
    md_path = REPORTS_DIR / "informe_estrategia_unificada.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# AUDITORÍA CUANTITATIVA: ESTRATEGIA UNIFICADA\n\n")
        f.write("### Confluencia de Medias Móviles (EMA 30/200) + Momentum (MACD/RSI) + Price Action Causal\n\n")
        f.write("## 1. Definición Matemática y Reglas de Ejecución\n")
        f.write("- **Filtro de Régimen (Estrategia A):** `EMA(30) > EMA(200)` y `Close > EMA(200)` para compras.\n")
        f.write("- **Filtro de Momentum (Estrategia B):** `MACD Histograma > 0` y `45 <= RSI <= 75` (fuerza sin sobrecompra extrema).\n")
        f.write("- **Gatillo de Entrada (Estrategia C):** Patrón confirmado al cierre de $t$ (`Engulfing Bullish` o `Hammer`).\n")
        f.write("- **Cero Look-Ahead:** Entrada estricta en el `Open` de $t+1$.\n")
        f.write("- **Gestión de Salida:** Stop Loss = $3.0 \\times \\text{ATR}$, Take Profit = $6.0 \\times \\text{ATR}$ (Ratio 1:2), o cruce contrario de EMA 30/200.\n")
        f.write("- **Costos Deducidos:** Comisión CME ($2.00/lado) y Slippage (0.5 ticks/lado) en futuros.\n\n")
        f.write("## 2. Resultados Empíricos Comparativos\n\n")
        f.write(md_table)
        f.write("\n\n## 3. Conclusiones y Comparación frente a los Componentes Aislados\n\n")

    logger.info(f"Informe guardado en {md_path}")
    print("\n--- RESUMEN ESTRATEGIA UNIFICADA ---")
    print(res_df.to_string(index=False))


if __name__ == "__main__":
    run_unified_evaluation()
