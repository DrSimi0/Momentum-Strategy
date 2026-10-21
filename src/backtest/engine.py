"""Motor de backtest barra a barra para la estrategia de ruptura Donchian con stop chandelier.

Reglas de ejecución (fijas, ver DECISIONS.md):
- Señal al cierre de la barra i; entrada a la apertura de i+1 con deslizamiento y comisión taker.
- Stop inicial y trailing a ``atr_mult * ATR`` del extremo favorable (se ajusta solo a favor).
- Si la apertura salta el stop, se ejecuta a la apertura (peor precio).
- Funding real en cada timestamp de funding si la posición venía abierta desde antes de la barra.
- Liquidación simulada con margen cruzado sobre todo el equity.
- Al final del periodo, la posición abierta se cierra al cierre de la última barra.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

BAR = pd.Timedelta(hours=4)


@dataclass(frozen=True)
class StrategyParams:
    channel_n: int
    atr_mult: float

    @property
    def key(self) -> str:
        return f"N{self.channel_n}_k{self.atr_mult:g}"


@dataclass(frozen=True)
class CostModel:
    fee_rate: float = 0.0005
    slippage_rate: float = 0.0005
    funding_multiplier: float = 1.0  # solo se aplica al funding PAGADO

    def scaled(self, factor: float) -> "CostModel":
        return CostModel(self.fee_rate * factor, self.slippage_rate * factor, self.funding_multiplier * factor)


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 10_000.0
    risk_per_trade: float = 0.01
    max_leverage: float = 3.0
    atr_period: int = 14
    maintenance_margin_rate: float = 0.005
    costs: CostModel = field(default_factory=CostModel)


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity: pd.DataFrame
    liquidations: int
    params: StrategyParams | None
    start: pd.Timestamp
    end: pd.Timestamp


TRADE_COLS = ["entry_time", "exit_time", "side", "qty", "entry_raw", "entry_price", "exit_raw", "exit_price",
              "notional_entry", "equity_at_entry", "risk_usdt", "gross_pnl", "fees", "slippage", "funding",
              "net_pnl", "bars_held", "exit_reason"]


def prepare_bars(klines: pd.DataFrame, funding: pd.DataFrame) -> pd.DataFrame:
    """Une velas con funding: cada funding se asigna a la barra cuya apertura coincide con su hora."""
    bars = klines.copy().reset_index(drop=True)
    f = funding.copy()
    f["open_time"] = f["funding_time"].dt.floor("h")
    f = f.drop_duplicates("open_time", keep="last")
    bars = bars.merge(f[["open_time", "funding_rate", "mark_price"]], on="open_time", how="left")
    bars["funding_price"] = bars["mark_price"].where(bars["mark_price"] > 0, bars["open"])
    return bars.drop(columns="mark_price")


def wilder_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    prev = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev), np.abs(low - prev)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


def donchian(high: np.ndarray, low: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Máximo/mínimo de las n barras ANTERIORES (excluye la barra actual)."""
    hi = pd.Series(high).rolling(n).max().shift(1).to_numpy()
    lo = pd.Series(low).rolling(n).min().shift(1).to_numpy()
    return hi, lo


def _to_utc_ts(val) -> pd.Timestamp:
    ts = pd.Timestamp(val)
    if ts.tz is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def period_slice(bars: pd.DataFrame, start, end) -> tuple[int, int]:
    """Índices [i0, i1] (inclusive) de las barras con open_time en [start, end)."""
    t = bars["open_time"]
    st_ts = _to_utc_ts(start)
    end_ts = _to_utc_ts(end)
    idx = np.flatnonzero((t >= st_ts) & (t < end_ts))
    if len(idx) == 0:
        raise ValueError(f"Sin barras en [{start}, {end})")
    return int(idx[0]), int(idx[-1])


def _liq_price(side: int, qty: float, entry: float, equity: float, mmr: float) -> float:
    if side > 0:
        return max((qty * entry - equity) / (qty * (1 - mmr)), 0.0)
    return (equity + qty * entry) / (qty * (1 + mmr))


