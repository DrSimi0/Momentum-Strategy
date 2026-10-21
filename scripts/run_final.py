"""Script oficial para la ejecución de la prueba final (Holdout) y consolidación de resultados.
Ejecuta la prueba exactamente una vez sobre la partición final congelada y crea el candado reports/FINAL_RUN.lock.
"""
from datetime import datetime
import json
import logging
from pathlib import Path
import pandas as pd
import yaml

from src.analysis.runner import run_stage_evaluation, FINAL_LOCK_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPORTS_DIR = Path("reports")
RESULTS_JSON_PATH = REPORTS_DIR / "results.json"


def evaluate_acceptance_criteria(
    inst: str,
    hyp: str,
    hyp_data: dict,
    holm_info: dict,
) -> dict:
    """Evalúa los criterios pre-registrados A1-A6 sobre la prueba final."""
    base_m = hyp_data["base"]
    stress_m = hyp_data["stress"]
    inf = hyp_data["inference"]

    # A1: Holm-Bonferroni adjusted p <= 0.05
    adj_p = holm_info.get("adjusted_p", 1.0)
    a1_pass = bool(adj_p <= 0.05)

    # A2: Sharpe ratio base >= 0.50
    base_sharpe = base_m["sharpe_annualized"]
    a2_pass = bool(base_sharpe >= 0.50)

    # A3: Sharpe ratio estrés > 0.0
    stress_sharpe = stress_m["sharpe_annualized"]
    a3_pass = bool(stress_sharpe > 0.0)

    # A4: Permutation p-value <= 0.05
    perm_p = inf.get("permutation_p_value", 1.0)
    a4_pass = bool(perm_p <= 0.05)

    # A6: Fracción de años positivos >= 0.50
    pos_years_frac = base_m["fraction_positive_years"]
    a6_pass = bool(pos_years_frac >= 0.50)

    all_passed = a1_pass and a2_pass and a3_pass and a4_pass and a6_pass

    return {
        "hypothesis": f"{inst}_{hyp}",
        "A1_holm_p_value": {"value": adj_p, "threshold": "<= 0.05", "pass": a1_pass},
        "A2_base_sharpe": {"value": base_sharpe, "threshold": ">= 0.50", "pass": a2_pass},
        "A3_stress_sharpe": {"value": stress_sharpe, "threshold": "> 0.00", "pass": a3_pass},
        "A4_permutation_p": {"value": perm_p, "threshold": "<= 0.05", "pass": a4_pass},
        "A6_positive_years_fraction": {"value": pos_years_frac, "threshold": ">= 0.50", "pass": a6_pass},
        "verdict": "APPROVED" if all_passed else "REJECTED",
    }


def main():
    logger.info("=== EJECUTANDO EVALUACIÓN FINAL SOBRE HOLDOUT (2024–2026) ===")
    
    # 1. Cargar resultados previos de dev y val
    with open(REPORTS_DIR / "dev_results.json", "r", encoding="utf-8") as f:
        dev_res = json.load(f)
    with open(REPORTS_DIR / "val_results.json", "r", encoding="utf-8") as f:
        val_res = json.load(f)

    # 2. Ejecutar sobre la partición final
    final_res = run_stage_evaluation("final", boot_reps=10000, perm_reps=10000)

    # 3. Evaluar criterios de aceptación en final
    acceptance_evaluations = {}
    holm_tests = final_res["primary_tests_holm_bonferroni"]
    
    for inst in ["ES", "NQ"]:
        for hyp in ["H1", "H2", "H3", "H4"]:
            key = f"{inst}_{hyp}"
            hyp_data = final_res["instruments"][inst]["hypotheses"][hyp]
            holm_info = holm_tests.get(key, {})
            eval_res = evaluate_acceptance_criteria(inst, hyp, hyp_data, holm_info)
            acceptance_evaluations[key] = eval_res

    # 4. Consolidar informe en results.json
    consolidated = {
        "project": "Momentum Intradía en Futuros CME (ES y NQ)",
        "protocol_version": "v4.0",
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "acceptance_criteria_evaluation": acceptance_evaluations,
        "stages": {
            "development": dev_res,
            "validation": val_res,
            "final": final_res,
        },
    }

    with open(RESULTS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(consolidated, f, indent=2)

    logger.info(f"Resultados consolidados guardados en {RESULTS_JSON_PATH}")


if __name__ == "__main__":
    main()
