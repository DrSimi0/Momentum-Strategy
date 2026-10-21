"""Cada métrica contra un cálculo manual en un ejemplo pequeño (los valores esperados se derivan a mano
en los comentarios)."""
import math

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from src.evaluation import metrics as M
from src.evaluation import robustness as R

SQ365 = math.sqrt(365)
R4 = [0.01, -0.02, 0.03, 0.00]  # media 0.005; desvíos 0.005,-0.025,0.025,-0.005; suma cuadrados 0.0013


def _trades():
    # net = gross - fees - slippage - funding
    return pd.DataFrame({
        "net_pnl": [100.0, -50.0, 200.0, -25.0, 0.0, 75.0],
        "gross_pnl": [110.0, -40.0, 215.0, -20.0, 8.0, 85.0],
        "fees": [5.0, 5.0, 8.0, 3.0, 4.0, 5.0],
        "slippage": [3.0, 3.0, 5.0, 1.0, 2.0, 3.0],
        "funding": [2.0, 2.0, 2.0, 1.0, 2.0, 2.0],
        "risk_usdt": [50.0, 50.0, 100.0, 25.0, 50.0, 50.0],
        "bars_held": [1, 2, 3, 1, 2, 3],
    })


# ----------------------------------------------------------------------------- rendimiento
def test_daily_equity_and_returns():
    t = pd.to_datetime(["2024-01-01 00:00", "2024-01-01 12:00", "2024-01-02 00:00", "2024-01-03 00:00"], utc=True)
    eq = pd.DataFrame({"time": t, "equity": [100.0, 105.0, 110.0, 99.0]})
    d = M.daily_equity(eq)
    # vela que cierra 01-02 00:00 pertenece al 01-01; punto inicial = día previo
    assert list(d.values) == [100.0, 110.0, 99.0]
    assert np.allclose(M.daily_returns(eq).values, [0.10, -0.10])


def test_total_and_annualized_return():
    assert M.total_return(pd.Series([100.0, 121.0])) == pytest.approx(0.21)
    # 1.21^(365/730) - 1 = 1.1 - 1
    assert M.annualized_return(0.21, 730) == pytest.approx(0.10)
    assert M.annualized_return(-1.5, 100) == -1.0


def test_volatility_sharpe_sortino():
    sd = math.sqrt(0.0013 / 3)  # varianza muestral (n-1 = 3)
    assert M.annualized_volatility(pd.Series(R4)) == pytest.approx(sd * SQ365)
    assert M.sharpe_ratio(R4) == pytest.approx(0.005 / sd * SQ365)          # ~4.5889
    # desviación a la baja: sqrt((0 + 0.0004 + 0 + 0)/4) = 0.01
    assert M.sortino_ratio(R4) == pytest.approx(0.005 / 0.01 * SQ365)       # ~9.5525
    assert math.isnan(M.sharpe_ratio([0.01, 0.01, 0.01]))


def test_drawdown_and_durations():
    idx = pd.date_range("2024-01-01", periods=8, freq="D", tz="UTC")
    eq = pd.Series([100, 120, 90, 130, 104, 110, 115, 120], index=idx, dtype=float)
    # peor caída 90/120 - 1 = -25%; segunda 104/130 - 1 = -20%
    assert M.max_drawdown(eq) == pytest.approx(0.25)
    d = M.drawdown_durations(eq)
    # episodio 1: pico día1 -> recupera día3 (2 días); episodio 2: pico día3 -> fin día7 sin recuperar (4 días)
    assert d["max_dd_duration_days"] == pytest.approx(4)
    assert d["worst_dd_duration_days"] == pytest.approx(2)
    assert d["worst_dd_recovered"] is True


def test_calmar():
    assert M.calmar_ratio(0.10, 0.25) == pytest.approx(0.4)
    assert math.isnan(M.calmar_ratio(0.1, 0.0))


def test_var_cvar():
    r = [-0.08, -0.06] + [0.01] * 18  # n = 20
    # 95%: k = ceil(20*0.05) = 1 -> VaR = CVaR = 0.08
    assert M.var_cvar(r, 0.95) == pytest.approx((0.08, 0.08))
    # 90%: k = 2 -> VaR = 0.06, CVaR = (0.08+0.06)/2 = 0.07
    assert M.var_cvar(r, 0.90) == pytest.approx((0.06, 0.07))
    # 99%: k = ceil(0.2) = 1
    assert M.var_cvar(r, 0.99) == pytest.approx((0.08, 0.08))


# ----------------------------------------------------------------------------- operaciones y costos
def test_trade_metrics():
    m = M.trade_metrics(_trades())
    assert m["n_trades"] == 6
    assert m["win_rate"] == pytest.approx(3 / 6)                  # 100, 200, 75 (0 no cuenta como acierto)
    assert m["avg_win"] == pytest.approx(375 / 3)                 # 125
    assert m["avg_loss"] == pytest.approx(-75 / 2)                # -37.5
    assert m["expectancy_usdt"] == pytest.approx(300 / 6)         # 50
    assert m["expectancy_r"] == pytest.approx((2 - 1 + 2 - 1 + 0 + 1.5) / 6)  # 0.58333
    assert m["profit_factor"] == pytest.approx(375 / 75)          # 5
    # 5% de 6 -> ceil(0.3) = 1 operación (200) sobre ganancia neta 300
    assert m["top5pct_share"] == pytest.approx(200 / 300)
    assert m["gross_expectancy_usdt"] == pytest.approx(358 / 6)


