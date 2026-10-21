"""Pruebas de robustez: bootstrap por bloques, Monte Carlo, estrés de costos, sensibilidad,
subperiodos, regímenes y walk-forward."""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Callable

import numpy as np
import pandas as pd

from src.backtest.engine import BacktestConfig, StrategyParams, run_backtest
from src.evaluation import metrics as M


# ----------------------------------------------------------------------------- bootstrap
def default_block_length(n: int) -> int:
    """Regla n^(1/3) redondeada (mínimo 1)."""
    return max(1, int(round(n ** (1 / 3))))


def circular_block_bootstrap(x, stat: Callable[[np.ndarray], float], reps: int, block: int,
                             rng: np.random.Generator) -> np.ndarray:
    x = np.asarray(x, float)
    n = len(x)
    n_blocks = math.ceil(n / block)
    starts = rng.integers(0, n, size=(reps, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(reps, -1)[:, :n] % n
    return np.array([stat(x[row]) for row in idx])


def bootstrap_ci(x, stat: Callable[[np.ndarray], float], reps: int, seed: int, alpha: float = 0.05,
                 block: int | None = None) -> dict:
    x = np.asarray(x, float)
    if len(x) < 2:
        return {"lo": float("nan"), "hi": float("nan"), "block": None, "point": float("nan")}
    b = block or default_block_length(len(x))
    dist = circular_block_bootstrap(x, stat, reps, b, np.random.default_rng(seed))
    dist = dist[np.isfinite(dist)]
    return {"point": float(stat(x)), "lo": float(np.quantile(dist, alpha / 2)),
            "hi": float(np.quantile(dist, 1 - alpha / 2)), "block": b, "reps": reps}


# ----------------------------------------------------------------------------- Monte Carlo
def path_max_drawdown(returns: np.ndarray) -> float:
    eq = np.concatenate([[1.0], np.cumprod(1 + returns)])
    return float(-(eq / np.maximum.accumulate(eq) - 1).min())


def mc_trade_order_drawdown(trade_returns, reps: int, seed: int) -> dict:
    """Permuta el orden de los retornos por operación (sobre equity) y mide el máximo drawdown."""
    r = np.asarray(trade_returns, float)
    if len(r) == 0:
        return {"p50": float("nan"), "p95": float("nan"), "p99": float("nan"), "observed": float("nan")}
    rng = np.random.default_rng(seed)
    dds = np.array([path_max_drawdown(rng.permutation(r)) for _ in range(reps)])
    return {"observed": path_max_drawdown(r), "p50": float(np.quantile(dds, 0.5)),
            "p95": float(np.quantile(dds, 0.95)), "p99": float(np.quantile(dds, 0.99)), "reps": reps}


# ----------------------------------------------------------------------------- regímenes y subperiodos
def regime_labels(bars: pd.DataFrame, lookback_days: int, bull: float, bear: float) -> pd.Series:
    """Régimen por día UTC usando el retorno de los ``lookback_days`` días que terminan el día ANTERIOR."""
    close = bars.set_index("open_time")["close"].resample("1D").last()
    ret = close.shift(1) / close.shift(1 + lookback_days) - 1
    lab = pd.Series(np.where(ret > bull, "bull", np.where(ret < bear, "bear", "sideways")), index=close.index)
    return lab[ret.notna()]


def _trade_group_stats(tr: pd.DataFrame) -> dict:
    tm = M.trade_metrics(tr)
    return {k: tm.get(k) for k in ("n_trades", "win_rate", "expectancy_usdt", "expectancy_r", "profit_factor")} | {
        "net_pnl": float(tr["net_pnl"].sum()) if len(tr) else 0.0}


def regime_breakdown(result, labels: pd.Series) -> pd.DataFrame:
    tr = result.trades.copy()
    tr["regime"] = tr["entry_time"].dt.floor("D").map(labels)
    r = M.daily_returns(result.equity)
    rd = pd.DataFrame({"r": r.values, "regime": (r.index.floor("D")).map(labels)}, index=r.index)
    rows = []
    for reg in ("bull", "bear", "sideways"):
        sub = rd[rd["regime"] == reg]["r"]
        rows.append({"regime": reg, "days": len(sub), "sharpe_daily_ann": M.sharpe_ratio(sub)}
                    | _trade_group_stats(tr[tr["regime"] == reg]))
    return pd.DataFrame(rows)


def subperiod_breakdown(result) -> pd.DataFrame:
    """Métricas por año calendario dentro del periodo."""
    eq_d = M.daily_equity(result.equity)
    tr = result.trades
    rows = []
    for year in sorted(set(eq_d.index.year[1:])):
        prev = eq_d[eq_d.index.year < year]
        seg = pd.concat([prev.iloc[-1:], eq_d[eq_d.index.year == year]])  # incluye el cierre del año previo
        r = seg.pct_change().dropna()
        rows.append({"year": int(year), "total_return": M.total_return(seg), "sharpe": M.sharpe_ratio(r),
                     "max_drawdown": M.max_drawdown(seg)}
                    | _trade_group_stats(tr[tr["entry_time"].dt.year == year]))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- re-ejecuciones
def cost_stress(bars, params: StrategyParams, cfg: BacktestConfig, start, end, factor: float = 2.0) -> dict:
    """Comisiones y deslizamiento x factor; el funding PAGADO también x factor (el cobrado no cambia)."""
    res = run_backtest(bars, params, replace(cfg, costs=cfg.costs.scaled(factor)), start, end)
    return {"factor": factor, "result": res} | M.trade_metrics(res.trades) | {
        "total_return": M.total_return(res.equity["equity"]), "sharpe": M.sharpe_ratio(M.daily_returns(res.equity))}


def summarize_run(res) -> dict:
    tm = M.trade_metrics(res.trades)
    return {"n_trades": tm["n_trades"], "expectancy_usdt": tm.get("expectancy_usdt"),
            "expectancy_r": tm.get("expectancy_r"), "profit_factor": tm.get("profit_factor"),
            "total_return": M.total_return(res.equity["equity"]),
            "sharpe": M.sharpe_ratio(M.daily_returns(res.equity))}


def sensitivity_params(base: StrategyParams, factors) -> list[tuple[float, float, StrategyParams]]:
    return [(fn, fk, StrategyParams(int(round(base.channel_n * fn)), round(base.atr_mult * fk, 4)))
            for fn in factors for fk in factors]


def parameter_sensitivity(bars, base: StrategyParams, cfg, start, end, factors, on_run=None) -> pd.DataFrame:
    rows = []
    for fn, fk, p in sensitivity_params(base, factors):
        res = run_backtest(bars, p, cfg, start, end)
        if on_run:
            on_run(p)
        rows.append({"f_n": fn, "f_k": fk, "channel_n": p.channel_n, "atr_mult": p.atr_mult} | summarize_run(res))
    return pd.DataFrame(rows)


def walk_forward_windows(first_test_start: str, data_end, earliest_train_start: str, train_months: int,
                         test_months: int) -> list[dict]:
    """Ventanas rodantes; la última puede ser parcial (>= 1 mes). El entrenamiento no empieza antes de
    ``earliest_train_start`` (necesario por el calentamiento de indicadores)."""
    out, ts = [], pd.Timestamp(first_test_start)
    end_all = pd.Timestamp(data_end).tz_localize(None)
    while ts + pd.DateOffset(months=1) <= end_all:
        te = min(ts + pd.DateOffset(months=test_months), end_all)
        trs = max(ts - pd.DateOffset(months=train_months), pd.Timestamp(earliest_train_start))
        out.append({"train_start": trs, "train_end": ts, "test_start": ts, "test_end": te})
        ts = te
    return out


def select_best(results: dict[StrategyParams, dict], metric: str = "sharpe") -> StrategyParams:
    """Mayor métrica; empate o NaN -> primer elemento en el orden de la rejilla."""
    best, best_v = None, -np.inf
    for p, m in results.items():
        v = m.get(metric)
        if v is not None and np.isfinite(v) and v > best_v:
            best, best_v = p, v
    return best if best is not None else next(iter(results))


def walk_forward(bars, grid: list[StrategyParams], cfg, windows: list[dict], metric: str = "sharpe",
                 on_run=None) -> pd.DataFrame:
    rows = []
    for w in windows:
        train = {}
        for p in grid:
            train[p] = summarize_run(run_backtest(bars, p, cfg, w["train_start"], w["train_end"]))
            if on_run:
                on_run(p)
        sel = select_best(train, metric)
        test = summarize_run(run_backtest(bars, sel, cfg, w["test_start"], w["test_end"]))
        rows.append({k: str(v.date()) for k, v in w.items()} | {"selected": sel.key,
                    "train_sharpe": train[sel]["sharpe"]} | {f"test_{k}": v for k, v in test.items()})
    return pd.DataFrame(rows)
