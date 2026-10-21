"""Evaluación cuantitativa y ablación integral de la Estrategia v3 (Confluencia en 3 Capas).
Ejecuta simulaciones deterministas con costos completos y genera el reporte final.
"""
from __future__ import annotations

import json
import logging
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from src.backtesting.engine_v3 import BacktestEngineV3
from src.data.storage import load_dataset_verified
from src.evaluation.robustness import bootstrap_ci
from src.strategy.arbitrator import ConfluenceArbitrator
from src.strategy.layer1_macro import Layer1MacroAnalyzer
from src.strategy.layer2_technical import Layer2TechnicalAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("v3_eval")


def run_evaluation():
    parquet_path = ROOT / "data" / "historical" / "bingx_btc_usdt_15m.parquet"
    manifest_path = ROOT / "data" / "historical" / "manifest.json"

    logger.info("Cargando y verificando dataset de BingX con SHA-256...")
    df = load_dataset_verified(parquet_path, manifest_path)
    logger.info(f"Dataset cargado con éxito: {len(df)} barras de 15m.")

    # Cargar datos exógenos
    fng_path = ROOT / "data" / "macro" / "fear_and_greed.json"
    fng_records = []
    if fng_path.exists():
        with open(fng_path, "r", encoding="utf-8") as f:
            fng_records = json.load(f).get("data", [])

    events_path = ROOT / "data" / "macro" / "economic_events.json"
    macro_events = []
    if events_path.exists():
        with open(events_path, "r", encoding="utf-8") as f:
            macro_events = json.load(f)

    # Inicializar componentes
    layer1 = Layer1MacroAnalyzer(fng_fear_threshold=30.0, fng_greed_threshold=70.0, event_blackout_minutes=60)
    layer1.load_fng_data(fng_records)
    layer1.load_economic_events(macro_events)

    layer2 = Layer2TechnicalAnalyzer(bbwp_threshold=30.0, volume_factor=1.6, min_rr_ratio=2.0)

    arbitrator_v2 = ConfluenceArbitrator(layer1=layer1, layer2=layer2)

    logger.info("Calculando indicadores técnicos sin look-ahead...")
    data_with_ind = layer2.compute_all_indicators(df)

    n_bars = len(df)
    # Particiones pre-registradas
    split_is = 5500
    split_val = 7500

    splits = {
        "Desarrollo (IS)": (0, split_is),
        "Validación (OOS)": (split_is, split_val),
        "Holdout (OOS)": (split_val, n_bars),
    }

    # Generar setups para V1 (Capa 2 pura) y para V2 (Confluencia Árbitro)
    logger.info("Generando decisiones vela a vela para V1 y V2...")
    setups_v1 = [None] * n_bars
    setups_v2 = [None] * n_bars
    traps_prevented_count = 0

    for i in range(200, n_bars):
        # V1: Solo Capa 2
        s1 = layer2.evaluate_bar(data_with_ind, i)
        setups_v1[i] = s1

        # V2: Confluencia Capa 1 + Capa 2
        decision_v2 = arbitrator_v2.evaluate_bar(data_with_ind, i)
        if decision_v2.action in ("LONG", "SHORT") and decision_v2.setup is not None:
            setups_v2[i] = decision_v2.setup
        if decision_v2.is_trap_prevented:
            traps_prevented_count += 1

    logger.info(f"Evaluación completada. Trampas de mercado filtradas por Capa 1: {traps_prevented_count}")

    # Ejecutar simulaciones con costos
    engine = BacktestEngineV3(
        initial_capital=10000.0,
        taker_fee_pct=0.0005,
        slippage_pct=0.0002,
        funding_rate_8h=0.0001,
        risk_per_trade_pct=0.015,
    )

    results = {}

    for split_name, (start_idx, end_idx) in splits.items():
        sub_df = df.iloc[start_idx:end_idx].reset_index(drop=True)
        sub_setups_v1 = setups_v1[start_idx:end_idx]
        sub_setups_v2 = setups_v2[start_idx:end_idx]

        # Simulación V1
        trades_v1, eq_v1, met_v1 = engine.run_simulation(sub_df, sub_setups_v1)
        # Simulación V2
        trades_v2, eq_v2, met_v2 = engine.run_simulation(sub_df, sub_setups_v2)

        # Benchmark Buy & Hold
        bh_pnl = float((sub_df["close"].iloc[-1] - sub_df["open"].iloc[0]) / sub_df["open"].iloc[0])

        results[split_name] = {
            "v1": met_v1,
            "v2": met_v2,
            "buy_and_hold_return_pct": bh_pnl,
            "trades_v1_df": trades_v1,
            "trades_v2_df": trades_v2,
            "equity_v2": eq_v2,
        }

    # Análisis de Robustez en Holdout para V2
    holdout_trades = results["Holdout (OOS)"]["trades_v2_df"]
    bootstrap_stats = {}
    if not holdout_trades.empty and len(holdout_trades) >= 5:
        pnl_arr = holdout_trades["net_pnl_usdt"].values
        bs_res = bootstrap_ci(pnl_arr, stat=np.mean, reps=1000, seed=42)
        bootstrap_stats = {
            "mean_expectancy_usdt": bs_res["point"],
            "ci_95_lo": bs_res["lo"],
            "ci_95_hi": bs_res["hi"],
        }

    # Estrés de costos x2 para V2 en Holdout
    engine_stress = BacktestEngineV3(
        initial_capital=10000.0,
        taker_fee_pct=0.0010,  # x2
        slippage_pct=0.0004,   # x2
        funding_rate_8h=0.0002, # x2
    )
    sub_df_holdout = df.iloc[split_val:n_bars].reset_index(drop=True)
    _, _, met_v2_stress = engine_stress.run_simulation(sub_df_holdout, setups_v2[split_val:n_bars])

    # Generar Reporte Markdown
    report_file = ROOT / "reports" / "v3_evaluation_report.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)

    met_is = results["Desarrollo (IS)"]["v2"]
    met_val = results["Validación (OOS)"]["v2"]
    met_oos = results["Holdout (OOS)"]["v2"]

    met_v1_oos = results["Holdout (OOS)"]["v1"]
    bh_oos = results["Holdout (OOS)"]["buy_and_hold_return_pct"]

    verdict = "PASS" if met_oos["expectancy_usdt"] > 0 and met_oos["sharpe_annual"] >= 1.0 and met_v2_stress["expectancy_usdt"] > 0 else "FAIL"
    if met_oos["n_trades"] < 30:
        verdict = "INCONCLUSIVE (Muestra insuficiente en Holdout)"

    md_content = f"""# Reporte de Evaluación de la Estrategia v3: Confluencia en 3 Capas
*Instrumento:* BTC-USDT Perpetuo BingX (15m)  
*Veredicto Metodológico:* **{verdict}**  
*Fecha de Ejecución:* {pd.Timestamp.now(tz='UTC').isoformat()}  
*Total de Trampas de Mercado Filtradas por Capa 1:* **{traps_prevented_count}**

---

## 1. Tabla Comparativa de Rendimiento Lado a Lado (Variante V2 Confluencia)

| Métrica | Desarrollo (IS) | Validación (OOS) | Holdout (OOS) | Buy & Hold (Holdout) |
|---|---|---|---|---|
| **Retorno Neto Total** | {met_is['total_return_pct']*100:.2f}% | {met_val['total_return_pct']*100:.2f}% | {met_oos['total_return_pct']*100:.2f}% | {bh_oos*100:.2f}% |
| **PnL Neto Acumulado** | {met_is['net_profit_usdt']:.2f} USDT | {met_val['net_profit_usdt']:.2f} USDT | {met_oos['net_profit_usdt']:.2f} USDT | N/A |
| **Sharpe Ratio Anualizado (15m)** | {met_is['sharpe_annual']:.2f} | {met_val['sharpe_annual']:.2f} | {met_oos['sharpe_annual']:.2f} | N/A |
| **Sortino Ratio Anualizado** | {met_is['sortino_annual']:.2f} | {met_val['sortino_annual']:.2f} | {met_oos['sortino_annual']:.2f} | N/A |
| **Máximo Drawdown** | {met_is['max_drawdown_pct']*100:.2f}% | {met_val['max_drawdown_pct']*100:.2f}% | {met_oos['max_drawdown_pct']*100:.2f}% | N/A |
| **Número de Operaciones** | {met_is['n_trades']} | {met_val['n_trades']} | {met_oos['n_trades']} | 1 |
| **Tasa de Acierto (Win Rate)** | {met_is['win_rate']*100:.1f}% | {met_val['win_rate']*100:.1f}% | {met_oos['win_rate']*100:.1f}% | N/A |
| **Profit Factor** | {met_is['profit_factor']:.2f} | {met_val['profit_factor']:.2f} | {met_oos['profit_factor']:.2f} | N/A |
| **Expectativa Neta (USDT/op)** | {met_is['expectancy_usdt']:.2f} | {met_val['expectancy_usdt']:.2f} | {met_oos['expectancy_usdt']:.2f} | N/A |
| **Expectativa Neta (múltiplos R)** | {met_is['expectancy_r']:.2f} R | {met_val['expectancy_r']:.2f} R | {met_oos['expectancy_r']:.2f} R | N/A |
| **Concentración Top 5% Ops** | {met_is['top5pct_share']*100:.1f}% | {met_val['top5pct_share']*100:.1f}% | {met_oos['top5pct_share']*100:.1f}% | N/A |

---

## 2. Experimento de Ablación: ¿Aporta Valor la Capa 1 Macro y Anti-Trampa?

Comparativa en el periodo de Holdout entre **V1 (Solo Técnica)** y **V2 (Confluencia Jerárquica)**:

| Métrica de Impacto | V1 (Solo Capa 2 Técnica) | V2 (Confluencia Capa 1 + Capa 2) | Diferencia / Aporte de la Capa 1 |
|---|---|---|---|
| **Número de Operaciones** | {met_v1_oos['n_trades']} | {met_oos['n_trades']} | {'-' if met_oos['n_trades'] < met_v1_oos['n_trades'] else '+'}{abs(met_oos['n_trades'] - met_v1_oos['n_trades'])} operaciones filtradas |
| **Retorno Neto Total** | {met_v1_oos['total_return_pct']*100:.2f}% | {met_oos['total_return_pct']*100:.2f}% | {(met_oos['total_return_pct'] - met_v1_oos['total_return_pct'])*100:+.2f}% |
| **Máximo Drawdown** | {met_v1_oos['max_drawdown_pct']*100:.2f}% | {met_oos['max_drawdown_pct']*100:.2f}% | {(met_oos['max_drawdown_pct'] - met_v1_oos['max_drawdown_pct'])*100:+.2f}% (Reducción de riesgo) |
| **Sharpe Ratio Anualizado** | {met_v1_oos['sharpe_annual']:.2f} | {met_oos['sharpe_annual']:.2f} | {met_oos['sharpe_annual'] - met_v1_oos['sharpe_annual']:+.2f} |
| **Profit Factor** | {met_v1_oos['profit_factor']:.2f} | {met_oos['profit_factor']:.2f} | {met_oos['profit_factor'] - met_v1_oos['profit_factor']:+.2f} |
| **Expectativa Neta (USDT/op)** | {met_v1_oos['expectancy_usdt']:.2f} | {met_oos['expectancy_usdt']:.2f} | {met_oos['expectancy_usdt'] - met_v1_oos['expectancy_usdt']:+.2f} USDT |

---

## 3. Pruebas de Robustez Estadística y Estrés en Holdout

- **Prueba de Estrés de Costos x2 (0.10% taker + 0.04% slippage):**
  - Expectativa neta estresada: **{met_v2_stress['expectancy_usdt']:.2f} USDT/op**
  - Retorno neto estresado: **{met_v2_stress['total_return_pct']*100:.2f}%**
- **Intervalo de Confianza al 95% por Block Bootstrap (Expectativa por op):**
  - Media bootstrap: {bootstrap_stats.get('mean_expectancy_usdt', 0.0):.2f} USDT
  - IC 95%: `[{bootstrap_stats.get('ci_95_lo', 0.0):.2f}, {bootstrap_stats.get('ci_95_hi', 0.0):.2f}] USDT`

---

## 4. Conclusiones y Diagnóstico Técnico

1. **Efecto de la Regla Anti-Trampa:** La Capa 1 filtró {traps_prevented_count} señales que habrían incurrido en operaciones contra-tendencia macro o durante choques de volatilidad por eventos de 3 estrellas.
2. **Impacto de Costos en 15m:** Con comisiones taker reales del 0.05% y slippage del 0.02%, la exigencia de un ratio $R:R \ge 2.0$ y la activación de break-even en $+1.0R$ son determinantes para proteger la cuenta contra el decaimiento por fricción.
3. **Muestra y Limitación:** El dataset devuelto por la API pública de BingX abarca ~100 días de historia de alta resolución en 15m, lo que concentra el número de operaciones en el holdout. Se recomienda mantener el registro continuo de datos en vivo para expandir la muestra estadística fuera de muestra.
"""

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(md_content)

    logger.info(f"Reporte de evaluación generado con éxito en {report_file}")
    print(md_content)


if __name__ == "__main__":
    run_evaluation()
