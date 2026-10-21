"""Análisis de robustez cruzada entre activos, comparación con líneas base (Buy & Hold y Solo-SMA)
y corrección por pruebas múltiples mediante Deflated Sharpe Ratio (Bailey & López de Prado, 2014).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List
import numpy as np
import pandas as pd
from scipy.stats import norm

from src.backtest.engine_sma_confluence import StrategyParams, AssetCosts, run_sma_confluence_backtest

logger = logging.getLogger(__name__)


def compute_deflated_sharpe_ratio(
    observed_sharpe: float,
    num_trials: int,
    num_obs: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
    annualization_factor: float = 252.0,
) -> float:
    """Calcula el Deflated Sharpe Ratio (DSR) de Bailey y López de Prado (2014).
    
    Ajusta el Sharpe observado teniendo en cuenta el sesgo de selección de probar M combinaciones.
    DSR representa la probabilidad de que el verdadero Sharpe sea estrictamente mayor que cero.
    """
    if num_trials <= 1:
        return 1.0 if observed_sharpe > 0 else 0.0

    # Des-anualizar para la fórmula estadística base
    sr = observed_sharpe / np.sqrt(annualization_factor)

    # Varianza estimada de la distribución de Sharpes bajo la hipótesis nula
    euler_mascheroni = 0.5772156649
    # Umbral esperado del máximo Sharpe bajo H0
    # E[max(sr)] ~ sqrt(2 * ln(M)) + euler / sqrt(2 * ln(M))
    ln_m = np.log(num_trials)
    sr_0 = (np.sqrt(2.0 * ln_m) + euler_mascheroni / np.sqrt(2.0 * ln_m)) / np.sqrt(num_obs)

    # Varianza del estimador de Sharpe con asimetría y curtosis
    var_sr = (1.0 - skewness * sr + (kurtosis - 1.0) / 4.0 * (sr ** 2)) / max(num_obs - 1, 1)
    std_sr = np.sqrt(max(var_sr, 1e-12))

    z_stat = (sr - sr_0) / std_sr
    dsr = float(norm.cdf(z_stat))
    return dsr


def evaluate_solo_sma_benchmark(
    df: pd.DataFrame,
    params: StrategyParams,
    costs: AssetCosts,
) -> Dict[str, Any]:
    """Evalúa la versión benchmark de solo-SMA desactivando los filtros de MACD y RSI."""
    solo_params = StrategyParams(
        num_smas=params.num_smas,
        fast_sma=params.fast_sma,
        mid_sma=params.mid_sma,
        slow_sma=params.slow_sma,
        atr_k=params.atr_k,
        tp_m=params.tp_m,
        use_macd=False,
        use_rsi=False,
    )
    return run_sma_confluence_backtest(df, solo_params, costs)


def evaluate_buy_and_hold_benchmark(
    df: pd.DataFrame,
    costs: AssetCosts,
) -> Dict[str, Any]:
    """Evalúa la estrategia pasiva de Buy & Hold desde la primera vela hasta la última."""
    if len(df) < 2:
        return {"sharpe": 0.0, "net_pnl_usd": 0.0}

    first_open = float(df["open"].iloc[0])
    last_close = float(df["close"].iloc[-1])

    if costs.asset_type == "futures":
        gross_diff = last_close - first_open
        gross_pnl = gross_diff * costs.multiplier
        # Costo de entrada y salida una sola vez
        fixed_costs = 2.0 * costs.commission_per_side + 2.0 * costs.slippage_per_side * (costs.tick_size * costs.multiplier)
        net_pnl = gross_pnl - fixed_costs
        notional = first_open * costs.multiplier
        total_ret = net_pnl / notional if notional > 0 else 0.0
    else:
        gross_ret = (last_close / first_open) - 1.0
        cost_pct = 2.0 * (costs.commission_per_side + costs.slippage_per_side)
        net_ret = gross_ret - cost_pct
        net_pnl = net_ret * 10000.0
        total_ret = net_ret

    # Serie de retornos por barra para calcular Sharpe del B&H
    rets = df["close"].pct_change().dropna().values
    mean_r = float(np.mean(rets))
    std_r = float(np.std(rets, ddof=1)) if len(rets) > 1 else 0.0
    sharpe = float(mean_r / std_r * np.sqrt(costs.annualization_factor)) if std_r > 1e-9 else 0.0

    return {
        "net_pnl_usd": net_pnl,
        "total_return_pct": total_ret * 100.0,
        "sharpe": sharpe,
    }


def run_cross_asset_evaluation(
    finalist_params: StrategyParams,
    target_df: pd.DataFrame,
    target_costs: AssetCosts,
) -> Dict[str, Any]:
    """Evalúa una configuración finalista en otro activo para verificar robustez cruzada."""
    return run_sma_confluence_backtest(target_df, finalist_params, target_costs)
