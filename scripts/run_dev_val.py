"""Ejecución de la Fase 4: Evaluación sobre Desarrollo y Validación.
NO toca la partición final (holdout).
"""
import json
import logging
from pathlib import Path
from src.analysis.runner import run_stage_evaluation

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPORTS_DIR = Path("reports")


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=== EVALUANDO PARTICIÓN DE DESARROLLO (2018–2021) ===")
    dev_results = run_stage_evaluation("development", boot_reps=10000, perm_reps=10000)
    with open(REPORTS_DIR / "dev_results.json", "w", encoding="utf-8") as f:
        json.dump(dev_results, f, indent=2)
    logger.info("Resultados de Desarrollo guardados en reports/dev_results.json")

    logger.info("=== EVALUANDO PARTICIÓN DE VALIDACIÓN (2022–2023) ===")
    val_results = run_stage_evaluation("validation", boot_reps=10000, perm_reps=10000)
    with open(REPORTS_DIR / "val_results.json", "w", encoding="utf-8") as f:
        json.dump(val_results, f, indent=2)
    logger.info("Resultados de Validación guardados en reports/val_results.json")


if __name__ == "__main__":
    main()
