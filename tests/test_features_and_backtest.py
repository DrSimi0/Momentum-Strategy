"""Tests unitarios exhaustivos para el pipeline de características, backtest e inferencia.
Valida:
1. Manejo exacto de zonas horarias y DST (marzo y noviembre).
2. Exclusión de cierres anticipados.
3. Ausencia de fuga de futuro (no look-ahead) en mediana expansiva y señales.
4. Cálculo a mano exacto de PnL, deslizamiento y comisiones en ES y NQ.
5. Inferencia estadística, bootstrap reproducible y corrección de Holm-Bonferroni.
"""
import math
import numpy as np
import pandas as pd
import pytest

from src.data.calendar import get_market_sessions, utc_to_et, TIMEZONE_ET
from src.data.validate import validate_ohlcv_invariants, check_critical_bars, DataIntegrityError
from src.features.build import (
    compute_daily_intraday_features,
    compute_expanding_volatility_filters,
    generate_hypothesis_signals,
)
from src.backtest.costs import CostSpec, calculate_trade_costs, DEFAULT_COST_CASES
from src.backtest.engine import simulate_trades
from src.analysis.metrics import (
    compute_performance_metrics,
    run_predictive_regression,
    compute_oos_r_squared,
)
from src.analysis.inference import (
    bootstrap_sharpe_distribution,
    permutation_test_signals,
    holm_bonferroni_correction,
)


# =========================================================================
# 1. Calendario y manejo de DST
# =========================================================================

def test_dst_transitions_march_and_november():
    """Verifica que la conversión UTC -> ET sea exacta en los domingos de cambio de horario (marzo y noviembre)."""
    # Marzo 2024: Domingo 10 de marzo 2024 a las 02:00 ET pasa a 03:00 ET (UTC-4)
    # 2024-03-08 (antes del cambio, invierno): 15:30 ET = 20:30 UTC
    # 2024-03-11 (lunes posterior, verano): 15:30 ET = 19:30 UTC
    ts_winter_utc = pd.to_datetime(["2024-03-08 20:30:00"], utc=True)
    ts_summer_utc = pd.to_datetime(["2024-03-11 19:30:00"], utc=True)

    et_winter = utc_to_et(ts_winter_utc)
    et_summer = utc_to_et(ts_summer_utc)

    assert et_winter[0].hour == 15 and et_winter[0].minute == 30
    assert et_winter[0].strftime("%z") == "-0500"  # EST

    assert et_summer[0].hour == 15 and et_summer[0].minute == 30
    assert et_summer[0].strftime("%z") == "-0400"  # EDT

    # Noviembre 2024: Domingo 3 de noviembre pasa a invierno (UTC-5)
    # 2024-11-01 (viernes previo, verano): 15:30 ET = 19:30 UTC
    # 2024-11-04 (lunes posterior, invierno): 15:30 ET = 20:30 UTC
    ts_nov_summer = pd.to_datetime(["2024-11-01 19:30:00"], utc=True)
    ts_nov_winter = pd.to_datetime(["2024-11-04 20:30:00"], utc=True)

    assert utc_to_et(ts_nov_summer)[0].hour == 15
    assert utc_to_et(ts_nov_summer)[0].strftime("%z") == "-0400"

    assert utc_to_et(ts_nov_winter)[0].hour == 15
    assert utc_to_et(ts_nov_winter)[0].strftime("%z") == "-0500"


def test_calendar_early_closes_excluded():
    """Verifica que el calendario detecte y excluya días de cierre anticipado (e.g., víspera de Navidad o Black Friday)."""
    # 2023: 2023-07-03 (cierre anticipado a las 13:00 ET por el 4 de julio)
    # 2023-11-24 (Black Friday, cierre a las 13:00 ET)
    sessions, early_closes = get_market_sessions("2023-01-01", "2023-12-31")
    assert "2023-07-03" in early_closes
    assert "2023-11-24" in early_closes
    # No deben figurar en las sesiones válidas de trading completo
    valid_str = [s.strftime("%Y-%m-%d") for s in sessions]
    assert "2023-07-03" not in valid_str
    assert "2023-11-24" not in valid_str


# =========================================================================
# 2. Validación de OHLCV
# =========================================================================

