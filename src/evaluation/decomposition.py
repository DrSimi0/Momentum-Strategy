"""Módulo para la descomposición detallada del resultado, fricciones de costos y baselines."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from src.backtest.engine import BacktestConfig, BacktestResult, StrategyParams, run_backtest
from src.evaluation import metrics as M
from src.evaluation.baselines import buy_and_hold, random_entry_baseline


def decompose_trades_costs(trades: pd.DataFrame) -> dict:
    """Desglosa por operación las componentes de PnL y fricciones."""
    n = len(trades)
    if n == 0:
        return {
            "n_trades": 0,
            "gross_expectancy_usdt": 0.0,
            "fees_per_trade": 0.0,
            "slippage_per_trade": 0.0,
            "funding_per_trade": 0.0,
            "total_cost_per_trade": 0.0,
            "net_expectancy_usdt": 0.0,
            "costs_pct_of_gross": float("nan"),
        }

    gross = float(trades["gross_pnl"].sum())
    fees = float(trades["fees"].sum())
    slip = float(trades["slippage"].sum())
    fund = float(trades["funding"].sum())
    total_costs = fees + slip + fund
    net = float(trades["net_pnl"].sum())

    return {
        "n_trades": n,
        "gross_expectancy_usdt": gross / n,
        "fees_per_trade": fees / n,
        "slippage_per_trade": slip / n,
        "funding_per_trade": fund / n,
        "total_cost_per_trade": total_costs / n,
        "net_expectancy_usdt": net / n,
        "total_gross_usdt": gross,
        "total_fees_usdt": fees,
        "total_slippage_usdt": slip,
        "total_funding_usdt": fund,
        "total_costs_usdt": total_costs,
        "total_net_usdt": net,
        "costs_pct_of_gross": (total_costs / gross * 100.0) if gross > 0 else float("nan"),
    }


def analyze_gain_concentration(trades: pd.DataFrame) -> dict:
    """Analiza cuánto explican las mejores operaciones del beneficio neto total."""
    net = trades["net_pnl"].to_numpy(float) if len(trades) else np.array([])
    total_net = float(net.sum()) if len(net) else 0.0
    n = len(net)
    if n == 0 or total_net <= 0:
        return {
            "top_5pct_trades_count": 0,
            "top_5pct_share_pct": float("nan"),
            "top_10pct_trades_count": 0,
            "top_10pct_share_pct": float("nan"),
            "total_net_pnl": total_net,
        }

    sorted_desc = np.sort(net)[::-1]
    k_5 = max(1, math.ceil(0.05 * n))
    k_10 = max(1, math.ceil(0.10 * n))

    share_5 = float(sorted_desc[:k_5].sum() / total_net * 100.0)
    share_10 = float(sorted_desc[:k_10].sum() / total_net * 100.0)

    return {
        "top_5pct_trades_count": k_5,
        "top_5pct_share_pct": share_5,
        "top_10pct_trades_count": k_10,
        "top_10pct_share_pct": share_10,
        "total_net_pnl": total_net,
    }


def run_full_decomposition(bars: pd.DataFrame, params: StrategyParams, bt_cfg: BacktestConfig,
                           periods: dict[str, list[str]], seed: int = 42, random_reps: int = 200) -> dict:
    """Ejecuta la descomposición en desarrollo, validación y holdout."""
    results = {}
    baselines = {}
    concentrations = {}
    cost_breakdowns = {}

    for name, (start, end) in periods.items():
        res = run_backtest(bars, params, bt_cfg, start, end)
        results[name] = res
        cost_breakdowns[name] = decompose_trades_costs(res.trades)
        concentrations[name] = analyze_gain_concentration(res.trades)

        # Baseline Buy & Hold
        bh = buy_and_hold(bars, bt_cfg, start, end)
        m_strat = M.performance_metrics(res.equity, res.trades, res.liquidations, res.start, res.end)
        m_bh = M.performance_metrics(bh.equity, bh.trades, bh.liquidations, bh.start, bh.end)

        # Baseline aleatorio
        rand = random_entry_baseline(bars, res, bt_cfg, reps=random_reps, seed=seed)

        baselines[name] = {
            "strategy": {
                "total_return": m_strat["total_return"],
                "cagr": m_strat["cagr"],
                "sharpe": m_strat["sharpe"],
                "max_drawdown": m_strat["max_drawdown"],
                "expectancy_usdt": m_strat["expectancy_usdt"],
            },
            "buy_and_hold": {
                "total_return": m_bh["total_return"],
                "cagr": m_bh["cagr"],
                "sharpe": m_bh["sharpe"],
                "max_drawdown": m_bh["max_drawdown"],
                "expectancy_usdt": m_bh["expectancy_usdt"],
            },
            "random_baseline": {
                "median_total_return": rand["median"]["total_return"],
                "median_cagr": rand["median"]["cagr"],
                "median_sharpe": rand["median"]["sharpe"],
                "median_max_drawdown": rand["median"]["max_drawdown"],
                "median_expectancy": rand["median"]["expectancy_usdt"],
                "p2_5_sharpe": rand["p2_5"]["sharpe"],
                "p97_5_sharpe": rand["p97_5"]["sharpe"],
            },
        }

    return {
        "cost_breakdowns": cost_breakdowns,
        "concentrations": concentrations,
        "baselines_by_period": baselines,
    }
