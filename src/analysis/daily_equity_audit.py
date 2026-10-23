"""Motor de Auditoría Cuantitativa Rigurosa sobre la Curva de Equity Diaria.
Calcula CAGR, Sharpe diario, Max DD en $ y %, Calmar, análisis de Prop Firms con Micros,
test de permutación (10,000 iteraciones), mapa de vecinos y concentración de trades.
"""
from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis

from src.analysis.robustness import compute_deflated_sharpe_ratio
from src.strategies.unified_strategy import UnifiedStrategyParams, run_unified_backtest
from src.backtest.engine_sma_confluence import AssetCosts

logger = logging.getLogger(__name__)


def build_daily_equity_curve(
    trades: List[Dict[str, Any]],
    df_bars: pd.DataFrame,
    initial_capital: float = 50000.0,
    multiplier_scale: float = 1.0,
) -> Dict[str, Any]:
    """Construye la serie continua de equity diaria sobre todos los días de negociación."""
    if not trades or len(df_bars) == 0:
        return {
            "cagr": 0.0,
            "sharpe_daily": 0.0,
            "max_dd_usd": 0.0,
            "max_dd_pct": 0.0,
            "calmar": 0.0,
            "total_net_pnl": 0.0,
            "total_return_pct": 0.0,
            "daily_df": pd.DataFrame(),
        }

    # Calendario de días únicos de mercado
    ts_series = pd.to_datetime(df_bars["ts_event"], utc=True)
    all_dates = pd.Series(ts_series.dt.date.unique()).sort_values().reset_index(drop=True)

    # Agrupar PnL de trades por fecha de salida
    tr_df = pd.DataFrame(trades)
    tr_df["exit_date_day"] = pd.to_datetime(tr_df["exit_date"], utc=True).dt.date
    daily_pnl = tr_df.groupby("exit_date_day")["net_pnl_usd"].sum() * multiplier_scale

    # Alinear al calendario completo de días
    daily_df = pd.DataFrame({"date": all_dates})
    daily_df["pnl_usd"] = daily_df["date"].map(daily_pnl).fillna(0.0)
    daily_df["cum_pnl"] = daily_df["pnl_usd"].cumsum()
    daily_df["equity"] = initial_capital + daily_df["cum_pnl"]

    # Retornos diarios
    daily_df["ret"] = daily_df["equity"].pct_change().fillna(0.0)

    # Métricas de drawdown sobre equity diaria
    daily_df["peak"] = daily_df["equity"].cummax()
    daily_df["dd_usd"] = daily_df["peak"] - daily_df["equity"]
    daily_df["dd_pct"] = (daily_df["dd_usd"] / daily_df["peak"]) * 100.0

    max_dd_usd = float(daily_df["dd_usd"].max())
    max_dd_pct = float(daily_df["dd_pct"].max())

    # Retorno total y CAGR
    total_net_pnl = float(daily_df["cum_pnl"].iloc[-1])
    total_return_pct = (total_net_pnl / initial_capital) * 100.0

    n_days = len(daily_df)
    n_years = max(n_days / 252.0, 0.1)
    final_equity = float(daily_df["equity"].iloc[-1])
    cagr = float((final_equity / initial_capital) ** (1.0 / n_years) - 1.0) if final_equity > 0 else -1.0

    # Sharpe diario estricto: mean(ret_d) / std(ret_d) * sqrt(252)
    rets = daily_df["ret"].values
    mean_ret = float(np.mean(rets))
    std_ret = float(np.std(rets, ddof=1)) if len(rets) > 1 else 0.0
    sharpe_daily = float((mean_ret / std_ret) * np.sqrt(252.0)) if std_ret > 1e-9 else 0.0

    # Calmar Ratio = CAGR / Max DD (%)
    calmar = float(cagr / (max_dd_pct / 100.0)) if max_dd_pct > 0 else 0.0

    # Estadísticos para DSR
    skew_val = float(skew(rets)) if len(rets) > 2 else 0.0
    kurt_val = float(kurtosis(rets, fisher=False)) if len(rets) > 3 else 3.0

    return {
        "initial_capital": initial_capital,
        "final_equity": final_equity,
        "total_net_pnl": total_net_pnl,
        "total_return_pct": total_return_pct,
        "cagr": cagr,
        "sharpe_daily": sharpe_daily,
        "max_dd_usd": max_dd_usd,
        "max_dd_pct": max_dd_pct,
        "calmar": calmar,
        "skewness": skew_val,
        "kurtosis": kurt_val,
        "n_trading_days": n_days,
        "daily_df": daily_df,
    }