def test_validate_ohlcv_invariants():
    """Verifica detección de anomalías en precios y volúmenes."""
    valid_df = pd.DataFrame({
        "ts_event": pd.date_range("2024-01-02 09:30", periods=5, freq="min", tz="UTC"),
        "open": [100.0, 101.0, 102.0, 101.5, 103.0],
        "high": [102.0, 103.0, 104.0, 102.5, 105.0],
        "low": [99.0, 100.5, 101.0, 101.0, 102.0],
        "close": [101.0, 102.0, 101.5, 102.0, 104.0],
        "volume": [10, 20, 15, 30, 25],
    })
    # Caso válido: no lanza excepción
    validate_ohlcv_invariants(valid_df)

    # Caso high < low
    bad_df = valid_df.copy()
    bad_df.loc[2, "high"] = 90.0
    with pytest.raises(DataIntegrityError):
        validate_ohlcv_invariants(bad_df)

    # Caso precio <= 0
    bad_price = valid_df.copy()
    bad_price.loc[1, "close"] = -5.0
    with pytest.raises(DataIntegrityError):
        validate_ohlcv_invariants(bad_price)


# =========================================================================
# 3. Características intradía y garantía anti look-ahead
# =========================================================================

def test_hand_calculated_intraday_features():
    """Verifica el cálculo de r1, r12, r13 contra valores resueltos analíticamente a mano."""
    prev_close = 5000.0
    times = ["09:30", "09:59", "15:00", "15:29", "15:30", "15:59"]
    opens =  [5005.0, 5010.0, 5020.0, 5025.0, 5030.0, 5040.0]
    closes = [5008.0, 5020.0, 5022.0, 5030.0, 5035.0, 5060.0]

    rows = []
    for t, o, c in zip(times, opens, closes):
        rows.append({"time_et_str": t, "open": o, "high": max(o, c) + 1, "low": min(o, c) - 1, "close": c})

    day_df = pd.DataFrame(rows)
    feat = compute_daily_intraday_features(day_df, prev_close_price=prev_close)
    assert feat is not None

    # r1: log(close 09:59 / prev_close) = log(5020 / 5000)
    expected_r1 = math.log(5020.0 / 5000.0)
    assert pytest.approx(feat["r1"], 1e-9) == expected_r1

    # r12: log(close 15:29 / open 15:00) = log(5030 / 5020)
    expected_r12 = math.log(5030.0 / 5020.0)
    assert pytest.approx(feat["r12"], 1e-9) == expected_r12

    # r13: log(close 15:59 / open 15:30) = log(5060 / 5030)
    expected_r13 = math.log(5060.0 / 5030.0)
    assert pytest.approx(feat["r13"], 1e-9) == expected_r13

    assert feat["entry_price"] == 5030.0
    assert feat["exit_price"] == 5060.0


def test_anti_lookahead_expanding_volatility():
    """Garantiza que la mediana expansiva del día t sea estrictamente invariante ante cambios en el día t."""
    n_days = 300
    rng = np.random.default_rng(42)
    fake_vols = rng.uniform(0.0005, 0.0020, size=n_days)

    df1 = pd.DataFrame({"first_30m_vol": fake_vols.copy()})
    df2 = pd.DataFrame({"first_30m_vol": fake_vols.copy()})
    # Modificamos drásticamente el valor de volatilidad del día 280
    df2.loc[280, "first_30m_vol"] = 999.0

    res1 = compute_expanding_volatility_filters(df1, min_history_days=250)
    res2 = compute_expanding_volatility_filters(df2, min_history_days=250)

    # La mediana histórica disponible AL INICIO del día 280 debe ser IDÉNTICA
    assert res1.loc[280, "vol_expanding_median"] == res2.loc[280, "vol_expanding_median"]
    # En cambio, el día 281 sí puede cambiar porque ya incorpora el día 280 como historia previa
    assert res1.loc[281, "vol_expanding_median"] != res2.loc[281, "vol_expanding_median"]


# =========================================================================
# 4. Motor de simulación y costos calculados a mano
# =========================================================================

