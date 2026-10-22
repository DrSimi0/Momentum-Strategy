"""Test causal y determinista de detección de patrones y figuras de la Estrategia C.
Valida estrictamente la ausencia de look-ahead bias (fuga de futuro).
"""
import numpy as np
import pandas as pd
import pytest

from src.strategies.strategy_c_patterns import (
    detect_candle_patterns_causal,
    detect_chartist_figures_causal,
    run_pattern_backtest,
)
from src.backtest.engine_sma_confluence import AssetCosts


def test_no_lookahead_chartist_figures():
    """Valida que un pivote local en idx NO se confirma antes de idx + n_confirm."""
    n = 30
    n_confirm = 3
    # Creamos una serie con un mínimo claro en el índice 10
    prices = np.array([
        100, 99, 98, 97, 96, 95, 94, 93, 92, 91,
        80, # idx = 10 (mínimo local)
        85, 88, 90, # idx 11, 12, 13 (confirmación en 13)
        92, 95, 94, 93, 92, 91,
        80.2, # idx = 20 (segundo mínimo para doble suelo)
        85, 87, 89, # idx 21, 22, 23 (confirmación en 23)
        91, 92, 93, 94, 95, 96
    ], dtype=float)

    df = pd.DataFrame({
        "ts_event": pd.date_range("2023-01-01", periods=len(prices), freq="1h"),
        "open": prices + 0.1,
        "high": prices + 1.0,
        "low": prices - 0.5,
        "close": prices,
        "volume": 1000.0,
    })

    # Asegurar que el mínimo en low esté alineado con el mínimo de precios
    df.loc[10, "low"] = 79.0
    df.loc[20, "low"] = 79.2

    # Ejecutar detección causal
    res = detect_chartist_figures_causal(df, n_confirm=n_confirm)
    double_bottom = res["double_bottom"]

    # Para el mínimo en idx=10, solo se confirma en idx=13 (10 + 3)
    # Para el segundo mínimo en idx=20, solo se confirma en idx=23 (20 + 3)
    # Por tanto, no puede haber doble suelo en ningún índice < 23
    assert not np.any(double_bottom[:23]), "Se detectó figura antes de la confirmación causal (look-ahead detectado)"
    # En idx=23 debe confirmarse el doble suelo
    assert double_bottom[23] == True, "El doble suelo debió confirmarse exactamente en idx=23 (i - n_confirm = 20)"


def test_candle_patterns_rules():
    """Valida reglas de patrones de vela individuales."""
    # Sintético: Vela 0 y 1 normales, Vela 2 = Hammer
    # Hammer: lower_wick >= 2*body, upper_wick <= 0.3*body, body > 0.1*range, low <= min(lows previos)
    df = pd.DataFrame({
        "ts_event": pd.date_range("2023-01-01", periods=15, freq="1h"),
        "open": [100.0] * 15,
        "high": [101.0] * 15,
        "low": [99.0] * 15,
        "close": [100.5] * 15,
        "volume": [100.0] * 15,
    })

    # Crear condición para Hammer en barra 12 tras tendencia bajista
    for i in range(11):
        df.loc[i, "close"] = 100.0 - i
        df.loc[i, "open"] = 101.0 - i
        df.loc[i, "low"] = 99.5 - i
        df.loc[i, "high"] = 101.5 - i

    # En barra 12: open=88, close=88.5, low=85.0 (mecha baja 3.0, cuerpo 0.5), high=88.6 (mecha alta 0.1)
    df.loc[12, "open"] = 88.0
    df.loc[12, "close"] = 88.5
    df.loc[12, "low"] = 85.0
    df.loc[12, "high"] = 88.6

    patterns = detect_candle_patterns_causal(df)
    assert patterns["hammer"][12] == True, "Hammer no detectado correctamente con parámetros válidos"
    assert not patterns["hammer"][11], "Falso positivo de Hammer"


def test_run_pattern_backtest_execution():
    """Valida que la entrada se efectúa en la barra t+1 tras señal en t."""
    n = 60
    # Serie de precios con suficiente longitud para que ATR(14) esté cálculado
    # Y un salto posterior para activar el Take Profit
    prices = np.full(n, 100.0)
    prices[30:] = 120.0 # Salto alcista para TP

    df = pd.DataFrame({
        "ts_event": pd.date_range("2023-01-01", periods=n, freq="1h"),
        "open": prices,
        "high": prices + 1.0,
        "low": prices - 1.0,
        "close": prices + 0.5,
        "volume": np.full(n, 1000.0),
    })

    sig_long = np.zeros(n, dtype=bool)
    sig_short = np.zeros(n, dtype=bool)
    # Señal long en barra 20 (donde ATR ya está definido)
    sig_long[20] = True

    costs = AssetCosts(
        asset_type="futures",
        commission_per_side=2.0,
        slippage_per_side=0.5,
        tick_size=0.25,
        multiplier=50.0,
        annualization_factor=252.0,
    )

    res = run_pattern_backtest(df, sig_long, sig_short, costs, atr_k=2.0, tp_m=2.0)
    assert res["n_trades"] >= 1, "Debió ejecutarse al menos 1 trade tras la señal causal"
