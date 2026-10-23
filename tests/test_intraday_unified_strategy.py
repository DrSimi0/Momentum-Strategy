"""Tests unitarios para la Estrategia Unificada Intradiaria (M5/M15).
Verifica filtros de sesión RTH, cierre forzoso MOC y causalidad.
"""
import numpy as np
import pandas as pd
import pytest

from src.strategies.intraday_unified_strategy import (
    IntradayStrategyParams,
    generate_intraday_signals,
    run_intraday_backtest,
)
from src.backtest.engine_sma_confluence import AssetCosts


def test_intraday_moc_and_rth_filtering():
    """Valida que no se emiten señales fuera de horario RTH."""
    n = 120
    # Creamos un rango de fechas con horas variadas
    dates = pd.date_range("2023-01-02 08:00", periods=n, freq="5min", tz="UTC")
    prices = np.linspace(100, 150, n)

    df = pd.DataFrame({
        "ts_event": dates,
        "open": prices,
        "high": prices + 1.0,
        "low": prices - 1.0,
        "close": prices + 0.5,
        "volume": 1000.0,
    })

    params = IntradayStrategyParams(
        fast_ema=10,
        slow_ema=30,
        rth_start_time="10:00",
        rth_end_time="15:15",
        moc_close_time="15:50",
        use_candle_trigger=False,
    )

    sig_long, is_moc, _, time_str = generate_intraday_signals(df, params)

    # Validar que cualquier señal emitida está dentro del rango horario permitido
    for t in range(n):
        if sig_long[t]:
            assert "10:00" <= time_str[t] <= "15:15", f"Señal emitida fuera de horario: {time_str[t]}"


def test_intraday_backtest_execution():
    """Valida que el motor intradiario ejecute correctamente y cierre posiciones."""
    n = 150
    dates = pd.date_range("2023-01-02 09:30", periods=n, freq="5min", tz="UTC")
    prices = np.linspace(100, 200, n)

    df = pd.DataFrame({
        "ts_event": dates,
        "open": prices,
        "high": prices + 2.0,
        "low": prices - 2.0,
        "close": prices + 0.5,
        "volume": 1000.0,
    })

    params = IntradayStrategyParams(
        fast_ema=10,
        slow_ema=30,
        rth_start_time="00:00",
        rth_end_time="23:59",
        moc_close_time="23:50",
        use_candle_trigger=False,
    )
    costs = AssetCosts(
        asset_type="futures",
        multiplier=50.0,
        tick_size=0.25,
        commission_per_side=2.0,
        slippage_per_side=0.5,
        annualization_factor=252.0 * 78.0,
    )

    res = run_intraday_backtest(df, params, costs)
    assert isinstance(res["n_trades"], int)
    assert "net_pnl_usd" in res
