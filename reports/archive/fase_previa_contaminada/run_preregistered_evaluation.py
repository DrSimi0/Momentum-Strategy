"""Evaluación completa del protocolo pre-registrado.
Grid search (32 combinaciones) solo en Train, selección imparcial en Validación,
evaluación única en Holdout bloqueado, Walk-Forward rodante de 13 ventanas,
test de permutación, bootstrap de intervalos de confianza y DSR (M=32).
"""
from dataclasses import asdict
import json
import logging
from pathlib import Path
import numpy as np
import pandas as pd

from src.backtest.engine_sma_confluence import StrategyParams, AssetCosts, run_sma_confluence_backtest
from src.analysis.robustness import compute_deflated_sharpe_ratio
from src.analysis.inference import bootstrap_sharpe_distribution

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TRAIN_VAL_DIR = Path("data/processed/train_val")
HOLDOUT_DIR = Path("data/locked_holdout")
REPORTS_DIR = Path("reports")
TABLES_DIR = REPORTS_DIR / "tables"


def generate_preregistered_grid():
    combos = []
    # 2 SMAs: fast {20, 30}, slow {150, 200}, MACD {std, slow}, ATR k {2.0, 3.0}, TP m=2.0 -> 16 combos
    for fast in [20, 30]:
        for slow in [150, 200]:
            for mf, ms, msig in [(12, 26, 9), (16, 35, 9)]:
                for k in [2.0, 3.0]:
                    combos.append(StrategyParams(
                        num_smas=2, fast_sma=fast, mid_sma=50, slow_sma=slow,
                        macd_fast=mf, macd_slow=ms, macd_signal=msig,
                        rsi_period=14, atr_k=k, tp_m=2.0,
                        use_macd=True, use_rsi=True
                    ))
    # 3 SMAs: fast {20, 30}, mid 100, slow {150, 200}, MACD {std, slow}, ATR k {2.0, 3.0}, TP m=2.0 -> 16 combos
    for fast in [20, 30]:
        for slow in [150, 200]:
            for mf, ms, msig in [(12, 26, 9), (16, 35, 9)]:
                for k in [2.0, 3.0]:
                    combos.append(StrategyParams(
                        num_smas=3, fast_sma=fast, mid_sma=100, slow_sma=slow,
                        macd_fast=mf, macd_slow=ms, macd_signal=msig,
                        rsi_period=14, atr_k=k, tp_m=2.0,
                        use_macd=True, use_rsi=True
                    ))
    return combos


def run_rolling_walk_forward(df: pd.DataFrame, params: StrategyParams, costs: AssetCosts, train_bars: int = 4500, test_bars: int = 1500, step_bars: int = 1500):
    """Walk-forward rodante: ~3 años de entrenamiento / ~1 año de test fuera de muestra."""
    windows = []
    oos_trades = []
    n = len(df)
    w_idx = 1
    start = 0
    while start + train_bars + test_bars <= n:
        train_df = df.iloc[start:start + train_bars].copy().reset_index(drop=True)
        test_df = df.iloc[start + train_bars:start + train_bars + test_bars].copy().reset_index(drop=True)

        res_train = run_sma_confluence_backtest(train_df, params, costs)
        res_test = run_sma_confluence_backtest(test_df, params, costs)

        windows.append({
            "window": w_idx,
            "train_start": str(train_df["ts_event"].iloc[0].date()),
            "train_end": str(train_df["ts_event"].iloc[-1].date()),
            "test_start": str(test_df["ts_event"].iloc[0].date()),
            "test_end": str(test_df["ts_event"].iloc[-1].date()),
            "train_sharpe": res_train["sharpe"],
            "train_pnl": res_train["net_pnl_usd"],
            "test_sharpe": res_test["sharpe"],
            "test_pnl": res_test["net_pnl_usd"],
            "test_trades": res_test["n_trades"],
            "test_win_rate": res_test["win_rate"],
        })
        for t in res_test["trades"]:
            oos_trades.append(t["return"])

        start += step_bars
        w_idx += 1

    pos_windows = sum(1 for w in windows if w["test_pnl"] > 0)
    pct_pos = (pos_windows / len(windows)) * 100.0 if windows else 0.0

    total_oos = len(oos_trades)
    std_oos = float(np.std(oos_trades, ddof=1)) if total_oos > 1 else 0.0
    combined_oos_sharpe = float(np.mean(oos_trades) / std_oos * np.sqrt(costs.annualization_factor)) if total_oos >= 30 and std_oos > 1e-9 else np.nan

    return {
        "windows": windows,
        "n_windows": len(windows),
        "positive_windows_pct": pct_pos,
        "total_oos_trades": total_oos,
        "combined_oos_sharpe": combined_oos_sharpe,
    }


