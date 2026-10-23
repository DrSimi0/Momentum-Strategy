"""Script de Auditoría Forense y Correcciones Cuantitativas Exhaustivas:
1. Recalcula las 10 configuraciones (4 Swing H1/H4 y 6 Menor Temporalidad M15/M5) sobre Capital Fijo ($50,000 USD)
   e identifica cuáles alcanzaron equity negativo (quiebra formal).
2. Ejecuta Test de Permutación Monte Carlo (10,000 iteraciones) para los 9 vecinos paramétricos del grid de NQ 15m
   y cuenta cuántos tienen p < 0.05.
3. Calcula el Buy & Hold riguroso ajustado por tiempo en mercado bajo la misma metodología diaria.
4. Genera tabla comparativa unificada H1/H4 vs M15/M5.
5. Modela la potencia analítica del Forward Test para Sharpe de 0.6, 0.4 y 0.2.
"""
from dataclasses import replace
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis, norm

from src.strategies.intraday_unified_strategy import (
    IntradayStrategyParams,
    run_intraday_backtest,
)
from src.strategies.unified_strategy import (
    UnifiedStrategyParams,
    run_unified_backtest,
)
from src.analysis.daily_equity_audit import (
    build_daily_equity_curve,
    compute_deflated_sharpe_ratio,
    run_permutation_test,
)
from src.backtest.engine_sma_confluence import AssetCosts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("forensic_audit")

PROCESSED_DIR = Path("data/processed")
TABLES_DIR = Path("reports/auditoria_intradia/tables")
TABLES_DIR.mkdir(parents=True, exist_ok=True)


def get_costs(symbol: str) -> AssetCosts:
    if symbol == "ES":
        return AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0)
    elif symbol == "NQ":
        return AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0)
    raise ValueError(f"Símbolo {symbol} no reconocido")