def analyze_prop_firm_and_micros(
    trades: List[Dict[str, Any]],
    df_bars: pd.DataFrame,
    asset: str = "NQ",
) -> Dict[str, Any]:
    """Evalúa la viabilidad en Prop Firms con contratos Micro (MES/MNQ) y riesgo fijo por trade."""
    if not trades:
        return {}

    # Ratio de escala Micro vs E-mini: 1/10
    # MNQ es 1/10 de NQ, MES es 1/10 de ES
    micro_scale = 0.10

    # 1. 1 Contrato Micro con capital de $10,000 USD
    res_micro_10k = build_daily_equity_curve(trades, df_bars, initial_capital=10000.0, multiplier_scale=micro_scale)
    
    # 2. 1 Contrato Micro con capital de $50,000 USD (cuenta estándar de prop firm)
    res_micro_50k = build_daily_equity_curve(trades, df_bars, initial_capital=50000.0, multiplier_scale=micro_scale)

    # 3. 1 Contrato E-mini estándar con capital de $50,000 USD
    res_emini_50k = build_daily_equity_curve(trades, df_bars, initial_capital=50000.0, multiplier_scale=1.0)

    # Límites típicos de Prop Firms
    prop_limit_50k = 2000.0   # $2,000 Max Trailing DD en cuenta de $50k
    prop_limit_100k = 3000.0  # $3,000 Max Trailing DD en cuenta de $100k

    fits_emini_50k = res_emini_50k["max_dd_usd"] <= prop_limit_50k
    fits_micro_50k = res_micro_50k["max_dd_usd"] <= prop_limit_50k
    fits_micro_100k = res_micro_50k["max_dd_usd"] <= prop_limit_100k

    # 4. Simulación de Riesgo Fijo Dinámico (0.5% y 1.0% de la cuenta por trade)
    # R = Equity * risk_pct. Distancia SL = 3 * ATR. Multiplicador = 20 o 50.
    # Q = R / (dist * mult)
    fixed_risk_results = {}
    for r_pct in [0.005, 0.01]:
        eq = 50000.0
        peak = 50000.0
        max_dd = 0.0
        scaled_trades = []
        for t in trades:
            dist = abs(t["entry_price"] - (t["entry_price"] - t.get("stop_dist", 50.0)))
            pt_val = 20.0 if asset == "NQ" else 50.0
            risk_usd = eq * r_pct
            # Si el trade original fue perdedor por SL, perdió dist * pt_val
            # Escalamos el PnL del trade según la fracción de riesgo
            unit_risk = abs(t["net_pnl_usd"]) if t["net_pnl_usd"] < 0 else (risk_usd)
            q = max(0.05, risk_usd / unit_risk) if unit_risk > 0 else 0.1
            pnl_scaled = t["net_pnl_usd"] * q
            eq += pnl_scaled
            if eq > peak:
                peak = eq
            dd = peak - eq
            if dd > max_dd:
                max_dd = dd

        fixed_risk_results[f"risk_{int(r_pct*1000)}bp"] = {
            "final_equity": eq,
            "net_pnl": eq - 50000.0,
            "max_dd_usd": max_dd,
            "max_dd_pct": (max_dd / peak) * 100.0 if peak > 0 else 0.0,
            "fits_prop_50k": max_dd <= prop_limit_50k,
        }

    return {
        "emini_50k": res_emini_50k,
        "micro_50k": res_micro_50k,
        "micro_10k": res_micro_10k,
        "fits_emini_prop_50k": fits_emini_50k,
        "fits_micro_prop_50k": fits_micro_50k,
        "fits_micro_prop_100k": fits_micro_100k,
        "fixed_risk": fixed_risk_results,
    }


