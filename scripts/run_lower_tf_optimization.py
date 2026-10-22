"""Optimización y Evaluación Especializada de la Estrategia Unificada para M5 y M15.
Compara sistemáticamente el impacto del filtro de horario RTH, cierre MOC,
filtro de volatilidad y reescala de medias intradiarias frente a la línea base.
"""
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd

from src.strategies.intraday_unified_strategy import (
    IntradayStrategyParams,
    run_intraday_backtest,
)
from src.backtest.engine_sma_confluence import AssetCosts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("opt_lower_tf")

PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports/short_timeframes")
TABLES_DIR = REPORTS_DIR / "tables"


def run_intraday_optimization():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    costs_map = {
        "ES": AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0),
        "NQ": AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0),
    }

    # Configuraciones para aislar cada mejora
    configs = [
        ("0_Línea_Base_Sin_Filtros", IntradayStrategyParams(
            fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0,
            rth_start_time="00:00", rth_end_time="23:59", moc_close_time="23:59",
            use_volatility_filter=False, use_candle_trigger=True
        )),
        ("1_Solo_Cierre_MOC", IntradayStrategyParams(
            fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0,
            rth_start_time="00:00", rth_end_time="23:59", moc_close_time="15:50",
            use_volatility_filter=False, use_candle_trigger=True
        )),
        ("2_RTH_Horario_Institucional_MOC", IntradayStrategyParams(
            fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0,
            rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50",
            use_volatility_filter=False, use_candle_trigger=True
        )),
        ("3_Intraday_Medias_80_y_Volatilidad", IntradayStrategyParams(
            fast_ema=20, slow_ema=80, atr_k=2.0, tp_m=2.0,
            rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50",
            use_volatility_filter=True, use_candle_trigger=True
        )),
        ("4_Intraday_Agresiva_EMA_10_50", IntradayStrategyParams(
            fast_ema=10, slow_ema=50, atr_k=1.5, tp_m=2.0,
            rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50",
            use_volatility_filter=True, use_candle_trigger=True
        )),
    ]

    test_assets = [
        ("ES", "15m", PROCESSED_DIR / "ES_15m.parquet"),
        ("ES", "5m", PROCESSED_DIR / "ES_5m.parquet"),
        ("NQ", "15m", PROCESSED_DIR / "NQ_15m.parquet"),
        ("NQ", "5m", PROCESSED_DIR / "NQ_5m.parquet"),
    ]

    results = []

    for sym, tf, f_path in test_assets:
        if not f_path.exists():
            continue

        logger.info(f"Procesando optimización en {sym} ({tf})...")
        df = pd.read_parquet(f_path)
        costs = costs_map[sym]
        cost_per_trade = 2.0 * costs.commission_per_side + 2.0 * costs.slippage_per_side * costs.tick_size * costs.multiplier

        for cfg_name, params in configs:
            res = run_intraday_backtest(df, params, costs)
            n_tr = res["n_trades"]
            total_friction = n_tr * cost_per_trade
            gross_pnl = res["net_pnl_usd"] + total_friction

            row = {
                "Activo": sym,
                "Timeframe": tf,
                "Configuración": cfg_name,
                "N_Trades": n_tr,
                "Win_Rate_%": round(res["win_rate"] * 100, 2),
                "Profit_Factor": round(res["profit_factor"], 2) if not np.isnan(res["profit_factor"]) else 0.0,
                "Gross_PnL_USD": round(gross_pnl, 2),
                "Friccion_Costos_USD": round(total_friction, 2),
                "Net_PnL_USD": round(res["net_pnl_usd"], 2),
                "Sharpe": round(res["sharpe"], 2) if not np.isnan(res["sharpe"]) else "N/A",
                "Max_DD_USD": round(res["max_drawdown"], 2),
                "Expectancy_Trade_USD": round(res["avg_expectancy_usd"], 2),
            }
            results.append(row)

    res_df = pd.DataFrame(results)
    csv_path = TABLES_DIR / "lower_tf_optimization_results.csv"
    res_df.to_csv(csv_path, index=False)
    logger.info(f"Resultados guardados en {csv_path}")

    # Tabla Markdown
    md_table = "| " + " | ".join(res_df.columns) + " |\n"
    md_table += "| " + " | ".join(["---"] * len(res_df.columns)) + " |\n"
    for _, r in res_df.iterrows():
        md_table += "| " + " | ".join(str(val) for val in r.values) + " |\n"

    # Redactar informe final de la rama menor temporalidad
    md_path = REPORTS_DIR / "informe_optimizacion_menor_temporalidad.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# AUDITORÍA Y OPTIMIZACIÓN EN MENOR TEMPORALIDAD (M5 Y M15)\n\n")
        f.write("### Rama de Trabajo: `feature/lower-tf-m5-m15`\n\n")
        f.write("## 1. Justificación y Objetivos de la Rama\n")
        f.write("Al evaluar la estrategia swing de 1h/4h directamente en 5m y 15m, el número de trades se multiplica por 10, ")
        f.write("provocando que el costo de comisiones y slippage devore más de $34,000 USD y deteriore el Sharpe a la mitad. ")
        f.write("En esta rama se implementaron y evaluaron 4 mecanismos de adaptación intradiaria:\n")
        f.write("1. **Filtro Horario RTH:** Operar exclusivamente entre 10:00 y 15:15 ET (evitando el spread nocturno y la volatilidad caótica de la apertura).\n")
        f.write("2. **Cierre Forzado MOC (15:50 ET):** Cero riesgo de gap overnight.\n")
        f.write("3. **Filtro de Expansión de Volatilidad (ATR):** Entrar solo cuando hay momentum dinámico real para cubrir los costos de transacción.\n")
        f.write("4. **Escala de Medias Intradiarias:** Adaptación a la duración de una sesión (EMA 20 y EMA 80).\n\n")
        f.write("## 2. Tabla Comparativa de Optimización\n\n")
        f.write(md_table)
        f.write("\n\n## 3. Conclusiones y Comparativa frente a la Rama Principal (`main`)\n")

    logger.info(f"Informe guardado en {md_path}")
    print("\n--- RESUMEN DE OPTIMIZACIÓN INTRADIARIA (M5 / M15) ---")
    print(res_df.to_string(index=False))


if __name__ == "__main__":
    run_intraday_optimization()
