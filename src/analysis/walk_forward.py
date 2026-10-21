"""Análisis Walk-Forward (ventanas rodantes) para configuraciones finalistas.
Evalúa la persistencia del rendimiento fuera de muestra a lo largo del tiempo.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List
import numpy as np
import pandas as pd

from src.backtest.engine_sma_confluence import StrategyParams, AssetCosts, run_sma_confluence_backtest

logger = logging.getLogger(__name__)


def run_walk_forward_analysis(
    df: pd.DataFrame,
    params: StrategyParams,
    costs: AssetCosts,
    n_windows: int = 5,
    train_ratio: float = 0.70,
) -> Dict[str, Any]:
    """Ejecuta análisis walk-forward dividiendo el dataset en n ventanas rodantes."""
    n = len(df)
    window_size = n // n_windows
    if window_size < 100:
        return {"error": "Insuficientes barras para walk-forward rodante.", "windows": []}

    window_results = []
    oos_returns = []

    for w in range(n_windows):
        start_idx = w * (n - window_size) // max(n_windows - 1, 1) if n_windows > 1 else 0
        end_idx = min(start_idx + window_size, n)
        w_df = df.iloc[start_idx:end_idx].reset_index(drop=True)

        w_len = len(w_df)
        split_point = int(w_len * train_ratio)
        train_slice = w_df.iloc[:split_point]
        test_slice = w_df.iloc[split_point:]

        res_train = run_sma_confluence_backtest(train_slice, params, costs)
        res_test = run_sma_confluence_backtest(test_slice, params, costs)

        window_results.append({
            "window": w + 1,
            "train_start": str(train_slice["ts_event"].iloc[0]) if "ts_event" in train_slice.columns else str(train_slice.index[0]),
            "test_end": str(test_slice["ts_event"].iloc[-1]) if "ts_event" in test_slice.columns else str(test_slice.index[-1]),
            "train_sharpe": res_train["sharpe"],
            "test_sharpe": res_test["sharpe"],
            "test_net_pnl": res_test["net_pnl_usd"],
            "test_win_rate": res_test["win_rate"],
            "test_trades": res_test["n_trades"],
        })
        for t in res_test["trades"]:
            oos_returns.append(t["return"])

    total_oos_trades = len(oos_returns)
    mean_oos = float(np.mean(oos_returns)) if total_oos_trades > 0 else 0.0
    std_oos = float(np.std(oos_returns, ddof=1)) if total_oos_trades > 1 else 0.0
    combined_oos_sharpe = float(mean_oos / std_oos * np.sqrt(costs.annualization_factor)) if std_oos > 1e-9 else 0.0

    return {
        "n_windows": n_windows,
        "total_oos_trades": total_oos_trades,
        "combined_oos_sharpe": combined_oos_sharpe,
        "windows": window_results,
    }
