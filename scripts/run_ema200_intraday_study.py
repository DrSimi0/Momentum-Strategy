"""Estudio Cuantitativo Riguroso de la Estrategia Intradía con EMA 200.
Partición temporal estricta de 5 años:
- 3 Años In-Sample (Train/Optimización): 2021-10-20 a 2024-10-19
- 2 Años Out-of-Sample (Test Virgen): 2024-10-20 a 2026-10-19
Genera tablas de optimización, evaluación fuera de muestra y reporte final.
"""
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple
import itertools
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.strategies.intraday_ema200_strategy import (
    IntradayEma200Params,
    run_ema200_backtest,
)
from src.backtest.engine_sma_confluence import AssetCosts

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
OUTPUT_TABLES = REPORTS_DIR / "auditoria_intradia" / "tables"
OUTPUT_TABLES.mkdir(parents=True, exist_ok=True)

# Parámetros temporales inmutables
DATE_START_5Y = pd.Timestamp("2021-10-20", tz="UTC")
DATE_SPLIT_3Y = pd.Timestamp("2024-10-20", tz="UTC")
DATE_END_5Y = pd.Timestamp("2026-10-19 23:59:59", tz="UTC")

INITIAL_CAPITAL = 50000.0


def get_costs_map() -> Dict[str, AssetCosts]:
    return {
        "ES": AssetCosts(
            asset_type="futures",
            multiplier=50.0,
            tick_size=0.25,
            commission_per_side=2.0,
            slippage_per_side=0.5,
            annualization_factor=252.0,
        ),
        "NQ": AssetCosts(
            asset_type="futures",
            multiplier=20.0,
            tick_size=0.25,
            commission_per_side=2.0,
            slippage_per_side=0.5,
            annualization_factor=252.0,
        ),
    }


