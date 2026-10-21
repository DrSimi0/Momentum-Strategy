"""Motor de simulación de backtesting para estrategias intradía en futuros CME.
Ejecuta órdenes a mercado en la barra de 15:30 ET (open) y liquida en 15:59 ET (close).
"""
from __future__ import annotations

import logging
from typing import Dict, Optional
import numpy as np
import pandas as pd

from src.backtest.costs import CostSpec, calculate_trade_costs

logger = logging.getLogger(__name__)


def simulate_trades(
    df: pd.DataFrame,
    signal_col: str,
    multiplier_usd_per_point: float,
    tick_size_points: float,
    tick_value_usd: float,
    cost_spec: CostSpec,
    num_contracts: int = 1,
) -> pd.DataFrame:
    """Ejecuta la simulación de trading barra por barra diaria.
    
    Args:
        df: DataFrame con columnas 'entry_price', 'exit_price', y `signal_col`.
        signal_col: Nombre de la columna de señal (-1: Short, 0: No opera, +1: Long).
        multiplier_usd_per_point: Multiplicador del futuro (50 para ES, 20 para NQ).
        tick_size_points: Tamaño del tick (0.25 para ES y NQ).
        tick_value_usd: Valor monetario del tick (12.50 para ES, 5.00 para NQ).
        cost_spec: Estructura con comisiones y deslizamiento.
        num_contracts: Número de contratos (por defecto 1).
        
    Returns:
        DataFrame con detalle de operaciones, PnL bruto, neto y retornos porcentuales.
    """
    out = df.copy()
    if signal_col not in out.columns:
        raise KeyError(f"Columna de señal '{signal_col}' no encontrada en el DataFrame.")

    # Costos fijos por operación (round-turn)
    trade_costs = calculate_trade_costs(
        tick_size_points=tick_size_points,
        tick_value_usd=tick_value_usd,
        cost_spec=cost_spec,
        num_contracts=num_contracts,
    )

    signals = out[signal_col].fillna(0).astype(int).values
    entry_prices = out["entry_price"].values
    exit_prices = out["exit_price"].values

    n = len(out)
    gross_pnl_usd = np.zeros(n, dtype=float)
    net_pnl_usd = np.zeros(n, dtype=float)
    costs_usd = np.zeros(n, dtype=float)
    commission_usd = np.zeros(n, dtype=float)
    slippage_usd = np.zeros(n, dtype=float)
    notional_usd = np.zeros(n, dtype=float)
    daily_returns = np.zeros(n, dtype=float)
    gross_returns = np.zeros(n, dtype=float)

    for i in range(n):
        sig = signals[i]
        if sig == 0 or np.isnan(entry_prices[i]) or np.isnan(exit_prices[i]):
            continue

        entry = entry_prices[i]
        exit_ = exit_prices[i]
        notional = entry * multiplier_usd_per_point * num_contracts
        notional_usd[i] = notional

        # PnL bruto
        points_diff = (exit_ - entry) if sig == 1 else (entry - exit_)
        gross = points_diff * multiplier_usd_per_point * num_contracts
        gross_pnl_usd[i] = gross
        gross_returns[i] = gross / notional if notional > 0 else 0.0

        # Costos y PnL neto
        comm = trade_costs["commission_usd"]
        slip = trade_costs["slippage_usd"]
        total_c = trade_costs["total_cost_usd"]

        costs_usd[i] = total_c
        commission_usd[i] = comm
        slippage_usd[i] = slip
        net = gross - total_c
        net_pnl_usd[i] = net
        daily_returns[i] = net / notional if notional > 0 else 0.0

    out["trade_signal"] = signals
    out["notional_usd"] = notional_usd
    out["gross_pnl_usd"] = gross_pnl_usd
    out["commission_usd"] = commission_usd
    out["slippage_usd"] = slippage_usd
    out["total_cost_usd"] = costs_usd
    out["net_pnl_usd"] = net_pnl_usd
    out["gross_return"] = gross_returns
    out["daily_return"] = daily_returns  # 0.0 en días sin operación

    return out
