"""Evaluación directa de la Estrategia Cuantitativa Unificada en M15 y M5.
Cuantifica el impacto destructivo del ruido de microestructura y las comisiones en alta frecuencia.
"""
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List

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
logger = logging.getLogger("eval_short_tf")

PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports/short_timeframes")
TABLES_DIR = REPORTS_DIR / "tables"


def run_evaluation():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    costs_map = {
        "ES": AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0),
        "NQ": AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0),
        "BTC-USDT": AssetCosts(asset_type="crypto", multiplier=1.0, tick_size=0.1, commission_per_side=0.0005, slippage_per_side=0.0002, annualization_factor=365.0),
        "ETH-USDT": AssetCosts(asset_type="crypto", multiplier=1.0, tick_size=0.01, commission_per_side=0.0005, slippage_per_side=0.0002, annualization_factor=365.0),
    }

    params = UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0, long_only=True, use_candle_trigger=True)

    test_matrix = [
        ("ES", "15m", PROCESSED_DIR / "ES_15m.parquet"),
        ("ES", "5m", PROCESSED_DIR / "ES_5m.parquet"),
        ("NQ", "15m", PROCESSED_DIR / "NQ_15m.parquet"),
        ("NQ", "5m", PROCESSED_DIR / "NQ_5m.parquet"),
        ("BTC-USDT", "15m", PROCESSED_DIR / "BTC_USDT_15m.parquet"),
        ("BTC-USDT", "5m", PROCESSED_DIR / "BTC_USDT_5m.parquet"),
    ]

    results = []

    for sym, tf, f_path in test_matrix:
        if not f_path.exists():
            logger.warning(f"Archivo no encontrado: {f_path}")
            continue

        logger.info(f"Evaluando {sym} en {tf}...")
        df = pd.read_parquet(f_path)
        costs = costs_map[sym]

        res = run_unified_backtest(df, params, costs)

        trades = res.get("trades", [])
        n_tr = len(trades)
        
        # Calcular costos totales pagados
        if costs.asset_type == "futures":
            cost_per_trade = 2.0 * costs.commission_per_side + 2.0 * costs.slippage_per_side * costs.tick_size * costs.multiplier
            total_frictional_costs = n_tr * cost_per_trade
        else:
            total_frictional_costs = sum(t["return"] for t in trades) * 10000.0 * 0.0014

        gross_pnl_usd = res["net_pnl_usd"] + total_frictional_costs

        row = {
            "Activo": sym,
            "Timeframe": tf,
            "N_Trades": n_tr,
            "Win_Rate_%": round(res["win_rate"] * 100, 2),
            "Profit_Factor": round(res["profit_factor"], 2) if not np.isnan(res["profit_factor"]) else 0.0,
            "Gross_PnL_USD": round(gross_pnl_usd, 2),
            "Comisiones_Slippage_USD": round(total_frictional_costs, 2),
            "Net_PnL_USD": round(res["net_pnl_usd"], 2),
            "Sharpe": round(res["sharpe"], 2) if not np.isnan(res["sharpe"]) else "N/A",
            "Max_Drawdown_USD": round(res["max_drawdown"], 2),
            "Veredicto": "FAIL_NEGATIVE" if res["net_pnl_usd"] < 0 or res.get("sharpe", -99) < 1.0 else "PASS",
        }
        results.append(row)

    res_df = pd.DataFrame(results)
    csv_path = TABLES_DIR / "direct_m15_m5_results.csv"
    res_df.to_csv(csv_path, index=False)
    logger.info(f"Guardado {csv_path}")

    print("\n--- RESULTADOS EVALUACIÓN M15 Y M5 (DIRECTO) ---")
    print(res_df.to_string(index=False))


if __name__ == "__main__":
    run_evaluation()
