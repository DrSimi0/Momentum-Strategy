"""Baselines: buy & hold y entradas aleatorias con la misma exposición que la estrategia.

Ambos usan el mismo modelo de costos que el motor (comisión, deslizamiento y funding real).
- Buy & hold: largo 1x en el perpetuo desde la apertura de la primera barra hasta el cierre de la última.
- Aleatorio: se toman las duraciones, lados y apalancamientos de entrada de las operaciones reales, se
  permutan y se colocan en posiciones aleatorias sin solaparse (mismo tiempo total en mercado).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest.engine import BAR, TRADE_COLS, BacktestConfig, BacktestResult, _to_utc_ts, period_slice
from src.evaluation import metrics as M


def simulate_fixed_trades(bars: pd.DataFrame, specs: list[tuple[int, int, int, float]], cfg: BacktestConfig,
                          start, end) -> BacktestResult:
    """specs: (barra_entrada a, barra_salida b, lado, apalancamiento). Entra en open[a], sale en close[b]."""
    i0, i1 = period_slice(bars, start, end)
    o, h, l, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    frate = np.nan_to_num(bars["funding_rate"].to_numpy(float))
    fprice = bars["funding_price"].to_numpy(float)
    times = bars["open_time"]
    m_fee, m_slip = cfg.costs.maker_fee, cfg.costs.maker_slippage
    t_fee, t_slip = cfg.costs.taker_fee, cfg.costs.taker_slippage
    fmult = cfg.costs.funding_multiplier
    mmr = cfg.maintenance_margin_rate
    n = i1 - i0 + 1
    eq = np.empty(n)
    notional = np.zeros(n)
    cfee, cslip, cfund = np.zeros(n), np.zeros(n), np.zeros(n)
    cash, tf, ts, tfu = cfg.initial_capital, 0.0, 0.0, 0.0
    cursor, trades, liquidations = i0, [], 0
    for a, b, side, lev in sorted(specs):
        if cash <= 0:
            break
        eq[cursor - i0:a - i0] = cash
        cfee[cursor - i0:a - i0], cslip[cursor - i0:a - i0], cfund[cursor - i0:a - i0] = tf, ts, tfu
        raw_in = o[a]
        fill_in = raw_in * (1 + side * m_slip)
        qty = lev * cash / fill_in
        fee_in, slip_in = m_fee * qty * fill_in, qty * abs(fill_in - raw_in)
        seg = slice(a, b + 1)
        pay = side * qty * fprice[seg] * frate[seg]
        pay[0] = 0.0  # la barra de entrada no paga funding
        pay = np.where(pay > 0, pay * fmult, pay)
        cum_pay = np.cumsum(pay)
        base = cash - fee_in - cum_pay
        mtm = base + side * qty * (c[seg] - fill_in)
        adverse = l[seg] if side > 0 else h[seg]
        worst = base + side * qty * (adverse - fill_in)
        liq_hit = np.flatnonzero(worst <= mmr * qty * adverse)
        reason = "fixed_exit"
        if len(liq_hit):
            liquidations += 1
            j = int(liq_hit[0])
            b, seg = a + j, slice(a, a + j + 1)
            mtm, cum_pay = mtm[: j + 1], cum_pay[: j + 1]
            raw_out = fill_out = adverse[j]
            fee_out = mmr * qty * raw_out + t_fee * qty * raw_out
            reason = "liquidation"
        else:
            raw_out = c[b]
            fill_out = raw_out * (1 - side * t_slip)
            fee_out = t_fee * qty * fill_out
        slip_out = qty * abs(fill_out - raw_out)
        fund = float(cum_pay[-1])
        new_cash = max(cash - fee_in - fund + side * qty * (fill_out - fill_in) - fee_out, 0.0)
        eq[a - i0:b - i0 + 1] = np.maximum(mtm, 0.0)
        eq[b - i0] = new_cash
        notional[a - i0:b - i0] = side * qty * c[a:b]
        cfee[a - i0:b - i0 + 1] = tf + fee_in
        cslip[a - i0:b - i0 + 1] = ts + slip_in
        cfund[a - i0:b - i0 + 1] = tfu + cum_pay
        tf, ts, tfu = tf + fee_in + fee_out, ts + slip_in + slip_out, tfu + fund
        cfee[b - i0], cslip[b - i0], cfund[b - i0] = tf, ts, tfu
        trades.append(dict(entry_time=times.iloc[a], exit_time=times.iloc[b] + BAR, side=side, qty=qty,
                           entry_raw=raw_in, entry_price=fill_in, exit_raw=raw_out, exit_price=fill_out,
                           notional_entry=qty * fill_in, equity_at_entry=cash, risk_usdt=np.nan,
                           gross_pnl=side * qty * (raw_out - raw_in), fees=fee_in + fee_out,
                           slippage=slip_in + slip_out, funding=fund,
                           net_pnl=new_cash - cash, bars_held=b - a + 1, exit_reason=reason))
        cash, cursor = new_cash, b + 1
    eq[cursor - i0:] = cash
    cfee[cursor - i0:], cslip[cursor - i0:], cfund[cursor - i0:] = tf, ts, tfu
    t = pd.concat([pd.Series([_to_utc_ts(start)]), times.iloc[i0:i1 + 1] + BAR], ignore_index=True)
    ini = cfg.initial_capital
    equity = pd.DataFrame({"time": t, "equity": np.r_[ini, eq], "notional": np.r_[0.0, notional],
                           "cum_fees": np.r_[0.0, cfee], "cum_slippage": np.r_[0.0, cslip],
                           "cum_funding": np.r_[0.0, cfund]})
    equity["gross_equity"] = equity["equity"] + equity["cum_fees"] + equity["cum_slippage"] + equity["cum_funding"]
    return BacktestResult(pd.DataFrame(trades, columns=TRADE_COLS), equity, liquidations, None,
                          _to_utc_ts(start), _to_utc_ts(end))


def buy_and_hold(bars: pd.DataFrame, cfg: BacktestConfig, start, end) -> BacktestResult:
    i0, i1 = period_slice(bars, start, end)
    return simulate_fixed_trades(bars, [(i0, i1, 1, 1.0)], cfg, start, end)


def random_specs(i0: int, i1: int, durations: np.ndarray, sides: np.ndarray, levs: np.ndarray,
                 rng: np.random.Generator) -> list[tuple[int, int, int, float]]:
    """Coloca las operaciones permutadas en huecos aleatorios (composición uniforme del tiempo plano)."""
    n = len(durations)
    if n == 0:
        return []
    order = rng.permutation(n)
    d, s, lv = durations[order], sides[order], levs[order]
    flat = (i1 - i0 + 1) - int(d.sum())
    if flat < 0:
        raise ValueError("Las duraciones exceden el periodo")
    cuts = np.sort(rng.choice(flat + n, size=n, replace=False))
    gaps = np.diff(np.concatenate([[-1], cuts, [flat + n]])) - 1
    specs, pos = [], i0
    for j in range(n):
        pos += int(gaps[j])
        specs.append((pos, pos + int(d[j]) - 1, int(s[j]), float(lv[j])))
        pos += int(d[j])
    return specs


def random_entry_baseline(bars: pd.DataFrame, strat: BacktestResult, cfg: BacktestConfig, reps: int,
                          seed: int) -> dict:
    """Distribución de métricas de reps simulaciones aleatorias con la misma exposición que la estrategia."""
    i0, i1 = period_slice(bars, strat.start, strat.end)
    tr = strat.trades
    durations = tr["bars_held"].to_numpy(int)
    sides = tr["side"].to_numpy(int)
    levs = (tr["notional_entry"] / tr["equity_at_entry"]).to_numpy(float)
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(reps):
        res = simulate_fixed_trades(bars, random_specs(i0, i1, durations, sides, levs, rng), cfg,
                                    strat.start, strat.end)
        r = M.daily_returns(res.equity)
        tot = M.total_return(res.equity["equity"])
        days = (strat.end - strat.start) / pd.Timedelta(days=1)
        mdd = M.max_drawdown(res.equity.set_index("time")["equity"])
        cagr = M.annualized_return(tot, days)
        rows.append({"total_return": tot, "cagr": cagr, "sharpe": M.sharpe_ratio(r), "max_drawdown": mdd,
                     "calmar": M.calmar_ratio(cagr, mdd), "expectancy_usdt": float(res.trades["net_pnl"].mean()),
                     "ann_volatility": M.annualized_volatility(r), "liquidations": res.liquidations})
    df = pd.DataFrame(rows)
    q = df.quantile([0.025, 0.5, 0.975])
    return {"reps": reps, "median": q.loc[0.5].to_dict(), "p2_5": q.loc[0.025].to_dict(),
            "p97_5": q.loc[0.975].to_dict(), "samples": df}
