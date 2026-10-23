"""Script de Auditoría Cuantitativa Estricta de la Rama Intradía (M15 y M5).
Evalúa exactamente las 6 configuraciones pre-registradas sobre la curva de equity diaria:
1. NQ 15m: EMA 20/80 + RTH 10:00-15:15 ET + cierre MOC 15:50 ET + filtro ATR
2. NQ 15m: línea base sin filtros intradía
3. ES 15m: línea base sin filtros intradía
4. NQ 5m: EMA 20/80 + RTH + MOC + filtro ATR
5. ES 5m: EMA 10/50 agresiva + filtro ATR
6. NQ 5m: cierre MOC sin filtro de volatilidad
"""
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
from src.analysis.daily_equity_audit import (
    build_daily_equity_curve,
    run_permutation_test,
    run_concentration_test,
    compute_pnl_year_by_year,
)
from src.analysis.robustness import compute_deflated_sharpe_ratio
from src.backtest.engine_sma_confluence import AssetCosts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("intraday_audit")

PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports/auditoria_intradia")
TABLES_DIR = REPORTS_DIR / "tables"


def analyze_intraday_prop_firm(
    daily_df: pd.DataFrame,
    trades: List[Dict[str, Any]],
    scale: float = 1.0,
    cost_adjustment_per_trade: float = 0.0,
) -> Dict[str, Any]:
    """Calcula la pérdida máxima diaria (Daily Loss) y trailing drawdown para Prop Firms."""
    if daily_df.empty or not trades:
        return {"worst_day_pnl": 0.0, "max_trailing_dd": 0.0}

    # PnL ajustado a la escala (ej. 0.10 para micro)
    # Comisiones micro: RT MNQ es $1.70 vs Emini $9.00 (ahorro de $7.30 por trade)
    scaled_trades = []
    for t in trades:
        pnl_base = t["net_pnl_usd"] * scale + cost_adjustment_per_trade
        scaled_trades.append({"exit_date": t["exit_date"], "net_pnl_usd": pnl_base})

    tr_df = pd.DataFrame(scaled_trades)
    tr_df["date"] = pd.to_datetime(tr_df["exit_date"], utc=True).dt.date
    daily_pnl = tr_df.groupby("date")["net_pnl_usd"].sum()

    # Peor pérdida en un solo día
    worst_day_pnl = float(daily_pnl.min()) if len(daily_pnl) > 0 else 0.0

    # Curva de equity para Trailing Drawdown
    all_dates = daily_df["date"].values
    full_daily = pd.DataFrame({"date": all_dates})
    full_daily["pnl"] = full_daily["date"].map(daily_pnl).fillna(0.0)
    full_daily["equity"] = 50000.0 * scale + full_daily["pnl"].cumsum()
    full_daily["peak"] = full_daily["equity"].cummax()
    full_daily["dd"] = full_daily["peak"] - full_daily["equity"]

    max_trailing_dd = float(full_daily["dd"].max())

    return {
        "worst_day_pnl": worst_day_pnl,
        "max_trailing_dd": max_trailing_dd,
        "capital_base": 50000.0 * scale,
    }


