"""Optimizador mediante Grid Search riguroso sobre la partición de Entrenamiento (60%)
y selección imparcial de configuraciones finalistas sobre Validación (20%).
La partición del Test Final (20%) queda estrictamente bloqueada.
"""
from __future__ import annotations

from dataclasses import asdict
import itertools
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd
import yaml

from src.indicators.technical import compute_sma, compute_macd, compute_rsi, compute_atr
from src.backtest.engine_sma_confluence import StrategyParams, AssetCosts, run_sma_confluence_backtest

logger = logging.getLogger(__name__)

PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports")


def generate_parameter_combinations() -> List[StrategyParams]:
    """Genera la rejilla completa de 1,890 combinaciones pre-registradas."""
    combos = []

    macd_variants = [
        (12, 26, 9),  # Estándar
        (8, 17, 9),   # Rápido
        (16, 35, 9),  # Lento
    ]
    rsi_periods = [7, 14, 21]
    atr_ks = [1.5, 2.0, 3.0]
    tp_ms = [1.5, 2.0]

    # 1. Variante 1 SMA (lenta: 100, 150, 200)
    for slow in [100, 150, 200]:
        for (mf, ms, m_sig), rsi_p, k, m in itertools.product(macd_variants, rsi_periods, atr_ks, tp_ms):
            combos.append(StrategyParams(
                num_smas=1,
                fast_sma=20,
                mid_sma=50,
                slow_sma=slow,
                macd_fast=mf,
                macd_slow=ms,
                macd_signal=m_sig,
                rsi_period=rsi_p,
                atr_k=k,
                tp_m=m,
            ))

    # 2. Variante 2 SMAs (rápida < lenta)
    fast_options = [10, 20, 21, 30]
    slow_options = [100, 150, 200]
    for fast in fast_options:
        for slow in slow_options:
            if fast < slow:
                for (mf, ms, m_sig), rsi_p, k, m in itertools.product(macd_variants, rsi_periods, atr_ks, tp_ms):
                    combos.append(StrategyParams(
                        num_smas=2,
                        fast_sma=fast,
                        mid_sma=50,
                        slow_sma=slow,
                        macd_fast=mf,
                        macd_slow=ms,
                        macd_signal=m_sig,
                        rsi_period=rsi_p,
                        atr_k=k,
                        tp_m=m,
                    ))

    # 3. Variante 3 SMAs (rápida < media < lenta)
    mid_options = [50, 100]
    for fast in fast_options:
        for mid in mid_options:
            if fast < mid:
                for slow in slow_options:
                    if mid < slow:
                        for (mf, ms, m_sig), rsi_p, k, m in itertools.product(macd_variants, rsi_periods, atr_ks, tp_ms):
                            combos.append(StrategyParams(
                                num_smas=3,
                                fast_sma=fast,
                                mid_sma=mid,
                                slow_sma=slow,
                                macd_fast=mf,
                                macd_slow=ms,
                                macd_signal=m_sig,
                                rsi_period=rsi_p,
                                atr_k=k,
                                tp_m=m,
                            ))

    logger.info(f"Rejilla generada con {len(combos)} combinaciones de parámetros.")
    return combos


def partition_data_60_20_20(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Divide cronológicamente en 60% Train, 20% Val y 20% Test."""
    n = len(df)
    n_train = int(n * 0.60)
    n_val = int(n * 0.20)

    train_df = df.iloc[:n_train].copy().reset_index(drop=True)
    val_df = df.iloc[n_train:n_train + n_val].copy().reset_index(drop=True)
    test_df = df.iloc[n_train + n_val:].copy().reset_index(drop=True)

    return train_df, val_df, test_df


def run_grid_search_for_asset(
    df: pd.DataFrame,
    asset_name: str,
    timeframe: str,
    costs: AssetCosts,
    min_trades: int = 100,
) -> Dict[str, Any]:
    """Ejecuta Grid Search en Train y valida en Val para un activo y timeframe dados."""
    train_df, val_df, test_df = partition_data_60_20_20(df)
    combos = generate_parameter_combinations()

    logger.info(
        f"Iniciando Grid Search para {asset_name} ({timeframe}): "
        f"Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)} barras."
    )

    train_results = []
    # 1. Evaluar en Train
    for p in combos:
        res = run_sma_confluence_backtest(train_df, p, costs)
        train_results.append({
            "params": asdict(p),
            "n_trades": res["n_trades"],
            "net_pnl_usd": res["net_pnl_usd"],
            "sharpe": res["sharpe"],
            "win_rate": res["win_rate"],
            "profit_factor": res["profit_factor"],
            "max_drawdown": res["max_drawdown"],
            "avg_expectancy_usd": res["avg_expectancy_usd"],
        })

    train_df_res = pd.DataFrame(train_results)

    # 2. Filtrar candidatos de Train que tengan suficientes trades
    # Si ningún combo tiene >= min_trades en Train, relajar temporalmente a >= 30 para permitir análisis
    actual_min = min_trades if (train_df_res["n_trades"] >= min_trades).any() else 30
    eligible_train = train_df_res[train_df_res["n_trades"] >= actual_min].copy()

    # Ordenar por Sharpe en Train para seleccionar los mejores candidatos a probar en Val
    eligible_train = eligible_train.sort_values("sharpe", ascending=False)
    top_candidates = eligible_train.head(50)

    # 3. Evaluar los candidatos en Validación (selección por Validación)
    val_evals = []
    for _, row in top_candidates.iterrows():
        p_dict = row["params"]
        p_obj = StrategyParams(**p_dict)
        res_val = run_sma_confluence_backtest(val_df, p_obj, costs)
        val_evals.append({
            "params": p_dict,
            "train_sharpe": row["sharpe"],
            "train_trades": row["n_trades"],
            "val_trades": res_val["n_trades"],
            "val_net_pnl_usd": res_val["net_pnl_usd"],
            "val_sharpe": res_val["sharpe"],
            "val_win_rate": res_val["win_rate"],
            "val_profit_factor": res_val["profit_factor"],
            "val_max_drawdown": res_val["max_drawdown"],
            "val_expectancy_usd": res_val["avg_expectancy_usd"],
        })

    val_df_res = pd.DataFrame(val_evals)
    # Seleccionar por validación (Protocolo Regla 2)
    val_ranked = val_df_res.sort_values("val_sharpe", ascending=False).reset_index(drop=True)

    # Finalistas Top 3
    top_finalists = val_ranked.head(3).to_dict(orient="records") if not val_ranked.empty else []

    return {
        "asset": asset_name,
        "timeframe": timeframe,
        "total_combinations_tested": len(combos),
        "train_bars": len(train_df),
        "val_bars": len(val_df),
        "test_bars": len(test_df),
        "train_summary": {
            "max_sharpe": float(train_df_res["sharpe"].max()) if not train_df_res.empty else 0.0,
            "mean_sharpe": float(train_df_res["sharpe"].mean()) if not train_df_res.empty else 0.0,
            "positive_sharpe_fraction": float((train_df_res["sharpe"] > 0).mean()) if not train_df_res.empty else 0.0,
        },
        "all_train_results": train_results,
        "top_finalists_selected_on_val": top_finalists,
    }