def run_forensic_corrections():
    # =========================================================================
    # ITEM 2 & TABLA COMPARATIVA: RECÁLCULO DE LAS 10 CONFIGURACIONES SOBRE CAPITAL FIJO ($50,000)
    # =========================================================================
    logger.info("Iniciando recalculo integral de las 10 configuraciones sobre capital fijo ($50,000 USD)...")

    # 4 Configuraciones Swing
    swing_configs = [
        ("Swing_1_ES_1h", "ES", "1h", UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0)),
        ("Swing_2_NQ_1h", "NQ", "1h", UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0)),
        ("Swing_3_ES_4h", "ES", "4h", UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0)),
        ("Swing_4_NQ_4h", "NQ", "4h", UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0)),
    ]

    # 6 Configuraciones Menor Temporalidad
    intra_configs = [
        ("Intra_1_NQ_15m_Opt", "NQ", "15m", IntradayStrategyParams(fast_ema=20, slow_ema=80, atr_k=2.0, tp_m=2.0, rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50", use_volatility_filter=True)),
        ("Intra_2_NQ_15m_Base", "NQ", "15m", IntradayStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0, rth_start_time="00:00", rth_end_time="23:59", moc_close_time="23:59", use_volatility_filter=False)),
        ("Intra_3_ES_15m_Base", "ES", "15m", IntradayStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0, rth_start_time="00:00", rth_end_time="23:59", moc_close_time="23:59", use_volatility_filter=False)),
        ("Intra_4_NQ_5m_Opt", "NQ", "5m", IntradayStrategyParams(fast_ema=20, slow_ema=80, atr_k=2.0, tp_m=2.0, rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50", use_volatility_filter=True)),
        ("Intra_5_ES_5m_Agr", "ES", "5m", IntradayStrategyParams(fast_ema=10, slow_ema=50, atr_k=1.5, tp_m=2.0, rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50", use_volatility_filter=True)),
        ("Intra_6_NQ_5m_MOC_SinVol", "NQ", "5m", IntradayStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0, rth_start_time="00:00", rth_end_time="23:59", moc_close_time="15:50", use_volatility_filter=False)),
    ]

    all_comparative_rows = []

    # Procesar Swing
    for cfg_id, sym, tf, params in swing_configs:
        df = pd.read_parquet(PROCESSED_DIR / f"{sym}_{tf}.parquet")
        costs = get_costs(sym)
        res = run_unified_backtest(df, params, costs)
        daily = build_daily_equity_curve(res["trades"], df, initial_capital=50000.0)
        d_df = daily["daily_df"]

        # Retornos diarios normalizados sobre capital fijo inicial ($50k)
        ret_fixed = d_df["pnl_usd"] / 50000.0
        sh_fixed = float((ret_fixed.mean() / ret_fixed.std(ddof=1)) * np.sqrt(252.0)) if ret_fixed.std(ddof=1) > 1e-9 else 0.0

        # Sharpe tradicional compuesto sobre equity acumulada
        sh_comp = daily["sharpe_daily"]

        min_eq = float(d_df["equity"].min())
        days_insolvent = int((d_df["equity"] <= 0).sum())
        is_bankrupt = bool(min_eq <= 0)

        # Buy & Hold en la misma serie
        p_start = df["close"].iloc[0]
        p_end = df["close"].iloc[-1]
        bh_total_ret = ((p_end / p_start) - 1.0) * 100.0
        bars_held = sum(t["bars_held"] for t in res["trades"])
        time_market = (bars_held / len(df)) * 100.0
        bh_adj_cagr = ((1.0 + (bh_total_ret / 100.0) * (time_market / 100.0)) ** (1.0 / 16.36) - 1.0) * 100.0

        ts_d = pd.to_datetime(df["ts_event"], utc=True).dt.date
        df_d = pd.DataFrame({"date": ts_d, "close": df["close"]}).groupby("date")["close"].last()
        bh_daily_rets = df_d.pct_change().dropna()
        bh_sh = float((bh_daily_rets.mean() / bh_daily_rets.std(ddof=1)) * np.sqrt(252.0))
        bh_adj_sh = bh_sh * np.sqrt(time_market / 100.0)

        all_comparative_rows.append({
            "Grupo": "Swing (H1/H4)",
            "Configuracion": cfg_id,
            "Activo": sym,
            "TF": tf,
            "N_Trades": res["n_trades"],
            "Win_Rate_%": round(res["win_rate"] * 100, 2),
            "Profit_Factor": round(res["profit_factor"], 2) if not np.isnan(res["profit_factor"]) else 0.0,
            "Net_PnL_USD": round(daily["total_net_pnl"], 2),
            "CAGR_%": round(daily["cagr"] * 100, 2),
            "Sharpe_Oficial_Capital_Fijo_50k": round(sh_fixed, 2),
            "Sharpe_Compuesto_Equity_Movil": round(sh_comp, 2),
            "Max_DD_USD": round(daily["max_dd_usd"], 2),
            "Max_DD_%_Pico": round(daily["max_dd_pct"], 2),
            "Min_Equity_USD": round(min_eq, 2),
            "Dias_Insolvente": days_insolvent,
            "Llego_a_Equity_Negativo": is_bankrupt,
            "Time_in_Market_%": round(time_market, 2),
            "B&H_Ajustado_CAGR_%": round(bh_adj_cagr, 2),
            "B&H_Ajustado_Sharpe": round(bh_adj_sh, 2),
            "Bate_B&H_Ajustado": bool(sh_fixed > bh_adj_sh),
        })

    # Procesar Intradía
    for cfg_id, sym, tf, params in intra_configs:
        df = pd.read_parquet(PROCESSED_DIR / f"{sym}_{tf}.parquet")
        costs = get_costs(sym)
        res = run_intraday_backtest(df, params, costs)
        daily = build_daily_equity_curve(res["trades"], df, initial_capital=50000.0)
        d_df = daily["daily_df"]

        ret_fixed = d_df["pnl_usd"] / 50000.0
        sh_fixed = float((ret_fixed.mean() / ret_fixed.std(ddof=1)) * np.sqrt(252.0)) if ret_fixed.std(ddof=1) > 1e-9 else 0.0
        sh_comp = daily["sharpe_daily"]

        min_eq = float(d_df["equity"].min())
        days_insolvent = int((d_df["equity"] <= 0).sum())
        is_bankrupt = bool(min_eq <= 0)

        p_start = df["close"].iloc[0]
        p_end = df["close"].iloc[-1]
        bh_total_ret = ((p_end / p_start) - 1.0) * 100.0
        bars_held = sum(t["bars_held"] for t in res["trades"])
        time_market = (bars_held / len(df)) * 100.0
        bh_adj_cagr = ((1.0 + (bh_total_ret / 100.0) * (time_market / 100.0)) ** (1.0 / 16.36) - 1.0) * 100.0

        ts_d = pd.to_datetime(df["ts_event"], utc=True).dt.date
        df_d = pd.DataFrame({"date": ts_d, "close": df["close"]}).groupby("date")["close"].last()
        bh_daily_rets = df_d.pct_change().dropna()
        bh_sh = float((bh_daily_rets.mean() / bh_daily_rets.std(ddof=1)) * np.sqrt(252.0))
        bh_adj_sh = bh_sh * np.sqrt(time_market / 100.0)

        all_comparative_rows.append({
            "Grupo": "Menor Temporalidad (M15/M5)",
            "Configuracion": cfg_id,
            "Activo": sym,
            "TF": tf,
            "N_Trades": res["n_trades"],
            "Win_Rate_%": round(res["win_rate"] * 100, 2),
            "Profit_Factor": round(res["profit_factor"], 2) if not np.isnan(res["profit_factor"]) else 0.0,
            "Net_PnL_USD": round(daily["total_net_pnl"], 2),
            "CAGR_%": round(daily["cagr"] * 100, 2),
            "Sharpe_Oficial_Capital_Fijo_50k": round(sh_fixed, 2),
            "Sharpe_Compuesto_Equity_Movil": round(sh_comp, 2),
            "Max_DD_USD": round(daily["max_dd_usd"], 2),
            "Max_DD_%_Pico": round(daily["max_dd_pct"], 2),
            "Min_Equity_USD": round(min_eq, 2),
            "Dias_Insolvente": days_insolvent,
            "Llego_a_Equity_Negativo": is_bankrupt,
            "Time_in_Market_%": round(time_market, 2),
            "B&H_Ajustado_CAGR_%": round(bh_adj_cagr, 2),
            "B&H_Ajustado_Sharpe": round(bh_adj_sh, 2),
            "Bate_B&H_Ajustado": bool(sh_fixed > bh_adj_sh),
        })

    comp_df = pd.DataFrame(all_comparative_rows)
    comp_df.to_csv(TABLES_DIR / "tabla_comparativa_h1_h4_vs_m15_m5_capital_fijo.csv", index=False)
    logger.info("Tabla comparativa de las 10 configuraciones guardada con exito.")

    # =========================================================================
    # ITEM 4: PERMUTACIÓN MONTE CARLO (10,000 ITERACIONES) PARA LOS 9 VECINOS
    # =========================================================================
    logger.info("Iniciando Monte Carlo de permutacion (10,000 iteraciones) para los 9 vecinos...")
    df_nq15 = pd.read_parquet(PROCESSED_DIR / "NQ_15m.parquet")
    costs_nq = get_costs("NQ")

    fast_emas = [10, 20, 30]
    slow_emas = [50, 80, 120]
    neighbor_perm_rows = []

    for fe in fast_emas:
        for se in slow_emas:
            logger.info(f"Permutacion Monte Carlo para vecino EMA ({fe}, {se})...")
            p = IntradayStrategyParams(
                fast_ema=fe, slow_ema=se, atr_k=2.0, tp_m=2.0,
                rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50",
                use_volatility_filter=True, use_candle_trigger=True
            )
            res = run_intraday_backtest(df_nq15, p, costs_nq)
            trades = res["trades"]
            n_tr = len(trades)

            # Test de permutación con 10,000 iteraciones
            perm_res = run_permutation_test(trades, df_nq15, costs_nq, n_iterations=10000)

            daily = build_daily_equity_curve(trades, df_nq15, initial_capital=50000.0)
            ret_f = daily["daily_df"]["pnl_usd"] / 50000.0
            sh_f = float((ret_f.mean() / ret_f.std(ddof=1)) * np.sqrt(252.0))

            passes_p05 = bool(perm_res["p_value"] < 0.05)

            neighbor_perm_rows.append({
                "Fast_EMA": fe,
                "Slow_EMA": se,
                "N_Trades": n_tr,
                "Real_Net_PnL_USD": round(res["net_pnl_usd"], 2),
                "Real_Sharpe_Fijo": round(sh_f, 2),
                "MonteCarlo_Mean_PnL_USD": round(perm_res["mean_random_pnl"], 2),
                "MonteCarlo_Std_PnL_USD": round(perm_res["std_random_pnl"], 2),
                "P_Value_Permutacion": round(perm_res["p_value"], 4),
                "Percentil_Real_%": round(perm_res["percentile"], 2),
                "Significativo_p_menor_0.05": passes_p05,
            })

    perm_df = pd.DataFrame(neighbor_perm_rows)
    perm_df.to_csv(TABLES_DIR / "vecinos_nq15_permutacion_10000.csv", index=False)
    logger.info("Tabla de permutaciones de los 9 vecinos guardada.")

    # =========================================================================
    # ITEM 6: MODELO ANALÍTICO DE POTENCIA PARA FORWARD TEST
    # =========================================================================
    logger.info("Modelando potencia analitica para Forward Test...")
    power_rows = []
    # Test unilateral H0: Sharpe <= 0 vs H1: Sharpe > 0 al 95% de confianza (alpha = 0.05)
    z_alpha = norm.ppf(0.95) # 1.6449

    sharpe_scenarios = [0.6, 0.4, 0.2]
    power_targets = [0.50, 0.80, 0.90, 0.95]

    for sh in sharpe_scenarios:
        for p_t in power_targets:
            z_beta = norm.ppf(p_t)
            # Años requeridos: N_years = ((Z_alpha + Z_beta) / Sharpe)^2
            years_needed = ((z_alpha + z_beta) / sh) ** 2
            # Para NQ 15m Optimizada, genera ~36.43 trades por año
            trades_needed = years_needed * 36.43
            power_rows.append({
                "Sharpe_Verdadero": sh,
                "Potencia_Deseada_%": int(p_t * 100),
                "Nivel_Significancia_Alpha_%": 5.0,
                "Años_Requeridos": round(years_needed, 2),
                "Meses_Requeridos": round(years_needed * 12.0, 1),
                "Trades_Esperados_NQ15": int(round(trades_needed)),
            })

    power_df = pd.DataFrame(power_rows)
    power_df.to_csv(TABLES_DIR / "forward_test_potencia_analitica.csv", index=False)
    logger.info("Tabla de potencia analitica guardada con exito.")


if __name__ == "__main__":
    run_forensic_corrections()
    print("Auditoria forense y tablas completadas con exito.")
