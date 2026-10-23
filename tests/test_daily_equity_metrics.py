"""Tests unitarios para la auditoría de equity diaria, análisis de Prop Firms y permutación.
"""
import numpy as np
import pandas as pd
import pytest

from src.analysis.daily_equity_audit import (
    build_daily_equity_curve,
    analyze_prop_firm_and_micros,
    run_permutation_test,
    run_concentration_test,
)
from src.backtest.engine_sma_confluence import AssetCosts


def test_build_daily_equity_curve_metrics():
    """Valida el cálculo de CAGR, Sharpe diario anualizado y Calmar ratio."""
    dates = pd.date_range("2020-01-01", periods=252, freq="D", tz="UTC")
    df_bars = pd.DataFrame({"ts_event": dates, "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000})

    # Simular 10 trades ganadores distribuidos a lo largo del año
    trades = [
        {"exit_date": dates[i * 20], "net_pnl_usd": 1000.0, "return": 0.01, "bars_held": 5}
        for i in range(1, 11)
    ]

    res = build_daily_equity_curve(trades, df_bars, initial_capital=50000.0)
    assert res["total_net_pnl"] == 10000.0
    assert res["final_equity"] == 60000.0
    assert res["cagr"] > 0
    assert res["sharpe_daily"] > 0
    assert res["max_dd_usd"] == 0.0 # Curva monótonamente creciente no tiene drawdown


def test_prop_firm_and_micros_scaling():
    """Valida que los micro contratos escalen el riesgo y PnL al 10% de E-mini."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D", tz="UTC")
    df_bars = pd.DataFrame({"ts_event": dates, "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000})

    # 1 trade con pérdida de $10,000 en E-mini (sobrepasa límite prop firm de $2k)
    trades = [
        {"entry_price": 100.0, "exit_date": dates[10], "net_pnl_usd": -10000.0, "return": -0.10, "bars_held": 2, "stop_dist": 5.0}
    ]

    res = analyze_prop_firm_and_micros(trades, df_bars, asset="NQ")
    assert res["emini_50k"]["max_dd_usd"] == 10000.0
    assert res["fits_emini_prop_50k"] == False # No cabe en $2,000 DD

    # En Micro, la pérdida debe ser exactamente $1,000 USD (1/10)
    assert res["micro_50k"]["max_dd_usd"] == 1000.0
    assert res["fits_micro_prop_50k"] == True # Sí cabe en $2,000 DD


def test_concentration_top_trades():
    """Valida la eliminación exacta de los 5 mejores trades."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D", tz="UTC")
    df_bars = pd.DataFrame({"ts_event": dates, "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000})

    trades = [{"exit_date": dates[i], "net_pnl_usd": float(i * 100), "bars_held": 1} for i in range(1, 11)]
    # Trades tienen PnL: 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000
    # Top 5 son: 1000, 900, 800, 700, 600 (Suma = 4000)
    # Remaining: 100, 200, 300, 400, 500 (Suma = 1500)

    res = run_concentration_test(trades, df_bars, initial_capital=50000.0, top_n=5)
    assert res["pnl_top5"] == 4000.0
    assert res["pnl_without_top5"] == 1500.0