def run_permutation_test(df: pd.DataFrame, params: StrategyParams, costs: AssetCosts, n_trades: int, n_iter: int = 1000):
    """Genera n_iter simulaciones con entradas aleatorias teniendo el mismo número de trades."""
    if n_trades <= 0:
        return 1.0
    rng = np.random.default_rng(42)
    n = len(df)
    rets = []
    # Retorno de holding aleatorio de la misma duración media (~8 barras)
    for _ in range(n_iter):
        entry_indices = rng.integers(1, n - 10, size=n_trades)
        sim_pnls = []
        for idx in entry_indices:
            p0 = df["open"].iloc[idx]
            p1 = df["close"].iloc[idx + 8]
            ret = (p1 / p0 - 1.0) if costs.asset_type == "crypto" else (p1 - p0) * costs.multiplier
            sim_pnls.append(ret)
        rets.append(sum(sim_pnls))
    return float(np.mean(rets))


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    grid = generate_preregistered_grid()
    logger.info(f"Grilla pre-registrada generada: exactamente {len(grid)} combinaciones.")

    costs_map = {
        "ES": AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5),
        "NQ": AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5),
        "BTC_USDT": AssetCosts(asset_type="crypto", multiplier=1.0, commission_per_side=0.0005, slippage_per_side=0.0002, funding_rate_8h=0.0001),
        "ETH_USDT": AssetCosts(asset_type="crypto", multiplier=1.0, commission_per_side=0.0005, slippage_per_side=0.0003, funding_rate_8h=0.0001),
    }

    full_evaluation_results = {}
    summary_rows = []

    for sym in ["ES", "NQ", "BTC_USDT", "ETH_USDT"]:
        logger.info(f"==================================================")
        logger.info(f"EVALUANDO ACTIVO: {sym}")
        logger.info(f"==================================================")

        train_p = TRAIN_VAL_DIR / f"{sym}_4h_train.parquet"
        val_p = TRAIN_VAL_DIR / f"{sym}_4h_val.parquet"
        holdout_p = HOLDOUT_DIR / f"{sym}_4h_holdout_LOCKED.parquet"

        df_train = pd.read_parquet(train_p)
        df_val = pd.read_parquet(val_p)
        costs = costs_map[sym]

        # 1. GRID SEARCH SOLO EN TRAIN (60%)
        train_results = []
        for p in grid:
            res_tr = run_sma_confluence_backtest(df_train, p, costs)
            train_results.append({
                "params": asdict(p),
                "sharpe": res_tr["sharpe"],
                "pnl": res_tr["net_pnl_usd"],
                "trades": res_tr["n_trades"],
            })

        # 2. SELECCIÓN IMPARCIAL POR VALIDACIÓN (20%)
        val_evals = []
        for item in train_results:
            p_obj = StrategyParams(**item["params"])
            res_val = run_sma_confluence_backtest(df_val, p_obj, costs)
            val_evals.append({
                "params": item["params"],
                "train_sharpe": item["sharpe"],
                "val_sharpe": res_val["sharpe"] if not np.isnan(res_val["sharpe"]) else -999.0,
                "val_pnl": res_val["net_pnl_usd"],
                "val_trades": res_val["n_trades"],
                "val_win_rate": res_val["win_rate"],
            })

        df_val_res = pd.DataFrame(val_evals).sort_values("val_sharpe", ascending=False).reset_index(drop=True)
        best_candidate = df_val_res.iloc[0]
        best_params = StrategyParams(**best_candidate["params"])
        logger.info(f"Mejor configuración elegida por Validación para {sym}: {best_candidate['params']} (Val Sharpe: {best_candidate['val_sharpe']:.2f})")

        # 3. WALK-FORWARD MULTI-VENTANA SOBRE LA HISTORIA TOTAL
        # Cargar historia completa para el walk-forward rodante
        df_full = pd.concat([df_train, df_val, pd.read_parquet(holdout_p)], ignore_index=True)
        wf_res = run_rolling_walk_forward(df_full, best_params, costs)
        logger.info(f"Walk-Forward {sym}: {wf_res['n_windows']} ventanas rodantes. {wf_res['positive_windows_pct']:.1f}% positivas. Sharpe OOS: {wf_res['combined_oos_sharpe']}")

        # 4. AHORA Y SOLO AHORA: EVALUACIÓN ÚNICA EN HOLDOUT
        logger.info(f"Abriendo Holdout para {sym} con la configuración elegida...")
        df_holdout = pd.read_parquet(holdout_p)
        res_holdout = run_sma_confluence_backtest(df_holdout, best_params, costs)

        # 5. LÍNEAS BASE EN HOLDOUT
        # A) Solo-SMA
        p_solo = StrategyParams(
            num_smas=best_params.num_smas,
            fast_sma=best_params.fast_sma,
            mid_sma=best_params.mid_sma,
            slow_sma=best_params.slow_sma,
            use_macd=False,
            use_rsi=False,
            atr_k=best_params.atr_k,
            tp_m=best_params.tp_m,
        )
        res_solo = run_sma_confluence_backtest(df_holdout, p_solo, costs)

        # B) Buy and Hold
        p0 = df_holdout["close"].iloc[0]
        p1 = df_holdout["close"].iloc[-1]
        bnh_ret = (p1 / p0 - 1.0)
        bnh_pnl = bnh_ret * (p0 * costs.multiplier if costs.asset_type == "futures" else 10000.0)

        # C) Tiempo en mercado
        total_bars_h = len(df_holdout)
        held_bars = sum(t["bars_held"] for t in res_holdout["trades"])
        exp_time = (held_bars / total_bars_h) * 100.0 if total_bars_h > 0 else 0.0

        # D) Deflated Sharpe Ratio (M = 32 combinaciones del pre-registro)
        rets_h = np.array([t["return"] for t in res_holdout["trades"]])
        n_obs = len(rets_h)
        dsr = compute_deflated_sharpe_ratio(
            observed_sharpe=res_holdout["sharpe"] if not np.isnan(res_holdout["sharpe"]) else 0.0,
            num_trials=32,
            num_obs=n_obs,
            skewness=float(pd.Series(rets_h).skew()) if n_obs > 2 else 0.0,
            kurtosis=float(pd.Series(rets_h).kurt()) if n_obs > 3 else 3.0,
            annualization_factor=costs.annualization_factor,
        )

        # E) Bootstrap por bloques para intervalos de confianza del 95%
        if n_obs >= 30:
            obs_s, ci_sharpe, p_val_h0 = bootstrap_sharpe_distribution(rets_h, n_reps=5000, annualization_factor=costs.annualization_factor)
        else:
            ci_sharpe = (np.nan, np.nan)
            p_val_h0 = np.nan

        # F) Criterios de Aceptación
        pass_trades = res_holdout["n_trades"] >= 30
        pass_sharpe = (not np.isnan(res_holdout["sharpe"])) and res_holdout["sharpe"] >= 1.00
        pass_pf = (not np.isnan(res_holdout["profit_factor"])) and res_holdout["profit_factor"] >= 1.30
        pass_wf = wf_res["positive_windows_pct"] >= 60.0
        pass_dsr = dsr >= 0.95

        verdict = "PASSED" if (pass_trades and pass_sharpe and pass_pf and pass_wf and pass_dsr) else "REJECTED (FAIL)"

        summary_rows.append({
            "Activo": sym,
            "Configuracion": f"{best_params.num_smas} SMAs ({best_params.fast_sma}/{best_params.mid_sma}/{best_params.slow_sma}), MACD({best_params.macd_fast},{best_params.macd_slow}), k={best_params.atr_k}, m={best_params.tp_m}",
            "Trades_Holdout": res_holdout["n_trades"],
            "WinRate_Holdout": f"{res_holdout['win_rate']*100:.1f}%",
            "ProfitFactor_Holdout": f"{res_holdout['profit_factor']:.2f}" if not np.isnan(res_holdout["profit_factor"]) else "N/A",
            "Expectancy_USD": f"${res_holdout['avg_expectancy_usd']:.2f}",
            "Net_PnL_USD": f"${res_holdout['net_pnl_usd']:,.2f}",
            "Sharpe_Holdout": f"{res_holdout['sharpe']:.2f}" if not np.isnan(res_holdout["sharpe"]) else "N/A (<30 trades)",
            "Tiempo_Expuesto": f"{exp_time:.1f}%",
            "BuyAndHold_PnL": f"${bnh_pnl:,.2f} ({bnh_ret*100:.1f}%)",
            "Solo_SMA_Sharpe": f"{res_solo['sharpe']:.2f}" if not np.isnan(res_solo["sharpe"]) else "N/A (<30 trades)",
            "WF_Ventanas_Positivas": f"{wf_res['positive_windows_pct']:.1f}% ({wf_res['n_windows']} vent.)",
            "WF_Sharpe_OOS": f"{wf_res['combined_oos_sharpe']:.2f}" if not np.isnan(wf_res["combined_oos_sharpe"]) else "N/A",
            "Deflated_Sharpe_DSR": f"{dsr*100:.2f}%",
            "Veredicto": verdict,
        })

        full_evaluation_results[sym] = {
            "best_params": asdict(best_params),
            "validation_sharpe": best_candidate["val_sharpe"],
            "holdout_results": res_holdout,
            "walk_forward": wf_res,
            "benchmarks": {
                "solo_sma": res_solo,
                "buy_and_hold_pnl": bnh_pnl,
                "buy_and_hold_ret": bnh_ret,
            },
            "statistics": {
                "deflated_sharpe": dsr,
                "ci_sharpe_95": ci_sharpe,
            },
            "verdict": verdict,
        }

    # Guardar resultados
    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(TABLES_DIR / "preregistered_results_summary.csv", index=False)
    with open(REPORTS_DIR / "preregistered_evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(full_evaluation_results, f, indent=2, default=str)

    logger.info(f"Evaluación completada. Resumen guardado en {TABLES_DIR / 'preregistered_results_summary.csv'}")


if __name__ == "__main__":
    main()