def test_cost_metrics():
    c = M.cost_metrics(_trades())
    assert (c["fees"], c["slippage"], c["funding"]) == (30.0, 17.0, 11.0)
    assert c["total_costs"] == 58.0
    assert c["costs_pct_of_gross"] == pytest.approx(58 / 358)
    assert c["avg_cost_per_trade"] == pytest.approx(58 / 6)
    assert c["gross_expectancy_usdt"] == pytest.approx(358 / 6)


def test_exposure_metrics():
    eq = pd.DataFrame({"equity": [1000.0, 1000.0, 1100.0, 1000.0, 1000.0],
                       "notional": [0.0, 2000.0, 2200.0, 0.0, 0.0]})
    tr = pd.DataFrame({"bars_held": [2], "notional_entry": [2000.0], "equity_at_entry": [1000.0],
                       "qty": [20.0], "entry_price": [100.0], "exit_price": [110.0]})
    e = M.exposure_metrics(eq, tr, years=1.0)
    assert e["time_in_market"] == pytest.approx(2 / 4)
    assert e["avg_leverage"] == pytest.approx((2 + 2 + 0 + 0) / 4)
    assert e["max_leverage"] == pytest.approx(2.0)
    # 20*(100+110) = 4200 sobre equity media (1000+1100+1000+1000)/4 = 1025
    assert e["turnover_annual"] == pytest.approx(4200 / 1025)


# ----------------------------------------------------------------------------- PSR / DSR
def test_psr_manual():
    # momentos poblacionales a mano: m2 = 0.0013/4, m3 = 0, m4 = 7.825e-7/4
    m2, m4 = 0.0013 / 4, 7.825e-7 / 4
    skew, kurt = 0.0, m4 / m2 ** 2                     # kurt ~ 1.85207
    sr = 0.005 / math.sqrt(0.0013 / 3)                  # ~0.240192 (no anualizado)
    z = sr * math.sqrt(3) / math.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr ** 2)
    assert M.probabilistic_sharpe_ratio(R4) == pytest.approx(norm.cdf(z))   # ~0.6604
    assert M.probabilistic_sharpe_ratio(R4) == pytest.approx(0.6604, abs=1e-3)


def test_expected_max_sharpe_and_dsr():
    g = 0.5772156649015329
    exp = 0.1 * ((1 - g) * norm.ppf(1 - 1 / 10) + g * norm.ppf(1 - 1 / (10 * math.e)))
    assert M.expected_max_sharpe(10, 0.01) == pytest.approx(exp)
    assert M.expected_max_sharpe(1, 0.01) == 0.0
    assert M.deflated_sharpe_ratio(R4, 1, 0.01) == pytest.approx(M.probabilistic_sharpe_ratio(R4, 0.0))
    assert M.deflated_sharpe_ratio(R4, 10, 0.01) == pytest.approx(M.probabilistic_sharpe_ratio(R4, exp))
    assert M.deflated_sharpe_ratio(R4, 10, 0.01) < M.probabilistic_sharpe_ratio(R4)


# ----------------------------------------------------------------------------- robustez
def test_block_bootstrap_properties():
    x = np.arange(10, dtype=float)
    # bloque = n: cada remuestreo es una rotación circular completa -> media idéntica
    d = R.circular_block_bootstrap(x, np.mean, 50, 10, np.random.default_rng(0))
    assert np.allclose(d, 4.5)
    assert R.default_block_length(125) == 5
    ci = R.bootstrap_ci(np.r_[np.ones(50), -np.ones(50)] + 0.5, np.mean, 2000, seed=1)
    assert ci["lo"] < 0.5 < ci["hi"] and ci["point"] == pytest.approx(0.5)


def test_mc_drawdown():
    # 1 -> 1.1 -> 0.55 -> 0.66 : caída 0.55/1.1 - 1 = -50%
    assert R.path_max_drawdown(np.array([0.1, -0.5, 0.2])) == pytest.approx(0.5)
    mc = R.mc_trade_order_drawdown([0.01, 0.02, 0.03], 100, seed=0)
    assert mc["p95"] == 0.0
    # con una sola pérdida el drawdown es siempre esa pérdida
    mc = R.mc_trade_order_drawdown([0.1, -0.2, 0.1], 100, seed=0)
    assert mc["p95"] == pytest.approx(0.2)


def test_regime_labels_use_previous_day():
    t = pd.date_range("2024-01-01", periods=5 * 6, freq="4h", tz="UTC")
    closes = np.repeat([100.0, 100.0, 115.0, 115.0, 80.0], 6)
    bars = pd.DataFrame({"open_time": t, "close": closes})
    lab = R.regime_labels(bars, lookback_days=1, bull=0.10, bear=-0.10)
    # etiqueta del 01-04: retorno 01-02 -> 01-03 = +15% -> bull; del 01-05: 01-03 -> 01-04 = 0 -> sideways
    assert lab.loc["2024-01-04"] == "bull" and lab.loc["2024-01-05"] == "sideways"


def test_walk_forward_windows():
    w = R.walk_forward_windows("2022-01-01", "2023-04-01", "2020-03-01", 24, 6)
    assert [str(x["test_start"].date()) for x in w] == ["2022-01-01", "2022-07-01", "2023-01-01"]
    assert str(w[-1]["test_end"].date()) == "2023-04-01"         # última ventana parcial
    assert str(w[0]["train_start"].date()) == "2020-03-01"       # recortada por calentamiento
