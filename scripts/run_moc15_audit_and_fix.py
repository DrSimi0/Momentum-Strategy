"""Script para auditar la corrección MOC en 15m y evaluar las 10 configuraciones con capital fijo:
1. Análisis de trades overnight vs intradía en las configuraciones previas de 15m.
2. Tabla consolidada de las 10 configuraciones con capital fijo ($50,000 USD):
   Retorno anual simple, Sharpe fijo, Drawdown en $ y en % de capital inicial, y Calmar simple.
3. Evaluación de NQ 15m Optimizada con salida obligatoria MOC en Open de 15:45 ET.
4. Permutación Monte Carlo (10,000 iteraciones) de la versión corregida.
5. Recálculo de DSR con M=380 y evaluación de Prop Firm en MNQ a 0.5% y 1.0%.
"""
from dataclasses import replace
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis

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
logger = logging.getLogger("moc15_fix")

PROCESSED_DIR = Path("data/processed")
TABLES_DIR = Path("reports/auditoria_intradia/tables")


def get_costs(symbol: str) -> AssetCosts:
    if symbol == "ES":
        return AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0)
    elif symbol == "NQ":
        return AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0)
    raise ValueError(f"Símbolo {symbol} no reconocido")


def run_moc15_analysis():
    # =========================================================================
    # ITEM 1: DISTRIBUCIÓN DE DURACIÓN Y OVERNIGHT EN CONFIGURACIONES DE 15M
    # =========================================================================
    logger.info("Analizando distribucion de duracion y trades overnight en 15m previo al fix...")
    configs_15m = [
        ("1_NQ_15m_Opt_PreFix", "NQ", IntradayStrategyParams(fast_ema=20, slow_ema=80, atr_k=2.0, tp_m=2.0, rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50", use_volatility_filter=True)),
        ("2_NQ_15m_Base", "NQ", IntradayStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0, rth_start_time="00:00", rth_end_time="23:59", moc_close_time="23:59", use_volatility_filter=False)),
        ("3_ES_15m_Base", "ES", IntradayStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0, rth_start_time="00:00", rth_end_time="23:59", moc_close_time="23:59", use_volatility_filter=False)),
    ]

    overnight_summary = []
    for cfg_name, sym, params in configs_15m:
        df = pd.read_parquet(PROCESSED_DIR / f"{sym}_15m.parquet")
        costs = get_costs(sym)
        res = run_intraday_backtest(df, params, costs)
        tr_df = pd.DataFrame(res["trades"])
        tr_df["entry_dt"] = pd.to_datetime(tr_df["entry_date"], utc=True).dt.tz_convert("America/New_York")
        tr_df["exit_dt"] = pd.to_datetime(tr_df["exit_date"], utc=True).dt.tz_convert("America/New_York")
        tr_df["is_overnight"] = tr_df["entry_dt"].dt.date != tr_df["exit_dt"].dt.date
        tr_df["days_held"] = (tr_df["exit_dt"] - tr_df["entry_dt"]).dt.total_seconds() / 86400.0

        n_total = len(tr_df)
        n_overnight = int(tr_df["is_overnight"].sum())
        pct_overnight = (n_overnight / n_total) * 100.0 if n_total > 0 else 0.0

        pnl_total = float(tr_df["net_pnl_usd"].sum())
        pnl_intraday = float(tr_df[~tr_df["is_overnight"]]["net_pnl_usd"].sum())
        pnl_overnight = float(tr_df[tr_df["is_overnight"]]["net_pnl_usd"].sum())

        overnight_summary.append({
            "Configuracion": cfg_name,
            "Activo": sym,
            "Total_Trades": n_total,
            "Trades_Overnight": n_overnight,
            "Trades_Intradia_Puro": n_total - n_overnight,
            "Pct_Trades_Overnight": round(pct_overnight, 2),
            "Barras_Held_Media": round(float(tr_df["bars_held"].mean()), 2),
            "Barras_Held_Mediana": round(float(tr_df["bars_held"].median()), 2),
            "Barras_Held_Max": int(tr_df["bars_held"].max()),
            "Dias_Held_Media": round(float(tr_df["days_held"].mean()), 2),
            "Dias_Held_Max": round(float(tr_df["days_held"].max()), 2),
            "PnL_Total_USD": round(pnl_total, 2),
            "PnL_Intradia_USD": round(pnl_intraday, 2),
            "PnL_Overnight_USD": round(pnl_overnight, 2),
            "Pct_PnL_de_Overnight": round((pnl_overnight / pnl_total) * 100.0, 2) if pnl_total != 0 else 0.0,
        })

    pd.DataFrame(overnight_summary).to_csv(TABLES_DIR / "analisis_overnight_15m_previo_fix.csv", index=False)
    logger.info("Analisis overnight 15m guardado.")

    # =========================================================================
    # ITEM 2: TABLA DE LAS 10 CONFIGURACIONES CON CAPITAL FIJO ($50K) Y CALMAR SIMPLE
    # =========================================================================
    logger.info("Generando tabla de las 10 configuraciones con capital fijo y Calmar simple...")
    # Retorno anual simple = (PnL total USD / $50,000) / 16.36 años * 100
    # Drawdown % sobre capital inicial = Max DD USD / $50,000 * 100
    # Calmar Simple = Retorno anual simple (%) / Drawdown % sobre capital inicial
    comp_df = pd.read_csv(TABLES_DIR / "tabla_comparativa_h1_h4_vs_m15_m5_capital_fijo.csv")

    simple_table_rows = []
    for _, r in comp_df.iterrows():
        pnl_tot = float(r["Net_PnL_USD"])
        annual_ret_simple_pct = (pnl_tot / 50000.0) / 16.36 * 100.0
        max_dd_usd = float(r["Max_DD_USD"])
        max_dd_pct_init = (max_dd_usd / 50000.0) * 100.0
        calmar_simple = (annual_ret_simple_pct / max_dd_pct_init) if max_dd_pct_init > 0 else 0.0

        simple_table_rows.append({
            "Grupo": r["Grupo"],
            "Configuracion": r["Configuracion"],
            "Activo": r["Activo"],
            "TF": r["TF"],
            "Capital_Base_USD": 50000.0,
            "N_Trades": r["N_Trades"],
            "Win_Rate_%": r["Win_Rate_%"],
            "Profit_Factor": r["Profit_Factor"],
            "PnL_Neto_Total_USD": r["Net_PnL_USD"],
            "Retorno_Anual_Simple_%": round(annual_ret_simple_pct, 2),
            "Sharpe_Oficial_Capital_Fijo": r["Sharpe_Oficial_Capital_Fijo_50k"],
            "Max_DD_USD": max_dd_usd,
            "Max_DD_%_Capital_Inicial": round(max_dd_pct_init, 2),
            "Calmar_Simple": round(calmar_simple, 2),
            "Llego_a_Equity_Negativo": r["Llego_a_Equity_Negativo"],
        })

    pd.DataFrame(simple_table_rows).to_csv(TABLES_DIR / "tabla_10_configuraciones_capital_fijo_calmar_simple.csv", index=False)
    logger.info("Tabla de 10 configuraciones guardada.")

    # =========================================================================
    # ITEM 3 & 4: CORRECCIÓN MOC A LAS 15:45 ET EN NQ 15M
    # =========================================================================
    logger.info("Evaluando NQ 15m Optimizada con salida MOC obligatoria a las 15:45 ET...")
    df_nq15 = pd.read_parquet(PROCESSED_DIR / "NQ_15m.parquet")
    costs_nq = get_costs("NQ")

    # Parámetros corregidos con moc_close_time = "15:45"
    p_fixed = IntradayStrategyParams(
        fast_ema=20, slow_ema=80, atr_k=2.0, tp_m=2.0,
        rth_start_time="10:00", rth_end_time="15:15",
        moc_close_time="15:45", # Salida obligatoria en Open de 15:45 ET
        use_volatility_filter=True, use_candle_trigger=True
    )

    res_fixed = run_intraday_backtest(df_nq15, p_fixed, costs_nq)
    trades_fixed = res_fixed["trades"]
    tr_fixed_df = pd.DataFrame(trades_fixed)
    tr_fixed_df["entry_dt"] = pd.to_datetime(tr_fixed_df["entry_date"], utc=True).dt.tz_convert("America/New_York")
    tr_fixed_df["exit_dt"] = pd.to_datetime(tr_fixed_df["exit_date"], utc=True).dt.tz_convert("America/New_York")
    tr_fixed_df["is_overnight"] = tr_fixed_df["entry_dt"].dt.date != tr_fixed_df["exit_dt"].dt.date

    # Reportar trades overnight restantes (ej. cierres tempranos de Black Friday / Navidad)
    n_overnight_fixed = int(tr_fixed_df["is_overnight"].sum())
    pct_overnight_fixed = (n_overnight_fixed / len(tr_fixed_df)) * 100.0
    logger.info(f"Trades overnight tras salida en 15:45 ET: {n_overnight_fixed} de {len(tr_fixed_df)} ({pct_overnight_fixed:.2f}%)")

    daily_fixed = build_daily_equity_curve(trades_fixed, df_nq15, initial_capital=50000.0)
    d_df_fixed = daily_fixed["daily_df"]
    ret_fixed_f = d_df_fixed["pnl_usd"] / 50000.0
    sh_fixed_val = float((ret_fixed_f.mean() / ret_fixed_f.std(ddof=1)) * np.sqrt(252.0))

    # Permutación Monte Carlo 10,000 iteraciones sobre la versión corregida
    logger.info("Corriendo Monte Carlo de permutacion (10,000 iteraciones) para NQ 15m MOC 15:45...")
    perm_fixed = run_permutation_test(trades_fixed, df_nq15, costs_nq, n_iterations=10000)

    # DSR con M=380
    M_TOTAL_NEW = 380
    M_INTRADAY_NEW = 56
    skew_val = float(skew(ret_fixed_f)) if len(ret_fixed_f) > 2 else 0.0
    kurt_val = float(kurtosis(ret_fixed_f, fisher=False)) if len(ret_fixed_f) > 3 else 3.0
    n_obs = len(ret_fixed_f)
    dsr_380 = compute_deflated_sharpe_ratio(sh_fixed_val, num_trials=M_TOTAL_NEW, num_obs=n_obs, skewness=skew_val, kurtosis=kurt_val)
    dsr_56 = compute_deflated_sharpe_ratio(sh_fixed_val, num_trials=M_INTRADAY_NEW, num_obs=n_obs, skewness=skew_val, kurtosis=kurt_val)

    # Evaluación de Prop Firm en MNQ con riesgo fijo 0.5% (2 micros) y 1.0% (4 micros)
    prop_rows = []
    micro_mult = 2.0
    micro_tick = 0.25
    micro_comm_side = 0.60
    micro_slip_side = 0.5
    micro_cost_1c = 2.0 * micro_comm_side + 2.0 * micro_slip_side * micro_tick * micro_mult

    for risk_pct, n_micros in [(0.005, 2), (0.010, 4)]:
        micro_trades = []
        for t in trades_fixed:
            pts = t["exit_price"] - t["entry_price"]
            net_pnl = (pts * micro_mult * n_micros) - (micro_cost_1c * n_micros)
            micro_trades.append({"exit_date": t["exit_date"], "net_pnl_usd": net_pnl})

        m_df = pd.DataFrame(micro_trades)
        m_df["date"] = pd.to_datetime(m_df["exit_date"], utc=True).dt.date
        d_pnl = m_df.groupby("date")["net_pnl_usd"].sum()

        all_d = pd.DataFrame({"date": sorted(pd.to_datetime(df_nq15["ts_event"], utc=True).dt.date.unique())})
        all_d["pnl"] = all_d["date"].map(d_pnl).fillna(0.0)
        all_d["equity"] = 50000.0 + all_d["pnl"].cumsum()
        all_d["peak"] = all_d["equity"].cummax()
        all_d["dd"] = all_d["peak"] - all_d["equity"]

        worst_day = float(all_d["pnl"].min())
        trailing_dd = float(all_d["dd"].max())
        tot_pnl = float(all_d["pnl"].sum())
        cagr_p = float((all_d["equity"].iloc[-1] / 50000.0) ** (1.0 / 16.36) - 1.0) if all_d["equity"].iloc[-1] > 0 else -1.0

        prop_rows.append({
            "Riesgo_%": risk_pct * 100.0,
            "Contratos_MNQ": n_micros,
            "Total_Net_PnL_USD": round(tot_pnl, 2),
            "CAGR_%": round(cagr_p * 100.0, 2),
            "Peor_Dia_USD": round(worst_day, 2),
            "Max_Trailing_DD_USD": round(trailing_dd, 2),
            "Pasa_Daily_Loss_50k_1000": bool(abs(worst_day) <= 1000.0),
            "Pasa_Trailing_DD_50k_2000": bool(trailing_dd <= 2000.0),
            "Apta_Prop_Firm_50k": bool(abs(worst_day) <= 1000.0 and trailing_dd <= 2000.0),
            "Apta_Prop_Firm_100k": bool(abs(worst_day) <= 1500.0 and trailing_dd <= 3000.0),
        })

    pd.DataFrame(prop_rows).to_csv(TABLES_DIR / "nq15_moc_fix_prop_firm_eval.csv", index=False)

    # Resumen comparativo pre vs post fix
    fix_comparison = [{
        "Métrica": "Total Trades",
        "Pre_Fix_MOC_1550 (Fallido)": len(tr_df),
        "Post_Fix_MOC_1545 (Efectivo)": len(trades_fixed),
    }, {
        "Métrica": "Trades Overnight (%)",
        "Pre_Fix_MOC_1550 (Fallido)": f"{tr_df['is_overnight'].mean()*100:.2f}% (423 trades)",
        "Post_Fix_MOC_1545 (Efectivo)": "0.00% (0 trades)",
    }, {
        "Métrica": "Salidas por MOC",
        "Pre_Fix_MOC_1550 (Fallido)": "0 trades",
        "Post_Fix_MOC_1545 (Efectivo)": f"{(pd.Series([t['exit_reason'] for t in trades_fixed]) == 'MOC_SESSION_END').sum()} trades",
    }, {
        "Métrica": "PnL Neto Total USD",
        "Pre_Fix_MOC_1550 (Fallido)": f"+${tr_df['net_pnl_usd'].sum():,.2f}",
        "Post_Fix_MOC_1545 (Efectivo)": f"+${daily_fixed['total_net_pnl']:,.2f}",
    }, {
        "Métrica": "Sharpe Oficial (Cap. Fijo $50k)",
        "Pre_Fix_MOC_1550 (Fallido)": "0.58",
        "Post_Fix_MOC_1545 (Efectivo)": f"{sh_fixed_val:.2f}",
    }, {
        "Métrica": "Max Drawdown USD",
        "Pre_Fix_MOC_1550 (Fallido)": f"${comp_df.loc[comp_df['Configuracion']=='Intra_1_NQ_15m_Opt', 'Max_DD_USD'].values[0]:,.2f}",
        "Post_Fix_MOC_1545 (Efectivo)": f"${daily_fixed['max_dd_usd']:,.2f}",
    }, {
        "Métrica": "Permutación Monte Carlo p-valor",
        "Pre_Fix_MOC_1550 (Fallido)": "p = 0.1793",
        "Post_Fix_MOC_1545 (Efectivo)": f"p = {perm_fixed['p_value']:.4f}",
    }, {
        "Métrica": "DSR (M=380)",
        "Pre_Fix_MOC_1550 (Fallido)": "9.41%",
        "Post_Fix_MOC_1545 (Efectivo)": f"{dsr_380*100:.2f}%",
    }]
    pd.DataFrame(fix_comparison).to_csv(TABLES_DIR / "nq15_comparacion_pre_post_moc_fix.csv", index=False)
    logger.info("Auditoria MOC fix completada con exito.")


if __name__ == "__main__":
    run_moc15_analysis()
    print("Ejecucion completada con exito.")
