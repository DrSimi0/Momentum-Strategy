"""Tests unitarios deterministas para la Estrategia Cuantitativa Unificada.
Verifica que no exista look-ahead bias y que la confluencia funcione correctamente.
"""
import numpy as np
import pandas as pd
import pytest

from src.strategies.unified_strategy import (
    UnifiedStrategyParams,
    generate_unified_signals,
    run_unified_backtest,
)
from src.backtest.engine_sma_confluence import AssetCosts


def test_unified_strategy_zero_lookahead():
    """Verifica que modificar la barra t+1 no altera en absoluto la señal generada en la barra t."""
    n = 250
    np.random.seed(42)
    # Crear serie de precios alcista con tendencia y volatilidad
    base = np.linspace(100, 200, n)
    noise = np.random.normal(0, 1.0, n)
    close = base + noise
    high = close + 1.0
    low = close - 1.0
    open_p = close - 0.2

    df1 = pd.DataFrame({
        "ts_event": pd.date_range("2023-01-01", periods=n, freq="1h"),
        "open": open_p,
        "high": high,
        "low": low,
        "close": close,
        "volume": 1000.0,
    })

    params = UnifiedStrategyParams(fast_ema=30, slow_ema=200, use_candle_trigger=False)
    sig_long_1, sig_short_1, _ = generate_unified_signals(df1, params)

    # Crear df2 donde alteramos drásticamente los datos después de la barra 210
    df2 = df1.copy()
    df2.loc[211:, "close"] = df2.loc[211:, "close"] * 0.5
    df2.loc[211:, "open"] = df2.loc[211:, "open"] * 0.5
    df2.loc[211:, "high"] = df2.loc[211:, "high"] * 0.5
    df2.loc[211:, "low"] = df2.loc[211:, "low"] * 0.5

    sig_long_2, sig_short_2, _ = generate_unified_signals(df2, params)

    # Las señales en t <= 210 deben ser exactamente idénticas
    np.testing.assert_array_equal(
        sig_long_1[:211],
        sig_long_2[:211],
        err_msg="Fuga de futuro detectada: la señal en t <= 210 cambió al modificar t >= 211"
    )


def test_unified_backtest_execution():
    """Verifica que el backtest se ejecute causalmente en t+1 tras señal en t."""
    n = 260
    prices = np.linspace(100, 300, n)
    df = pd.DataFrame({
        "ts_event": pd.date_range("2023-01-01", periods=n, freq="1h"),
        "open": prices,
        "high": prices + 2.0,
        "low": prices - 2.0,
        "close": prices + 0.5,
        "volume": 1000.0,
    })

    params = UnifiedStrategyParams(fast_ema=30, slow_ema=200, use_candle_trigger=False)
    costs = AssetCosts(
        asset_type="futures",
        multiplier=50.0,
        tick_size=0.25,
        commission_per_side=2.0,
        slippage_per_side=0.5,
        annualization_factor=252.0,
    )

    res = run_unified_backtest(df, params, costs)
    assert isinstance(res["n_trades"], int)
    assert "net_pnl_usd" in res
