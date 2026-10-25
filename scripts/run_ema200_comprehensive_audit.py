"""Auditoría Exhaustiva de la Estrategia NQ 5m EMA 200 (Solo Largos) y Versión Simétrica (Largos + Cortos).
Cubre:
1. Pruebas históricas profundas (2010-06 a 2021-10) y recientes (2024-10 a 2026-10) en NQ 5m y ES 5m.
2. Test de permutación Monte Carlo (10,000 iteraciones) dentro de RTH para largos, cortos y combinados.
3. Intervalos de confianza por Bootstrap de Bloques (10 días).
4. PnL por año y régimen de mercado (bull vs bear).
5. Deflated Sharpe Ratio (DSR) con espacio M real acumulado.
6. Distribución de las 36 combinaciones de entrenamiento en test.
7. Grid de 27 vecinos paramétricos con permutación en cada uno.
8. Simulación de Prop Firm con MNQ (micro contratos) y sensibilidad de costos.
"""
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple, Optional
import itertools
import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.strategies.intraday_ema200_strategy import (
    IntradayEma200Params,
    run_ema200_backtest,
)
from src.backtest.engine_sma_confluence import AssetCosts
from src.analysis.daily_equity_audit import compute_deflated_sharpe_ratio

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
AUDIT_DIR = REPORTS_DIR / "auditoria_intradia"
TABLES_DIR = AUDIT_DIR / "tables"
TABLES_DIR.mkdir(parents=True, exist_ok=True)

# Parámetros temporales inmutables
DATE_START_HIST = pd.Timestamp("2010-06-07 13:30:00", tz="UTC")
DATE_SPLIT_TRAIN_START = pd.Timestamp("2021-10-20 00:00:00", tz="UTC")
DATE_SPLIT_TRAIN_END = pd.Timestamp("2024-10-19 23:59:59", tz="UTC")
DATE_TEST_END = pd.Timestamp("2026-10-19 23:59:59", tz="UTC")

INITIAL_CAPITAL = 50000.0


def get_costs_map(slippage_ticks: float = 0.5) -> Dict[str, AssetCosts]:
    return {
        "ES": AssetCosts(
            asset_type="futures",
            multiplier=50.0,
            tick_size=0.25,
            commission_per_side=2.0,
            slippage_per_side=slippage_ticks,
            annualization_factor=252.0,
        ),
        "NQ": AssetCosts(
            asset_type="futures",
            multiplier=20.0,
            tick_size=0.25,
            commission_per_side=2.0,
            slippage_per_side=slippage_ticks,
            annualization_factor=252.0,
        ),
    }


