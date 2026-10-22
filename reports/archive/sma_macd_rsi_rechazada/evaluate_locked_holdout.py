"""Evaluación final y única sobre el Holdout Bloqueado (2010-06 a 2017-12).
Ejecuta exclusivamente las dos configuraciones finalistas fijadas por validación
para ES y NQ, verificando previamente los hashes SHA-256 de integridad.
"""
from dataclasses import asdict
import hashlib
import json
import logging
from pathlib import Path
import numpy as np
import pandas as pd

from src.backtest.engine_sma_confluence import StrategyParams, AssetCosts, run_sma_confluence_backtest
from src.analysis.robustness import compute_deflated_sharpe_ratio
from src.analysis.inference import bootstrap_sharpe_distribution

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HOLDOUT_DIR = Path("data/locked_holdout")
HASH_FILE = HOLDOUT_DIR / "HOLDOUT_2010_2017_SHA256.txt"
REPORTS_DIR = Path("reports")
TABLES_DIR = REPORTS_DIR / "tables"


def verify_sha256_before_eval():
    """Verifica que ningún archivo haya sido modificado antes de la evaluación."""
    expected = {}
    with open(HASH_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    expected[parts[1]] = parts[0]

    for fname, exp_hash in expected.items():
        actual_hash = hashlib.sha256(open(HOLDOUT_DIR / fname, "rb").read()).hexdigest()
        if actual_hash != exp_hash:
            raise RuntimeError(f"VIOLACIÓN DE INTEGRIDAD EN HOLDOUT: {fname} no coincide con el commit original.")
    logger.info("Verificación SHA-256 exitosa. El Holdout está 100% íntegro e inalterado.")


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    verify_sha256_before_eval()

    # Configuraciones finalistas congeladas en la Etapa 4
    finalists = {
        "ES": StrategyParams(
            num_smas=3, fast_sma=30, mid_sma=100, slow_sma=200,
            macd_fast=16, macd_slow=35, macd_signal=9,
            rsi_period=14, atr_k=2.0, tp_m=2.0,
            use_macd=True, use_rsi=True
        ),
        "NQ": StrategyParams(
            num_smas=3, fast_sma=30, mid_sma=100, slow_sma=200,
            macd_fast=16, macd_slow=35, macd_signal=9,
            rsi_period=14, atr_k=3.0, tp_m=2.0,
            use_macd=True, use_rsi=True
        ),
    }

    costs_map = {
        "ES": AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5),
        "NQ": AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5),
    }

    base_capital = {
        "ES": 100000.0,
        "NQ": 150000.0,
    }

    results = {}
    summary_rows = []

    for sym in ["ES", "NQ"]:
        logger.info(f"Abriendo Holdout 2010-2017 para {sym}...")
        p_holdout = HOLDOUT_DIR / f"{sym}_holdout_2010_2017_4h.parquet"
        df_h = pd.read_parquet(p_holdout)

        params = finalists[sym]
        costs = costs_map[sym]
        cap = base_capital[sym]

        # 1. Backtest en Holdout de la Finalista
        res_h = run_sma_confluence_backtest(df_h, params, costs)

        # 2. Líneas Base en Holdout
        # A) Solo-SMA (sin MACD ni RSI)
        p_solo = StrategyParams(
            num_smas=params.num_smas, fast_sma=params.fast_sma, mid_sma=params.mid_sma, slow_sma=params.slow_sma,
            use_macd=False, use_rsi=False, atr_k=params.atr_k, tp_m=params.tp_m
        )
        res_solo = run_sma_confluence_backtest(df_h, p_solo, costs)

        # B) Buy and Hold
        p0 = df_h["close"].iloc[0]
        p1 = df_h["close"].iloc[-1]
        bnh_ret = (p1 / p0 - 1.0)
        bnh_pnl = bnh_ret * (p0 * costs.multiplier)

        # C) Tiempo en mercado
        tot_bars = len(df_h)
        held_bars = sum(t["bars_held"] for t in res_h["trades"])
        exp_time = (held_bars / tot_bars * 100.0) if tot_bars > 0 else 0.0

        # D) Drawdown relativo porcentual sobre capital base
        max_dd = res_h["max_drawdown"]
        dd_rel_pct = (max_dd / cap) * 100.0

        # E) Deflated Sharpe Ratio (M = 32 combinaciones del pre-registro)
        rets_h = np.array([t["return"] for t in res_h["trades"]])
        n_obs = len(rets_h)
        dsr = compute_deflated_sharpe_ratio(
            observed_sharpe=res_h["sharpe"] if not np.isnan(res_h["sharpe"]) else 0.0,
            num_trials=32,
            num_obs=n_obs,
            skewness=float(pd.Series(rets_h).skew()) if n_obs > 2 else 0.0,
            kurtosis=float(pd.Series(rets_h).kurt()) if n_obs > 3 else 3.0,
            annualization_factor=costs.annualization_factor,
        )

        # F) Bootstrap por bloques para intervalos de confianza del 95%
        if n_obs >= 30:
            _, ci_sharpe, p_val_h0 = bootstrap_sharpe_distribution(rets_h, n_reps=5000, annualization_factor=costs.annualization_factor)
        else:
            ci_sharpe = (np.nan, np.nan)
            p_val_h0 = np.nan

        # G) Verificación de Criterios de Aceptación Pre-registrados
        crit_trades = res_h["n_trades"] >= 100
        crit_sharpe = (not np.isnan(res_h["sharpe"])) and res_h["sharpe"] >= 1.00
        crit_pf = (not np.isnan(res_h["profit_factor"])) and res_h["profit_factor"] >= 1.30
        crit_dd = dd_rel_pct <= 20.0
        crit_dsr = dsr >= 0.95

        verdict = "PASSED" if (crit_trades and crit_sharpe and crit_pf and crit_dd and crit_dsr) else "REJECTED (FAIL)"

        summary_rows.append({
            "Activo": sym,
            "Periodo_Holdout": f"{df_h['ts_event'].iloc[0].date()} a {df_h['ts_event'].iloc[-1].date()} (7.5 años)",
            "Configuracion": f"{params.num_smas} SMAs ({params.fast_sma}/{params.mid_sma}/{params.slow_sma}), MACD({params.macd_fast},{params.macd_slow}), k={params.atr_k}, m={params.tp_m}",
            "Trades_Holdout": res_h["n_trades"],
            "Criterio_N_ge_100": "SI" if crit_trades else f"NO ({res_h['n_trades']} < 100)",
            "WinRate_Holdout": f"{res_h['win_rate']*100:.1f}%",
            "ProfitFactor_Holdout": f"{res_h['profit_factor']:.2f}" if not np.isnan(res_h["profit_factor"]) else "N/A",
            "Expectancy_USD": f"${res_h['avg_expectancy_usd']:.2f}",
            "Net_PnL_USD": f"${res_h['net_pnl_usd']:,.2f}",
            "Sharpe_Holdout": f"{res_h['sharpe']:.2f}" if not np.isnan(res_h["sharpe"]) else "N/A (<30 trades)",
            "Max_Drawdown_USD": f"${max_dd:,.2f} ({dd_rel_pct:.1f}% de ${cap:,.0f})",
            "Criterio_DD_le_20pct": "SI" if crit_dd else f"NO ({dd_rel_pct:.1f}% > 20%)",
            "Tiempo_Expuesto": f"{exp_time:.1f}%",
            "BuyAndHold_PnL": f"${bnh_pnl:,.2f} ({bnh_ret*100:.1f}%)",
            "Solo_SMA_Sharpe": f"{res_solo['sharpe']:.2f}" if not np.isnan(res_solo["sharpe"]) else "N/A (<30 trades)",
            "Solo_SMA_PnL": f"${res_solo['net_pnl_usd']:,.2f}",
            "Deflated_Sharpe_DSR": f"{dsr*100:.2f}%",
            "IC_Sharpe_95": f"[{ci_sharpe[0]:.2f}, {ci_sharpe[1]:.2f}]" if not np.isnan(ci_sharpe[0]) else "N/A",
            "Veredicto_Final": verdict,
        })

        results[sym] = {
            "params": asdict(params),
            "holdout_results": res_h,
            "benchmarks": {
                "solo_sma": res_solo,
                "buy_and_hold_pnl": bnh_pnl,
                "buy_and_hold_ret": bnh_ret,
            },
            "statistics": {
                "deflated_sharpe": dsr,
                "ci_sharpe_95": ci_sharpe,
                "p_val_h0": p_val_h0,
            },
            "verdict": verdict,
        }

    df_res = pd.DataFrame(summary_rows)
    csv_out = TABLES_DIR / "final_holdout_evaluation_summary.csv"
    df_res.to_csv(csv_out, index=False)
    with open(REPORTS_DIR / "final_holdout_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"Evaluación del Holdout 2010-2017 concluida. Resultados en {csv_out}")


if __name__ == "__main__":
    main()
