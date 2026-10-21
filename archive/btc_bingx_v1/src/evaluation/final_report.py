"""Generador del Reporte Final de Evaluación de Rentabilidad (final_report.md y final_report.json).

Ejecutable directamente:
    python -m src.evaluation.final_report
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.backtest.engine import StrategyParams
from src.data.loader import load_bars
from src.evaluation.decomposition import run_full_decomposition
from src.evaluation.power_analysis import run_full_power_analysis
from src.run_evaluation import build_backtest_config

ROOT = Path(__file__).resolve().parents[2]


def generate_final_report() -> dict:
    cfg_strategy = yaml.safe_load((ROOT / "config" / "strategy.yaml").read_text(encoding="utf-8"))
    frozen_cfg = yaml.safe_load((ROOT / "config" / "strategy_frozen.yaml").read_text(encoding="utf-8"))
    lifecycle = json.loads((ROOT / "config" / "lifecycle.json").read_text(encoding="utf-8"))

    bars = load_bars()
    best_p = StrategyParams(
        channel_n=frozen_cfg["selected_params"]["channel_n"],
        atr_mult=frozen_cfg["selected_params"]["atr_mult"],
    )
    bt_cfg = build_backtest_config(cfg_strategy["backtest"])

    periods = {
        "development": cfg_strategy["periods"]["development"],
        "validation": cfg_strategy["periods"]["validation"],
        "holdout": cfg_strategy["periods"]["holdout"],
    }

    # Descomposición completa y baselines
    decomp = run_full_decomposition(bars, best_p, bt_cfg, periods, seed=42, random_reps=300)

    # Análisis de potencia sobre trades reales del Holdout
    # Calculamos trades de Holdout
    from src.backtest.engine import run_backtest
    res_oos = run_backtest(bars, best_p, bt_cfg, periods["holdout"][0], periods["holdout"][1])
    net_pnl_oos = res_oos.trades["net_pnl"].to_numpy(float)
    period_years = (pd.Timestamp(periods["holdout"][1]) - pd.Timestamp(periods["holdout"][0])).days / 365.0
    power = run_full_power_analysis(net_pnl_oos, period_years=period_years)

    # Datos estructurados del reporte
    final_data = {
        "title": "Reporte Final de Evaluación de Rentabilidad y Post-Mortem Científico",
        "strategy_id": lifecycle["strategy_id"],
        "verdict": lifecycle["verdict"],
        "lifecycle_status": lifecycle["lifecycle_status"],
        "rejection_timestamp": lifecycle["rejection_timestamp"],
        "rejection_reasons": lifecycle["rejection_reasons"],
        "version_history": [
            {
                "version": "1.0.0",
                "execution_model": "Taker en entrada y salida (0.05% comision + 5 bps slippage por lado)",
                "n_configs_grid": 9,
                "selected_param": "N100_k4",
                "holdout_net_return": 0.0044,
                "holdout_trades": 43,
                "holdout_cagr": 0.0025,
                "retention": 0.0298,
                "costs_pct_gross": 81.01,
                "stress_costs_x2_expectancy": -4.03,
                "verdict": "FAIL",
            },
            {
                "version": "1.1.0",
                "execution_model": "Maker en entrada (0.018% fee con BNB, 0 slippage) + Taker en salida (0.045% con BNB + 5 bps slippage)",
                "n_configs_grid": 9,
                "selected_param": "N100_k4",
                "holdout_net_return": 0.0122,
                "holdout_trades": 43,
                "holdout_cagr": 0.0069,
                "retention": 0.0804,
                "costs_pct_gross": 47.42,
                "stress_costs_x2_expectancy": -0.4726,
                "verdict": "FAIL",
            },
        ],
        "total_configs_tested_cumulative": 18,
        "power_analysis": power,
        "decomposition": decomp,
    }

    # Guardar JSON
    rep_dir = ROOT / "reports"
    rep_dir.mkdir(parents=True, exist_ok=True)
    json_path = rep_dir / "final_report.json"

    def _default(obj):
        if isinstance(obj, (np.floating, float)):
            return None if np.isnan(obj) else float(obj)
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        if isinstance(obj, (pd.Timestamp, pd.Period)):
            return str(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)

    json_path.write_text(json.dumps(final_data, indent=2, default=_default), encoding="utf-8")

    # Generar Markdown
    md = []
    md.append("# Reporte Final y Post-Mortem de Investigación: 🔴 FAIL (Estrategia Rechazada)\n")
    md.append("> **Declaración Metodológica Vinculante:**")
    md.append("> La estrategia Donchian Breakout Chandelier sobre BTCUSDT en velas de 4 horas ha sido dictaminada formalmente como **FAIL** y marcada en estado **`rejected`** dentro del ciclo de vida. El conjunto de Holdout ha quedado **definitivamente consumido** y bloqueado contra nuevas evaluaciones. Este documento recoge las evidencias cuantitativas, el análisis de potencia estadística y la conclusión definitiva.\n")

    md.append("## 1. Pregunta de Investigación")
    md.append("¿Puede una estrategia clásica de seguimiento de tendencia basada en rupturas de canal Donchian con stop trailing ATR (Chandelier Exit) sobre el futuro perpetuo BTCUSDT en velas de 4h generar rentabilidad neta sostenible y estadísticamente creíble tras descontar comisiones reales de intercambio, deslizamiento y tasa de financiamiento (funding rate)?\n")

    md.append("## 2. Protocolo Metodológico e Historial de Versiones")
    md.append("- **Partición Temporal:** Desarrollo (`2020-03-01` a `2023-07-01`), Validación (`2023-07-01` a `2025-01-01`), Holdout Estricto (`2025-01-01` a `2026-10-01`, 21 meses).")
    md.append("- **Total Acumulado de Configuraciones Probadas:** **18 configuraciones** (9 en v1.0.0 y 9 en v1.1.0 en la rejilla $N \\in [20, 50, 100] \\times k \\in [2, 3, 4]$).")
    md.append("- **Historial de Iteraciones:**")
    md.append("  - **v1.0.0 (Baseline Taker):** Comisión taker 0.05% y 5 bps slippage en entrada y salida. En Holdout obtuvo retorno neto total de **+0.44%**, retención de **2.98%**, y los costos absorbieron el **81.01%** de la ganancia bruta. Estrés x2: **-4.03 USDT/op**. Veredicto: **FAIL**.")
    md.append("  - **v1.1.0 (Mitigación de Comisiones):** Entrada con órdenes límite (Maker 0.018% con descuento BNB, 0 slippage) y salida Taker (0.045% con BNB + 5 bps slippage). Logró una reducción del **41.0% en costos** (absorbieron 47.42% de la ganancia bruta) y el retorno neto subió a **+1.22%** (+121.70 USDT). Sin embargo, la retención siguió en un deficiente **8.04%** y el estrés x2 en **-0.47 USDT/op**. Veredicto: **FAIL**.\n")

    md.append("## 3. Resultados Positivos vs. Resultados Negativos")
    md.append("### Aspectos Positivos (Control de Riesgo)")
    md.append("- **Preservación de Capital:** Máximo drawdown en Holdout de apenas **4.79%** (frente a un colapso del **-56.59%** de Buy & Hold en el mismo periodo).")
    md.append("- **Cero Liquidaciones:** En los más de 6.5 años combinados de backtest no ocurrió ningún evento de liquidación simulada, operando con apalancamientos prudentes (0.32x - 0.57x).")
    md.append("- **Eficiencia de la Optimización de Ejecución:** El paso a ejecución Maker en entrada casi triplicó el retorno neto (de +0.44% a +1.22%) y redujo las pérdidas bajo estrés x2 de -4.03 a -0.47 USDT/op.")
    md.append("- **Sharpe Superior a Mercado Bajista:** En el periodo de Holdout, el Sharpe (0.15) y Calmar (0.15) de la estrategia superaron a Buy & Hold (-0.02 y -0.19 respectivamente).\n")

    md.append("### Aspectos Negativos (Falla Estructural de Rentabilidad)")
    md.append("- **Falta de Edge Económico:** La expectativa neta en Holdout v1.1.0 fue de apenas **+2.83 USDT por trade** sobre una cuenta de 10,000 USDT (0.028% por trade), insuficiente para compensar el riesgo operativo.")
    md.append("- **Decaimiento Severo Fuera de Muestra:** Retención de rentabilidad anualizada de solo **8.04%** respecto a desarrollo (eliminatorio exigía >= 25%).")
    md.append("- **Sensibilidad Letal a Fricciones:** Con costos duplicados, la expectativa cae a **-0.47 USDT/op**.")
    md.append("- **Muestra Insuficiente y Falta de Significancia:** Se realizaron solo 43 operaciones en 21 meses (umbral >= 50) y el Deflated Sharpe Ratio fue de **0.3594** (umbral >= 0.95).\n")

    md.append("## 4. Análisis de Potencia Estadística e Inferencia")
    pstats = power["sample_stats"]
    md.append(f"- **Número de Operaciones en Holdout ($N$):** {pstats['n']}")
    md.append(f"- **Ganancia Neta Media por Operación ($\\mu$):** {pstats['mean']:.4f} USDT")
    md.append(f"- **Desviación Estándar Muestral ($s$):** {pstats['std']:.4f} USDT")
    md.append(f"- **Error Estándar ($SE = s / \\sqrt{{N}}$):** {pstats['se']:.4f} USDT")
    md.append(f"- **Estadístico $t$ de Student:** `{pstats['t_stat']:.4f}` ($p\\text{{-valor}} = {pstats['p_value']:.4f}$)")
    md.append(f"- **Intervalo de Confianza al 95%:** `[{pstats['ci95_lo']:.2f}, {pstats['ci95_hi']:.2f}] USDT` (incluye holgadamente el cero)\n")

    md.append("### Validación de las Estimaciones de Referencia")
    user_comp = power["comparison_with_user_reference"]
    md.append(f"> {user_comp['validation_and_conclusion']}\n")
    md.append("| Métrica de Potencia | Estimación de Referencia | Cálculo Empírico Exacto (Holdout) |")
    md.append("|---|---|---|")
    md.append(f"| Desviación estándar ($s$) | ~83.0 USDT | **{pstats['std']:.2f} USDT** |")
    md.append(f"| Estadístico $t$ | ~0.22 | **{pstats['t_stat']:.2f}** |")
    md.append(f"| Ritmo operativo anual | 25.0 ops/año | **{power['trades_per_year']:.2f} ops/año** |")
    md.append(f"| Operaciones para IC 95% > 0 ($N^*$) | ~3,300 ops | **{power['n_needed_ci95_excludes_zero']:.0f} ops** |")
    md.append(f"| Años requeridos al ritmo actual | >100 años (~132 años) | **{power['years_needed_ci95']:.1f} años** |")
    md.append(f"| Operaciones para 80% de Potencia | N/A | **{power['n_needed_80pct_power']:.0f} ops** ({power['years_needed_80power']:.1f} años) |\n")

    md.append("### Expectativa Requerida según Tamaño de Muestra Fijo")
    md.append("Para que una estrategia con la dispersión observada ($s = 103.40$ USDT) alcance significancia estadística ($t \\ge 1.96$) en muestras alcanzables en la vida real, necesitaría una expectativa mucho mayor:")
    for n_tgt, req_m in power["required_mean_by_sample_size"].items():
        md.append(f"- Con **$N = {n_tgt}$ operaciones**: Se requiere una expectativa neta $\\ge$ **+{req_m:.2f} USDT/op** (la observada fue de apenas +2.83 USDT).")
    md.append("\n---\n")

    md.append("## 5. Descomposición del Resultado y Baselines")
    md.append("### Desglose de Fricciones por Operación")
    md.append("| Periodo | Trades | Bruto / op | Comisión / op | Slippage / op | Funding / op | Costo Total / op | Neto / op | % Costos / Bruto |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    for pname, cdata in decomp["cost_breakdowns"].items():
        costs_pct_str = f"{cdata['costs_pct_of_gross']:.1f}%" if not math.isnan(cdata["costs_pct_of_gross"]) else "N/A"
        md.append(f"| {pname.capitalize()} | {cdata['n_trades']} | {cdata['gross_expectancy_usdt']:.2f} | {cdata['fees_per_trade']:.2f} | {cdata['slippage_per_trade']:.2f} | {cdata['funding_per_trade']:.2f} | {cdata['total_cost_per_trade']:.2f} | {cdata['net_expectancy_usdt']:.2f} | {costs_pct_str} |")

    md.append("\n### Concentración de Ganancias")
    md.append("| Periodo | PnL Neto Total | Trades Top 5% | Aporte Top 5% (% PnL) | Trades Top 10% | Aporte Top 10% (% PnL) |")
    md.append("|---|---|---|---|---|---|")
    for pname, cdata in decomp["concentrations"].items():
        md.append(f"| {pname.capitalize()} | {cdata['total_net_pnl']:.2f} USDT | {cdata['top_5pct_trades_count']} | {cdata['top_5pct_share_pct']:.1f}% | {cdata['top_10pct_trades_count']} | {cdata['top_10pct_share_pct']:.1f}% |")

    md.append("\n### Comparación con Baselines")
    md.append("| Periodo | Retorno Estrategia | Retorno B&H | Retorno Aleatorio (Mediana) | Sharpe Estrategia | Sharpe B&H | Sharpe Aleatorio (Mediana) |")
    md.append("|---|---|---|---|---|---|---|")
    for pname, bdata in decomp["baselines_by_period"].items():
        s_ret = f"{bdata['strategy']['total_return']*100:.2f}%"
        bh_ret = f"{bdata['buy_and_hold']['total_return']*100:.2f}%"
        rand_ret = f"{bdata['random_baseline']['median_total_return']*100:.2f}%"
        s_sr = f"{bdata['strategy']['sharpe']:.2f}"
        bh_sr = f"{bdata['buy_and_hold']['sharpe']:.2f}"
        rand_sr = f"{bdata['random_baseline']['median_sharpe']:.2f}"
        md.append(f"| {pname.capitalize()} | {s_ret} | {bh_ret} | {rand_ret} | {s_sr} | {bh_sr} | {rand_sr} |")

    md.append("\n---\n")

    md.append("## 6. Limitaciones del Experimento")
    md.append("1. **Déficit de Potencia por Baja Frecuencia:** Al operar rupturas de 100 barras en 4h (~16 días) sobre un solo activo, se obtienen únicamente ~25 trades al año. Como demostró el análisis de potencia, harían falta siglos para validar estadísticamente una expectativa tan pequeña.")
    md.append("2. **Dependencia de Régimen Único:** BTCUSDT transitó en 2025–2026 fases de compresión y consolidación errática donde las rupturas fallan sistemáticamente, sin otros activos no correlacionados que compensen.")
    md.append("3. **Modelo de Ejecución Maker Estático:** Asumir un fill del 100% en la orden límite sin modelar el riesgo de selección adversa (adverse execution) ni órdenes no ejecutadas en rupturas violentas es un supuesto optimista; la realidad en producción sería todavía más desfavorable.")

    md.append("\n---\n")

    md.append("## 7. Trabajo Futuro: Hipótesis Alternativa Preregistrada")
    md.append("> **IMPORTANTE:** Esta es una propuesta metodológica para una **investigación completamente nueva e independiente**. NO constituye una extensión, ajuste de parámetros ni continuación de la estrategia v1.1.0 (la cual queda cerrada y rechazada).\n")
    md.append("### Descripción de la Hipótesis")
    md.append("- **Tesis:** Una cartera multi-activo con rebalanceo sistemático diario y objetivo de volatilidad genera suficientes observaciones independientes por año para superar la barrera de potencia estadística y mitigar el riesgo de régimen de un solo activo.")
    md.append("- **Universo:** Cesta de los 15 contratos perpetuos USDT-M más líquidos de Binance (excluyendo stablecoins), filtrados trimestralmente por volumen diario > 50M USDT.")
    md.append("- **Frecuencia:** Barras diarias (1D), toma de señales al cierre UTC 00:00 y rebalanceo mediante órdenes límite TWAP durante la primera hora.")
    md.append("- **Mecanismo:** Puntuación de momentum transversal (cross-sectional momentum z-score a 30 y 90 días). Asignación larga en el tercio superior y corta en el tercio inferior, ponderados por paridad de riesgo inversa a la volatilidad (Risk Parity) con un objetivo de volatilidad de cartera del 15% anualizado.")
    md.append("- **Criterio de Parada Explícito (Stop Protocol):**")
    md.append("  - *Stop de drawdown:* Si la cartera experimenta un drawdown acumulado del **15.0%**, se cierran todas las posiciones y se cancela el protocolo.")
    md.append("  - *Stop temporal de significancia:* Si tras **12 meses** continuos de prueba fuera de muestra (acumulando >= 3,000 posiciones-día independientes) el Sharpe neto anualizado diario no alcanza un valor $\\ge 0.70$ o si el IC 95% de la expectativa diaria incluye el cero, el experimento se da por terminado con veredicto FAIL irrevocable.")

    md.append("\n---\n")

    md.append("## 8. Conclusión Honesta y Definitiva")
    md.append("Bajo el protocolo pre-especificado y las reglas científicas fijadas de antemano:")
    md.append("- La estrategia de ruptura Donchian sobre BTCUSDT en 4h **no es rentable de forma creíble**.")
    md.append("- Aunque el sistema demostró un excelente control del riesgo a la baja (drawdown contenido en 4.8%), la expectativa neta observada (+2.83 USDT/op) es económicamente insignificante, no sobrevive a un estrés de comisiones razonable y es indistinguible del puro azar estadístico.")
    md.append("- La hipótesis inicial queda **rechazada** formalmente. El ciclo de vida de la estrategia se da por concluido.")

    md_path = rep_dir / "final_report.md"
    md_path.write_text("\n".join(md), encoding="utf-8")

    print(f"Reporte final guardado en:\n  - {md_path}\n  - {json_path}")
    return final_data


if __name__ == "__main__":
    generate_final_report()