def run_backtest(bars: pd.DataFrame, params: StrategyParams, cfg: BacktestConfig, start, end) -> BacktestResult:
    o, h, l, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    frate = bars["funding_rate"].to_numpy(float)
    fprice = bars["funding_price"].to_numpy(float)
    times = bars["open_time"]
    atr = wilder_atr(h, l, c, cfg.atr_period)
    dch, dcl = donchian(h, l, params.channel_n)
    i0, i1 = period_slice(bars, start, end)
    if i0 < params.channel_n + cfg.atr_period:
        raise ValueError("Calentamiento insuficiente antes del periodo")
    fee, slip, fmult = cfg.costs.fee_rate, cfg.costs.slippage_rate, cfg.costs.funding_multiplier
    mmr, k = cfg.maintenance_margin_rate, params.atr_mult

    cash = cfg.initial_capital
    cum_fee = cum_slip = cum_fund = 0.0
    side, qty = 0, 0.0
    pending = 0
    trades: list[dict] = []
    tr: dict = {}
    eq_rows = [(_to_utc_ts(start), cash, cash, 0.0, 0.0, 0.0, 0.0)]
    liquidations = 0
    last_equity = cash
    entry_fill = stop = extreme = liq = 0.0

    def close_trade(i: int, raw: float, fill: float, reason: str, extra_fee: float = 0.0) -> None:
        nonlocal cash, cum_fee, cum_slip, side, qty
        f = fee * qty * fill + extra_fee
        s = qty * abs(fill - raw)
        cash += side * qty * (fill - entry_fill) - f
        cum_fee += f
        cum_slip += s
        tr.update(exit_time=times.iloc[i] + BAR, exit_raw=raw, exit_price=fill, bars_held=i - tr["_i"] + 1,
                  exit_reason=reason)
        tr["fees"] += f
        tr["slippage"] += s
        tr["gross_pnl"] = side * qty * (raw - tr["entry_raw"])
        tr["net_pnl"] = tr["gross_pnl"] - tr["fees"] - tr["slippage"] - tr["funding"]
        trades.append({kk: tr[kk] for kk in TRADE_COLS})
        side, qty = 0, 0.0

    for i in range(i0, i1 + 1):
        if pending and last_equity > 0:
            dist = k * atr[i - 1]
            raw = o[i]
            entry_fill = raw * (1 + pending * slip)
            q = cfg.risk_per_trade * last_equity / dist
            q = min(q, cfg.max_leverage * last_equity / entry_fill)
            side, qty = pending, q
            f = fee * qty * entry_fill
            s = qty * abs(entry_fill - raw)
            cash -= f
            cum_fee += f
            cum_slip += s
            stop = entry_fill - side * dist
            extreme = entry_fill
            liq = _liq_price(side, qty, entry_fill, last_equity - f, mmr)
            tr = dict(entry_time=times.iloc[i], side=side, qty=qty, entry_raw=raw, entry_price=entry_fill,
                      notional_entry=qty * entry_fill, equity_at_entry=last_equity, risk_usdt=qty * dist,
                      fees=f, slippage=s, funding=0.0, _i=i)
            just_entered = True
        else:
            just_entered = False
        pending = 0

        if side != 0 and not just_entered and not np.isnan(frate[i]):
            pay = side * qty * fprice[i] * frate[i]
            if pay > 0:
                pay *= fmult
            cash -= pay
            cum_fund += pay
            tr["funding"] += pay

        if side > 0:
            if (not just_entered and o[i] <= liq) or (l[i] <= liq and liq > stop):
                liquidations += 1
                close_trade(i, liq, liq, "liquidation", extra_fee=mmr * qty * liq)
            elif l[i] <= stop:
                raw = min(o[i], stop)
                close_trade(i, raw, raw * (1 - slip), "stop")
        elif side < 0:
            if (not just_entered and o[i] >= liq) or (h[i] >= liq and liq < stop):
                liquidations += 1
                close_trade(i, liq, liq, "liquidation", extra_fee=mmr * qty * liq)
            elif h[i] >= stop:
                raw = max(o[i], stop)
                close_trade(i, raw, raw * (1 + slip), "stop")

        if side != 0:
            if side > 0:
                extreme = max(extreme, h[i])
                stop = max(stop, extreme - k * atr[i])
            else:
                extreme = min(extreme, l[i])
                stop = min(stop, extreme + k * atr[i])
            if i == i1:
                close_trade(i, c[i], c[i] * (1 - side * slip), "end_of_period")

        notional = side * qty * c[i]
        equity = cash + (side * qty * (c[i] - entry_fill) if side != 0 else 0.0)
        equity = max(equity, 0.0)
        last_equity = equity
        eq_rows.append((times.iloc[i] + BAR, equity, equity + cum_fee + cum_slip + cum_fund, notional,
                        cum_fee, cum_slip, cum_fund))

        if side == 0 and i < i1 and equity > 0 and not np.isnan(dch[i]):
            if c[i] > dch[i]:
                pending = 1
            elif c[i] < dcl[i]:
                pending = -1

    equity_df = pd.DataFrame(eq_rows, columns=["time", "equity", "gross_equity", "notional", "cum_fees",
                                               "cum_slippage", "cum_funding"])
    trades_df = pd.DataFrame(trades, columns=TRADE_COLS)
    return BacktestResult(trades_df, equity_df, liquidations, params,
                          _to_utc_ts(start), _to_utc_ts(end))
