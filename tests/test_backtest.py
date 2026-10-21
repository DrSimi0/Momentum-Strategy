"""Motor de backtest y baselines contra un ejemplo calculado a mano."""
import numpy as np
import pandas as pd
import pytest

from src.backtest.engine import BacktestConfig, CostModel, StrategyParams, run_backtest
from src.evaluation.baselines import buy_and_hold, random_specs, simulate_fixed_trades

T = pd.date_range("2024-01-01", periods=8, freq="4h", tz="UTC")
START, END = T[3], T[7] + pd.Timedelta(hours=4)
CFG = BacktestConfig(initial_capital=10_000, risk_per_trade=0.01, max_leverage=3, atr_period=1,
                     costs=CostModel(fee_rate=0.001, slippage_rate=0.001))


def bars(funding_at_6=0.001):
    b = pd.DataFrame({"open_time": T,
                      "open": [100, 100, 100, 100, 100, 102, 103, 100.0],
                      "high": [101, 101, 101, 101, 103, 104, 103, 101.0],
                      "low": [99, 99, 99, 99, 99, 101, 100, 99.5],
                      "close": [100, 100, 100, 100, 102, 103, 100.5, 100.0]})
    b["funding_rate"] = np.nan
    b.loc[6, "funding_rate"] = funding_at_6
    b["funding_price"] = b["open"]
    return b


def test_engine_hand_example():
    r = run_backtest(bars(), StrategyParams(channel_n=2, atr_mult=1.0), CFG, START, END)
    assert len(r.trades) == 1
    t = r.trades.iloc[0]
    # señal en barra 4 (102 > max(101,101)); ATR(1)=TR=4 -> distancia 4; qty = 1% * 10000 / 4 = 25
    assert t.side == 1 and t.qty == pytest.approx(25)
    assert t.entry_price == pytest.approx(102 * 1.001)               # 102.102
    # stop trailing tras barra 5: max(98.102, 104 - 3) = 101 ; barra 6 low 100 -> sale a 101 * 0.999
    assert t.exit_raw == pytest.approx(101) and t.exit_price == pytest.approx(100.899)
    assert t.gross_pnl == pytest.approx(25 * (101 - 102))             # -25
    assert t.fees == pytest.approx(0.001 * 25 * 102.102 + 0.001 * 25 * 100.899)   # 5.075025
    assert t.slippage == pytest.approx(25 * 0.102 + 25 * 0.101)                   # 5.075
    assert t.funding == pytest.approx(25 * 103 * 0.001)                           # 2.575 (largo paga)
    assert t.net_pnl == pytest.approx(-37.725025)
    assert t.risk_usdt == pytest.approx(100)
    eq = r.equity.set_index("time")["equity"]
    assert eq.iloc[-1] == pytest.approx(10_000 - 37.725025)
    # cierre barra 5: caja 10000 - 2.55255 + 25*(103 - 102.102)
    assert eq.loc[T[5] + pd.Timedelta(hours=4)] == pytest.approx(10_000 - 2.55255 + 22.45)
    assert r.equity["gross_equity"].iloc[-1] == pytest.approx(10_000 - 25)
    assert r.liquidations == 0


def test_funding_multiplier_only_on_paid():
    p = StrategyParams(2, 1.0)
    base = run_backtest(bars(), p, CFG, START, END).trades.iloc[0]
    stressed = run_backtest(bars(), p, BacktestConfig(**{**CFG.__dict__, "costs": CFG.costs.scaled(2)}),
                            START, END).trades.iloc[0]
    assert stressed.funding == pytest.approx(2 * base.funding)
    assert stressed.fees > 1.9 * base.fees
    received = run_backtest(bars(-0.001), p, BacktestConfig(**{**CFG.__dict__, "costs": CFG.costs.scaled(2)}),
                            START, END).trades.iloc[0]
    assert received.funding == pytest.approx(-25 * 103 * 0.001)  # el cobrado no se duplica


def test_end_of_period_exit():
    b = bars()
    b.loc[6, ["high", "low", "close"]] = [104.5, 102.5, 104.0]  # stop sube a 104.5 - 2 = 102.5, no se toca
    b.loc[7, ["open", "high", "low", "close"]] = [104, 106, 103.5, 105.0]
    t = run_backtest(b, StrategyParams(2, 1.0), CFG, START, END).trades.iloc[0]
    assert t.exit_reason == "end_of_period" and t.exit_price == pytest.approx(105 * 0.999)


def test_fixed_trades_and_buy_hold():
    b = bars()
    r = buy_and_hold(b, CFG, START, END)
    t = r.trades.iloc[0]
    q = 10_000 / (100 * 1.001)  # 1x en la apertura de la barra 3
    assert t.qty == pytest.approx(q)
    exp = -0.001 * q * 100.1 - q * 103 * 0.001 + q * (100 * 0.999 - 100.1) - 0.001 * q * 99.9
    assert t.net_pnl == pytest.approx(exp)
    assert r.equity["equity"].iloc[-1] == pytest.approx(10_000 + exp)
    assert t.gross_pnl - t.fees - t.slippage - t.funding == pytest.approx(t.net_pnl)


def test_random_specs_preserve_exposure():
    rng = np.random.default_rng(0)
    d, s, lv = np.array([3, 5, 2]), np.array([1, -1, 1]), np.array([0.5, 1.0, 2.0])
    for _ in range(50):
        sp = random_specs(10, 39, d, s, lv, rng)
        assert sorted(b - a + 1 for a, b, _, _ in sp) == [2, 3, 5]
        assert all(10 <= a <= b <= 39 for a, b, _, _ in sp)
        assert all(sp[i][1] < sp[i + 1][0] for i in range(len(sp) - 1))  # sin solapes
