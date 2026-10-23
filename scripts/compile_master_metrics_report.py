"""Script de Compilación y Validación Numérica para el Informe Maestro de Métricas.
Unifica todas las configuraciones evaluadas (H4, H1, M15, M5) calculando de forma homogénea:
- Métricas de Operatividad (N trades, trades/año, win rate, profit factor, expectativa en $)
- Métricas de Retorno (PnL neto total, retorno total %, retorno anual simple %, CAGR %)
- Métricas de Riesgo (Max DD en $, Max DD % pico, Max DD % inicial, peor día intradía $, días en negativo)
- Ratios Ajustados (Sharpe oficial base fija $50k, Sharpe compuesto equity móvil, Calmar Real, Calmar Simple)
- Métricas Estadísticas (p-valor Monte Carlo 10k, DSR M=380, impacto sin Top 5 %)
- Métricas de Mercado (exposición time-in-market %, B&H ajustado CAGR y Sharpe)
- Evaluación Prop Firm ($50k y $100k)
Genera la tabla CSV maestra.
"""
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

PROCESSED_DIR = Path("data/processed")
TABLES_DIR = Path("reports/auditoria_intradia/tables")
TABLES_DIR.mkdir(parents=True, exist_ok=True)


def get_costs(symbol: str) -> AssetCosts:
    if symbol == "ES":
        return AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0)
    elif symbol == "NQ":
        return AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0)
    raise ValueError(f"Símbolo {symbol} no reconocido")