def test_hand_calculated_es_trade_costs_and_pnl():
    """Verifica PnL y costos calculados a mano para 1 contrato de ES:
    Long (+1): Entrada en 4000.0, Salida en 4010.0 (+10 puntos).
    Multiplicador = $50/pt. Deslizamiento = 0.5 ticks/lado ($6.25/lado = $12.50 round-turn).
    Comisión = $2.00/lado ($4.00 round-turn).
    PnL Bruto = 10 * 50 = $500.00.
    Costos = $12.50 + $4.00 = $16.50.
    PnL Neto = $500.00 - $16.50 = $483.50.
    Nocional = 4000.0 * 50 = $200,000.00.
    Retorno neto = 483.50 / 200000 = 0.0024175.
    """
    df = pd.DataFrame({
        "entry_price": [4000.0],
        "exit_price": [4010.0],
        "sig_H1": [1],
    })

    sim = simulate_trades(
        df=df,
        signal_col="sig_H1",
        multiplier_usd_per_point=50.0,
        tick_size_points=0.25,
        tick_value_usd=12.50,
        cost_spec=DEFAULT_COST_CASES["base"],
        num_contracts=1,
    )

    assert sim.loc[0, "gross_pnl_usd"] == 500.0
    assert sim.loc[0, "commission_usd"] == 4.0
    assert sim.loc[0, "slippage_usd"] == 12.50
    assert sim.loc[0, "total_cost_usd"] == 16.50
    assert sim.loc[0, "net_pnl_usd"] == 483.50
    assert sim.loc[0, "notional_usd"] == 200000.0
    assert pytest.approx(sim.loc[0, "daily_return"], 1e-9) == 0.0024175


def test_hand_calculated_nq_short_trade_costs():
    """Verifica PnL y costos para 1 contrato de NQ en Short (-1):
    Entrada en 18000.0, Salida en 18050.0 (-50 puntos en contra = pérdida bruta).
    Multiplicador = $20/pt. Tick = 0.25 ($5.00/tick).
    Caso Estrés: Slippage = 1.0 tick/lado ($10.00 round-turn). Comisión = $2.50/lado ($5.00 round-turn).
    Costos = $15.00.
    PnL Bruto = -50 * 20 = -$1000.00.
    PnL Neto = -$1000.00 - $15.00 = -$1015.00.
    """
    df = pd.DataFrame({
        "entry_price": [18000.0],
        "exit_price": [18050.0],
        "sig_H1": [-1],
    })

    sim = simulate_trades(
        df=df,
        signal_col="sig_H1",
        multiplier_usd_per_point=20.0,
        tick_size_points=0.25,
        tick_value_usd=5.00,
        cost_spec=DEFAULT_COST_CASES["stress"],
        num_contracts=1,
    )

    assert sim.loc[0, "gross_pnl_usd"] == -1000.0
    assert sim.loc[0, "total_cost_usd"] == 15.0
    assert sim.loc[0, "net_pnl_usd"] == -1015.0


# =========================================================================
# 5. Inferencia estadística, bootstrap reproducible y Holm-Bonferroni
# =========================================================================

def test_bootstrap_reproducibility():
    """Verifica que el bootstrap estacionario sea 100% reproducible fijando la semilla."""
    rng = np.random.default_rng(123)
    returns = rng.normal(0.0005, 0.01, size=200)

    res1 = bootstrap_sharpe_distribution(returns, n_reps=1000, seed=20260421)
    res2 = bootstrap_sharpe_distribution(returns, n_reps=1000, seed=20260421)

    assert res1[0] == res2[0]  # Sharpe observado
    assert res1[1] == res2[1]  # CI
    assert res1[2] == res2[2]  # p-valor


def test_holm_bonferroni_correction_monotonicity():
    """Verifica que los p-valores ajustados por Holm-Bonferroni sean monótonos y controlen FWER."""
    raw_p = {
        "T1": 0.005,
        "T2": 0.020,
        "T3": 0.040,
        "T4": 0.150,
    }
    # m = 4
    # T1: 4 * 0.005 = 0.02
    # T2: 3 * 0.020 = 0.06
    # T3: 2 * 0.040 = 0.08
    # T4: 1 * 0.150 = 0.15
    adj = holm_bonferroni_correction(raw_p)

    assert pytest.approx(adj["T1"]["adjusted_p"], 1e-6) == 0.02
    assert pytest.approx(adj["T2"]["adjusted_p"], 1e-6) == 0.06
    assert pytest.approx(adj["T3"]["adjusted_p"], 1e-6) == 0.08
    assert pytest.approx(adj["T4"]["adjusted_p"], 1e-6) == 0.15

    # T1 rechaza H0 al 5%, T2, T3, T4 no rechazan
    assert adj["T1"]["reject_h0"] is True
    assert adj["T2"]["reject_h0"] is False
    assert adj["T3"]["reject_h0"] is False


def test_predictive_regression_hac():
    """Verifica que la regresión predictiva con Newey-West recupere coeficientes lineales."""
    rng = np.random.default_rng(999)
    x = rng.normal(0, 1, size=300)
    y = 0.5 * x + rng.normal(0, 0.5, size=300)

    reg = run_predictive_regression(y, x, lags=5)
    assert pytest.approx(reg["beta"], abs=0.1) == 0.5
    assert reg["p_value"] < 0.01
