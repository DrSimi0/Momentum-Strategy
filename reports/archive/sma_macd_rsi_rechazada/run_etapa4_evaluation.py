"""ETAPA 4 - EVALUACIÓN RIGUROSA SOBRE EL UNIVERSO DE DESARROLLO (2017-12 a 2026-10).
El Holdout bloqueado (2010-2017) NO es tocado ni leído por este script.

4.1 Grid search solo en entrenamiento (70%, 2017-2024); selección por validación (30%, 2024-2026).
4.2 Walk-forward rodante (3 años train / 1 año test) exclusivamente en el tramo 2017-2026.
4.3 Métricas por activo: trades, win rate, profit factor, expectativa por trade, tiempo en mercado,
    retorno neto, max drawdown, Sharpe (anualizado documentado) y buy & hold del mismo periodo.
4.4 Comparación contra: buy & hold, solo-SMA y test de permutación con señales aleatorias.
4.5 Estabilidad paramétrica y Deflated Sharpe Ratio (DSR) ajustado por M=32 combinaciones.
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
REPORTS_DIR = Path("reports")
TABLES_DIR = REPORTS_DIR / "tables"


def generate_preregistered_grid():
    """Genera las exactamente 32 combinaciones pre-registradas en PREREGISTRO.md."""
    combos = []
    # 1. 2 SMAs: fast {20, 30}, slow {150, 200}, MACD {std, slow}, ATR k {2.0, 3.0}, TP m=2.0 -> 16 combos
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
    # 2. 3 SMAs: fast {20, 30}, mid 100, slow {150, 200}, MACD {std, slow}, ATR k {2.0, 3.0}, TP m=2.0 -> 16 combos
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


def run_rolling_walk_forward_development(
    df_dev: pd.DataFrame,
    params: StrategyParams,
    costs: AssetCosts,
    train_bars: int = 4500,  # ~3 años de 4h
    test_bars: int = 1500,   # ~1 año de 4h
    step_bars: int = 1500,   # Paso anual
):
    """Walk-forward rodante confinado estrictamente al universo de desarrollo 2017-2026."""
    windows = []
    oos_trades = []
    n = len(df_dev)
    w_idx = 1
    start = 0

    while start + train_bars + test_bars <= n:
        train_df = df_dev.iloc[start:start + train_bars].copy().reset_index(drop=True)
        test_df = df_dev.iloc[start + train_bars:start + train_bars + test_bars].copy().reset_index(drop=True)

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
            "test_profit_factor": res_test["profit_factor"],
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


def run_permutation_test(df: pd.DataFrame, costs: AssetCosts, n_trades: int, n_iter: int = 1000):
    """Test de permutación con entradas aleatorias teniendo el mismo número de trades."""
    if n_trades <= 0:
        return 0.0
    rng = np.random.default_rng(20260421)
    n = len(df)
    sim_returns = []
    # Retención media de ~8 barras (32h)
    holding = min(8, n - 2)
    for _ in range(n_iter):
        entry_indices = rng.integers(1, n - holding - 1, size=n_trades)
        pnls = []
        for idx in entry_indices:
            p0 = df["open"].iloc[idx]
            p1 = df["close"].iloc[idx + holding]
            if costs.asset_type == "futures":
                diff = (p1 - p0)
                pnl = diff * costs.multiplier - (2.0 * costs.commission_per_side + 2.0 * costs.slippage_per_side * costs.tick_size * costs.multiplier)
            else:
                ret = (p1 / p0 - 1.0) - (2.0 * costs.commission_per_side + 2.0 * costs.slippage_per_side)
                pnl = ret * 10000.0
            pnls.append(pnl)
        sim_returns.append(sum(pnls))
    return float(np.mean(sim_returns))


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    grid = generate_preregistered_grid()
    logger.info(f"Grilla pre-registrada: exactamente {len(grid)} combinaciones.")

    costs_map = {
        "ES": AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5),
        "NQ": AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5),
        "BTC_USDT": AssetCosts(asset_type="crypto", multiplier=1.0, commission_per_side=0.0005, slippage_per_side=0.0002, funding_rate_8h=0.0001),
        "ETH_USDT": AssetCosts(asset_type="crypto", multiplier=1.0, commission_per_side=0.0005, slippage_per_side=0.0003, funding_rate_8h=0.0001),
    }

    # Capital base institucional fijado en PREREGISTRO.md
    base_capital = {
        "ES": 100000.0,
        "NQ": 150000.0,
        "BTC_USDT": 10000.0,
        "ETH_USDT": 10000.0,
    }

    eval_results = {}
    summary_rows = []

    # Evaluar los activos (Futuros primarios; Cripto exploratorio)
    for sym in ["ES", "NQ", "BTC_USDT", "ETH_USDT"]:
        is_crypto = ("BTC" in sym or "ETH" in sym)
        logger.info(f"==================================================")
        logger.info(f"EVALUANDO ACTIVO (DESARROLLO): {sym} ({'EXPLORATORIO' if is_crypto else 'FUTUROS CME'})")
        logger.info(f"==================================================")

        costs = costs_map[sym]
        cap = base_capital[sym]

        if not is_crypto:
            train_p = TRAIN_VAL_DIR / f"{sym}_4h_train.parquet"
            val_p = TRAIN_VAL_DIR / f"{sym}_4h_val.parquet"
            df_train = pd.read_parquet(train_p)
            df_val = pd.read_parquet(val_p)
            df_dev = pd.read_parquet(f"data/processed/{sym}_4h.parquet")
        else:
            # Cripto exploratorio: 70% Train, 30% Val
            df_raw = pd.read_parquet(f"data/raw/{sym.replace('_', '-')}_4h.parquet")
            n_c = len(df_raw)
            n_tr_c = int(n_c * 0.70)
            df_train = df_raw.iloc[:n_tr_c].copy().reset_index(drop=True)
            df_val = df_raw.iloc[n_tr_c:].copy().reset_index(drop=True)
            df_dev = df_raw

        logger.info(f"{sym}: Train={len(df_train)} ({df_train['ts_event'].iloc[0].date()} a {df_train['ts_event'].iloc[-1].date()}) | Val={len(df_val)} ({df_val['ts_event'].iloc[0].date()} a {df_val['ts_event'].iloc[-1].date()})")

        # 4.1 GRID SEARCH SOLO EN ENTRENAMIENTO
        train_evals = []
        for p in grid:
            r_tr = run_sma_confluence_backtest(df_train, p, costs)
            train_evals.append({
                "params": asdict(p),
                "sharpe": r_tr["sharpe"],
                "pnl": r_tr["net_pnl_usd"],
                "trades": r_tr["n_trades"],
                "win_rate": r_tr["win_rate"],
            })

        # SELECCIÓN IMPARCIAL POR VALIDACIÓN (30%)
        val_evals = []
        for item in train_evals:
            p_obj = StrategyParams(**item["params"])
            r_v = run_sma_confluence_backtest(df_val, p_obj, costs)
            val_evals.append({
                "params": item["params"],
                "train_sharpe": item["sharpe"],
                "train_pnl": item["pnl"],
                "train_trades": item["trades"],
                "val_sharpe": r_v["sharpe"] if not np.isnan(r_v["sharpe"]) else -999.0,
                "val_pnl": r_v["net_pnl_usd"],
                "val_trades": r_v["n_trades"],
                "val_win_rate": r_v["win_rate"],
                "val_profit_factor": r_v["profit_factor"],
                "val_max_drawdown": r_v["max_drawdown"],
            })

        df_val_res = pd.DataFrame(val_evals).sort_values("val_sharpe", ascending=False).reset_index(drop=True)
        best_candidate = df_val_res.iloc[0]
        best_params = StrategyParams(**best_candidate["params"])
        logger.info(f"Finalista elegida por Validación para {sym}: {best_candidate['params']}")
        logger.info(f"  Val Sharpe: {best_candidate['val_sharpe']:.2f} | Val PnL: ${best_candidate['val_pnl']:,.2f} | Val Trades: {best_candidate['val_trades']}")

        # 4.2 WALK-FORWARD RODANTE CONFINADO A DESARROLLO (2017-2026)
        wf_res = run_rolling_walk_forward_development(
            df_dev, best_params, costs,
            train_bars=4500 if not is_crypto else 3000,
            test_bars=1500 if not is_crypto else 1000,
            step_bars=1500 if not is_crypto else 1000,
        )
        logger.info(f"Walk-Forward {sym}: {wf_res['n_windows']} ventanas. {wf_res['positive_windows_pct']:.1f}% positivas. OOS Trades: {wf_res['total_oos_trades']} | Sharpe OOS: {wf_res['combined_oos_sharpe']}")

        # 4.3 BACKTEST DE LA FINALISTA EN VALIDACIÓN
        res_val_finalist = run_sma_confluence_backtest(df_val, best_params, costs)

        # 4.4 LÍNEAS BASE EN VALIDACIÓN
        # Solo-SMA
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
        res_solo_val = run_sma_confluence_backtest(df_val, p_solo, costs)

        # Buy & Hold
        p0 = df_val["close"].iloc[0]
        p1 = df_val["close"].iloc[-1]
        bnh_ret = (p1 / p0 - 1.0)
        bnh_pnl = bnh_ret * (p0 * costs.multiplier if costs.asset_type == "futures" else 10000.0)

        # Test de permutación aleatoria (1,000 iteraciones con mismo número de trades)
        perm_mean_pnl = run_permutation_test(df_val, costs, res_val_finalist["n_trades"], n_iter=1000)

        # Tiempo en mercado
        tot_bars_v = len(df_val)
        held_bars_v = sum(t["bars_held"] for t in res_val_finalist["trades"])
        exp_time = (held_bars_v / tot_bars_v * 100.0) if tot_bars_v > 0 else 0.0

        # Drawdown relativo porcentual
        max_dd_val = res_val_finalist["max_drawdown"]
        dd_rel_pct = (max_dd_val / cap) * 100.0

        # Deflated Sharpe Ratio (M = 32 combinaciones del pre-registro)
        rets_v = np.array([t["return"] for t in res_val_finalist["trades"]])
        n_obs = len(rets_v)
        dsr = compute_deflated_sharpe_ratio(
            observed_sharpe=res_val_finalist["sharpe"] if not np.isnan(res_val_finalist["sharpe"]) else 0.0,
            num_trials=32,
            num_obs=n_obs,
            skewness=float(pd.Series(rets_v).skew()) if n_obs > 2 else 0.0,
            kurtosis=float(pd.Series(rets_v).kurt()) if n_obs > 3 else 3.0,
            annualization_factor=costs.annualization_factor,
        )

        # Bootstrap por bloques estacionarios (IC 95%)
        if n_obs >= 30:
            _, ci_sharpe, p_val_h0 = bootstrap_sharpe_distribution(rets_v, n_reps=5000, annualization_factor=costs.annualization_factor)
        else:
            ci_sharpe = (np.nan, np.nan)
            p_val_h0 = np.nan

        summary_rows.append({
            "Activo": sym,
            "Tipo": "EXPLORATORIO" if is_crypto else "FUTUROS CME",
            "Configuracion_Finalista": f"{best_params.num_smas} SMAs ({best_params.fast_sma}/{best_params.mid_sma}/{best_params.slow_sma}), MACD({best_params.macd_fast},{best_params.macd_slow}), k={best_params.atr_k}, m={best_params.tp_m}",
            "Train_Sharpe": f"{best_candidate['train_sharpe']:.2f}" if not np.isnan(best_candidate["train_sharpe"]) else "N/A",
            "Val_Trades": res_val_finalist["n_trades"],
            "Val_WinRate": f"{res_val_finalist['win_rate']*100:.1f}%",
            "Val_ProfitFactor": f"{res_val_finalist['profit_factor']:.2f}" if not np.isnan(res_val_finalist["profit_factor"]) else "N/A",
            "Val_Net_PnL": f"${res_val_finalist['net_pnl_usd']:,.2f}",
            "Val_Sharpe": f"{res_val_finalist['sharpe']:.2f}" if not np.isnan(res_val_finalist["sharpe"]) else "N/A (<30 trades)",
            "Val_Max_DD": f"${max_dd_val:,.2f} ({dd_rel_pct:.1f}% de ${cap:,.0f})",
            "Val_Exp_Time": f"{exp_time:.1f}%",
            "Val_BuyAndHold_PnL": f"${bnh_pnl:,.2f} ({bnh_ret*100:.1f}%)",
            "Val_Permutacion_Aleatoria_PnL": f"${perm_mean_pnl:,.2f}",
            "Val_Solo_SMA_Sharpe": f"{res_solo_val['sharpe']:.2f}" if not np.isnan(res_solo_val["sharpe"]) else "N/A (<30 trades)",
            "WF_Ventanas_Positivas": f"{wf_res['positive_windows_pct']:.1f}% ({wf_res['n_windows']} vent.)",
            "WF_OOS_Trades": wf_res["total_oos_trades"],
            "WF_OOS_Sharpe": f"{wf_res['combined_oos_sharpe']:.2f}" if not np.isnan(wf_res["combined_oos_sharpe"]) else "N/A (<30 trades)",
            "Deflated_Sharpe_DSR": f"{dsr*100:.2f}%",
        })

        eval_results[sym] = {
            "best_params": asdict(best_params),
            "validation_results": res_val_finalist,
            "walk_forward_development": wf_res,
            "benchmarks": {
                "solo_sma": res_solo_val,
                "buy_and_hold_pnl": bnh_pnl,
                "buy_and_hold_ret": bnh_ret,
                "random_permutation_pnl": perm_mean_pnl,
            },
            "statistics": {
                "deflated_sharpe": dsr,
                "ci_sharpe_95": ci_sharpe,
                "p_value_h0": p_val_h0,
            },
        }

    df_summary = pd.DataFrame(summary_rows)
    csv_out = TABLES_DIR / "etapa4_development_evaluation_summary.csv"
    df_summary.to_csv(csv_out, index=False)
    with open(REPORTS_DIR / "etapa4_development_results.json", "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2, default=str)

    logger.info(f"ETAPA 4 completada con éxito. Resumen guardado en {csv_out}")


if __name__ == "__main__":
    main()
