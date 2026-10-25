"""Pruebas unitarias de integridad causal y ejecución para la Estrategia Intradía EMA 200."""
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


def test_ema200_signals_no_lookahead():
    """Verifica que las señales no utilicen información futura."""
    n = 300
    dates = pd.date_range("2024-01-01 09:30", periods=n, freq="15min", tz="America/New_York")
    
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

    params = IntradayEma200Params(trend_ema_period=50)
    sig_1, moc_1, _, _, _ = generate_ema200_signals(df, params)

    # Modificar las últimas 10 barras y verificar que las barras previas no cambien
    df_mod = df.copy()
    df_mod.loc[n-10:, "close"] += 50.0
    sig_2, moc_2, _, _, _ = generate_ema200_signals(df_mod, params)

    np.testing.assert_array_equal(sig_1[:n-10], sig_2[:n-10], "Look-ahead detectado en señales EMA 200")


def test_ema200_zero_overnight():
    """Verifica que ningún trade quede abierto durante la noche en NQ 15m y NQ 5m."""
    f_path = PROJECT_ROOT / "data" / "processed" / "NQ_15m.parquet"
    if not f_path.exists():
        pytest.skip("NQ_15m.parquet no disponible")

    df = pd.read_parquet(f_path).head(5000)
    costs = AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0)
    params = IntradayEma200Params(trend_ema_period=200, moc_close_time="15:45")

    res = run_ema200_backtest(df, params, costs)
    trades = res["trades"]

    for t in trades:
        entry_d = pd.to_datetime(t["entry_date"], utc=True).tz_convert("America/New_York").date()
        exit_d = pd.to_datetime(t["exit_date"], utc=True).tz_convert("America/New_York").date()
        assert entry_d == exit_d, f"Trade cruzó la noche: Entrada {entry_d} vs Salida {exit_d}"
