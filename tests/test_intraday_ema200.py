"""Pruebas unitarias de integridad causal y ejecución para la Estrategia Intradía EMA 200.
Valida formalmente:
1. Entrada estricta en el Open de t+1 tras señal generada al cierre de t.
2. Ausencia total de look-ahead bias en señales largas y cortas.
3. Cero trades overnight (100% de operaciones cierran en el día).
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.strategies.intraday_ema200_strategy import (
    IntradayEma200Params,
    generate_ema200_signals,
    run_ema200_backtest,
)
from src.backtest.engine_sma_confluence import AssetCosts


def test_execution_strictly_at_open_t_plus_1():
    """Valida formalmente que toda entrada se ejecute exactamente al precio Open de la barra t+1
    respecto a la barra donde se generó la señal (al cierre de t).
    """
    f_path = PROJECT_ROOT / "data" / "processed" / "NQ_5m.parquet"
    if not f_path.exists():
        pytest.skip("NQ_5m.parquet no disponible")

    df = pd.read_parquet(f_path).head(10000)
    costs = AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0)
    params = IntradayEma200Params(trend_ema_period=200, trigger_type="price_cross", moc_close_time="15:50", allow_short=True)

    sig_long, sig_short, _, _, _, _ = generate_ema200_signals(df, params)
    res = run_ema200_backtest(df, params, costs)
    trades = res["trades"]

    assert len(trades) > 0, "No se generaron trades para la prueba"

    open_arr = df["open"].values

    for t in trades:
        entry_idx = t["entry_bar_idx"]
        signal_idx = entry_idx - 1

        # 1. Comprobar que en la barra anterior (signal_idx) efectivamente hubo señal
        if t["direction"] == "LONG":
            assert sig_long[signal_idx] == True, f"Trade Long en barra {entry_idx} sin señal en barra {signal_idx}"
        else:
            assert sig_short[signal_idx] == True, f"Trade Short en barra {entry_idx} sin señal en barra {signal_idx}"

        # 2. Comprobar que el precio de entrada coincide con el Open de t+1
        expected_price = open_arr[entry_idx]
        actual_price = t["entry_price"]
        assert actual_price == expected_price, f"Precio de entrada {actual_price} != Open[t+1] {expected_price}"


def test_ema200_signals_no_lookahead():
    """Verifica causalidad: alterar datos futuros no modifica señales pasadas."""
    n = 350
    dates = pd.date_range("2024-01-01 09:30", periods=n, freq="5min", tz="America/New_York")

    np.random.seed(42)
    close = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.random.rand(n) * 0.5
    low = close - np.random.rand(n) * 0.5
    open_p = close + np.random.randn(n) * 0.2

    df = pd.DataFrame({
        "ts_event": dates,
        "open": open_p,
        "high": high,
        "low": low,
        "close": close,
        "volume": 1000,
    })

    params = IntradayEma200Params(trend_ema_period=50, allow_short=True)
    sig_long_1, sig_short_1, _, _, _, _ = generate_ema200_signals(df, params)

    # Modificar las últimas 15 barras y verificar que el pasado sea idéntico
    df_mod = df.copy()
    df_mod.loc[n - 15:, "close"] += 50.0
    sig_long_2, sig_short_2, _, _, _, _ = generate_ema200_signals(df_mod, params)

    np.testing.assert_array_equal(sig_long_1[:n - 15], sig_long_2[:n - 15], "Look-ahead en señales Long")
    np.testing.assert_array_equal(sig_short_1[:n - 15], sig_short_2[:n - 15], "Look-ahead en señales Short")


def test_ema200_zero_overnight():
    """Verifica que ningún trade quede abierto durante la noche (cierre forzoso intradía)."""
    f_path = PROJECT_ROOT / "data" / "processed" / "NQ_5m.parquet"
    if not f_path.exists():
        pytest.skip("NQ_5m.parquet no disponible")

    df = pd.read_parquet(f_path).head(10000)
    costs = AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0)
    params = IntradayEma200Params(trend_ema_period=200, moc_close_time="15:50", allow_short=True)

    res = run_ema200_backtest(df, params, costs)
    trades = res["trades"]

    for t in trades:
        entry_d = pd.to_datetime(t["entry_date"], utc=True).tz_convert("America/New_York").date()
        exit_d = pd.to_datetime(t["exit_date"], utc=True).tz_convert("America/New_York").date()
        assert entry_d == exit_d, f"Trade cruzó la noche: Entrada {entry_d} vs Salida {exit_d}"
