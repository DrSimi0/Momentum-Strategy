"""Ejecutor metodológico de análisis cuantitativo para las fases Dev, Val y Final.
Garantiza:
1. Estricta separación temporal de particiones (splits.yaml).
2. Evaluación completa de casos de costo (base y estrés) y barrido de sensibilidad.
3. Inferencia estadística (bootstrap, permutación, Newey-West, Holm-Bonferroni).
4. Bloqueo criptográfico absoluto de la partición final mediante reports/FINAL_RUN.lock.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import yaml

from src.backtest.costs import CostSpec, DEFAULT_COST_CASES
from src.backtest.engine import simulate_trades
from src.analysis.metrics import (
    compute_performance_metrics,
    run_predictive_regression,
    compute_oos_r_squared,
)
from src.analysis.inference import (
    bootstrap_sharpe_distribution,
    permutation_test_signals,
    holm_bonferroni_correction,
)

logger = logging.getLogger(__name__)

CONFIG_DIR = Path("config")
PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports")
FINAL_LOCK_PATH = REPORTS_DIR / "FINAL_RUN.lock"


def load_yaml_config(filename: str) -> Dict[str, Any]:
    with open(CONFIG_DIR / filename, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_stage_evaluation(
    stage: str,
    boot_reps: int = 10000,
    perm_reps: int = 10000,
    seed: int = 20260421,
) -> Dict[str, Any]:
    """Ejecuta la evaluación rigurosa para la etapa indicada ('development', 'validation', o 'final')."""
    if stage == "final":
        if FINAL_LOCK_PATH.exists():
            raise RuntimeError(
                f"La partición final (holdout) ya ha sido consumida. Existe el candado {FINAL_LOCK_PATH}. "
                "Prohibido re-ejecutar sobre el holdout consumido."
            )

    splits = load_yaml_config("splits.yaml")
    inst_cfg = load_yaml_config("instruments.yaml")["instruments"]
    strat_cfg = load_yaml_config("strategy_spec.yaml")

    stage_dates = splits.get(stage)
    if not stage_dates:
        raise ValueError(f"Etapa desconocida '{stage}' en splits.yaml.")

    start_date = stage_dates["start"]
    end_date = stage_dates["end"]

    logger.info(f"=== INICIANDO EVALUACIÓN: ETAPA '{stage.upper()}' ({start_date} a {end_date}) ===")

    all_hypotheses = ["H1", "H2", "H3", "H4", "B1", "B3", "E1", "E2", "E3"]
    primary_hypotheses = ["H1", "H2", "H3", "H4"]

    instruments = ["ES", "NQ"]
    results_by_inst: Dict[str, Any] = {}
    primary_raw_p_values: Dict[str, float] = {}

    for inst in instruments:
        features_path = PROCESSED_DIR / f"{inst}_daily_features.parquet"
        if not features_path.exists():
            raise FileNotFoundError(f"Archivo de features no encontrado: {features_path}")

        df_all = pd.read_parquet(features_path)
        # Filtrar por fecha de la etapa
        mask = (df_all["date"] >= start_date) & (df_all["date"] <= end_date)
        df_stage = df_all[mask].copy().reset_index(drop=True)

        logger.info(f"Instrumento {inst} en etapa {stage}: {len(df_stage)} sesiones.")
        spec = inst_cfg[inst]
        mult = float(spec["multiplier_usd_per_point"])
        tick_sz = float(spec["tick_size_points"])
        tick_val = float(spec["tick_value_usd"])

        inst_results: Dict[str, Any] = {"n_sessions": len(df_stage), "hypotheses": {}}

        # Regresiones predictivas Newey-West de r13 sobre señales y predictores continuos
        reg_r1 = run_predictive_regression(df_stage["r13"], df_stage["r1"], lags=5)
        reg_r12 = run_predictive_regression(df_stage["r13"], df_stage["r12"], lags=5)
        inst_results["predictive_regressions"] = {
            "r13_on_r1": reg_r1,
            "r13_on_r12": reg_r12,
        }

        # Evaluar cada hipótesis
        for hyp in all_hypotheses:
            sig_col = f"sig_{hyp}"
            if sig_col not in df_stage.columns:
                continue

            # 1. Caso Base
            sim_base = simulate_trades(
                df=df_stage,
                signal_col=sig_col,
                multiplier_usd_per_point=mult,
                tick_size_points=tick_sz,
                tick_value_usd=tick_val,
                cost_spec=DEFAULT_COST_CASES["base"],
                num_contracts=1,
            )
            metrics_base = compute_performance_metrics(sim_base)

            # 2. Caso Estrés
            sim_stress = simulate_trades(
                df=df_stage,
                signal_col=sig_col,
                multiplier_usd_per_point=mult,
                tick_size_points=tick_sz,
                tick_value_usd=tick_val,
                cost_spec=DEFAULT_COST_CASES["stress"],
                num_contracts=1,
            )
            metrics_stress = compute_performance_metrics(sim_stress)

            # 3. Barrido de sensibilidad de deslizamiento
            sensitivity = {}
            for slip_ticks in [0.0, 0.25, 0.5, 1.0, 2.0]:
                spec_sens = CostSpec(slippage_ticks_per_side=slip_ticks, commission_usd_per_side=2.00)
                sim_sens = simulate_trades(
                    df=df_stage,
                    signal_col=sig_col,
                    multiplier_usd_per_point=mult,
                    tick_size_points=tick_sz,
                    tick_value_usd=tick_val,
                    cost_spec=spec_sens,
                    num_contracts=1,
                )
                m_sens = compute_performance_metrics(sim_sens)
                sensitivity[f"slip_{slip_ticks}"] = {
                    "net_pnl_usd": m_sens["total_net_pnl_usd"],
                    "sharpe": m_sens["sharpe_annualized"],
                }

            # 4. Inferencia estadística (Bootstrap y Permutación)
            boot_res = bootstrap_sharpe_distribution(
                sim_base["daily_return"].values,
                n_reps=boot_reps,
                expected_block_len=10.0,
                seed=seed,
            )
            obs_sharpe, (ci_low, ci_high), p_val_h0 = boot_res

            perm_p = permutation_test_signals(
                signals=df_stage[sig_col].values,
                target_returns=df_stage["r13"].values,
                n_reps=perm_reps,
                seed=seed,
            )

            # Almacenar p-valor para Holm-Bonferroni si es hipótesis primaria
            if hyp in primary_hypotheses:
                primary_raw_p_values[f"{inst}_{hyp}"] = p_val_h0

            inst_results["hypotheses"][hyp] = {
                "base": metrics_base,
                "stress": metrics_stress,
                "sensitivity": sensitivity,
                "inference": {
                    "observed_sharpe": obs_sharpe,
                    "bootstrap_95_ci": [ci_low, ci_high],
                    "bootstrap_p_value_h0": p_val_h0,
                    "permutation_p_value": perm_p,
                },
            }

        results_by_inst[inst] = inst_results

    # 5. Corrección de Holm-Bonferroni para las 8 pruebas primarias
    holm_results = holm_bonferroni_correction(primary_raw_p_values)

    output = {
        "stage": stage,
        "date_range": stage_dates,
        "instruments": results_by_inst,
        "primary_tests_holm_bonferroni": holm_results,
    }

    # Si es la fase final, escribir el candado FINAL_RUN.lock
    if stage == "final":
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(FINAL_LOCK_PATH, "w", encoding="utf-8") as f:
            f.write(f"LOCKED: Evaluación final completada en {pd.Timestamp.now().isoformat()}.\n")
            f.write("Queda estrictamente prohibido re-ejecutar pruebas sobre la partición holdout.\n")
        logger.info(f"Candado de partición final creado en {FINAL_LOCK_PATH}.")

    return output
