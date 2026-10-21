"""Métricas de rendimiento, operaciones, riesgo y costos.

Convenciones (ver DECISIONS.md):
- Mercado 24/7: la curva de equity se muestrea al cierre de cada día UTC y se anualiza con 365 días
  (volatilidad y Sharpe con raíz de 365). Tasa libre de riesgo = 0.
- Todas las cifras salen del registro de operaciones y de la curva de equity NETOS de costos.
- VaR/CVaR históricos sobre retornos diarios, expresados como pérdida positiva.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import norm

DAYS_PER_YEAR = 365
EULER_GAMMA = 0.5772156649015329


# ----------------------------------------------------------------------------- curva de equity
def daily_equity(equity: pd.DataFrame, col: str = "equity") -> pd.Series:
    """Equity al cierre de cada día UTC. El primer punto es el capital inicial (día anterior)."""
    s = equity.set_index("time")[col]
    s.index = s.index - pd.Timedelta(microseconds=1)  # una vela que cierra a 00:00 pertenece al día previo
    return s.resample("1D").last().ffill()


def daily_returns(equity: pd.DataFrame, col: str = "equity") -> pd.Series:
    return daily_equity(equity, col).pct_change().dropna()


def total_return(eq: pd.Series) -> float:
    return float(eq.iloc[-1] / eq.iloc[0] - 1)


def annualized_return(total: float, days: float) -> float:
    if days <= 0:
        return float("nan")
    if 1 + total <= 0:
        return -1.0
    return float((1 + total) ** (DAYS_PER_YEAR / days) - 1)


def annualized_volatility(r: pd.Series) -> float:
    return float(np.std(r, ddof=1) * math.sqrt(DAYS_PER_YEAR)) if len(r) > 1 else float("nan")


def sharpe_ratio(r, periods: int = DAYS_PER_YEAR) -> float:
    r = np.asarray(r, float)
    if len(r) < 2:
        return float("nan")
    sd = np.std(r, ddof=1)
    return float(np.mean(r) / sd * math.sqrt(periods)) if sd > 0 else float("nan")


def sortino_ratio(r, periods: int = DAYS_PER_YEAR) -> float:
    r = np.asarray(r, float)
    dd = math.sqrt(np.mean(np.minimum(r, 0.0) ** 2)) if len(r) else 0.0
    return float(np.mean(r) / dd * math.sqrt(periods)) if dd > 0 else float("nan")


def drawdown_series(eq: pd.Series) -> pd.Series:
    return eq / eq.cummax() - 1


def max_drawdown(eq: pd.Series) -> float:
    """Máximo drawdown como fracción positiva (0.25 = -25%)."""
    return float(-drawdown_series(eq).min())


def drawdown_durations(eq: pd.Series) -> dict:
    """Duración (días) del drawdown más largo y del más profundo, de pico a recuperación (o al final)."""
    vals, idx = eq.to_numpy(float), eq.index
    episodes = []  # (inicio_pico, fin, profundidad)
    peak_v, peak_t, depth, in_dd = vals[0], idx[0], 0.0, False
    for t, v in zip(idx[1:], vals[1:]):
        if v >= peak_v:
            if in_dd:
                episodes.append((peak_t, t, depth))
            peak_v, peak_t, depth, in_dd = v, t, 0.0, False
        else:
            in_dd = True
            depth = max(depth, 1 - v / peak_v)
    if in_dd:
        episodes.append((peak_t, idx[-1], depth))
    if not episodes:
        return {"max_dd_duration_days": 0.0, "worst_dd_duration_days": 0.0, "worst_dd_recovered": True}
    durs = [(e - s) / pd.Timedelta(days=1) for s, e, _ in episodes]
    worst = int(np.argmax([d for _, _, d in episodes]))
    recovered = not (in_dd and worst == len(episodes) - 1)
    return {"max_dd_duration_days": float(max(durs)), "worst_dd_duration_days": float(durs[worst]),
            "worst_dd_recovered": recovered}


def calmar_ratio(cagr: float, mdd: float) -> float:
    return float(cagr / mdd) if mdd > 0 else float("nan")


def var_cvar(r, level: float) -> tuple[float, float]:
    """VaR/CVaR históricos: k = ceil(n*(1-level)) peores observaciones. Devuelve pérdidas positivas."""
    s = np.sort(np.asarray(r, float))
    if len(s) == 0:
        return float("nan"), float("nan")
    k = max(1, math.ceil(len(s) * (1 - level) - 1e-9))
    return float(-s[k - 1]), float(-s[:k].mean())


# ----------------------------------------------------------------------------- operaciones
def trade_metrics(trades: pd.DataFrame) -> dict:
    n = len(trades)
    out = {"n_trades": n}
    if n == 0:
        return out | {k: float("nan") for k in ["win_rate", "avg_win", "avg_loss", "expectancy_usdt",
                                                 "expectancy_r", "profit_factor", "top5pct_share",
                                                 "gross_expectancy_usdt"]}
    net = trades["net_pnl"].to_numpy(float)
    wins, losses = net[net > 0], net[net < 0]
    risk = trades["risk_usdt"].to_numpy(float)
    m = math.ceil(0.05 * n)
    total = net.sum()
    out.update(
        win_rate=float(len(wins) / n),
        avg_win=float(wins.mean()) if len(wins) else float("nan"),
        avg_loss=float(losses.mean()) if len(losses) else float("nan"),
        expectancy_usdt=float(net.mean()),
        expectancy_r=float(np.mean(net / risk)) if np.all(np.isfinite(risk)) else float("nan"),
        profit_factor=float(wins.sum() / -losses.sum()) if len(losses) else float("inf"),
        top5pct_n=m,
        top5pct_share=float(np.sort(net)[::-1][:m].sum() / total) if total > 0 else float("nan"),
        gross_expectancy_usdt=float(trades["gross_pnl"].mean()),
        avg_bars_held=float(trades["bars_held"].mean()),
    )
    return out


def r_multiples(trades: pd.DataFrame) -> np.ndarray:
    return (trades["net_pnl"] / trades["risk_usdt"]).to_numpy(float)


def cost_metrics(trades: pd.DataFrame) -> dict:
    fees, slip, fund = (float(trades[c].sum()) for c in ("fees", "slippage", "funding"))
    total = fees + slip + fund
    gross = float(trades["gross_pnl"].sum())
    n = len(trades)
    return {"fees": fees, "slippage": slip, "funding": fund, "total_costs": total, "gross_pnl_total": gross,
            "costs_pct_of_gross": total / gross if gross > 0 else float("nan"),
            "avg_cost_per_trade": total / n if n else float("nan"),
            "gross_expectancy_usdt": gross / n if n else float("nan"),
            "cost_to_gross_expectancy": (total / gross) if gross > 0 else float("nan")}


def exposure_metrics(equity: pd.DataFrame, trades: pd.DataFrame, years: float) -> dict:
    e = equity.iloc[1:]
    n_bars = len(e)
    lev = (e["notional"].abs() / e["equity"].where(e["equity"] > 0)).fillna(0.0)
    entry_lev = (trades["notional_entry"] / trades["equity_at_entry"]).max() if len(trades) else 0.0
    traded = float((trades["qty"] * (trades["entry_price"] + trades["exit_price"])).sum()) if len(trades) else 0.0
    return {"time_in_market": float(trades["bars_held"].sum() / n_bars) if n_bars and len(trades) else 0.0,
            "avg_leverage": float(lev.mean()),
            "max_leverage": float(max(lev.max(), entry_lev)),
            "turnover_annual": traded / float(e["equity"].mean()) / years if years > 0 else float("nan")}


# ----------------------------------------------------------------------------- PSR / DSR
def _moments(r: np.ndarray) -> tuple[float, float]:
    d = r - r.mean()
    m2 = np.mean(d ** 2)
    return float(np.mean(d ** 3) / m2 ** 1.5), float(np.mean(d ** 4) / m2 ** 2)


def probabilistic_sharpe_ratio(r, sr_benchmark: float = 0.0) -> float:
    """PSR (Bailey & López de Prado 2012) con Sharpe NO anualizado de la frecuencia de r."""
    r = np.asarray(r, float)
    n = len(r)
    if n < 3 or np.std(r, ddof=1) == 0:
        return float("nan")
    sr = np.mean(r) / np.std(r, ddof=1)
    skew, kurt = _moments(r)
    denom = 1 - skew * sr + (kurt - 1) / 4 * sr ** 2
    return float(norm.cdf((sr - sr_benchmark) * math.sqrt(n - 1) / math.sqrt(denom)))


def expected_max_sharpe(n_trials: int, sr_variance: float) -> float:
    """SR0: Sharpe máximo esperado por azar entre n_trials (no anualizado)."""
    if n_trials < 2:
        return 0.0
    return float(math.sqrt(sr_variance) * ((1 - EULER_GAMMA) * norm.ppf(1 - 1 / n_trials)
                                           + EULER_GAMMA * norm.ppf(1 - 1 / (n_trials * math.e))))


def deflated_sharpe_ratio(r, n_trials: int, sr_variance: float) -> float:
    return probabilistic_sharpe_ratio(r, expected_max_sharpe(n_trials, sr_variance))


# ----------------------------------------------------------------------------- resumen
def performance_metrics(equity: pd.DataFrame, trades: pd.DataFrame, liquidations: int,
                        start: pd.Timestamp, end: pd.Timestamp) -> dict:
    eq_d = daily_equity(equity)
    r = eq_d.pct_change().dropna()
    days = (end - start) / pd.Timedelta(days=1)
    years = days / DAYS_PER_YEAR
    tot = total_return(equity["equity"])
    cagr = annualized_return(tot, days)
    mdd = max_drawdown(equity.set_index("time")["equity"])
    out = {"days": days, "total_return": tot, "cagr": cagr, "ann_volatility": annualized_volatility(r),
           "sharpe": sharpe_ratio(r), "sortino": sortino_ratio(r), "max_drawdown": mdd,
           "calmar": calmar_ratio(cagr, mdd), "psr": probabilistic_sharpe_ratio(r),
           "liquidations": int(liquidations),
           "gross_total_return": total_return(equity["gross_equity"]),
           "final_equity": float(equity["equity"].iloc[-1])}
    out |= drawdown_durations(equity.set_index("time")["equity"])
    for lv in (0.95, 0.99):
        v, cv = var_cvar(r, lv)
        out[f"var_{int(lv * 100)}"], out[f"cvar_{int(lv * 100)}"] = v, cv
    out |= trade_metrics(trades)
    if len(trades):
        out |= {f"cost_{k}": v for k, v in cost_metrics(trades).items()}
    out |= exposure_metrics(equity, trades, years)
    return out