def run_permutation_test(
    trades: List[Dict[str, Any]],
    df_bars: pd.DataFrame,
    costs: AssetCosts,
    n_iterations: int = 10000,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """Test de permutación Monte Carlo (10,000 iteraciones) comparando contra señales aleatorias."""
    if not trades or len(df_bars) < 100:
        return {"p_value": 1.0, "real_pnl": 0.0, "mean_random_pnl": 0.0, "percentile": 0.0}

    real_pnl = float(np.sum([t["net_pnl_usd"] for t in trades]))
    n_trades = len(trades)
    durations = np.array([t.get("bars_held", 5) for t in trades])
    avg_duration = int(max(np.mean(durations), 1))

    # Pre-calcular precios de entrada y salida para simulaciones rápidas vectorizadas
    open_arr = df_bars["open"].values
    close_arr = df_bars["close"].values
    n_bars = len(df_bars)
    valid_entry_indices = np.arange(50, n_bars - avg_duration - 2)

    is_futures = (costs.asset_type == "futures")
    fixed_cost_rt = (2.0 * costs.commission_per_side + 2.0 * costs.slippage_per_side * costs.tick_size * costs.multiplier) if is_futures else 0.0

    np.random.seed(random_seed)
    random_pnls = np.zeros(n_iterations)

    for i in range(n_iterations):
        # Seleccionar n_trades entradas aleatorias sin reemplazo
        rand_entries = np.random.choice(valid_entry_indices, size=n_trades, replace=False)
        rand_exits = np.minimum(rand_entries + avg_duration, n_bars - 1)
        
        # Calcular PnL de compras Long aleatorias
        p_in = open_arr[rand_entries + 1] # Ejecución causal en t+1
        p_out = close_arr[rand_exits]
        
        gross_pnl = (p_out - p_in) * costs.multiplier
        net_pnls = gross_pnl - fixed_cost_rt
        random_pnls[i] = np.sum(net_pnls)

    p_value = float(np.mean(random_pnls >= real_pnl))
    mean_rand = float(np.mean(random_pnls))
    std_rand = float(np.std(random_pnls))
    percentile = float(np.mean(random_pnls < real_pnl) * 100.0)

    return {
        "real_pnl": real_pnl,
        "n_iterations": n_iterations,
        "mean_random_pnl": mean_rand,
        "std_random_pnl": std_rand,
        "p_value": p_value,
        "percentile": percentile,
        "z_score": float((real_pnl - mean_rand) / std_rand) if std_rand > 0 else 0.0,
    }


def run_neighborhood_sensitivity(
    df: pd.DataFrame,
    costs: AssetCosts,
) -> pd.DataFrame:
    """Evalúa la grilla de vecinos paramétricos 3x3x3 (27 configuraciones) alrededor de EMA 30/200 Stop 3 ATR."""
    fast_emas = [20, 30, 40]
    slow_emas = [150, 200, 250]
    atr_ks = [2.0, 3.0, 4.0]

    rows = []
    for f_ema in fast_emas:
        for s_ema in slow_emas:
            for k in atr_ks:
                p = UnifiedStrategyParams(
                    fast_ema=f_ema,
                    slow_ema=s_ema,
                    atr_k=k,
                    tp_m=2.0,
                    long_only=True,
                    use_candle_trigger=True,
                )
                res = run_unified_backtest(df, p, costs)
                eq_res = build_daily_equity_curve(res.get("trades", []), df, initial_capital=50000.0)

                rows.append({
                    "fast_ema": f_ema,
                    "slow_ema": s_ema,
                    "atr_k": k,
                    "is_base": (f_ema == 30 and s_ema == 200 and k == 3.0),
                    "n_trades": res["n_trades"],
                    "win_rate_pct": round(res["win_rate"] * 100.0, 2),
                    "profit_factor": round(res["profit_factor"], 2) if not np.isnan(res["profit_factor"]) else 0.0,
                    "net_pnl_usd": round(res["net_pnl_usd"], 2),
                    "sharpe_daily": round(eq_res["sharpe_daily"], 2),
                    "cagr_pct": round(eq_res["cagr"] * 100.0, 2),
                    "max_dd_usd": round(eq_res["max_dd_usd"], 2),
                    "max_dd_pct": round(eq_res["max_dd_pct"], 2),
                    "calmar": round(eq_res["calmar"], 2),
                })

    return pd.DataFrame(rows)


def run_concentration_test(
    trades: List[Dict[str, Any]],
    df_bars: pd.DataFrame,
    initial_capital: float = 50000.0,
    top_n: int = 5,
) -> Dict[str, Any]:
    """Evalúa el impacto de eliminar los top_n mejores trades (test de concentración)."""
    if not trades or len(trades) <= top_n:
        return {}

    sorted_trades = sorted(trades, key=lambda t: t["net_pnl_usd"], reverse=True)
    top_5_trades = sorted_trades[:top_n]
    remaining_trades = sorted_trades[top_n:]

    pnl_full = sum(t["net_pnl_usd"] for t in trades)
    pnl_top5 = sum(t["net_pnl_usd"] for t in top_5_trades)
    pnl_without_top5 = sum(t["net_pnl_usd"] for t in remaining_trades)

    res_full = build_daily_equity_curve(trades, df_bars, initial_capital)
    res_without = build_daily_equity_curve(remaining_trades, df_bars, initial_capital)

    return {
        "top_n": top_n,
        "pnl_full": pnl_full,
        "pnl_top5": pnl_top5,
        "pnl_without_top5": pnl_without_top5,
        "pct_pnl_in_top5": (pnl_top5 / pnl_full * 100.0) if pnl_full > 0 else 0.0,
        "sharpe_full": res_full["sharpe_daily"],
        "sharpe_without_top5": res_without["sharpe_daily"],
        "max_dd_full": res_full["max_dd_usd"],
        "max_dd_without_top5": res_without["max_dd_usd"],
        "top_trades_detail": [
            {
                "entry_date": str(t.get("entry_date", "N/A")),
                "exit_date": str(t.get("exit_date", "N/A")),
                "pnl_usd": round(t["net_pnl_usd"], 2),
                "bars_held": t.get("bars_held", 0),
            } for t in top_5_trades
        ],
    }


def compute_pnl_year_by_year(
    trades: List[Dict[str, Any]],
    df_bars: pd.DataFrame,
    initial_capital: float = 50000.0,
) -> pd.DataFrame:
    """Calcula el PnL y retorno año a año desde 2010 a 2026."""
    if not trades:
        return pd.DataFrame()

    tr_df = pd.DataFrame(trades)
    tr_df["year"] = pd.to_datetime(tr_df["exit_date"], utc=True).dt.year

    yearly_rows = []
    years = sorted(tr_df["year"].unique())

    cum_cap = initial_capital
    for y in years:
        y_trades = tr_df[tr_df["year"] == y]
        y_pnl = float(y_trades["net_pnl_usd"].sum())
        y_n = len(y_trades)
        y_wins = float((y_trades["net_pnl_usd"] > 0).mean() * 100.0)
        y_ret = (y_pnl / cum_cap) * 100.0
        cum_cap += y_pnl

        yearly_rows.append({
            "Año": y,
            "N_Trades": y_n,
            "Win_Rate_%": round(y_wins, 2),
            "Net_PnL_USD": round(y_pnl, 2),
            "Retorno_Año_%": round(y_ret, 2),
            "Equity_Fin_Año": round(cum_cap, 2),
        })

    return pd.DataFrame(yearly_rows)
