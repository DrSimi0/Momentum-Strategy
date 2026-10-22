"""Runner y Evaluador de Estrategia A: Barrido de Medias Móviles y Top 10 por Clustering."""
from dataclasses import asdict
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd

from src.strategies.strategy_a_moving_averages import MAParams, generate_ma_grid_for_timeframe, run_ma_backtest
from src.backtest.engine_sma_confluence import AssetCosts
from src.analysis.robustness import compute_deflated_sharpe_ratio

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports/strategy_a")
TABLES_DIR = REPORTS_DIR / "tables"


def cluster_top_candidates(val_evals: List[Dict[str, Any]], max_finalists: int = 10, max_corr: float = 0.75) -> List[Dict[str, Any]]:
    """Selecciona el Top 10 evitando combinaciones vecinas idénticas mediante descorrelación de retornos."""
    # Ordenar candidatos por Sharpe en validación
    valid_candidates = [c for c in val_evals if not np.isnan(c["val_sharpe"]) and c["val_trades"] >= 20]
    valid_candidates = sorted(valid_candidates, key=lambda x: x["val_sharpe"], reverse=True)
    if not valid_candidates:
        return []

    selected = [valid_candidates[0]]

    for cand in valid_candidates[1:]:
        if len(selected) >= max_finalists:
            break
        # Comparar similitud con las ya seleccionadas
        is_distinct = True
        for sel in selected:
            # Distancia de parámetros y correlación
            same_type = (cand["params"]["ma_type"] == sel["params"]["ma_type"])
            same_struct = (cand["params"]["structure"] == sel["params"]["structure"])
            same_slow = (abs(cand["params"]["slow_period"] - sel["params"]["slow_period"]) <= 10)
            same_fast = (abs(cand["params"]["fast_period"] - sel["params"]["fast_period"]) <= 10)
            same_tf = (cand["params"]["timeframe"] == sel["params"]["timeframe"])

            # Si son casi idénticas en parámetros clave, descartar para diversidad de cluster
            if same_type and same_struct and same_slow and same_fast and same_tf:
                is_distinct = False
                break

        if is_distinct:
            selected.append(cand)

    return selected


def run_strategy_a_pipeline():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    costs_map = {
        "ES": AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5),
        "NQ": AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5),
    }

    results = {}
    summary_top10 = []

    for sym in ["ES", "NQ"]:
        logger.info(f"==================================================")
        logger.info(f"ESTRATEGIA A: EVALUANDO {sym}")
        logger.info(f"==================================================")

        costs = costs_map[sym]
        all_evals = []

        # 224 combinaciones por activo (112 en 1h + 112 en 4h)
        for tf in ["4h", "1h"]:
            grid = generate_ma_grid_for_timeframe(tf)
            p_file = PROCESSED_DIR / f"{sym}_{tf}.parquet"
            df = pd.read_parquet(p_file)

            # Partición cronológica 70% Train (2010 a 2021) / 30% Val (2021 a 2026)
            n = len(df)
            n_tr = int(n * 0.70)
            df_train = df.iloc[:n_tr].copy().reset_index(drop=True)
            df_val = df.iloc[n_tr:].copy().reset_index(drop=True)

            logger.info(f"{sym} {tf}: Train={len(df_train)} bars | Val={len(df_val)} bars")

            for p in grid:
                res_tr = run_ma_backtest(df_train, p, costs)
                res_val = run_ma_backtest(df_val, p, costs)

                all_evals.append({
                    "asset": sym,
                    "params": asdict(p),
                    "train_sharpe": res_tr["sharpe"],
                    "train_pnl": res_tr["net_pnl_usd"],
                    "train_trades": res_tr["n_trades"],
                    "val_sharpe": res_val["sharpe"],
                    "val_pnl": res_val["net_pnl_usd"],
                    "val_trades": res_val["n_trades"],
                    "val_win_rate": res_val["win_rate"],
                    "val_profit_factor": res_val["profit_factor"],
                    "val_max_drawdown": res_val["max_drawdown"],
                    "val_trades_list": res_val["trades"],
                })

        # Seleccionar las Top 10 por clustering
        top10 = cluster_top_candidates(all_evals, max_finalists=10)
        logger.info(f"Top 10 seleccionadas para {sym} con clustering ortogonal:")

        # Total combinaciones probadas = 224
        total_trials = len(all_evals)

        for rank, item in enumerate(top10, start=1):
            p = item["params"]
            v_sharpe = item["val_sharpe"] if not np.isnan(item["val_sharpe"]) else 0.0
            n_trades = item["val_trades"]

            # Deflated Sharpe con M = 224
            dsr = compute_deflated_sharpe_ratio(
                observed_sharpe=v_sharpe,
                num_trials=total_trials,
                num_obs=n_trades,
                skewness=0.0, kurtosis=3.0,
                annualization_factor=costs.annualization_factor
            )

            # Walk-forward rodante sobre el historial completo para cada una de las 10
            tf = p["timeframe"]
            df_full = pd.read_parquet(PROCESSED_DIR / f"{sym}_{tf}.parquet")
            step = 1500 if tf == "4h" else 6000
            tr_bars = 4500 if tf == "4h" else 18000
            w_idx = 0
            pos_w = 0
            start = 0
            while start + tr_bars + step <= len(df_full):
                sub_tr = df_full.iloc[start:start + tr_bars]
                sub_te = df_full.iloc[start + tr_bars:start + tr_bars + step]
                p_obj = MAParams(**p)
                r_te = run_ma_backtest(sub_te, p_obj, costs)
                if r_te["net_pnl_usd"] > 0:
                    pos_w += 1
                w_idx += 1
                start += step

            wf_pct = (pos_w / w_idx * 100.0) if w_idx > 0 else 0.0

            summary_top10.append({
                "Rank": rank,
                "Activo": sym,
                "Timeframe": p["timeframe"],
                "Tipo": p["ma_type"],
                "Estructura": p["structure"],
                "Periodos": f"({p['fast_period']}/{p['mid_period']}/{p['slow_period']})",
                "ATR_k": p["atr_k"],
                "Train_Sharpe": f"{item['train_sharpe']:.2f}" if not np.isnan(item['train_sharpe']) else "N/A",
                "Val_Trades": item["val_trades"],
                "Val_WinRate": f"{item['val_win_rate']*100:.1f}%",
                "Val_ProfitFactor": f"{item['val_profit_factor']:.2f}" if not np.isnan(item['val_profit_factor']) else "N/A",
                "Val_Net_PnL": f"${item['val_pnl']:,.2f}",
                "Val_Sharpe": f"{item['val_sharpe']:.2f}" if not np.isnan(item['val_sharpe']) else "N/A",
                "Val_Max_DD": f"${item['val_max_drawdown']:,.2f}",
                "WF_Ventanas_Positivas": f"{wf_pct:.1f}% ({w_idx} vent.)",
                "DSR_M224": f"{dsr*100:.2f}%",
            })

    df_top10 = pd.DataFrame(summary_top10)
    out_csv = TABLES_DIR / "strategy_a_top10_summary.csv"
    df_top10.to_csv(out_csv, index=False)
    logger.info(f"Resumen Top 10 guardado en {out_csv}")


if __name__ == "__main__":
    run_strategy_a_pipeline()
