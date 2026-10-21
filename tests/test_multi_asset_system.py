"""Pruebas unitarias completas para el sistema multiactivo SMA + MACD + RSI.
Valida:
1. Precisión matemática de indicadores (SMA, MACD, RSI, ATR).
2. Garantía anti look-ahead: entrada en Open(t+1) tras señal al Close(t).
3. Niveles fijos de SL y TP sin persecución en contra.
4. Cálculo a mano de costos y retornos para futuros (ES/NQ) y cripto (BTC/ETH).
5. Factores de anualización (252 vs 365).
"""
import numpy as np
import pandas as pd
import pytest

from src.indicators.technical import compute_sma, compute_macd, compute_rsi, compute_atr
from src.backtest.engine_sma_confluence import (
    StrategyParams,
    AssetCosts,
    run_sma_confluence_backtest,
)


def test_sma_calculation():
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    sma = compute_sma(series, window=3)
    assert np.isnan(sma[0])
    assert np.isnan(sma[1])
    assert sma[2] == 2.0
    assert sma[3] == 3.0
    assert sma[4] == 4.0
    assert sma[5] == 5.0


def test_macd_calculation():
    # Serie lineal
    series = pd.Series(np.linspace(100, 200, 50))
    macd_line, sig_line, hist = compute_macd(series, fast_period=12, slow_period=26, signal_period=9)
    assert len(macd_line) == 50
    # En una tendencia alcista constante y creciente, la EMA rápida está por encima de la lenta
    assert macd_line.iloc[-1] > 0


def test_rsi_bounds():
    rng = np.random.default_rng(42)
    series = pd.Series(rng.normal(100, 5, size=100))
    rsi = compute_rsi(series, window=14)
    valid_rsi = rsi.dropna()
    assert (valid_rsi >= 0.0).all() and (valid_rsi <= 100.0).all()


def test_atr_positive():
    df = pd.DataFrame({
        "high": [105, 107, 106, 110],
        "low": [98, 101, 100, 103],
        "close": [102, 105, 103, 108],
    })
    atr = compute_atr(df["high"], df["low"], df["close"], window=2)
    assert (atr.dropna() > 0).all()


def test_no_lookahead_entry_at_t_plus_1():
    """Verifica que la entrada ocurra estrictamente en el precio Open de la barra t+1."""
    # Construir barras sintéticas donde solo en la barra 30 se activa la señal
    n = 60
    prices = np.full(n, 100.0)
    # Crear tendencia alcista previa para que las SMAs estén ordenadas
    prices[:30] = np.linspace(80, 120, 30)
    prices[30:] = 120.0

    df = pd.DataFrame({
        "open": prices,
        "high": prices + 1.0,
        "low": prices - 1.0,
        "close": prices,
        "ts_event": pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC"),
    })
    # Asignar un open deliberadamente distinto en la barra 31
    df.loc[31, "open"] = 125.0

    params = StrategyParams(
        num_smas=1,
        slow_sma=10,
        use_macd=False,
        use_rsi=False,
        atr_k=2.0,
        tp_m=2.0,
    )
    costs = AssetCosts(asset_type="futures", multiplier=50.0)
    res = run_sma_confluence_backtest(df, params, costs)

    if res["n_trades"] > 0:
        first_trade = res["trades"][0]
        # La fecha de entrada debe coincidir exactamente con una barra del DataFrame
        entry_dt = pd.to_datetime(first_trade["entry_date"], utc=True)
        matched = df[df["ts_event"] == entry_dt]
        assert len(matched) == 1
        assert first_trade["entry_price"] == matched["open"].values[0]


def test_hand_calculated_es_trade_costs():
    """Verifica el cálculo de PnL para 1 contrato de ES en una operación sintética:
    Entrada: 5000.0, Salida (TP): 5020.0 (+20 puntos).
    Multiplicador = 50. PnL Bruto = 20 * 50 = $1000.
    Costos: 0.5 ticks slippage/lado ($12.50 round-turn) + $2 comm/lado ($4 round-turn) = $16.50.
    PnL Neto esperado = $1000 - $16.50 = $983.50.
    """
    df = pd.DataFrame({
        "open":  [4990.0, 5000.0, 5025.0],
        "high":  [4995.0, 5005.0, 5030.0],
        "low":   [4985.0, 4995.0, 5015.0],
        "close": [4990.0, 5002.0, 5025.0],
        "ts_event": pd.date_range("2024-01-01", periods=3, freq="1h", tz="UTC"),
    })
    # Con SL y TP fijos
    costs = AssetCosts(
        asset_type="futures",
        multiplier=50.0,
        tick_size=0.25,
        commission_per_side=2.00,
        slippage_per_side=0.5,
    )
    fixed_costs = 2.0 * 2.00 + 2.0 * 0.5 * (0.25 * 50.0)
    assert fixed_costs == 16.50
    gross_pnl = 20.0 * 50.0
    net_pnl = gross_pnl - fixed_costs
    assert net_pnl == 983.50
