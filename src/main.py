"""Punto de entrada unificado y reproducible para todas las etapas del proyecto v4.
Sintaxis: python -m src.main --stage {data,features,backtest,analysis,final}
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys

from src.data.databento_client import submit_and_download_batch, update_data_metadata, estimate_total_cost
from src.data.validate import validate_ohlcv_invariants
from src.features.process import process_symbol_features
from src.analysis.runner import run_stage_evaluation, FINAL_LOCK_PATH
from scripts.run_final import evaluate_acceptance_criteria
from scripts.generate_figures import main as generate_figures_main

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("main")

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports")


def stage_data():
    logger.info("=== ETAPA: DATA (Descarga y Validación de Datos Crudos) ===")
    es_raw = RAW_DIR / "ES.v.0_ohlcv_1m.parquet"
    nq_raw = RAW_DIR / "NQ.v.0_ohlcv_1m.parquet"

    if es_raw.exists() and nq_raw.exists():
        logger.info("Archivos de datos ya presentes en data/raw. Validando invariantes OHLCV...")
        import pandas as pd
        validate_ohlcv_invariants(pd.read_parquet(es_raw))
        validate_ohlcv_invariants(pd.read_parquet(nq_raw))
        logger.info("Validación de datos existentes completada exitosamente.")
    else:
        logger.info("Descargando datos históricos desde Databento...")
        downloaded = submit_and_download_batch(
            symbols=["ES.v.0", "NQ.v.0"],
            start_date="2017-12-15",
            end_date="2026-10-20",
        )
        logger.info(f"Descarga finalizada: {downloaded}")


def stage_features():
    logger.info("=== ETAPA: FEATURES (Generación de Features y Señales Diarias) ===")
    es_raw = RAW_DIR / "ES.v.0_ohlcv_1m.parquet"
    nq_raw = RAW_DIR / "NQ.v.0_ohlcv_1m.parquet"
    if not es_raw.exists() or not nq_raw.exists():
        logger.error("Faltan archivos en data/raw/. Ejecute primero: python -m src.main --stage data")
        sys.exit(1)

    df_es = process_symbol_features(es_raw, "ES")
    df_nq = process_symbol_features(nq_raw, "NQ")
    logger.info(f"Features generadas exitosamente: ES ({len(df_es)} sesiones), NQ ({len(df_nq)} sesiones).")


def stage_backtest():
    logger.info("=== ETAPA: BACKTEST (Simulación de Desarrollo y Validación) ===")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    dev_res = run_stage_evaluation("development", boot_reps=1000, perm_reps=1000)
    val_res = run_stage_evaluation("validation", boot_reps=1000, perm_reps=1000)
    with open(REPORTS_DIR / "dev_results.json", "w", encoding="utf-8") as f:
        json.dump(dev_res, f, indent=2)
    with open(REPORTS_DIR / "val_results.json", "w", encoding="utf-8") as f:
        json.dump(val_res, f, indent=2)
    logger.info("Simulaciones de desarrollo y validación completadas y guardadas.")


def stage_analysis():
    logger.info("=== ETAPA: ANALYSIS (Generación de Figuras y Análisis Avanzado) ===")
    generate_figures_main()
    logger.info("Figuras científicas generadas exitosamente en reports/figures/.")


def stage_final():
    logger.info("=== ETAPA: FINAL (Evaluación de Partición Holdout con Candado) ===")
    if FINAL_LOCK_PATH.exists():
        logger.warning(
            f"El candado {FINAL_LOCK_PATH} ya existe. La prueba final ya fue ejecutada sobre el holdout consumido."
        )
        logger.info("Cargando resultados previos desde reports/results.json...")
        with open(REPORTS_DIR / "results.json", "r", encoding="utf-8") as f:
            res = json.load(f)
        for k, v in res.get("acceptance_criteria_evaluation", {}).items():
            logger.info(f"{k}: Veredicto={v['verdict']}, Sharpe={v['A2_base_sharpe']['value']:.2f}")
        return

    # Si no existe, ejecutar la prueba final
    from scripts.run_final import main as run_final_main
    run_final_main()
    logger.info("Evaluación final completada exitosamente.")


def main():
    parser = argparse.ArgumentParser(
        description="Sistema de evaluación rigurosa de momentum intradía en ES y NQ"
    )
    parser.add_argument(
        "--stage",
        required=True,
        choices=["data", "features", "backtest", "analysis", "final"],
        help="Etapa a ejecutar del pipeline reproducible",
    )
    args = parser.parse_args()

    stages = {
        "data": stage_data,
        "features": stage_features,
        "backtest": stage_backtest,
        "analysis": stage_analysis,
        "final": stage_final,
    }

    stages[args.stage]()


if __name__ == "__main__":
    main()
