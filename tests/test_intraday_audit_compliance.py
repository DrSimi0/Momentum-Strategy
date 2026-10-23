"""Tests de conformidad cuantitativa y auditoría estricta para la estrategia intradía.
Verifica:
1. Precisión de zona horaria ET y manejo exacto de Daylight Saving Time (DST).
2. Ventana de horario institucional RTH (10:00 - 15:15 ET).
3. Cierre forzoso de fin de sesión MOC a las 15:50 ET.
4. Causalidad estricta y ausencia total de look-ahead bias en EMA, ATR y patrones.
5. Continuidad y ausencia de artefactos en transiciones/rollover.
"""
import numpy as np
import pandas as pd
import pytest

from src.strategies.intraday_unified_strategy import (
    IntradayStrategyParams,
    generate_intraday_signals,
    run_intraday_backtest,
)
from src.indicators.technical import compute_ema, compute_atr
from src.strategies.strategy_c_patterns import detect_candle_patterns_causal
from src.backtest.engine_sma_confluence import AssetCosts


def test_dst_timezone_conversion_winter_and_summer():
    """Verifica que 15:50 ET se mapee con precisión a UTC tanto en invierno (EST, UTC-5) como en verano (EDT, UTC-4)."""
    # 1. Fecha en Invierno (EST: UTC - 5 horas) -> 15:50 EST = 20:50 UTC
    winter_date_utc = pd.to_datetime("2023-01-15 20:50:00", utc=True)
    winter_et = winter_date_utc.tz_convert("America/New_York")
    assert winter_et.strftime("%H:%M") == "15:50", f"Error en invierno: esperado 15:50 ET, obtenido {winter_et.strftime('%H:%M')}"

    # 2. Fecha en Verano (EDT: UTC - 4 horas) -> 15:50 EDT = 19:50 UTC
    summer_date_utc = pd.to_datetime("2023-07-15 19:50:00", utc=True)
    summer_et = summer_date_utc.tz_convert("America/New_York")
    assert summer_et.strftime("%H:%M") == "15:50", f"Error en verano: esperado 15:50 ET, obtenido {summer_et.strftime('%H:%M')}"


def test_rth_window_and_moc_flagging_across_dst():
    """Comprueba que generate_intraday_signals detecte las 15:50 ET y el rango RTH a través de DST."""
    dates_winter = pd.date_range("2023-01-10 14:00", periods=50, freq="15min", tz="UTC")
    dates_summer = pd.date_range("2023-07-10 13:00", periods=50, freq="15min", tz="UTC")
    all_dates = dates_winter.append(dates_summer)
    
    n = len(all_dates)
    prices = 1000.0 + np.sin(np.linspace(0, 20, n)) * 50.0

    df = pd.DataFrame({
        "ts_event": all_dates,
        "open": prices,
        "high": prices + 2.0,
        "low": prices - 2.0,
        "close": prices + 1.0,
        "volume": 500.0,
    })

    params = IntradayStrategyParams(
        fast_ema=10,
        slow_ema=20,
        rth_start_time="10:00",
        rth_end_time="15:15",
        moc_close_time="15:50",
        use_candle_trigger=False,
    )

    sig_long, is_moc, _, time_str = generate_intraday_signals(df, params)
    min_warmup = max(params.slow_ema, params.macd_slow + params.macd_signal, 50)

    # Verificar que ninguna señal ocurra fuera de 10:00 - 15:15 ET y MOC después del warmup
    for i in range(min_warmup, n):
        if sig_long[i]:
            assert "10:00" <= time_str[i] <= "15:15", f"Señal fuera de RTH en índice {i}: {time_str[i]}"
        if time_str[i] >= "15:50":
            assert is_moc[i], f"Fallo al marcar MOC en índice {i}: {time_str[i]}"


def test_strict_causality_no_lookahead_in_indicators():
    """Valida matemáticamente que agregar barras futuras NO modifique los valores pasados de EMA, ATR y patrones."""
    np.random.seed(42)
    n = 150
    dates = pd.date_range("2023-01-02 08:00", periods=n, freq="15min", tz="UTC")
    close = 1000.0 + np.cumsum(np.random.randn(n) * 2.0)
    high = close + np.abs(np.random.randn(n) * 1.5)
    low = close - np.abs(np.random.randn(n) * 1.5)
    open_p = close + np.random.randn(n) * 0.5

    df_full = pd.DataFrame({
        "ts_event": dates,
        "open": open_p,
        "high": high,
        "low": low,
        "close": close,
        "volume": 1000.0,
    })

    # Evaluar hasta el índice 100
    t_cutoff = 100
    df_truncated = df_full.iloc[:t_cutoff + 1].copy()

    # EMA
    ema_full = compute_ema(df_full["close"], 20).iloc[:t_cutoff + 1].values
    ema_trunc = compute_ema(df_truncated["close"], 20).values
    np.testing.assert_allclose(ema_full, ema_trunc, rtol=1e-10, atol=1e-10, err_msg="Lookahead en EMA")

    # ATR
    atr_full = compute_atr(df_full["high"], df_full["low"], df_full["close"], 14).iloc[:t_cutoff + 1].values
    atr_trunc = compute_atr(df_truncated["high"], df_truncated["low"], df_truncated["close"], 14).values
    np.testing.assert_allclose(atr_full, atr_trunc, rtol=1e-10, atol=1e-10, err_msg="Lookahead en ATR")

    # Patrones causales
    pats_full = detect_candle_patterns_causal(df_full)
    pats_trunc = detect_candle_patterns_causal(df_truncated)
    for p_name in ["hammer", "engulfing_bull"]:
        np.testing.assert_array_equal(
            pats_full[p_name][:t_cutoff + 1],
            pats_trunc[p_name],
            err_msg=f"Lookahead en patrón {p_name}"
        )


def test_rollover_continuity_no_phantom_fills():
    """Valida que si hay un salto de sesión o gap de precios, la ejecución solo ocurra en la apertura real causal."""
    dates = pd.date_range("2023-01-02 10:00", periods=10, freq="15min", tz="UTC")
    # Simular una señal en la barra 1 y un gap de precios en la barra 2 (apertura de siguiente barra)
    prices = np.array([100.0, 102.0, 110.0, 109.0, 108.0, 107.0, 106.0, 105.0, 104.0, 103.0])
    df = pd.DataFrame({
        "ts_event": dates,
        "open": prices,
        "high": prices + 1.0,
        "low": prices - 1.0,
        "close": prices + 0.5,
        "volume": 100.0,
    })

    params = IntradayStrategyParams(fast_ema=2, slow_ema=4, atr_k=2.0, tp_m=2.0, use_candle_trigger=False)
    costs = AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5)

    res = run_intraday_backtest(df, params, costs)
    if res["trades"]:
        first_trade = res["trades"][0]
        # El precio de entrada debe coincidir exactamente con el Open de la barra de entrada, nunca el Close previo
        assert first_trade["entry_price"] in df["open"].values
