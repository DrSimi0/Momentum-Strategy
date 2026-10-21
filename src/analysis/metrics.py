"""Cálculo riguroso de métricas de rendimiento financiero y regresiones econométricas.
Incluye Sharpe anualizado (√252), drawdown, tasa de acierto, regresión predictiva Newey-West (HAC).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import statsmodels.api as sm

logger = logging.getLogger(__name__)


def compute_performance_metrics(
    sim_df: pd.DataFrame,
    annualization_factor: float = 252.0,
) -> Dict[str, Any]:
    """Calcula las métricas de rendimiento a partir del DataFrame de simulación.
    
    El Sharpe se calcula sobre la serie diaria de todos los días de sesión (0.0 si no se opera),
    permitiendo la comparación consistente entre estrategias con distinta frecuencia de operación.
    """
    daily_rets = sim_df["daily_return"].values
    net_pnls = sim_df["net_pnl_usd"].values
    gross_pnls = sim_df["gross_pnl_usd"].values
    signals = sim_df["trade_signal"].values
    
    n_days = len(sim_df)
    trade_mask = (signals != 0)
    n_trades = int(np.sum(trade_mask))

    total_net_pnl = float(np.sum(net_pnls))
    total_gross_pnl = float(np.sum(gross_pnls))
    total_commission = float(np.sum(sim_df["commission_usd"].values))
    total_slippage = float(np.sum(sim_df["slippage_usd"].values))
    total_costs = float(np.sum(sim_df["total_cost_usd"].values))

    # Métricas por operación
    if n_trades > 0:
        trades_net = net_pnls[trade_mask]
        trades_gross = gross_pnls[trade_mask]
        wins = trades_net > 0
        win_rate = float(np.mean(wins))
        avg_trade_net_usd = float(np.mean(trades_net))
        avg_trade_gross_usd = float(np.mean(trades_gross))
        std_trade_net_usd = float(np.std(trades_net, ddof=1)) if n_trades > 1 else 0.0

        pos_sum = float(np.sum(trades_net[trades_net > 0]))
        neg_sum = float(np.abs(np.sum(trades_net[trades_net < 0])))
        profit_factor = (pos_sum / neg_sum) if neg_sum > 0 else np.nan
    else:
        win_rate = 0.0
        avg_trade_net_usd = 0.0
        avg_trade_gross_usd = 0.0
        std_trade_net_usd = 0.0
        profit_factor = 0.0

    # Sharpe ratio anualizado
    mean_ret = float(np.mean(daily_rets))
    std_ret = float(np.std(daily_rets, ddof=1)) if n_days > 1 else 0.0
    if std_ret > 1e-12:
        sharpe = float((mean_ret / std_ret) * np.sqrt(annualization_factor))
    else:
        sharpe = 0.0

    # Sortino ratio (desviación a la baja)
    downside_rets = daily_rets[daily_rets < 0]
    if len(downside_rets) > 1:
        downside_std = float(np.sqrt(np.mean(downside_rets**2)))
        sortino = float((mean_ret / downside_std) * np.sqrt(annualization_factor)) if downside_std > 1e-12 else 0.0
    else:
        sortino = 0.0

    # Drawdown monetario acumulado
    cum_pnl = np.cumsum(net_pnls)
    peak = np.maximum.accumulate(cum_pnl)
    drawdown = peak - cum_pnl
    max_drawdown_usd = float(np.max(drawdown)) if len(drawdown) > 0 else 0.0

    # Desglose anual y fracción de años positivos (A6)
    if "date" in sim_df.columns:
        dates = pd.to_datetime(sim_df["date"])
    elif isinstance(sim_df.index, pd.DatetimeIndex):
        dates = sim_df.index
    else:
        dates = pd.date_range("2011-01-01", periods=n_days, freq="D")

    yearly_pnl = pd.Series(net_pnls, index=dates).resample("YE").sum()
    n_years = len(yearly_pnl)
    pos_years = int((yearly_pnl > 0).sum())
    fraction_positive_years = float(pos_years / n_years) if n_years > 0 else 0.0
    yearly_dict = {str(k.year): float(v) for k, v in yearly_pnl.items()}

    return {
        "n_days": n_days,
        "n_trades": n_trades,
        "trade_frequency": float(n_trades / n_days) if n_days > 0 else 0.0,
        "total_net_pnl_usd": total_net_pnl,
        "total_gross_pnl_usd": total_gross_pnl,
        "total_commission_usd": total_commission,
        "total_slippage_usd": total_slippage,
        "total_costs_usd": total_costs,
        "avg_trade_net_usd": avg_trade_net_usd,
        "avg_trade_gross_usd": avg_trade_gross_usd,
        "std_trade_net_usd": std_trade_net_usd,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "sharpe_annualized": sharpe,
        "sortino_annualized": sortino,
        "max_drawdown_usd": max_drawdown_usd,
        "n_years": n_years,
        "positive_years": pos_years,
        "fraction_positive_years": fraction_positive_years,
        "yearly_pnl_usd": yearly_dict,
    }


def run_predictive_regression(
    y: pd.Series | np.ndarray,
    x: pd.Series | np.ndarray,
    lags: int = 5,
) -> Dict[str, float]:
    """Ejecuta regresión MCO con errores estándar consistentes ante heterocedasticidad y autocorrelación (HAC / Newey-West).
    
    Modelo: y_t = alpha + beta * x_t + e_t
    """
    valid_mask = (~np.isnan(y)) & (~np.isnan(x))
    y_clean = np.asarray(y)[valid_mask]
    x_clean = np.asarray(x)[valid_mask]

    n = len(y_clean)
    if n < lags + 5:
        return {
            "n_obs": n,
            "alpha": np.nan,
            "beta": np.nan,
            "t_stat": np.nan,
            "p_value": np.nan,
            "r_squared": np.nan,
            "stderr": np.nan,
        }

    X = sm.add_constant(x_clean)
    model = sm.OLS(y_clean, X)
    results = model.fit(cov_type="HAC", cov_kwds={"maxlags": lags})

    alpha = float(results.params[0])
    beta = float(results.params[1])
    t_stat = float(results.tvalues[1])
    p_value = float(results.pvalues[1])
    r_squared = float(results.rsquared)
    stderr = float(results.bse[1])

    return {
        "n_obs": n,
        "alpha": alpha,
        "beta": beta,
        "t_stat": t_stat,
        "p_value": p_value,
        "r_squared": r_squared,
        "stderr": stderr,
    }


def compute_oos_r_squared(
    y_in: np.ndarray,
    x_in: np.ndarray,
    y_out: np.ndarray,
    x_out: np.ndarray,
) -> float:
    """Calcula el R² fuera de muestra (Campbell-Thompson, 2008).
    
    R²_oos = 1 - sum((y_out - y_pred)^2) / sum((y_out - y_mean_in)^2)
    """
    if len(y_in) < 10 or len(y_out) < 2:
        return np.nan

    # Estimar parámetros en muestra
    X_in = sm.add_constant(x_in)
    model = sm.OLS(y_in, X_in).fit()
    alpha, beta = model.params[0], model.params[1]

    y_pred = alpha + beta * x_out
    y_mean_hist = np.mean(y_in)

    ss_model = np.sum((y_out - y_pred)**2)
    ss_benchmark = np.sum((y_out - y_mean_hist)**2)

    if ss_benchmark <= 1e-12:
        return np.nan

    return float(1.0 - (ss_model / ss_benchmark))
