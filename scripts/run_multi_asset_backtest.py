"""Orquestador completo del estudio multiactivo SMA + MACD + RSI (ES, NQ, BTC, ETH).
Ejecuta:
1. Partición 60/20/20.
2. Grid Search en Entrenamiento (1,890 combinaciones por activo/timeframe).
3. Selección imparcial de finalistas en Validación (descartando <100 trades).
4. Generación de mapas de calor de estabilidad.
5. Walk-Forward de finalistas.
6. Pruebas de robustez cruzada (NQ vs ES, BTC vs ETH, índices vs cripto).
7. Comparación contra Buy & Hold y Solo-SMA.
8. Evaluación en Test Final con Deflated Sharpe Ratio.
9. Guardado en reports/results_sma_system.json y tablas CSV.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import logging
from pathlib import Path
import pandas as pd
import yaml

from src.backtest.engine_sma_confluence import StrategyParams, AssetCosts, run_sma_confluence_backtest
from src.analysis.grid_search import run_grid_search_for_asset, partition_data_60_20_20
from src.analysis.walk_forward import run_walk_forward_analysis
from src.analysis.heatmaps import generate_stability_heatmap
from src.analysis.robustness import (
    compute_deflated_sharpe_ratio,
    evaluate_solo_sma_benchmark,
    evaluate_buy_and_hold_benchmark,
    run_cross_asset_evaluation,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("orchestrator")

CONFIG_PATH = Path("config/multi_asset_costs.yaml")
PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports")
TABLES_DIR = Path("reports/tables")


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    asset_cfgs = cfg["assets"]

    # Activos y timeframes primarios para la investigación
    # Usamos 1h y 4h como timeframes centrales completos que cubren tanto intradía como swing en los 4 activos
    assets_to_evaluate = [
        ("ES", "1h"),
        ("NQ", "1h"),
        ("BTC-USDT", "1h"),
        ("ETH-USDT", "1h"),
        ("ES", "4h"),
        ("NQ", "4h"),
        ("BTC-USDT", "4h"),
        ("ETH-USDT", "4h"),
    ]

    all_study_results = {
        "metadata": {
            "title": "Estudio Multiactivo de Confluencia SMA + MACD + RSI",
            "protocol": "60% Train, 20% Val, 20% Test Final",
            "assets_evaluated": ["ES", "NQ", "BTC-USDT", "ETH-USDT"],
            "timeframes": ["1h", "4h"],
        },
        "experiments": {},
        "cross_asset_robustness": {},
        "total_combinations_tested": 0,
    }

    finalists_by_asset_tf = {}
    total_trials = 0

    # 1. EJECUCIÓN DEL GRID SEARCH Y VALIDACIÓN
    for asset_name, tf in assets_to_evaluate:
        logger.info(f"==================================================")
        logger.info(f"PROCESANDO: {asset_name} ({tf})")
        logger.info(f"==================================================")

        file_prefix = asset_name.replace("-", "_")
        parquet_file = PROCESSED_DIR / f"{file_prefix}_{tf}.parquet"
        if not parquet_file.exists():
            logger.warning(f"Archivo no encontrado: {parquet_file}. Saltando.")
            continue

        df = pd.read_parquet(parquet_file)
        c_spec = asset_cfgs[asset_name]

        is_crypto = (c_spec["family"] == "crypto")
        costs = AssetCosts(
            asset_type="crypto" if is_crypto else "futures",
            multiplier=float(c_spec.get("multiplier_usd_per_point", 1.0)),
            tick_size=float(c_spec.get("tick_size_points", 0.01)),
            commission_per_side=float(c_spec.get("commission_pct_per_side", 0.0005) if is_crypto else c_spec.get("commission_usd_per_side", 2.0)),
            slippage_per_side=float(c_spec.get("slippage_pct_per_side", 0.0002) if is_crypto else c_spec.get("slippage_ticks_per_side", 0.5)),
            funding_rate_8h=float(c_spec.get("default_funding_rate_8h", 0.0001)),
            annualization_factor=float(c_spec.get("annualization_days", 365.0)),
        )

        # Grid search
        grid_res = run_grid_search_for_asset(df, asset_name, tf, costs, min_trades=50)
        total_trials += grid_res["total_combinations_tested"]

        # Mapa de calor de estabilidad
        heatmap_path = generate_stability_heatmap(
            grid_results=grid_res["all_train_results"],
            asset_name=asset_name,
            timeframe=tf,
            fixed_num_smas=2,
            metric="sharpe",
        )
        logger.info(f"Mapa de calor generado: {heatmap_path}")

        # Particionar para evaluaciones posteriores
        train_df, val_df, test_df = partition_data_60_20_20(df)

        # Seleccionar mejor finalista de validación
        top_finalists = grid_res["top_finalists_selected_on_val"]
        best_finalist = top_finalists[0] if top_finalists else None

        finalist_evaluations = {}
        if best_finalist:
            p_obj = StrategyParams(**best_finalist["params"])
            finalists_by_asset_tf[(asset_name, tf)] = (p_obj, costs, df)

            # A) Walk-forward sobre el dataset completo
            wf_res = run_walk_forward_analysis(df, p_obj, costs, n_windows=5)

            # B) Líneas base en Validación
            solo_sma_val = evaluate_solo_sma_benchmark(val_df, p_obj, costs)
            bnh_val = evaluate_buy_and_hold_benchmark(val_df, costs)

            # C) EVALUACIÓN EN TEST FINAL (HOLDOUT)
            test_res = run_sma_confluence_backtest(test_df, p_obj, costs)
            solo_sma_test = evaluate_solo_sma_benchmark(test_df, p_obj, costs)
            bnh_test = evaluate_buy_and_hold_benchmark(test_df, costs)

            finalist_evaluations = {
                "params": best_finalist["params"],
                "validation": {
                    "strategy_sharpe": best_finalist["val_sharpe"],
                    "strategy_pnl_usd": best_finalist["val_net_pnl_usd"],
                    "solo_sma_sharpe": solo_sma_val["sharpe"],
                    "buy_and_hold_sharpe": bnh_val["sharpe"],
                },
                "walk_forward": {
                    "combined_oos_sharpe": wf_res.get("combined_oos_sharpe", 0.0),
                    "windows": wf_res.get("windows", []),
                },
                "test_final": {
                    "trades": test_res["n_trades"],
                    "net_pnl_usd": test_res["net_pnl_usd"],
                    "sharpe": test_res["sharpe"],
                    "win_rate": test_res["win_rate"],
                    "profit_factor": test_res["profit_factor"],
                    "max_drawdown": test_res["max_drawdown"],
                    "avg_expectancy_usd": test_res["avg_expectancy_usd"],
                    "solo_sma_sharpe": solo_sma_test["sharpe"],
                    "buy_and_hold_sharpe": bnh_test["sharpe"],
                    "buy_and_hold_pnl_usd": bnh_test["net_pnl_usd"],
                },
            }

        all_study_results["experiments"][f"{asset_name}_{tf}"] = {
            "asset": asset_name,
            "timeframe": tf,
            "train_summary": grid_res["train_summary"],
            "finalist_evaluation": finalist_evaluations,
        }

    all_study_results["total_combinations_tested"] = total_trials

    # 2. PRUEBAS DE ROBUSTEZ CRUZADA (CROSS-ASSET)
    logger.info("=== EJECUTANDO PRUEBAS DE ROBUSTEZ CRUZADA ===")
    cross_tests = [
        ("NQ_to_ES_1h", ("NQ", "1h"), ("ES", "1h")),
        ("ES_to_NQ_1h", ("ES", "1h"), ("NQ", "1h")),
        ("BTC_to_ETH_1h", ("BTC-USDT", "1h"), ("ETH-USDT", "1h")),
        ("ETH_to_BTC_1h", ("ETH-USDT", "1h"), ("BTC-USDT", "1h")),
        ("NQ_to_BTC_1h", ("NQ", "1h"), ("BTC-USDT", "1h")),
        ("BTC_to_NQ_1h", ("BTC-USDT", "1h"), ("NQ", "1h")),
    ]

    cross_results = {}
    for test_name, src_key, tgt_key in cross_tests:
        if src_key in finalists_by_asset_tf and tgt_key in finalists_by_asset_tf:
            src_params, _, _ = finalists_by_asset_tf[src_key]
            _, tgt_costs, tgt_df = finalists_by_asset_tf[tgt_key]

            # Evaluar configuración de origen en el activo destino
            res = run_cross_asset_evaluation(src_params, tgt_df, tgt_costs)
            cross_results[test_name] = {
                "source": f"{src_key[0]} ({src_key[1]})",
                "target": f"{tgt_key[0]} ({tgt_key[1]})",
                "target_sharpe": res["sharpe"],
                "target_net_pnl_usd": res["net_pnl_usd"],
                "target_trades": res["n_trades"],
                "target_win_rate": res["win_rate"],
            }
            logger.info(f"Cross-test {test_name}: Sharpe={res['sharpe']:.2f}, PnL=${res['net_pnl_usd']:,.0f}")

    all_study_results["cross_asset_robustness"] = cross_results

    # 3. CORRECCIÓN POR PRUEBAS MÚLTIPLES (DEFLATED SHARPE RATIO)
    logger.info("=== CALCULANDO DEFLATED SHARPE RATIOS ===")
    for exp_key, exp_data in all_study_results["experiments"].items():
        fin = exp_data.get("finalist_evaluation", {})
        tf_eval = fin.get("test_final", {})
        obs_sh = tf_eval.get("sharpe", 0.0)
        n_obs = tf_eval.get("trades", 100)

        c_spec = asset_cfgs[exp_data["asset"]]
        ann_factor = float(c_spec.get("annualization_days", 252.0))

        dsr = compute_deflated_sharpe_ratio(
            observed_sharpe=obs_sh,
            num_trials=total_trials,
            num_obs=max(n_obs, 20),
            annualization_factor=ann_factor,
        )
        tf_eval["deflated_sharpe_ratio"] = dsr
        tf_eval["total_trials_penalized"] = total_trials

    # 4. GUARDAR RESULTADOS EN JSON Y CSV
    with open(REPORTS_DIR / "results_sma_system.json", "w", encoding="utf-8") as f:
        json.dump(all_study_results, f, indent=2)

    # Generar tabla resumen CSV
    summary_rows = []
    for exp_key, exp_data in all_study_results["experiments"].items():
        fin = exp_data.get("finalist_evaluation", {})
        tf_eval = fin.get("test_final", {})
        val_eval = fin.get("validation", {})
        p = fin.get("params", {})

        summary_rows.append({
            "Asset": exp_data["asset"],
            "Timeframe": exp_data["timeframe"],
            "Num_SMAs": p.get("num_smas"),
            "Fast_SMA": p.get("fast_sma"),
            "Mid_SMA": p.get("mid_sma") if p.get("num_smas") == 3 else "N/A",
            "Slow_SMA": p.get("slow_sma"),
            "MACD": f"({p.get('macd_fast')},{p.get('macd_slow')},{p.get('macd_signal')})" if p.get("macd_fast") else "N/A",
            "RSI_Period": p.get("rsi_period"),
            "ATR_k": p.get("atr_k"),
            "TP_m": p.get("tp_m"),
            "Val_Sharpe": val_eval.get("strategy_sharpe"),
            "Test_Sharpe": tf_eval.get("sharpe"),
            "Test_Net_PnL": tf_eval.get("net_pnl_usd"),
            "Test_Trades": tf_eval.get("trades"),
            "Test_WinRate": tf_eval.get("win_rate"),
            "Test_ProfitFactor": tf_eval.get("profit_factor"),
            "Test_MaxDrawdown": tf_eval.get("max_drawdown"),
            "Deflated_Sharpe": tf_eval.get("deflated_sharpe_ratio"),
            "BuyAndHold_Sharpe": tf_eval.get("buy_and_hold_sharpe"),
            "Solo_SMA_Sharpe": tf_eval.get("solo_sma_sharpe"),
        })

    summary_df = pd.DataFrame(summary_rows)
    csv_path = TABLES_DIR / "summary_multi_asset_results.csv"
    summary_df.to_csv(csv_path, index=False)
    logger.info(f"Tabla resumen guardada en {csv_path}")


if __name__ == "__main__":
    main()
