"""Evaluación cuantitativa completa en temporalidades de 15 minutos (15m) y 5 minutos (5m)
para los cuatro activos: ES, NQ, BTC-USDT y ETH-USDT.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import pandas as pd
import yaml

from src.data.resampler import resample_ohlcv_bars
from src.data.crypto_downloader import download_crypto_history
from src.backtest.engine_sma_confluence import StrategyParams, AssetCosts, run_sma_confluence_backtest
from src.analysis.grid_search import run_grid_search_for_asset, partition_data_60_20_20
from src.analysis.heatmaps import generate_stability_heatmap
from src.analysis.robustness import (
    compute_deflated_sharpe_ratio,
    evaluate_solo_sma_benchmark,
    evaluate_buy_and_hold_benchmark,
    run_cross_asset_evaluation,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("short_timeframes")

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports")
TABLES_DIR = Path("reports/tables")
CONFIG_PATH = Path("config/multi_asset_costs.yaml")


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def prepare_short_timeframe_data():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    target_tfs = ["15m", "5m"]

    # 1. ES y NQ: Remuestreo desde 1m crudo
    for sym in ["ES", "NQ"]:
        needed_tfs = [tf for tf in target_tfs if not (PROCESSED_DIR / f"{sym}_{tf}.parquet").exists()]
        if needed_tfs:
            raw_p = RAW_DIR / f"{sym}.v.0_ohlcv_1m.parquet"
            logger.info(f"Cargando 1m para {sym}...")
            df_1m = pd.read_parquet(raw_p, columns=["ts_event", "open", "high", "low", "close", "volume"])
            for tf in needed_tfs:
                out_p = PROCESSED_DIR / f"{sym}_{tf}.parquet"
                logger.info(f"Generando {out_p} ({sym} {tf})...")
                df_tf = resample_ohlcv_bars(df_1m, target_timeframe=tf, asset_family="indices")
                df_tf.to_parquet(out_p, index=False)
                logger.info(f"Guardado {out_p} ({len(df_tf)} barras)")
        else:
            logger.info(f"Ya existen parquets remuestreados para {sym}")

    # 2. BTC y ETH: Descarga de 5m (y 15m si falta)
    for csym in ["BTC-USDT", "ETH-USDT"]:
        clean = csym.replace("-", "_")
        for tf in target_tfs:
            out_p = PROCESSED_DIR / f"{clean}_{tf}.parquet"
            raw_p = RAW_DIR / f"{csym}_{tf}.parquet"
            if not raw_p.exists():
                logger.info(f"Descargando {csym} ({tf}) desde BingX...")
                # 5m y 15m últimos meses disponibles en API pública
                download_crypto_history(symbol=csym, interval=tf, start_date="2024-01-01")
            
            if not out_p.exists() and raw_p.exists():
                df_c = pd.read_parquet(raw_p)
                df_c.to_parquet(out_p, index=False)
                logger.info(f"Copiado a processed: {out_p} ({len(df_c)} barras)")


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    prepare_short_timeframe_data()
    cfg = load_config()
    asset_cfgs = cfg["assets"]

    experiments = [
        ("ES", "15m"),
        ("NQ", "15m"),
        ("BTC-USDT", "15m"),
        ("ETH-USDT", "15m"),
        ("ES", "5m"),
        ("NQ", "5m"),
        ("BTC-USDT", "5m"),
        ("ETH-USDT", "5m"),
    ]

    all_results = {
        "title": "Evaluación Cuantitativa en Temporalidades Cortas (15m y 5m)",
        "experiments": {},
        "total_combinations_tested": 0,
    }

    total_trials = 0
    summary_rows = []

    for asset_name, tf in experiments:
        logger.info(f"==================================================")
        logger.info(f"EVALUANDO: {asset_name} ({tf})")
        logger.info(f"==================================================")

        file_prefix = asset_name.replace("-", "_")
        parquet_file = PROCESSED_DIR / f"{file_prefix}_{tf}.parquet"
        if not parquet_file.exists():
            logger.warning(f"Falta archivo {parquet_file}. Saltando.")
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

        grid_res = run_grid_search_for_asset(df, asset_name, tf, costs, min_trades=50)
        total_trials += grid_res["total_combinations_tested"]

        # Mapa de calor de estabilidad
        heatmap_p = generate_stability_heatmap(
            grid_results=grid_res["all_train_results"],
            asset_name=asset_name,
            timeframe=tf,
            fixed_num_smas=2,
            metric="sharpe",
        )

        train_df, val_df, test_df = partition_data_60_20_20(df)
        top_finalists = grid_res["top_finalists_selected_on_val"]
        best_finalist = top_finalists[0] if top_finalists else None

        if best_finalist:
            p_obj = StrategyParams(**best_finalist["params"])
            # Evaluación en Test Final
            test_res = run_sma_confluence_backtest(test_df, p_obj, costs)
            solo_test = evaluate_solo_sma_benchmark(test_df, p_obj, costs)
            bnh_test = evaluate_buy_and_hold_benchmark(test_df, costs)

            # Deflated Sharpe
            dsr = compute_deflated_sharpe_ratio(
                observed_sharpe=test_res["sharpe"],
                num_trials=grid_res["total_combinations_tested"],
                num_obs=max(test_res["n_trades"], 20),
                annualization_factor=costs.annualization_factor,
            )

            p = best_finalist["params"]
            summary_rows.append({
                "Asset": asset_name,
                "Timeframe": tf,
                "Num_SMAs": p.get("num_smas"),
                "Fast_SMA": p.get("fast_sma"),
                "Mid_SMA": p.get("mid_sma") if p.get("num_smas") == 3 else "N/A",
                "Slow_SMA": p.get("slow_sma"),
                "MACD": f"({p.get('macd_fast')},{p.get('macd_slow')},{p.get('macd_signal')})",
                "RSI_Period": p.get("rsi_period"),
                "ATR_k": p.get("atr_k"),
                "TP_m": p.get("tp_m"),
                "Val_Sharpe": best_finalist["val_sharpe"],
                "Test_Trades": test_res["n_trades"],
                "Test_Net_PnL": test_res["net_pnl_usd"],
                "Test_Sharpe": test_res["sharpe"],
                "Test_WinRate": test_res["win_rate"],
                "Test_ProfitFactor": test_res["profit_factor"],
                "Test_MaxDrawdown": test_res["max_drawdown"],
                "Deflated_Sharpe": dsr,
                "BuyAndHold_Sharpe": bnh_test["sharpe"],
                "Solo_SMA_Sharpe": solo_test["sharpe"],
            })

            all_results["experiments"][f"{asset_name}_{tf}"] = {
                "asset": asset_name,
                "timeframe": tf,
                "best_params": p,
                "val_sharpe": best_finalist["val_sharpe"],
                "test_final": test_res,
                "deflated_sharpe": dsr,
                "benchmarks": {
                    "solo_sma": solo_test,
                    "buy_and_hold": bnh_test,
                },
            }

    all_results["total_combinations_tested"] = total_trials

    # Guardar JSON y CSV
    with open(REPORTS_DIR / "results_short_timeframes.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)

    df_summary = pd.DataFrame(summary_rows)
    csv_out = TABLES_DIR / "summary_short_timeframes.csv"
    df_summary.to_csv(csv_out, index=False)
    logger.info(f"Resultados de temporalidades cortas guardados en {csv_out}")


if __name__ == "__main__":
    main()
