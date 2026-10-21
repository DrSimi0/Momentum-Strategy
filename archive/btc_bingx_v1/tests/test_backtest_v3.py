"""Pruebas unitarias del motor de backtesting v3 contra cálculos manuales exactos."""
import pytest
import pandas as pd
import numpy as np

from src.backtesting.engine_v3 import BacktestEngineV3, SQRT_35040
from src.strategy.layer2_technical import TechnicalSetup


def test_manual_calculation_single_trade():
    """Verifica que el PnL neto, comisiones y slippage coincidan exactamente con un cálculo manual."""
    # Crear mercado sintético de 5 barras
    # Barra 0: Se genera señal LONG
    # Barra 1: Se abre LONG al Open=100.0
    # Barra 2, 3: Se mantiene en mercado
    # Barra 4: Toca TP en High=110.0 -> salida a 110.0
    market_df = pd.DataFrame({
        "time": [1000, 2000, 3000, 4000, 5000],
        "open":  [99.0, 100.0, 102.0, 105.0, 108.0],
        "high":  [100.0, 101.0, 104.0, 107.0, 111.0],  # En t=4 toca 111.0 >= TP(110.0)
        "low":   [98.0, 99.0, 101.0, 103.0, 107.0],
        "close": [99.5, 100.5, 103.0, 106.0, 110.5],
        "volume": [10, 10, 10, 10, 10],
    })

    # Setup generado en barra 0
    setup_0 = TechnicalSetup(
        bar_index=0,
        timestamp_ms=1000,
        direction="LONG",
        entry_price=99.5,
        stop_loss=95.0,  # Riesgo R = |100.0 - 95.0| = 5.0
        take_profit=110.0,
        risk_r=5.0,
        max_horizon_bars=15,
        break_even_trigger_r=1.0,
    )
    setups = [setup_0, None, None, None, None]

    engine = BacktestEngineV3(
        initial_capital=10000.0,
        taker_fee_pct=0.0005,    # 0.05%
        slippage_pct=0.0002,     # 0.02%
        funding_rate_8h=0.0001,  # 0.01% por 8h
        risk_per_trade_pct=0.01, # Riesgo 1% = 100 USDT -> Units = 100 / 5 = 20 units -> Pos size = 20 * 100 = 2000 USDT
    )

    trades_df, equity_df, metrics = engine.run_simulation(market_df, setups)

    assert len(trades_df) == 1
    t = trades_df.iloc[0]

    # Verificaciones manuales exactas:
    # Entrada ejecutada en t=1 al Open=100.0
    assert t["entry_bar"] == 1
    assert t["entry_price"] == 100.0
    # Salida ejecutada en t=4 al TP=110.0
    assert t["exit_bar"] == 4
    assert t["exit_price"] == 110.0
    assert t["exit_reason"] == "TP"

    # Retorno bruto: (110 - 100) / 100 = 0.10 (10.0%)
    assert pytest.approx(t["gross_pnl_pct"], rel=1e-5) == 0.10

    # Comisiones (2 x 0.05%) = 0.0010
    assert pytest.approx(t["commission_pct"], rel=1e-5) == 0.0010
    # Slippage (2 x 0.02%) = 0.0004
    assert pytest.approx(t["slippage_pct"], rel=1e-5) == 0.0004
    # Funding (3 barras de tenencia: 4 - 1 = 3 -> 3/32 * 0.0001 = 0.000009375)
    expected_funding = (3.0 / 32.0) * 0.0001
    assert pytest.approx(t["funding_pct"], rel=1e-5) == expected_funding

    # Retorno neto esperado:
    expected_net_pct = 0.10 - (0.0010 + 0.0004 + expected_funding)
    assert pytest.approx(t["net_pnl_pct"], rel=1e-5) == expected_net_pct

    # PnL en USDT para tamaño de posición de 2000 USDT:
    expected_net_usdt = 2000.0 * expected_net_pct
    assert pytest.approx(t["net_pnl_usdt"], rel=1e-4) == expected_net_usdt

    # Expectativa en R: (110 - 100) / 5 = +2.0R
    assert pytest.approx(t["net_pnl_r"], rel=1e-5) == 2.0


def test_break_even_activation():
    """Verifica que el Stop-Loss se desplace a la entrada tras superar +1.0R y proteja contra pérdidas."""
    # R = 100 - 90 = 10. +1.0R = 110.0.
    # Barra 1: Entra a 100.0.
    # Barra 2: Sube a High=111.0 (activa Break-Even -> SL = 100.0).
    # Barra 3: Cae a Low=99.0 -> Toca el nuevo SL (100.0) -> Cierra en Break-Even.
    market_df = pd.DataFrame({
        "time": [1000, 2000, 3000, 4000],
        "open":  [98.0, 100.0, 105.0, 102.0],
        "high":  [99.0, 102.0, 111.0, 103.0],
        "low":   [97.0, 99.0, 104.0, 99.0],  # En barra 3 perfora 100.0
        "close": [98.5, 101.0, 106.0, 99.5],
        "volume": [10, 10, 10, 10],
    })

    setup = TechnicalSetup(
        bar_index=0,
        timestamp_ms=1000,
        direction="LONG",
        entry_price=98.5,
        stop_loss=90.0,
        take_profit=130.0,
        risk_r=10.0,
        max_horizon_bars=15,
        break_even_trigger_r=1.0,
    )
    setups = [setup, None, None, None]

    engine = BacktestEngineV3()
    trades_df, _, _ = engine.run_simulation(market_df, setups)

    assert len(trades_df) == 1
    t = trades_df.iloc[0]
    assert t["exit_reason"] == "BREAK_EVEN"
    assert t["exit_price"] == 100.0
    assert t["gross_pnl_pct"] == 0.0  # Sin pérdida ni ganancia bruta
    assert t["net_pnl_pct"] < 0  # Solo descontando los costos de taker y slippage


def test_time_expiration():
    """Verifica el cierre automático por límite de horizonte tras 15 barras."""
    n_bars = 20
    market_df = pd.DataFrame({
        "time": np.arange(n_bars) * 1000,
        "open": np.full(n_bars, 100.0),
        "high": np.full(n_bars, 101.0),
        "low": np.full(n_bars, 99.0),
        "close": np.full(n_bars, 100.5),
        "volume": np.full(n_bars, 10.0),
    })

    setup = TechnicalSetup(
        bar_index=0,
        timestamp_ms=0,
        direction="LONG",
        entry_price=100.0,
        stop_loss=90.0,
        take_profit=120.0,
        risk_r=10.0,
        max_horizon_bars=15,
    )
    setups = [setup] + [None] * (n_bars - 1)

    engine = BacktestEngineV3()
    trades_df, _, _ = engine.run_simulation(market_df, setups)

    assert len(trades_df) == 1
    t = trades_df.iloc[0]
    assert t["exit_reason"] == "TIME_EXPIRATION"
    assert t["bars_held"] == 15
