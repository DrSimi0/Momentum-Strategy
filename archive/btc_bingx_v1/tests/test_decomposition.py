"""Pruebas unitarias para el módulo de descomposición de costos y baselines."""
import pandas as pd
import pytest

from src.evaluation.decomposition import analyze_gain_concentration, decompose_trades_costs


def test_decompose_trades_costs_manual():
    df = pd.DataFrame({
        "gross_pnl": [100.0, -20.0],
        "fees": [5.0, 5.0],
        "slippage": [2.0, 2.0],
        "funding": [1.0, 1.0],
        "net_pnl": [92.0, -28.0],
    })
    res = decompose_trades_costs(df)
    assert res["n_trades"] == 2
    assert res["gross_expectancy_usdt"] == pytest.approx(40.0)
    assert res["fees_per_trade"] == pytest.approx(5.0)
    assert res["slippage_per_trade"] == pytest.approx(2.0)
    assert res["funding_per_trade"] == pytest.approx(1.0)
    assert res["total_cost_per_trade"] == pytest.approx(8.0)
    assert res["net_expectancy_usdt"] == pytest.approx(32.0)
    assert res["costs_pct_of_gross"] == pytest.approx(20.0)


def test_decompose_trades_costs_empty():
    res = decompose_trades_costs(pd.DataFrame())
    assert res["n_trades"] == 0
    assert res["gross_expectancy_usdt"] == 0.0


def test_analyze_gain_concentration_manual():
    # 2 trades: 92 y -28 -> total = 64
    # Top 5% de 2 -> ceil(0.1) = 1 trade (92)
    # 92 / 64 = 1.4375 -> 143.75%
    df = pd.DataFrame({"net_pnl": [92.0, -28.0]})
    res = analyze_gain_concentration(df)
    assert res["top_5pct_trades_count"] == 1
    assert res["top_5pct_share_pct"] == pytest.approx(143.75)
    assert res["total_net_pnl"] == pytest.approx(64.0)
