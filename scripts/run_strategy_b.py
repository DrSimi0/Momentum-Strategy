"""Runner y Evaluador de Estrategia B: Relación Dinámica RSI / MACD vs Líneas Base."""
from dataclasses import asdict
import json
import logging
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import pandas as pd

from src.strategies.strategy_b_rsi_macd import RSIMACDParams, compute_rsi_macd_features, run_rsi_macd_backtest
from src.backtest.engine_sma_confluence import AssetCosts
from src.analysis.robustness import compute_deflated_sharpe_ratio

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports/strategy_b")
TABLES_DIR = REPORTS_DIR / "tables"


def run_strategy_b_pipeline():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    costs_map = {
        "ES": AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5),
        "NQ": AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5),
    }

    model_types = ["REL_AGREEMENT", "REL_DIVERGENCE", "RSI_SOLO", "MACD_SOLO", "STATIC_AGREEMENT"]
    atr_ks = [2.0, 3.0]
    tp_ms = [1.5, 2.0]

    summary_rows = []

    for sym in ["ES", "NQ"]:
        costs = costs_map[sym]
        for tf in ["4h", "1h"]:
            df = pd.read_parquet(PROCESSED_DIR / f"{sym}_{tf}.parquet")
            n = len(df)
            n_tr = int(n * 0.70)
            df_train = df.iloc[:n_tr].copy().reset_index(drop=True)
            df_val = df.iloc[n_tr:].copy().reset_index(drop=True)

            feats_train = compute_rsi_macd_features(df_train)
            feats_val = compute_rsi_macd_features(df_val)

            for m_type in model_types:
                for k in atr_ks:
                    for m in tp_ms:
                        p = RSIMACDParams(model_type=m_type, timeframe=tf, atr_k=k, tp_m=m)
                        res_tr = run_rsi_macd_backtest(df_train, p, costs, feats_train)
                        res_val = run_rsi_macd_backtest(df_val, p, costs, feats_val)

                        summary_rows.append({
                            "Activo": sym,
                            "Timeframe": tf,
                            "Modelo": m_type,
                            "ATR_k": k,
                            "TP_m": m,
                            "Train_Trades": res_tr["n_trades"],
                            "Train_Sharpe": f"{res_tr['sharpe']:.2f}" if not np.isnan(res_tr['sharpe']) else "N/A",
                            "Train_PnL": f"${res_tr['net_pnl_usd']:,.2f}",
                            "Val_Trades": res_val["n_trades"],
                            "Val_WinRate": f"{res_val['win_rate']*100:.1f}%",
                            "Val_ProfitFactor": f"{res_val['profit_factor']:.2f}" if not np.isnan(res_val['profit_factor']) else "N/A",
                            "Val_PnL": f"${res_val['net_pnl_usd']:,.2f}",
                            "Val_Sharpe": f"{res_val['sharpe']:.2f}" if not np.isnan(res_val['sharpe']) else "N/A",
                            "Val_Max_DD": f"${res_val['max_drawdown']:,.2f}",
                        })

    df_res = pd.DataFrame(summary_rows)
    out_csv = TABLES_DIR / "strategy_b_comparison_summary.csv"
    df_res.to_csv(out_csv, index=False)
    logger.info(f"Resultados de Estrategia B guardados en {out_csv}")


if __name__ == "__main__":
    run_strategy_b_pipeline()