def run_intraday_audit():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    costs_map = {
        "ES": AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0),
        "NQ": AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5, annualization_factor=252.0),
    }

    # Las 6 configuraciones exactas ordenadas por el usuario
    eval_matrix = [
        ("NQ", "15m", "1_NQ_15m_Optimizada", PROCESSED_DIR / "NQ_15m.parquet", IntradayStrategyParams(
            fast_ema=20, slow_ema=80, atr_k=2.0, tp_m=2.0,
            rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50",
            use_volatility_filter=True, use_candle_trigger=True, long_only=True
        )),
        ("NQ", "15m", "2_NQ_15m_Linea_Base", PROCESSED_DIR / "NQ_15m.parquet", IntradayStrategyParams(
            fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0,
            rth_start_time="00:00", rth_end_time="23:59", moc_close_time="23:59",
            use_volatility_filter=False, use_candle_trigger=True, long_only=True
        )),
        ("ES", "15m", "3_ES_15m_Linea_Base", PROCESSED_DIR / "ES_15m.parquet", IntradayStrategyParams(
            fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0,
            rth_start_time="00:00", rth_end_time="23:59", moc_close_time="23:59",
            use_volatility_filter=False, use_candle_trigger=True, long_only=True
        )),
        ("NQ", "5m", "4_NQ_5m_Optimizada", PROCESSED_DIR / "NQ_5m.parquet", IntradayStrategyParams(
            fast_ema=20, slow_ema=80, atr_k=2.0, tp_m=2.0,
            rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50",
            use_volatility_filter=True, use_candle_trigger=True, long_only=True
        )),
        ("ES", "5m", "5_ES_5m_Agresiva", PROCESSED_DIR / "ES_5m.parquet", IntradayStrategyParams(
            fast_ema=10, slow_ema=50, atr_k=1.5, tp_m=2.0,
            rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50",
            use_volatility_filter=True, use_candle_trigger=True, long_only=True
        )),
        ("NQ", "5m", "6_NQ_5m_MOC_Sin_Volatilidad", PROCESSED_DIR / "NQ_5m.parquet", IntradayStrategyParams(
            fast_ema=30, slow_ema=200, atr_k=3.0, tp_m=2.0,
            rth_start_time="00:00", rth_end_time="23:59", moc_close_time="15:50",
            use_volatility_filter=False, use_candle_trigger=True, long_only=True
        )),
    ]

    metrics_rows = []
    prop_rows = []
    perm_rows = []
    conc_rows = []

    M_TOTAL_CUMULATIVE = 344
    M_INTRADAY_LOCAL = 26
    INITIAL_CAPITAL = 50000.0

    for sym, tf, cfg_label, f_path, params in eval_matrix:
        if not f_path.exists():
            logger.warning(f"Archivo no encontrado: {f_path}")
            continue

        logger.info(f"Auditoría rigurosa para {cfg_label}...")
        df = pd.read_parquet(f_path)
        costs = costs_map[sym]

        # 1. Backtest
        res_bt = run_intraday_backtest(df, params, costs)
        trades = res_bt.get("trades", [])
        n_trades = len(trades)

        # 2. Curva de equity diaria ($50,000 USD de base fija)
        eq_res = build_daily_equity_curve(trades, df, initial_capital=INITIAL_CAPITAL)
        daily_df = eq_res["daily_df"]

        # Calcular Max Drawdown con las dos bases explícitas
        max_dd_usd = eq_res["max_dd_usd"]
        max_dd_pct_peak = eq_res["max_dd_pct"]  # Base: Pico de equity
        max_dd_pct_initial = (max_dd_usd / INITIAL_CAPITAL) * 100.0  # Base: Capital inicial $50k

        cagr_pct = eq_res["cagr"] * 100.0
        calmar_peak = cagr_pct / max_dd_pct_peak if max_dd_pct_peak > 0 else 0.0
        calmar_initial = cagr_pct / max_dd_pct_initial if max_dd_pct_initial > 0 else 0.0

        # Retorno total
        tot_ret_pct = eq_res["total_return_pct"]
        cum_ret_to_dd_ratio = tot_ret_pct / max_dd_pct_initial if max_dd_pct_initial > 0 else 0.0

        # DSR con M=344 y M=26
        dsr_344 = compute_deflated_sharpe_ratio(
            observed_sharpe=eq_res["sharpe_daily"],
            num_trials=M_TOTAL_CUMULATIVE,
            num_obs=eq_res["n_trading_days"],
            skewness=eq_res["skewness"],
            kurtosis=eq_res["kurtosis"],
            annualization_factor=252.0,
        )
        dsr_26 = compute_deflated_sharpe_ratio(
            observed_sharpe=eq_res["sharpe_daily"],
            num_trials=M_INTRADAY_LOCAL,
            num_obs=eq_res["n_trading_days"],
            skewness=eq_res["skewness"],
            kurtosis=eq_res["kurtosis"],
            annualization_factor=252.0,
        )

        metrics_rows.append({
            "Configuracion": cfg_label,
            "Activo": sym,
            "TF": tf,
            "N_Trades": n_trades,
            "Win_Rate_%": round(res_bt["win_rate"] * 100.0, 2),
            "Profit_Factor": round(res_bt["profit_factor"], 2) if not np.isnan(res_bt["profit_factor"]) else 0.0,
            "Net_PnL_USD": round(eq_res["total_net_pnl"], 2),
            "Retorno_Total_%": round(tot_ret_pct, 2),
            "CAGR_%": round(cagr_pct, 2),
            "Sharpe_Diario_sqrt252": round(eq_res["sharpe_daily"], 2),
            "Max_DD_USD": round(max_dd_usd, 2),
            "Max_DD_%_Base_Pico": round(max_dd_pct_peak, 2),
            "Max_DD_%_Base_Inicial": round(max_dd_pct_initial, 2),
            "Calmar_Real_CAGR_div_DD": round(calmar_peak, 2),
            "Ratio_RetornoTot_div_DD": round(cum_ret_to_dd_ratio, 2),
            "DSR_M344_%": round(dsr_344 * 100.0, 2),
            "DSR_M26_%": round(dsr_26 * 100.0, 2),
        })

        # 3. Prop Firm: Pérdida Máxima Diaria y Trailing DD
        # Micro contratos (1/10)
        # Costo por trade micro en NQ: $1.70 vs Emini $9.00 -> corrección de +$7.30 por trade
        # Costo por trade micro en ES: $2.45 vs Emini $16.50 -> corrección de +$14.05 por trade
        cost_corr = 0.0
        prop_emini = analyze_intraday_prop_firm(daily_df, trades, scale=1.0)
        prop_micro = analyze_intraday_prop_firm(daily_df, trades, scale=0.10, cost_adjustment_per_trade=cost_corr)

        fits_prop_50k_dd = prop_micro["max_trailing_dd"] <= 2000.0
        fits_prop_50k_daily = abs(prop_micro["worst_day_pnl"]) <= 1000.0
        fits_prop_100k_dd = prop_micro["max_trailing_dd"] <= 3000.0
        fits_prop_100k_daily = abs(prop_micro["worst_day_pnl"]) <= 1500.0

        prop_rows.append({
            "Configuracion": cfg_label,
            "Emini_Peor_Dia_USD": round(prop_emini["worst_day_pnl"], 2),
            "Emini_Max_Trailing_DD_USD": round(prop_emini["max_trailing_dd"], 2),
            "Emini_Cabe_Prop_50k": "NO (Quiebra)",
            "Micro_Peor_Dia_USD": round(prop_micro["worst_day_pnl"], 2),
            "Micro_Max_Trailing_DD_USD": round(prop_micro["max_trailing_dd"], 2),
            "Micro_Pasa_Perdida_Diaria_50k": "SÍ" if fits_prop_50k_daily else "NO (Excede $1,000)",
            "Micro_Pasa_Trailing_DD_50k": "SÍ" if fits_prop_50k_dd else "NO (Excede $2,000)",
            "Micro_Apta_Prop_50k": "SÍ" if (fits_prop_50k_daily and fits_prop_50k_dd) else "NO",
            "Micro_Apta_Prop_100k": "SÍ" if (fits_prop_100k_daily and fits_prop_100k_dd) else "NO",
        })

        # 4. Test de Concentración
        conc_res = run_concentration_test(trades, df, initial_capital=INITIAL_CAPITAL, top_n=5)
        conc_rows.append({
            "Configuracion": cfg_label,
            "PnL_Total_Con_Top5": round(conc_res.get("pnl_full", 0.0), 2),
            "PnL_Top5": round(conc_res.get("pnl_top5", 0.0), 2),
            "Pct_PnL_En_Top5": round(conc_res.get("pct_pnl_in_top5", 0.0), 2),
            "PnL_Sin_Top5": round(conc_res.get("pnl_without_top5", 0.0), 2),
            "Sharpe_Con_Top5": round(conc_res.get("sharpe_full", 0.0), 2),
            "Sharpe_Sin_Top5": round(conc_res.get("sharpe_without_top5", 0.0), 2),
        })

        # 5. Test de Permutación Monte Carlo (10,000 iteraciones)
        logger.info(f"Permutación 10k para {cfg_label}...")
        perm_res = run_permutation_test(trades, df, costs, n_iterations=10000, random_seed=42)
        perm_rows.append({
            "Configuracion": cfg_label,
            "PnL_Real_USD": round(perm_res["real_pnl"], 2),
            "PnL_Medio_Aleatorio_USD": round(perm_res["mean_random_pnl"], 2),
            "P_Valor_Empírico": round(perm_res["p_value"], 5),
            "Percentil_%": round(perm_res["percentile"], 2),
            "Bate_Al_Azar_p05": "SÍ" if perm_res["p_value"] < 0.05 else "NO",
        })

        # 6. Desglose anual
        y_df = compute_pnl_year_by_year(trades, df, initial_capital=INITIAL_CAPITAL)
        y_df.to_csv(TABLES_DIR / f"pnl_yearly_{cfg_label}.csv", index=False)

    # Exportar tablas consolidadas
    pd.DataFrame(metrics_rows).to_csv(TABLES_DIR / "intraday_metricas_diarias.csv", index=False)
    pd.DataFrame(prop_rows).to_csv(TABLES_DIR / "intraday_prop_firms_eval.csv", index=False)
    pd.DataFrame(conc_rows).to_csv(TABLES_DIR / "intraday_concentracion_top5.csv", index=False)
    pd.DataFrame(perm_rows).to_csv(TABLES_DIR / "intraday_permutacion_montecarlo.csv", index=False)

    logger.info("Auditoría intradiaria completada.")


if __name__ == "__main__":
    run_intraday_audit()