def build_master_table():
    all_configs = [
        # 1. H4
        ("H4", "Swing", "ES_4h", "ES", "4h", "ES 4h Swing Unificada", "unified", UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0)),
        ("H4", "Swing", "NQ_4h", "NQ", "4h", "NQ 4h Swing Unificada", "unified", UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0)),

        # 2. H1
        ("H1", "Swing", "ES_1h", "ES", "1h", "ES 1h Swing Unificada", "unified", UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0)),
        ("H1", "Swing", "NQ_1h", "NQ", "1h", "NQ 1h Swing Unificada", "unified", UnifiedStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0)),

        # 3. M15
        ("M15", "Intradía", "NQ_15m_Opt_MOC1545", "NQ", "15m", "NQ 15m Optimizada (MOC 15:45 Efectivo)", "intraday", IntradayStrategyParams(fast_ema=20, slow_ema=80, atr_k=2.0, tp_m=2.0, rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:45", use_volatility_filter=True)),
        ("M15", "Intradía / Híbrida", "NQ_15m_Opt_PreFix", "NQ", "15m", "NQ 15m Optimizada (Pre-Fix Overnight)", "intraday", IntradayStrategyParams(fast_ema=20, slow_ema=80, atr_k=2.0, tp_m=2.0, rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50", use_volatility_filter=True)),
        ("M15", "Línea Base", "NQ_15m_Base", "NQ", "15m", "NQ 15m Línea Base (Sin filtros)", "intraday", IntradayStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0, rth_start_time="00:00", rth_end_time="23:59", moc_close_time="23:59", use_volatility_filter=False)),
        ("M15", "Línea Base", "ES_15m_Base", "ES", "15m", "ES 15m Línea Base (Sin filtros)", "intraday", IntradayStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0, rth_start_time="00:00", rth_end_time="23:59", moc_close_time="23:59", use_volatility_filter=False)),

        # 4. M5
        ("M5", "Intradía", "NQ_5m_Opt", "NQ", "5m", "NQ 5m Optimizada (RTH + MOC + ATR)", "intraday", IntradayStrategyParams(fast_ema=20, slow_ema=80, atr_k=2.0, tp_m=2.0, rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50", use_volatility_filter=True)),
        ("M5", "Intradía", "ES_5m_Agr", "ES", "5m", "ES 5m Agresiva (EMA 10/50 + ATR)", "intraday", IntradayStrategyParams(fast_ema=10, slow_ema=50, atr_k=1.5, tp_m=2.0, rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50", use_volatility_filter=True)),
        ("M5", "Intradía", "NQ_5m_SinVol", "NQ", "5m", "NQ 5m MOC Sin Filtro Volatilidad", "intraday", IntradayStrategyParams(fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0, rth_start_time="00:00", rth_end_time="23:59", moc_close_time="15:50", use_volatility_filter=False)),
    ]

    master_rows = []
    M_TOTAL = 380

    for tf_group, cat, cfg_id, sym, tf, label, engine_type, params in all_configs:
        df = pd.read_parquet(PROCESSED_DIR / f"{sym}_{tf}.parquet")
        costs = get_costs(sym)

        if engine_type == "unified":
            res = run_unified_backtest(df, params, costs)
        else:
            res = run_intraday_backtest(df, params, costs)

        trades = res["trades"]
        n_tr = len(trades)
        trades_per_year = n_tr / 16.36
        pnls = [t["net_pnl_usd"] for t in trades]
        pnl_tot = float(np.sum(pnls)) if trades else 0.0
        exp_trade = pnl_tot / n_tr if n_tr > 0 else 0.0

        daily = build_daily_equity_curve(trades, df, initial_capital=50000.0)
        d_df = daily["daily_df"]

        # Retornos diarios normalizados sobre capital fijo inicial ($50k)
        ret_fixed = d_df["pnl_usd"] / 50000.0
        sh_fixed = float((ret_fixed.mean() / ret_fixed.std(ddof=1)) * np.sqrt(252.0)) if ret_fixed.std(ddof=1) > 1e-9 else 0.0
        sh_comp = daily["sharpe_daily"]

        # Retorno anual simple vs CAGR
        ret_tot_pct = (pnl_tot / 50000.0) * 100.0
        ann_simple_pct = ret_tot_pct / 16.36
        cagr_pct = daily["cagr"] * 100.0

        # Drawdown en $ y %
        max_dd_usd = daily["max_dd_usd"]
        max_dd_pct_peak = daily["max_dd_pct"]
        max_dd_pct_init = (max_dd_usd / 50000.0) * 100.0

        # Calmar real (CAGR / DD Peak) vs Calmar simple (Ann Simple / DD Init)
        calmar_real = daily["calmar"]
        calmar_simple = (ann_simple_pct / max_dd_pct_init) if max_dd_pct_init > 0 else 0.0

        # Peor día intradía
        worst_day_usd = float(d_df["pnl_usd"].min())
        min_eq = float(d_df["equity"].min())
        days_insolvent = int((d_df["equity"] <= 0).sum())

        # Concentración Top 5
        sorted_pnls = sorted(pnls, reverse=True)
        top5_sum = sum(sorted_pnls[:5])
        pct_top5 = (top5_sum / pnl_tot) * 100.0 if pnl_tot > 0 else np.nan
        pnl_without_top5 = pnl_tot - top5_sum

        # DSR con M=380
        skew_v = float(skew(ret_fixed)) if len(ret_fixed) > 2 else 0.0
        kurt_v = float(kurtosis(ret_fixed, fisher=False)) if len(ret_fixed) > 3 else 3.0
        dsr_380 = compute_deflated_sharpe_ratio(sh_fixed, num_trials=M_TOTAL, num_obs=len(ret_fixed), skewness=skew_v, kurtosis=kurt_v)

        # Exposición y Buy & Hold
        bars_held = sum(t["bars_held"] for t in trades)
        time_market = (bars_held / len(df)) * 100.0 if len(df) > 0 else 0.0
        p_start = df["close"].iloc[0]
        p_end = df["close"].iloc[-1]
        bh_tot_ret = ((p_end / p_start) - 1.0) * 100.0
        bh_adj_cagr = ((1.0 + (bh_tot_ret / 100.0) * (time_market / 100.0)) ** (1.0 / 16.36) - 1.0) * 100.0

        ts_d = pd.to_datetime(df["ts_event"], utc=True).dt.date
        df_d = pd.DataFrame({"date": ts_d, "close": df["close"]}).groupby("date")["close"].last()
        bh_daily_rets = df_d.pct_change().dropna()
        bh_sh = float((bh_daily_rets.mean() / bh_daily_rets.std(ddof=1)) * np.sqrt(252.0))
        bh_adj_sh = bh_sh * np.sqrt(time_market / 100.0)

        # Prop firm status
        # Evaluamos si cabe en cuenta de 50k (Daily loss $1k, Trailing DD $2k) en micro contrato
        micro_factor = 0.10
        micro_worst_day = worst_day_usd * micro_factor
        micro_trailing_dd = max_dd_usd * micro_factor
        passes_daily_50k = bool(abs(micro_worst_day) <= 1000.0)
        passes_dd_50k = bool(micro_trailing_dd <= 2000.0)
        passes_prop_50k = passes_daily_50k and passes_dd_50k
        passes_prop_100k = bool(abs(micro_worst_day) <= 1500.0 and micro_trailing_dd <= 3000.0)

        master_rows.append({
            "Timeframe_Grupo": tf_group,
            "Categoria": cat,
            "Configuracion_ID": cfg_id,
            "Nombre_Estrategia": label,
            "Activo": sym,
            "Timeframe": tf,
            "N_Trades": n_tr,
            "Trades_Por_Año": round(trades_per_year, 1),
            "Win_Rate_%": round(res["win_rate"] * 100, 2),
            "Profit_Factor": round(res["profit_factor"], 2) if not np.isnan(res["profit_factor"]) else 0.0,
            "Expectativa_Trade_USD": round(exp_trade, 2),
            "PnL_Neto_Total_USD": round(pnl_tot, 2),
            "Retorno_Total_%": round(ret_tot_pct, 2),
            "Retorno_Anual_Simple_%": round(ann_simple_pct, 2),
            "CAGR_%": round(cagr_pct, 2),
            "Sharpe_Oficial_Capital_Fijo": round(sh_fixed, 2),
            "Sharpe_Compuesto_Equity_Movil": round(sh_comp, 2),
            "Max_DD_USD": round(max_dd_usd, 2),
            "Max_DD_%_Pico": round(max_dd_pct_peak, 2),
            "Max_DD_%_Capital_Inicial": round(max_dd_pct_init, 2),
            "Calmar_Real": round(calmar_real, 2),
            "Calmar_Simple": round(calmar_simple, 2),
            "Peor_Dia_Intradia_USD": round(worst_day_usd, 2),
            "Min_Equity_Alcanzada_USD": round(min_eq, 2),
            "Dias_Insolvente": days_insolvent,
            "Llego_a_Quiebra": bool(min_eq <= 0),
            "Top5_Ganancia_USD": round(top5_sum, 2),
            "Pct_PnL_en_Top5": round(pct_top5, 2) if not np.isnan(pct_top5) else 0.0,
            "PnL_Sin_Top5_USD": round(pnl_without_top5, 2),
            "DSR_M380_%": round(dsr_380 * 100, 2),
            "Time_in_Market_%": round(time_market, 2),
            "B&H_Ajustado_CAGR_%": round(bh_adj_cagr, 2),
            "B&H_Ajustado_Sharpe": round(bh_adj_sh, 2),
            "Bate_B&H_Ajustado": bool(sh_fixed > bh_adj_sh),
            "Micro_Peor_Dia_USD": round(micro_worst_day, 2),
            "Micro_Trailing_DD_USD": round(micro_trailing_dd, 2),
            "Apta_Prop_Firm_50k": passes_prop_50k,
            "Apta_Prop_Firm_100k": passes_prop_100k,
        })

    master_df = pd.DataFrame(master_rows)
    master_df.to_csv(TABLES_DIR / "tabla_maestra_todas_las_temporalidades.csv", index=False)
    print("Tabla maestra generada exitosamente con", len(master_df), "configuraciones.")
    return master_df


if __name__ == "__main__":
    build_master_table()