def prepare_dataset_splits(
    file_path: Path,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carga y particiona el dataset manteniendo suficiente warm-up para la EMA 200."""
    df_raw = pd.read_parquet(file_path)
    df_raw["ts_event"] = pd.to_datetime(df_raw["ts_event"], utc=True)
    df_raw = df_raw.sort_values("ts_event").reset_index(drop=True)

    # 1. Dataset completo de los 5 años (con 300 barras previas para calentar EMA 200)
    idx_start_5y = df_raw[df_raw["ts_event"] >= DATE_START_5Y].index[0]
    warmup_start = max(0, idx_start_5y - 300)
    df_5y = df_raw.iloc[warmup_start:].copy().reset_index(drop=True)

    # 2. Dataset Train (3 años: 2021-10-20 a 2024-10-19)
    # Incluye el warm-up inicial y termina exactamente antes de DATE_SPLIT_3Y
    df_train = df_raw[(df_raw.index >= warmup_start) & (df_raw["ts_event"] < DATE_SPLIT_3Y)].copy().reset_index(drop=True)

    # 3. Dataset Test (2 años vírgenes: 2024-10-20 a 2026-10-19)
    # Necesita 300 barras de warm-up tomadas inmediatamente antes de DATE_SPLIT_3Y
    idx_test_start = df_raw[df_raw["ts_event"] >= DATE_SPLIT_3Y].index[0]
    warmup_test_start = max(0, idx_test_start - 300)
    df_test = df_raw.iloc[warmup_test_start:].copy().reset_index(drop=True)

    return df_train, df_test, df_5y


def filter_trades_by_date(
    res: Dict[str, Any],
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    initial_capital: float = 50000.0,
) -> Dict[str, Any]:
    """Filtra los trades cuya fecha de entrada cae exactamente en el rango especificado y recalcula métricas."""
    raw_trades = res["trades"]
    valid_trades = [
        t for t in raw_trades
        if start_date <= pd.to_datetime(t["entry_date"], utc=True) <= end_date
    ]

    n_trades = len(valid_trades)
    if n_trades == 0:
        return {
            "n_trades": 0,
            "net_pnl_usd": 0.0,
            "sharpe_daily": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_usd": 0.0,
            "max_drawdown_pct": 0.0,
            "simple_annual_return": 0.0,
            "trades": [],
        }

    pnls = np.array([t["net_pnl_usd"] for t in valid_trades])
    pos_sum = float(np.sum(pnls[pnls > 0]))
    neg_sum = float(np.abs(np.sum(pnls[pnls < 0])))
    pf = (pos_sum / neg_sum) if neg_sum > 0 else (999.0 if pos_sum > 0 else 0.0)

    # Reconstrucción de la curva de equity diaria exacta para el período
    daily_pnl: Dict[str, float] = {}
    for t in valid_trades:
        d_str = str(pd.to_datetime(t["exit_date"], utc=True).date())
        daily_pnl[d_str] = daily_pnl.get(d_str, 0.0) + t["net_pnl_usd"]

    daily_s = pd.Series(daily_pnl).sort_index()
    daily_rets = daily_s / initial_capital
    mean_d = float(daily_rets.mean())
    std_d = float(daily_rets.std(ddof=1)) if len(daily_rets) > 1 else 0.0
    sharpe_daily = (mean_d / std_d * np.sqrt(252.0)) if std_d > 1e-9 else 0.0

    cum_pnl = daily_s.cumsum()
    equity_curve = initial_capital + cum_pnl
    peaks = np.maximum.accumulate(equity_curve)
    dd_usd = peaks - equity_curve
    max_dd_usd = float(dd_usd.max()) if len(dd_usd) > 0 else 0.0
    max_dd_pct = (max_dd_usd / initial_capital) * 100.0

    total_net_pnl = float(np.sum(pnls))
    years = (end_date - start_date).days / 365.25
    years = max(years, 0.1)
    simple_annual_ret = (total_net_pnl / initial_capital) / years * 100.0

    return {
        "n_trades": n_trades,
        "net_pnl_usd": total_net_pnl,
        "sharpe_daily": sharpe_daily,
        "win_rate": float(np.mean(pnls > 0)) * 100.0,
        "profit_factor": pf,
        "max_drawdown_usd": max_dd_usd,
        "max_drawdown_pct": max_dd_pct,
        "simple_annual_return": simple_annual_ret,
        "trades": valid_trades,
    }


def run_full_study():
    print("=" * 80)
    print("INICIANDO ESTUDIO INTRADÍA EMA 200: 3 AÑOS TRAIN vs 2 AÑOS TEST VIRGEN")
    print("=" * 80)

    costs_map = get_costs_map()
    assets = [
        ("NQ", "15m", PROCESSED_DIR / "NQ_15m.parquet", "15:45"),
        ("NQ", "5m", PROCESSED_DIR / "NQ_5m.parquet", "15:50"),
        ("ES", "15m", PROCESSED_DIR / "ES_15m.parquet", "15:45"),
        ("ES", "5m", PROCESSED_DIR / "ES_5m.parquet", "15:50"),
    ]

    # Grid de optimización en Train (36 combinaciones)
    trigger_types = ["candle_pattern", "price_cross", "macd_turn"]
    atr_ks = [1.5, 2.0, 2.5, 3.0]
    tp_ms = [1.5, 2.0, 3.0]

    all_train_results: List[Dict[str, Any]] = []
    best_configs: List[Dict[str, Any]] = []

    for sym, tf, f_path, moc_time in assets:
        print(f"\n---> Analizando {sym} {tf}...")
        df_train, df_test, _ = prepare_dataset_splits(f_path)
        costs = costs_map[sym]

        asset_train_results: List[Dict[str, Any]] = []

        for trig, k, m in itertools.product(trigger_types, atr_ks, tp_ms):
            params = IntradayEma200Params(
                trend_ema_period=200,
                atr_k=k,
                tp_m=m,
                trigger_type=trig,
                moc_close_time=moc_time,
                use_volatility_filter=True,
            )

            res_raw = run_ema200_backtest(df_train, params, costs, INITIAL_CAPITAL)
            res_train = filter_trades_by_date(res_raw, DATE_START_5Y, DATE_SPLIT_3Y, INITIAL_CAPITAL)

            record = {
                "symbol": sym,
                "timeframe": tf,
                "trigger_type": trig,
                "atr_k": k,
                "tp_m": m,
                "n_trades": res_train["n_trades"],
                "win_rate": res_train["win_rate"],
                "profit_factor": res_train["profit_factor"],
                "net_pnl_usd": res_train["net_pnl_usd"],
                "simple_annual_return": res_train["simple_annual_return"],
                "sharpe_daily": res_train["sharpe_daily"],
                "max_drawdown_usd": res_train["max_drawdown_usd"],
                "max_drawdown_pct": res_train["max_drawdown_pct"],
            }
            asset_train_results.append(record)
            all_train_results.append(record)

        df_res_asset = pd.DataFrame(asset_train_results)
        # Seleccionar la mejor configuración en Train:
        # Criterio: Sharpe diario más alto con mínimo 20 trades y PnL > 0
        valid = df_res_asset[(df_res_asset["n_trades"] >= 20) & (df_res_asset["net_pnl_usd"] > 0)]
        if len(valid) > 0:
            best_row = valid.sort_values("sharpe_daily", ascending=False).iloc[0]
        else:
            best_row = df_res_asset.sort_values("net_pnl_usd", ascending=False).iloc[0]

        best_trig = str(best_row["trigger_type"])
        best_k = float(best_row["atr_k"])
        best_m = float(best_row["tp_m"])

        print(f"  [Optimizada Train 3A] Mejor config: Trigger={best_trig}, k={best_k}, m={best_m}")
        print(f"  Train PnL: ${best_row['net_pnl_usd']:,.2f} | Sharpe: {best_row['sharpe_daily']:.2f} | DD: {best_row['max_drawdown_pct']:.1f}%")

        # ---------------------------------------------------------------------
        # EVALUACIÓN CIEGA EN TEST VIRGEN (Últimos 2 Años: 2024-10-20 a 2026-10-19)
        # ---------------------------------------------------------------------
        best_params = IntradayEma200Params(
            trend_ema_period=200,
            atr_k=best_k,
            tp_m=best_m,
            trigger_type=best_trig,
            moc_close_time=moc_time,
            use_volatility_filter=True,
        )

        res_test_raw = run_ema200_backtest(df_test, best_params, costs, INITIAL_CAPITAL)
        res_test = filter_trades_by_date(res_test_raw, DATE_SPLIT_3Y, DATE_END_5Y, INITIAL_CAPITAL)

        sharpe_train = float(best_row["sharpe_daily"])
        sharpe_test = float(res_test["sharpe_daily"])
        degradation = (sharpe_test / sharpe_train) if sharpe_train > 0 else 0.0

        is_profitable_oos = (res_test["net_pnl_usd"] > 0)
        verdict = "RENTABLE FUERA DE MUESTRA" if is_profitable_oos else "NO RENTABLE EN TEST"

        print(f"  [Test Virgen 2A] PnL: ${res_test['net_pnl_usd']:,.2f} | Sharpe: {sharpe_test:.2f} | DD: {res_test['max_drawdown_pct']:.1f}% | Veredicto: {verdict}")

        best_configs.append({
            "symbol": sym,
            "timeframe": tf,
            "best_trigger": best_trig,
            "best_atr_k": best_k,
            "best_tp_m": best_m,
            # Métricas Train (3 Años)
            "train_n_trades": int(best_row["n_trades"]),
            "train_win_rate": float(best_row["win_rate"]),
            "train_pf": float(best_row["profit_factor"]),
            "train_pnl_usd": float(best_row["net_pnl_usd"]),
            "train_annual_ret": float(best_row["simple_annual_return"]),
            "train_sharpe": sharpe_train,
            "train_max_dd_usd": float(best_row["max_drawdown_usd"]),
            "train_max_dd_pct": float(best_row["max_drawdown_pct"]),
            # Métricas Test (2 Años Vírgenes)
            "test_n_trades": int(res_test["n_trades"]),
            "test_win_rate": float(res_test["win_rate"]),
            "test_pf": float(res_test["profit_factor"]),
            "test_pnl_usd": float(res_test["net_pnl_usd"]),
            "test_annual_ret": float(res_test["simple_annual_return"]),
            "test_sharpe": sharpe_test,
            "test_max_dd_usd": float(res_test["max_drawdown_usd"]),
            "test_max_dd_pct": float(res_test["max_drawdown_pct"]),
            # Robustez y degradación
            "degradation_ratio": degradation,
            "is_profitable_oos": is_profitable_oos,
            "verdict": verdict,
        })

    # Guardar tablas CSV
    pd.DataFrame(all_train_results).to_csv(OUTPUT_TABLES / "optimizacion_ema200_train_3y.csv", index=False)
    df_comparison = pd.DataFrame(best_configs)
    df_comparison.to_csv(OUTPUT_TABLES / "comparacion_ema200_train_vs_test.csv", index=False)

    print("\nEstudio completado con éxito. Tablas guardadas en:", OUTPUT_TABLES)
    return df_comparison


if __name__ == "__main__":
    run_full_study()