def filter_trades_by_range(
    trades: List[Dict[str, Any]],
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
    direction: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Filtra trades por rango temporal y dirección opcional (LONG o SHORT)."""
    filtered = []
    for t in trades:
        e_dt = pd.to_datetime(t["entry_date"], utc=True)
        if start_ts <= e_dt <= end_ts:
            if direction is None or t.get("direction") == direction:
                filtered.append(t)
    return filtered


def compute_metrics_from_trades(
    trades: List[Dict[str, Any]],
    initial_capital: float = 50000.0,
    start_ts: Optional[pd.Timestamp] = None,
    end_ts: Optional[pd.Timestamp] = None,
) -> Dict[str, Any]:
    """Calcula el conjunto estricto de métricas cuantitativas sobre capital fijo."""
    n_trades = len(trades)
    if n_trades == 0:
        return {
            "n_trades": 0,
            "net_pnl_usd": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe_daily": 0.0,
            "max_drawdown_usd": 0.0,
            "max_drawdown_pct": 0.0,
            "simple_annual_return": 0.0,
            "worst_day_usd": 0.0,
            "daily_series": pd.Series(dtype=float),
        }

    pnls = np.array([t["net_pnl_usd"] for t in trades])
    pos_sum = float(np.sum(pnls[pnls > 0]))
    neg_sum = float(np.abs(np.sum(pnls[pnls < 0])))
    pf = (pos_sum / neg_sum) if neg_sum > 0 else (999.0 if pos_sum > 0 else 0.0)

    daily_pnl: Dict[str, float] = {}
    for t in trades:
        d_str = str(pd.to_datetime(t["exit_date"], utc=True).date())
        daily_pnl[d_str] = daily_pnl.get(d_str, 0.0) + t["net_pnl_usd"]

    daily_s = pd.Series(daily_pnl).sort_index()
    daily_rets = daily_s / initial_capital
    mean_d = float(daily_rets.mean())
    std_d = float(daily_rets.std(ddof=1)) if len(daily_rets) > 1 else 0.0
    sharpe_daily = (mean_d / std_d * np.sqrt(252.0)) if std_d > 1e-9 else 0.0

    cum_pnl = daily_s.cumsum()
    equity = initial_capital + cum_pnl
    peaks = np.maximum.accumulate(equity)
    dd_usd = peaks - equity
    max_dd_usd = float(dd_usd.max()) if len(dd_usd) > 0 else 0.0
    max_dd_pct = (max_dd_usd / initial_capital) * 100.0

    worst_day_usd = float(daily_s.min()) if len(daily_s) > 0 else 0.0
    total_net_pnl = float(np.sum(pnls))

    if start_ts is not None and end_ts is not None:
        years = max((end_ts - start_ts).days / 365.25, 0.1)
    else:
        years = max(len(daily_s) / 252.0, 0.1)
    simple_annual_ret = (total_net_pnl / initial_capital) / years * 100.0

    return {
        "n_trades": n_trades,
        "net_pnl_usd": total_net_pnl,
        "win_rate": float(np.mean(pnls > 0)) * 100.0,
        "profit_factor": pf,
        "sharpe_daily": sharpe_daily,
        "max_drawdown_usd": max_dd_usd,
        "max_drawdown_pct": max_dd_pct,
        "simple_annual_return": simple_annual_ret,
        "worst_day_usd": worst_day_usd,
        "daily_series": daily_s,
    }


def run_rth_permutation_test(
    trades: List[Dict[str, Any]],
    df_bars: pd.DataFrame,
    costs: AssetCosts,
    direction: str = "LONG",
    n_iterations: int = 10000,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """Test de permutación Monte Carlo dentro del horario RTH estricto (10:00 a 15:15 ET)."""
    if not trades or len(df_bars) < 200:
        return {"p_value": 1.0, "real_pnl": 0.0, "mean_rand": 0.0, "z_score": 0.0}

    real_pnl = float(np.sum([t["net_pnl_usd"] for t in trades]))
    n_trades = len(trades)
    durations = np.array([t.get("bars_held", 6) for t in trades])
    avg_duration = int(max(np.median(durations), 1))

    # Identificar índices válidos dentro del horario RTH (10:00 - 15:15 ET)
    ts = pd.to_datetime(df_bars["ts_event"], utc=True).dt.tz_convert("America/New_York")
    time_str = ts.dt.strftime("%H:%M").values
    valid_indices = np.where((time_str >= "10:00") & (time_str <= "15:15"))[0]
    # Filtrar que quede espacio para la salida
    valid_indices = valid_indices[valid_indices < len(df_bars) - avg_duration - 2]

    if len(valid_indices) < n_trades:
        return {"p_value": 1.0, "real_pnl": real_pnl, "mean_rand": 0.0, "z_score": 0.0}

    open_arr = df_bars["open"].values
    close_arr = df_bars["close"].values
    fixed_cost_rt = 2.0 * costs.commission_per_side + 2.0 * costs.slippage_per_side * costs.tick_size * costs.multiplier

    np.random.seed(random_seed)
    random_pnls = np.zeros(n_iterations)

    for i in range(n_iterations):
        rand_entries = np.random.choice(valid_indices, size=n_trades, replace=False)
        rand_exits = np.minimum(rand_entries + avg_duration, len(df_bars) - 1)

        p_in = open_arr[rand_entries + 1]  # Entrada causal en t+1
        p_out = close_arr[rand_exits]

        if direction == "SHORT":
            gross = (p_in - p_out) * costs.multiplier
        elif direction == "COMBINED":
            # 50% long y 50% short aleatorio
            dir_mask = np.random.choice([1.0, -1.0], size=n_trades)
            gross = dir_mask * (p_out - p_in) * costs.multiplier
        else:
            gross = (p_out - p_in) * costs.multiplier

        net = gross - fixed_cost_rt
        random_pnls[i] = np.sum(net)

    p_value = float(np.mean(random_pnls >= real_pnl))
    mean_rand = float(np.mean(random_pnls))
    std_rand = float(np.std(random_pnls))
    z_score = float((real_pnl - mean_rand) / std_rand) if std_rand > 0 else 0.0

    return {
        "real_pnl": real_pnl,
        "p_value": p_value,
        "mean_rand": mean_rand,
        "std_rand": std_rand,
        "z_score": z_score,
    }


def run_block_bootstrap(
    daily_s: pd.Series,
    initial_capital: float = 50000.0,
    block_size: int = 10,
    n_resamples: int = 2000,
    random_seed: int = 42,
) -> Dict[str, Tuple[float, float]]:
    """Calcula intervalo de confianza del 95% para Sharpe y PnL mediante Bootstrap de Bloques."""
    if len(daily_s) < block_size * 2:
        return {
            "sharpe_ci95": (0.0, 0.0),
            "pnl_ci95": (0.0, 0.0),
        }

    vals = daily_s.values
    n = len(vals)
    n_blocks = int(np.ceil(n / block_size))

    # Construir todos los bloques continuos posibles
    all_blocks = [vals[i : i + block_size] for i in range(n - block_size + 1)]
    m = len(all_blocks)

    np.random.seed(random_seed)
    boot_sharpes = np.zeros(n_resamples)
    boot_pnls = np.zeros(n_resamples)

    for r in range(n_resamples):
        rand_idx = np.random.randint(0, m, size=n_blocks)
        sampled = np.concatenate([all_blocks[idx] for idx in rand_idx])[:n]

        sampled_rets = sampled / initial_capital
        m_r = np.mean(sampled_rets)
        s_r = np.std(sampled_rets, ddof=1)
        sh = (m_r / s_r * np.sqrt(252.0)) if s_r > 1e-9 else 0.0

        boot_sharpes[r] = sh
        boot_pnls[r] = np.sum(sampled)

    sh_low, sh_high = np.percentile(boot_sharpes, [2.5, 97.5])
    pnl_low, pnl_high = np.percentile(boot_pnls, [2.5, 97.5])

    return {
        "sharpe_ci95": (float(sh_low), float(sh_high)),
        "pnl_ci95": (float(pnl_low), float(pnl_high)),
    }


def analyze_annual_and_regime_pnl(
    trades: List[Dict[str, Any]],
    initial_capital: float = 50000.0,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Genera tabla de PnL por año calendario y desglosa por régimen de mercado (bull vs bear)."""
    t_df = pd.DataFrame(trades)
    if len(t_df) == 0:
        return pd.DataFrame(), pd.DataFrame()

    t_df["exit_dt"] = pd.to_datetime(t_df["exit_date"], utc=True)
    t_df["year"] = t_df["exit_dt"].dt.year

    # PnL por año
    annual_records = []
    years = sorted(t_df["year"].unique())
    for yr in years:
        sub = t_df[t_df["year"] == yr]
        pnls = sub["net_pnl_usd"].values
        pos = pnls[pnls > 0]
        neg = np.abs(pnls[pnls < 0])
        pf = (np.sum(pos) / np.sum(neg)) if np.sum(neg) > 0 else 999.0

        annual_records.append({
            "year": yr,
            "n_trades": len(sub),
            "pnl_usd": float(np.sum(pnls)),
            "win_rate": float(np.mean(pnls > 0) * 100.0),
            "profit_factor": float(pf),
            "return_pct": float(np.sum(pnls) / initial_capital * 100.0),
        })

    df_annual = pd.DataFrame(annual_records)

    # Clasificación macro histórica de NQ (Nasdaq):
    # Años Bear/Crisis: 2011, 2015, 2018, 2022
    # Años Bull: 2010, 2012, 2013, 2014, 2016, 2017, 2019, 2020, 2021, 2023, 2024, 2025, 2026
    bear_years = {2011, 2015, 2018, 2022}
    t_df["regime"] = t_df["year"].apply(lambda y: "BEAR_SIDEWAYS" if y in bear_years else "BULL")

    regime_records = []
    for reg in ["BULL", "BEAR_SIDEWAYS"]:
        sub = t_df[t_df["regime"] == reg]
        if len(sub) == 0:
            continue
        pnls = sub["net_pnl_usd"].values
        regime_records.append({
            "regime": reg,
            "n_trades": len(sub),
            "pnl_usd": float(np.sum(pnls)),
            "win_rate": float(np.mean(pnls > 0) * 100.0),
            "profit_factor": float(np.sum(pnls[pnls > 0]) / np.abs(np.sum(pnls[pnls < 0]))) if np.sum(pnls < 0) != 0 else 0.0,
        })

    df_regime = pd.DataFrame(regime_records)
    return df_annual, df_regime


def run_comprehensive_audit():
    print("=" * 80)
    print("INICIANDO AUDITORÍA COMPLETA: NQ 5M EMA 200 (SOLO LARGOS Y SIMÉTRICA)")
    print("=" * 80)

    costs_map = get_costs_map(slippage_ticks=0.5)

    # Cargar datos completos de NQ 5m y ES 5m
    print("Cargando datos de 5 minutos...")
    df_nq5 = pd.read_parquet(PROCESSED_DIR / "NQ_5m.parquet")
    df_nq5["ts_event"] = pd.to_datetime(df_nq5["ts_event"], utc=True)
    df_nq5 = df_nq5.sort_values("ts_event").reset_index(drop=True)

    df_es5 = pd.read_parquet(PROCESSED_DIR / "ES_5m.parquet")
    df_es5["ts_event"] = pd.to_datetime(df_es5["ts_event"], utc=True)
    df_es5 = df_es5.sort_values("ts_event").reset_index(drop=True)

    # -------------------------------------------------------------------------
    # 1. PARTE 1: NQ 5m EMA 200 SOLO LARGOS (Y ES 5m DE CONTRASTE)
    # -------------------------------------------------------------------------
    print("\n[1/6] Ejecutando simulación Solo Largos (NQ 5m y ES 5m)...")
    params_long = IntradayEma200Params(
        trend_ema_period=200,
        atr_k=2.5,
        tp_m=3.0,
        trigger_type="price_cross",
        moc_close_time="15:50",
        use_volatility_filter=True,
        allow_short=False,
    )

    res_nq_all = run_ema200_backtest(df_nq5, params_long, costs_map["NQ"], INITIAL_CAPITAL)
    res_es_all = run_ema200_backtest(df_es5, params_long, costs_map["ES"], INITIAL_CAPITAL)

    # Partición Histórica (2010-06 a 2021-10) y Test Reciente (2024-10 a 2026-10)
    tr_nq_hist = filter_trades_by_range(res_nq_all["trades"], DATE_START_HIST, DATE_SPLIT_TRAIN_START)
    tr_nq_test = filter_trades_by_range(res_nq_all["trades"], DATE_SPLIT_TRAIN_END, DATE_TEST_END)
    tr_es_hist = filter_trades_by_range(res_es_all["trades"], DATE_START_HIST, DATE_SPLIT_TRAIN_START)
    tr_es_test = filter_trades_by_range(res_es_all["trades"], DATE_SPLIT_TRAIN_END, DATE_TEST_END)

    m_nq_hist = compute_metrics_from_trades(tr_nq_hist, INITIAL_CAPITAL, DATE_START_HIST, DATE_SPLIT_TRAIN_START)
    m_nq_test = compute_metrics_from_trades(tr_nq_test, INITIAL_CAPITAL, DATE_SPLIT_TRAIN_END, DATE_TEST_END)
    m_es_hist = compute_metrics_from_trades(tr_es_hist, INITIAL_CAPITAL, DATE_START_HIST, DATE_SPLIT_TRAIN_START)
    m_es_test = compute_metrics_from_trades(tr_es_test, INITIAL_CAPITAL, DATE_SPLIT_TRAIN_END, DATE_TEST_END)

    # Permutación Monte Carlo 10,000 iteraciones
    print("  Corriendo permutación Monte Carlo 10k iteraciones para NQ 5m (Historial y Test)...")
    df_nq_hist = df_nq5[df_nq5["ts_event"] < DATE_SPLIT_TRAIN_START].copy().reset_index(drop=True)
    df_nq_test = df_nq5[df_nq5["ts_event"] >= DATE_SPLIT_TRAIN_END].copy().reset_index(drop=True)

    perm_nq_hist = run_rth_permutation_test(tr_nq_hist, df_nq_hist, costs_map["NQ"], direction="LONG")
    perm_nq_test = run_rth_permutation_test(tr_nq_test, df_nq_test, costs_map["NQ"], direction="LONG")

    # Bootstrap de bloques de 10 días
    print("  Calculando intervalos de confianza por Bootstrap de bloques...")
    boot_nq_hist = run_block_bootstrap(m_nq_hist["daily_series"], INITIAL_CAPITAL)
    boot_nq_test = run_block_bootstrap(m_nq_test["daily_series"], INITIAL_CAPITAL)

    # DSR con M acumulado
    # M_previo = 380 + 144 (fase anterior) + 27 (vecinos) + 36 (simétrica) = 587
    M_TOTAL = 587
    ret_s_hist = m_nq_hist["daily_series"] / INITIAL_CAPITAL
    dsr_nq_hist = compute_deflated_sharpe_ratio(
        m_nq_hist["sharpe_daily"],
        num_trials=M_TOTAL,
        num_obs=len(ret_s_hist),
        skewness=float(skew(ret_s_hist)) if len(ret_s_hist) > 2 else 0.0,
        kurtosis=float(kurtosis(ret_s_hist, fisher=False)) if len(ret_s_hist) > 3 else 3.0,
    )
    ret_s_test = m_nq_test["daily_series"] / INITIAL_CAPITAL
    dsr_nq_test = compute_deflated_sharpe_ratio(
        m_nq_test["sharpe_daily"],
        num_trials=M_TOTAL,
        num_obs=len(ret_s_test),
        skewness=float(skew(ret_s_test)) if len(ret_s_test) > 2 else 0.0,
        kurtosis=float(kurtosis(ret_s_test, fisher=False)) if len(ret_s_test) > 3 else 3.0,
    )

    # PnL anual de NQ 5m Solo Largos
    df_annual_nq_long, df_regime_nq_long = analyze_annual_and_regime_pnl(res_nq_all["trades"], INITIAL_CAPITAL)
    df_annual_nq_long.to_csv(TABLES_DIR / "nq5m_long_annual_pnl.csv", index=False)
    df_regime_nq_long.to_csv(TABLES_DIR / "nq5m_long_regime_pnl.csv", index=False)

    print(f"\n  ---> NQ 5m Solo Largos Histórico (2010-2021): PnL ${m_nq_hist['net_pnl_usd']:,.2f} | Sharpe {m_nq_hist['sharpe_daily']:.2f} | p-val {perm_nq_hist['p_value']:.4f} | DSR {dsr_nq_hist:.2%}")
    print(f"  ---> NQ 5m Solo Largos Test (2024-2026): PnL ${m_nq_test['net_pnl_usd']:,.2f} | Sharpe {m_nq_test['sharpe_daily']:.2f} | p-val {perm_nq_test['p_value']:.4f} | DSR {dsr_nq_test:.2%}")
    print(f"  ---> ES 5m Contraste Histórico (2010-2021): PnL ${m_es_hist['net_pnl_usd']:,.2f} | Sharpe {m_es_hist['sharpe_daily']:.2f}")

    # -------------------------------------------------------------------------
    # 2. PARTE 2: DISTRIBUCIÓN DE LAS 36 COMBINACIONES EN EL TEST (2024-2026)
    # -------------------------------------------------------------------------
    print("\n[2/6] Evaluando la distribución de las 36 combinaciones en el Test...")
    train_36_file = TABLES_DIR / "optimizacion_ema200_train_3y.csv"
    train_36_df = pd.read_csv(train_36_file)
    train_36_nq5 = train_36_df[train_36_df["timeframe"] == "5m"][train_36_df["symbol"] == "NQ"].copy()

    test_36_results = []
    for _, row in train_36_nq5.iterrows():
        p_eval = IntradayEma200Params(
            trend_ema_period=200,
            atr_k=float(row["atr_k"]),
            tp_m=float(row["tp_m"]),
            trigger_type=str(row["trigger_type"]),
            moc_close_time="15:50",
            use_volatility_filter=True,
            allow_short=False,
        )
        res_eval = run_ema200_backtest(df_nq_test, p_eval, costs_map["NQ"], INITIAL_CAPITAL)
        tr_eval = filter_trades_by_range(res_eval["trades"], DATE_SPLIT_TRAIN_END, DATE_TEST_END)
        m_eval = compute_metrics_from_trades(tr_eval, INITIAL_CAPITAL, DATE_SPLIT_TRAIN_END, DATE_TEST_END)

        test_36_results.append({
            "trigger_type": row["trigger_type"],
            "atr_k": row["atr_k"],
            "tp_m": row["tp_m"],
            "train_pnl": row["net_pnl_usd"],
            "train_sharpe": row["sharpe_daily"],
            "test_pnl": m_eval["net_pnl_usd"],
            "test_sharpe": m_eval["sharpe_daily"],
            "test_win_rate": m_eval["win_rate"],
            "test_pf": m_eval["profit_factor"],
            "test_dd_pct": m_eval["max_drawdown_pct"],
            "is_positive": m_eval["net_pnl_usd"] > 0,
        })

    df_test_36 = pd.DataFrame(test_36_results)
    df_test_36.to_csv(TABLES_DIR / "distribucion_36_combinaciones_test.csv", index=False)
    n_pos = int(df_test_36["is_positive"].sum())
    pct_pos = (n_pos / len(df_test_36)) * 100.0
    print(f"  Combinaciones positivas en el Test: {n_pos} de {len(df_test_36)} ({pct_pos:.1f}%)")
    print(f"  Media PnL Test: ${df_test_36['test_pnl'].mean():,.2f} | Mediana PnL Test: ${df_test_36['test_pnl'].median():,.2f}")

    # -------------------------------------------------------------------------
    # 3. PARTE 3: GRID DE 27 VECINOS CON TEST DE PERMUTACIÓN
    # -------------------------------------------------------------------------
    print("\n[3/6] Evaluando el grid de 27 vecinos paramétricos con permutación...")
    ema_vals = [150, 200, 250]
    k_vals = [2.0, 2.5, 3.0]
    m_vals = [2.0, 3.0, 4.0]

    neighbors_results = []
    for ema_p, k, m in itertools.product(ema_vals, k_vals, m_vals):
        p_neigh = IntradayEma200Params(
            trend_ema_period=ema_p,
            atr_k=k,
            tp_m=m,
            trigger_type="price_cross",
            moc_close_time="15:50",
            use_volatility_filter=True,
            allow_short=False,
        )
        res_n = run_ema200_backtest(df_nq_test, p_neigh, costs_map["NQ"], INITIAL_CAPITAL)
        tr_n = filter_trades_by_range(res_n["trades"], DATE_SPLIT_TRAIN_END, DATE_TEST_END)
        m_n = compute_metrics_from_trades(tr_n, INITIAL_CAPITAL, DATE_SPLIT_TRAIN_END, DATE_TEST_END)
        perm_n = run_rth_permutation_test(tr_n, df_nq_test, costs_map["NQ"], n_iterations=1000)

        neighbors_results.append({
            "ema_period": ema_p,
            "atr_k": k,
            "tp_m": m,
            "n_trades": m_n["n_trades"],
            "pnl_usd": m_n["net_pnl_usd"],
            "sharpe": m_n["sharpe_daily"],
            "win_rate": m_n["win_rate"],
            "profit_factor": m_n["profit_factor"],
            "max_dd_pct": m_n["max_drawdown_pct"],
            "perm_p_val": perm_n["p_value"],
            "is_significant": perm_n["p_value"] < 0.05,
        })

    df_neighbors = pd.DataFrame(neighbors_results)
    df_neighbors.to_csv(TABLES_DIR / "vecinos_nq5m_test.csv", index=False)
    n_neigh_pos = int((df_neighbors["pnl_usd"] > 0).sum())
    n_neigh_sig = int(df_neighbors["is_significant"].sum())
    print(f"  Vecinos positivos en Test: {n_neigh_pos} de 27 ({n_neigh_pos/27*100:.1f}%) | Significativos (p<0.05): {n_neigh_sig} de 27")

    # -------------------------------------------------------------------------
    # 4. PARTE 4: HIPÓTESIS ADICIONAL - ESTRATEGIA SIMÉTRICA (LARGOS + CORTOS)
    # -------------------------------------------------------------------------
    print("\n[4/6] Evaluando Hipótesis Simétrica (Largos + Cortos)...")
    params_sym = IntradayEma200Params(
        trend_ema_period=200,
        atr_k=2.5,
        tp_m=3.0,
        trigger_type="price_cross",
        moc_close_time="15:50",
        use_volatility_filter=True,
        allow_short=True,
    )

    res_sym_all = run_ema200_backtest(df_nq5, params_sym, costs_map["NQ"], INITIAL_CAPITAL)

    # Desglose por lado en Historial (2010-2021) y en Test (2024-2026)
    tr_sym_hist = filter_trades_by_range(res_sym_all["trades"], DATE_START_HIST, DATE_SPLIT_TRAIN_START)
    tr_sym_test = filter_trades_by_range(res_sym_all["trades"], DATE_SPLIT_TRAIN_END, DATE_TEST_END)

    # Lados separados en Test
    tr_sym_test_long = [t for t in tr_sym_test if t["direction"] == "LONG"]
    tr_sym_test_short = [t for t in tr_sym_test if t["direction"] == "SHORT"]

    m_sym_hist = compute_metrics_from_trades(tr_sym_hist, INITIAL_CAPITAL, DATE_START_HIST, DATE_SPLIT_TRAIN_START)
    m_sym_test = compute_metrics_from_trades(tr_sym_test, INITIAL_CAPITAL, DATE_SPLIT_TRAIN_END, DATE_TEST_END)
    m_sym_test_long = compute_metrics_from_trades(tr_sym_test_long, INITIAL_CAPITAL, DATE_SPLIT_TRAIN_END, DATE_TEST_END)
    m_sym_test_short = compute_metrics_from_trades(tr_sym_test_short, INITIAL_CAPITAL, DATE_SPLIT_TRAIN_END, DATE_TEST_END)

    # Permutaciones 10k para Lado Largo, Lado Corto y Combinado en Test
    perm_sym_long = run_rth_permutation_test(tr_sym_test_long, df_nq_test, costs_map["NQ"], direction="LONG")
    perm_sym_short = run_rth_permutation_test(tr_sym_test_short, df_nq_test, costs_map["NQ"], direction="SHORT")
    perm_sym_comb = run_rth_permutation_test(tr_sym_test, df_nq_test, costs_map["NQ"], direction="COMBINED")

    # DSR Simétrica con M=587
    ret_sym_test = m_sym_test["daily_series"] / INITIAL_CAPITAL
    dsr_sym_test = compute_deflated_sharpe_ratio(
        m_sym_test["sharpe_daily"],
        num_trials=M_TOTAL,
        num_obs=len(ret_sym_test),
        skewness=float(skew(ret_sym_test)) if len(ret_sym_test) > 2 else 0.0,
        kurtosis=float(kurtosis(ret_sym_test, fisher=False)) if len(ret_sym_test) > 3 else 3.0,
    )

    # PnL anual y régimen para versión Simétrica
    df_annual_sym, df_regime_sym = analyze_annual_and_regime_pnl(res_sym_all["trades"], INITIAL_CAPITAL)
    df_annual_sym.to_csv(TABLES_DIR / "nq5m_simetrica_annual_pnl.csv", index=False)
    df_regime_sym.to_csv(TABLES_DIR / "nq5m_simetrica_regime_pnl.csv", index=False)

    print(f"  ---> Simétrica Test Combinado: PnL ${m_sym_test['net_pnl_usd']:,.2f} | Sharpe {m_sym_test['sharpe_daily']:.2f} | p-val {perm_sym_comb['p_value']:.4f}")
    print(f"  ---> Simétrica Test Lado Largo: PnL ${m_sym_test_long['net_pnl_usd']:,.2f} | Sharpe {m_sym_test_long['sharpe_daily']:.2f} | p-val {perm_sym_long['p_value']:.4f}")
    print(f"  ---> Simétrica Test Lado Corto: PnL ${m_sym_test_short['net_pnl_usd']:,.2f} | Sharpe {m_sym_test_short['sharpe_daily']:.2f} | p-val {perm_sym_short['p_value']:.4f}")

    # -------------------------------------------------------------------------
    # 5. PARTE 5: PROP FIRM CON MNQ (MICRO CONTRATOS)
    # -------------------------------------------------------------------------
    print("\n[5/6] Analizando viabilidad de Prop Firm con Micro E-mini (MNQ)...")
    # En MNQ: multiplicador = $2/punto (1/10 de NQ).
    # Comisiones reales de MNQ: ~$0.62 a $1.24 por lado.
    # Slippage: 0.5 ticks de MNQ = 0.5 * 0.25 * $2 = $0.25 por lado.
    # Simulamos el escalado de 1 micro a N micros.
    tr_test_mnq_base = []
    comm_micro_per_side = 0.85  # Promedio institucional realista
    fixed_cost_micro_rt = 2.0 * comm_micro_per_side + 2.0 * (0.5 * 0.25 * 2.0)  # = $1.70 + $0.50 = $2.20 RT

    for t in tr_nq_test:
        gross_mnq = (t["exit_price"] - t["entry_price"]) * 2.0
        net_mnq = gross_mnq - fixed_cost_micro_rt
        tr_test_mnq_base.append({
            "exit_date": t["exit_date"],
            "net_pnl": net_mnq,
        })

    daily_mnq: Dict[str, float] = {}
    for t in tr_test_mnq_base:
        d = str(pd.to_datetime(t["exit_date"], utc=True).date())
        daily_mnq[d] = daily_mnq.get(d, 0.0) + t["net_pnl"]

    s_mnq = pd.Series(daily_mnq).sort_index()
    worst_day_1_mnq = float(s_mnq.min())
    cum_mnq = s_mnq.cumsum()
    peaks_mnq = np.maximum.accumulate(cum_mnq)
    max_dd_1_mnq = float((peaks_mnq - cum_mnq).max())
    pnl_1_mnq = float(cum_mnq.iloc[-1])

    # Capacidad de contratos para caber en $2,000 y $3,000 USD de Max Drawdown
    max_contracts_2k = int(np.floor(2000.0 / max_dd_1_mnq)) if max_dd_1_mnq > 0 else 1
    max_contracts_3k = int(np.floor(3000.0 / max_dd_1_mnq)) if max_dd_1_mnq > 0 else 1

    prop_firm_data = {
        "worst_day_1_mnq": worst_day_1_mnq,
        "max_dd_1_mnq": max_dd_1_mnq,
        "pnl_1_mnq": pnl_1_mnq,
        "contracts_limit_2k": max_contracts_2k,
        "pnl_scaled_2k": pnl_1_mnq * max_contracts_2k,
        "pnl_pct_50k_account_2k": (pnl_1_mnq * max_contracts_2k / 50000.0) * 100.0,
        "worst_day_scaled_2k": worst_day_1_mnq * max_contracts_2k,
        "contracts_limit_3k": max_contracts_3k,
        "pnl_scaled_3k": pnl_1_mnq * max_contracts_3k,
        "pnl_pct_50k_account_3k": (pnl_1_mnq * max_contracts_3k / 50000.0) * 100.0,
        "worst_day_scaled_3k": worst_day_1_mnq * max_contracts_3k,
    }
    pd.DataFrame([prop_firm_data]).to_csv(TABLES_DIR / "prop_firm_mnq_analysis.csv", index=False)
    print(f"  1 Contrato MNQ: Max DD ${max_dd_1_mnq:,.2f} | Peor Día ${worst_day_1_mnq:,.2f} | PnL 2A ${pnl_1_mnq:,.2f}")
    print(f"  Para límite $2,000: Caben {max_contracts_2k} micros -> PnL ${prop_firm_data['pnl_scaled_2k']:,.2f} ({prop_firm_data['pnl_pct_50k_account_2k']:.1f}% cuenta $50k)")
    print(f"  Para límite $3,000: Caben {max_contracts_3k} micros -> PnL ${prop_firm_data['pnl_scaled_3k']:,.2f} ({prop_firm_data['pnl_pct_50k_account_3k']:.1f}% cuenta $50k)")

    # -------------------------------------------------------------------------
    # 6. PARTE 6: SENSIBILIDAD DE COSTOS DE SLIPPAGE
    # -------------------------------------------------------------------------
    print("\n[6/6] Analizando sensibilidad de costos de slippage (0.5, 1.0, 2.0 ticks)...")
    slip_results = []
    for s_ticks in [0.5, 1.0, 2.0]:
        c_slip = get_costs_map(slippage_ticks=s_ticks)["NQ"]
        r_slip = run_ema200_backtest(df_nq_test, params_long, c_slip, INITIAL_CAPITAL)
        tr_slip = filter_trades_by_range(r_slip["trades"], DATE_SPLIT_TRAIN_END, DATE_TEST_END)
        m_slip = compute_metrics_from_trades(tr_slip, INITIAL_CAPITAL, DATE_SPLIT_TRAIN_END, DATE_TEST_END)

        slip_results.append({
            "slippage_ticks_per_side": s_ticks,
            "cost_per_trade_rt": 4.0 + 2.0 * s_ticks * 0.25 * 20.0,
            "net_pnl_usd": m_slip["net_pnl_usd"],
            "sharpe_daily": m_slip["sharpe_daily"],
            "profit_factor": m_slip["profit_factor"],
            "max_dd_pct": m_slip["max_drawdown_pct"],
        })

    df_slippage = pd.DataFrame(slip_results)
    df_slippage.to_csv(TABLES_DIR / "sensibilidad_costos_slippage.csv", index=False)
    print(df_slippage.to_string(index=False))

    # Guardar resumen maestro consolidado
    master_summary = {
        "nq_hist_pnl": m_nq_hist["net_pnl_usd"],
        "nq_hist_sharpe": m_nq_hist["sharpe_daily"],
        "nq_hist_dd_pct": m_nq_hist["max_drawdown_pct"],
        "nq_hist_pval": perm_nq_hist["p_value"],
        "nq_hist_dsr": dsr_nq_hist,
        "nq_hist_sh_ci_low": boot_nq_hist["sharpe_ci95"][0],
        "nq_hist_sh_ci_high": boot_nq_hist["sharpe_ci95"][1],
        "nq_test_pnl": m_nq_test["net_pnl_usd"],
        "nq_test_sharpe": m_nq_test["sharpe_daily"],
        "nq_test_dd_pct": m_nq_test["max_drawdown_pct"],
        "nq_test_pval": perm_nq_test["p_value"],
        "nq_test_dsr": dsr_nq_test,
        "nq_test_sh_ci_low": boot_nq_test["sharpe_ci95"][0],
        "nq_test_sh_ci_high": boot_nq_test["sharpe_ci95"][1],
        "es_hist_pnl": m_es_hist["net_pnl_usd"],
        "es_hist_sharpe": m_es_hist["sharpe_daily"],
        "es_test_pnl": m_es_test["net_pnl_usd"],
        "es_test_sharpe": m_es_test["sharpe_daily"],
        "sym_test_pnl_comb": m_sym_test["net_pnl_usd"],
        "sym_test_sh_comb": m_sym_test["sharpe_daily"],
        "sym_test_pval_comb": perm_sym_comb["p_value"],
        "sym_test_dsr_comb": dsr_sym_test,
        "sym_test_pnl_long": m_sym_test_long["net_pnl_usd"],
        "sym_test_sh_long": m_sym_test_long["sharpe_daily"],
        "sym_test_pval_long": perm_sym_long["p_value"],
        "sym_test_pnl_short": m_sym_test_short["net_pnl_usd"],
        "sym_test_sh_short": m_sym_test_short["sharpe_daily"],
        "sym_test_pval_short": perm_sym_short["p_value"],
    }
    pd.DataFrame([master_summary]).to_csv(TABLES_DIR / "resumen_maestro_auditoria_completa.csv", index=False)
    print("\nAuditoría integral completada exitosamente. Todos los datos guardados en:", TABLES_DIR)


if __name__ == "__main__":
    run_comprehensive_audit()
