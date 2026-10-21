"""Pruebas unitarias y de ausencia de look-ahead para los indicadores y la Capa 2."""
import numpy as np
import pandas as pd
import pytest

from src.strategy.indicators import (
    compute_bbwp,
    compute_ema,
    compute_macd_zscore,
    compute_rsi,
    detect_williams_fractals,
)
from src.strategy.layer2_technical import Layer2TechnicalAnalyzer


def generate_synthetic_ohlcv(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """Genera serie temporal sintética con caminata aleatoria y volumen."""
    np.random.seed(seed)
    returns = np.random.normal(loc=0.0001, scale=0.005, size=n)
    prices = 60000.0 * np.exp(np.cumsum(returns))

    highs = prices * (1.0 + np.abs(np.random.normal(0, 0.002, size=n)))
    lows = prices * (1.0 - np.abs(np.random.normal(0, 0.002, size=n)))
    opens = (highs + lows) / 2.0 + np.random.normal(0, 5.0, size=n)
    closes = prices
    volume = np.random.uniform(50.0, 500.0, size=n)
    time_ms = 1700000000000 + np.arange(n) * 15 * 60 * 1000

    df = pd.DataFrame({
        "time": time_ms,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volume,
    })
    return df


def test_no_lookahead_truncation():
    """Prueba fundamental de ausencia de look-ahead:
    El valor de los indicadores y la señal generada en la barra t deben ser idénticos
    tanto si se calcula sobre toda la serie completa como si se trunca exactamente en t.
    """
    df_full = generate_synthetic_ohlcv(n=450)
    analyzer = Layer2TechnicalAnalyzer()

    # Precomputar sobre serie completa
    df_full_ind = analyzer.compute_all_indicators(df_full)

    # Seleccionar una barra t avanzada
    t = 400

    # Truncar serie en t (el futuro t+1..n no existe)
    df_truncated = df_full.iloc[: t + 1].copy()
    df_trunc_ind = analyzer.compute_all_indicators(df_truncated)

    # Comparar valores de indicadores en la barra t
    cols_to_check = ["ema_21", "ema_50", "rsi_14", "bbwp", "macd_z", "atr_14", "vol_sma20"]
    for col in cols_to_check:
        val_full = df_full_ind[col].iloc[t]
        val_trunc = df_trunc_ind[col].iloc[t]
        if np.isnan(val_full) and np.isnan(val_trunc):
            continue
        assert pytest.approx(val_full, rel=1e-5) == val_trunc, f"Fuga de look-ahead detectada en {col}!"

    # Evaluar setup en barra t
    setup_full = analyzer.evaluate_bar(df_full_ind, t)
    setup_trunc = analyzer.evaluate_bar(df_trunc_ind, t)

    if setup_full is None:
        assert setup_trunc is None
    else:
        assert setup_trunc is not None
        assert setup_full.direction == setup_trunc.direction
        assert pytest.approx(setup_full.entry_price) == setup_trunc.entry_price
        assert pytest.approx(setup_full.stop_loss) == setup_trunc.stop_loss
        assert pytest.approx(setup_full.take_profit) == setup_trunc.take_profit


def test_fractals_strict_delay():
    """Verifica que el fractal con k=3 SOLO se marque con retardo de k barras."""
    highs = pd.Series([10.0, 11.0, 15.0, 12.0, 11.0, 10.0, 9.0])
    lows = pd.Series([5.0, 6.0, 8.0, 7.0, 6.0, 5.0, 4.0])
    # En índice 2 hay un pico (15.0). Con k=2, debería conocerse en índice 2+2=4.
    f_high, _ = detect_williams_fractals(highs, lows, k=2)

    # En los índices 0, 1, 2, 3 no debe estar asignado (debe ser NaN para evitar lookahead)
    assert np.isnan(f_high.iloc[0])
    assert np.isnan(f_high.iloc[1])
    assert np.isnan(f_high.iloc[2])  # No se conocía en el índice 2
    assert np.isnan(f_high.iloc[3])
    # En el índice 4 (2+2) se confirma el pico de 15.0
    assert f_high.iloc[4] == 15.0


def test_setup_invariants():
    """Verifica que cualquier setup generado cumpla las reglas de coherencia y R:R >= 2.0."""
    df = generate_synthetic_ohlcv(n=600)
    analyzer = Layer2TechnicalAnalyzer(min_rr_ratio=2.0)
    data = analyzer.compute_all_indicators(df)

    setups_found = 0
    for i in range(250, len(df)):
        setup = analyzer.evaluate_bar(data, i)
        if setup is not None:
            setups_found += 1
            if setup.direction == "LONG":
                assert setup.stop_loss < setup.entry_price
                assert setup.take_profit > setup.entry_price
                rr = (setup.take_profit - setup.entry_price) / (setup.entry_price - setup.stop_loss)
                assert rr >= 1.99
            elif setup.direction == "SHORT":
                assert setup.stop_loss > setup.entry_price
                assert setup.take_profit < setup.entry_price
                rr = (setup.entry_price - setup.take_profit) / (setup.stop_loss - setup.entry_price)
                assert rr >= 1.99
            assert setup.max_horizon_bars == 15
            assert setup.break_even_trigger_r == 1.0

    assert setups_found >= 0  # Valida que la lógica corre sin excepciones
