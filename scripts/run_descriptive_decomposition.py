"""Script de Análisis Descriptivo Cuantitativo: Descomposición de Retornos RTH vs Overnight.
1. Descompone el retorno diario del subyacente (NQ y ES) en:
   - Sesión regular RTH (09:30 - 16:00 ET)
   - Fuera de sesión (Overnight: salto de Close_t a Open_t+1)
   Reporta retorno medio anualizado, Sharpe de cada segmento y % de contribución por año (2010 - 2026).
2. Descompone barra a barra el PnL de la versión original de NQ 15m (con posiciones overnight):
   Mide el movimiento de precio de cada barra mientras la posición está abierta:
   - Movimiento en horario regular RTH
   - Movimiento en saltos de precio overnight (fuera de sesión)
   Reporta PnL acumulado y por año.
3. Almacena tablas CSV y genera informe descriptivo neutral.
"""
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

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

PROCESSED_DIR = Path("data/processed")
TABLES_DIR = Path("reports/auditoria_intradia/tables")
TABLES_DIR.mkdir(parents=True, exist_ok=True)


def analyze_market_rth_vs_overnight(symbol: str) -> pd.DataFrame:
    df = pd.read_parquet(PROCESSED_DIR / f"{symbol}_15m.parquet")
    ts = pd.to_datetime(df["ts_event"], utc=True).dt.tz_convert("America/New_York")
    df["date"] = ts.dt.date

    days = sorted(df["date"].unique())
    first_b = df.groupby("date").first()
    last_b = df.groupby("date").last()

    day_df = pd.DataFrame({"date": days})
    day_df["year"] = pd.to_datetime(day_df["date"]).dt.year
    day_df["open_rth"] = day_df["date"].map(first_b["open"])
    day_df["close_rth"] = day_df["date"].map(last_b["close"])

    # RTH return = close_rth / open_rth - 1
    day_df["ret_rth"] = day_df["close_rth"] / day_df["open_rth"] - 1.0

    # Overnight return = open_rth[t] / close_rth[t-1] - 1
    day_df["prev_close_rth"] = day_df["close_rth"].shift(1)
    day_df["ret_overnight"] = day_df["open_rth"] / day_df["prev_close_rth"] - 1.0

    # Total daily return = close_rth[t] / close_rth[t-1] - 1
    day_df["ret_total"] = day_df["close_rth"] / day_df["prev_close_rth"] - 1.0

    # Agrupar por año
    yearly_rows = []
    years = sorted(day_df["year"].unique())

    for yr in years:
        sub = day_df[day_df["year"] == yr].dropna(subset=["ret_overnight", "ret_total"])
        n_days = len(sub)
        if n_days < 5:
            continue

        # Retorno medio anualizado (%): media * 252 * 100
        mean_rth = sub["ret_rth"].mean() * 252.0 * 100.0
        mean_overnight = sub["ret_overnight"].mean() * 252.0 * 100.0
        mean_total = sub["ret_total"].mean() * 252.0 * 100.0

        std_rth = sub["ret_rth"].std(ddof=1)
        std_overnight = sub["ret_overnight"].std(ddof=1)
        std_total = sub["ret_total"].std(ddof=1)

        sh_rth = (sub["ret_rth"].mean() / std_rth) * np.sqrt(252.0) if std_rth > 1e-9 else 0.0
        sh_overnight = (sub["ret_overnight"].mean() / std_overnight) * np.sqrt(252.0) if std_overnight > 1e-9 else 0.0
        sh_total = (sub["ret_total"].mean() / std_total) * np.sqrt(252.0) if std_total > 1e-9 else 0.0

        # % del retorno total (atribución aditiva simple)
        sum_components = mean_rth + mean_overnight
        pct_rth = (mean_rth / sum_components) * 100.0 if abs(sum_components) > 1e-6 else 50.0
        pct_overnight = (mean_overnight / sum_components) * 100.0 if abs(sum_components) > 1e-6 else 50.0

        yearly_rows.append({
            "Activo": symbol,
            "Año": yr,
            "N_Días": n_days,
            "Ret_Medio_RTH_%": round(mean_rth, 2),
            "Sharpe_RTH": round(sh_rth, 2),
            "Ret_Medio_Overnight_%": round(mean_overnight, 2),
            "Sharpe_Overnight": round(sh_overnight, 2),
            "Ret_Medio_Total_%": round(mean_total, 2),
            "Sharpe_Total": round(sh_total, 2),
            "Pct_Contrib_RTH_%": round(pct_rth, 2),
            "Pct_Contrib_Overnight_%": round(pct_overnight, 2),
        })

    # Resumen Global (2010 - 2026)
    sub_all = day_df.dropna(subset=["ret_overnight", "ret_total"])
    mean_rth_all = sub_all["ret_rth"].mean() * 252.0 * 100.0
    mean_ovn_all = sub_all["ret_overnight"].mean() * 252.0 * 100.0
    mean_tot_all = sub_all["ret_total"].mean() * 252.0 * 100.0
    sh_rth_all = (sub_all["ret_rth"].mean() / sub_all["ret_rth"].std(ddof=1)) * np.sqrt(252.0)
    sh_ovn_all = (sub_all["ret_overnight"].mean() / sub_all["ret_overnight"].std(ddof=1)) * np.sqrt(252.0)
    sh_tot_all = (sub_all["ret_total"].mean() / sub_all["ret_total"].std(ddof=1)) * np.sqrt(252.0)
    sum_all = mean_rth_all + mean_ovn_all
    pct_rth_all = (mean_rth_all / sum_all) * 100.0
    pct_ovn_all = (mean_ovn_all / sum_all) * 100.0

    yearly_rows.append({
        "Activo": symbol,
        "Año": "GLOBAL (2010-2026)",
        "N_Días": len(sub_all),
        "Ret_Medio_RTH_%": round(mean_rth_all, 2),
        "Sharpe_RTH": round(sh_rth_all, 2),
        "Ret_Medio_Overnight_%": round(mean_ovn_all, 2),
        "Sharpe_Overnight": round(sh_ovn_all, 2),
        "Ret_Medio_Total_%": round(mean_tot_all, 2),
        "Sharpe_Total": round(sh_tot_all, 2),
        "Pct_Contrib_RTH_%": round(pct_rth_all, 2),
        "Pct_Contrib_Overnight_%": round(pct_ovn_all, 2),
    })

    return pd.DataFrame(yearly_rows)


def analyze_strategy_bar_by_bar_decomposition() -> pd.DataFrame:
    df = pd.read_parquet(PROCESSED_DIR / "NQ_15m.parquet")
    costs = AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5)
    params = IntradayStrategyParams(fast_ema=20, slow_ema=80, rth_start_time="10:00", rth_end_time="15:15", moc_close_time="15:50")
    res = run_intraday_backtest(df, params, costs)
    trades = res["trades"]

    ts = pd.to_datetime(df["ts_event"], utc=True).dt.tz_convert("America/New_York")
    df["date"] = ts.dt.date
    dates_idx = {d: i for i, d in enumerate(df["ts_event"].values)}

    trade_decomp_rows = []
    fixed_cost = 2.0 * costs.commission_per_side + 2.0 * costs.slippage_per_side * costs.tick_size * costs.multiplier

    for t in trades:
        e_idx = dates_idx[t["entry_date"]]
        x_idx = dates_idx[t["exit_date"]]
        entry_p = t["entry_price"]
        exit_p = t["exit_price"]
        net_pnl = t["net_pnl_usd"]

        rth_pts = 0.0
        ovn_pts = 0.0

        if e_idx == x_idx:
            # Trade intradía puro dentro de una sola barra
            rth_pts = (exit_p - entry_p)
        else:
            # Barra de entrada
            rth_pts += (df["close"].iloc[e_idx] - entry_p)

            # Barras intermedias
            for b in range(e_idx + 1, x_idx):
                # Salto nocturno si hay cambio de día
                if df["date"].iloc[b] != df["date"].iloc[b-1]:
                    ovn_pts += (df["open"].iloc[b] - df["close"].iloc[b-1])
                else:
                    rth_pts += (df["open"].iloc[b] - df["close"].iloc[b-1])
                # Movimiento dentro de la barra RTH
                rth_pts += (df["close"].iloc[b] - df["open"].iloc[b])

            # Barra de salida
            if df["date"].iloc[x_idx] != df["date"].iloc[x_idx-1]:
                ovn_pts += (df["open"].iloc[x_idx] - df["close"].iloc[x_idx-1])
            else:
                rth_pts += (df["open"].iloc[x_idx] - df["close"].iloc[x_idx-1])
            rth_pts += (exit_p - df["open"].iloc[x_idx])

        # Verificación telescópica
        total_pts = rth_pts + ovn_pts
        expected_pts = exit_p - entry_p
        assert abs(total_pts - expected_pts) < 1e-4, f"Discrepancia en trade: {total_pts} vs {expected_pts}"

        rth_usd = rth_pts * costs.multiplier
        ovn_usd = ovn_pts * costs.multiplier

        trade_decomp_rows.append({
            "entry_date": t["entry_date"],
            "exit_date": t["exit_date"],
            "year": pd.to_datetime(t["exit_date"]).year,
            "net_pnl_usd": net_pnl,
            "gross_pnl_usd": net_pnl + fixed_cost,
            "rth_pnl_usd": rth_usd,
            "ovn_pnl_usd": ovn_usd,
            "bars_held": t["bars_held"],
            "is_overnight": bool(ovn_pts != 0.0),
        })

    td_df = pd.DataFrame(trade_decomp_rows)

    # Agrupar por año
    yearly_strat_rows = []
    years = sorted(td_df["year"].unique())

    for yr in years:
        sub = td_df[td_df["year"] == yr]
        n_tr = len(sub)
        n_ovn = int(sub["is_overnight"].sum())
        pnl_net = float(sub["net_pnl_usd"].sum())
        pnl_gross = float(sub["gross_pnl_usd"].sum())
        pnl_rth = float(sub["rth_pnl_usd"].sum())
        pnl_ovn = float(sub["ovn_pnl_usd"].sum())

        pct_ovn_contrib = (pnl_ovn / pnl_gross) * 100.0 if pnl_gross != 0 else 0.0
        pct_rth_contrib = (pnl_rth / pnl_gross) * 100.0 if pnl_gross != 0 else 0.0

        yearly_strat_rows.append({
            "Año": yr,
            "Total_Trades": n_tr,
            "Trades_Con_Overnight": n_ovn,
            "Trades_Intradia_Puros": n_tr - n_ovn,
            "PnL_Neto_Total_USD": round(pnl_net, 2),
            "PnL_Bruto_Total_USD": round(pnl_gross, 2),
            "PnL_RTH_Barras_USD": round(pnl_rth, 2),
            "PnL_Overnight_Gaps_USD": round(pnl_ovn, 2),
            "Pct_Contrib_RTH_%": round(pct_rth_contrib, 2),
            "Pct_Contrib_Overnight_%": round(pct_ovn_contrib, 2),
        })

    # Fila Global
    pnl_net_all = float(td_df["net_pnl_usd"].sum())
    pnl_gross_all = float(td_df["gross_pnl_usd"].sum())
    pnl_rth_all = float(td_df["rth_pnl_usd"].sum())
    pnl_ovn_all = float(td_df["ovn_pnl_usd"].sum())
    pct_ovn_all = (pnl_ovn_all / pnl_gross_all) * 100.0
    pct_rth_all = (pnl_rth_all / pnl_gross_all) * 100.0

    yearly_strat_rows.append({
        "Año": "GLOBAL (2010-2026)",
        "Total_Trades": len(td_df),
        "Trades_Con_Overnight": int(td_df["is_overnight"].sum()),
        "Trades_Intradia_Puros": int((~td_df["is_overnight"]).sum()),
        "PnL_Neto_Total_USD": round(pnl_net_all, 2),
        "PnL_Bruto_Total_USD": round(pnl_gross_all, 2),
        "PnL_RTH_Barras_USD": round(pnl_rth_all, 2),
        "PnL_Overnight_Gaps_USD": round(pnl_ovn_all, 2),
        "Pct_Contrib_RTH_%": round(pct_rth_all, 2),
        "Pct_Contrib_Overnight_%": round(pct_ovn_all, 2),
    })

    return pd.DataFrame(yearly_strat_rows)


def main():
    print("Iniciando análisis descriptivo de descomposición...")
    nq_market_df = analyze_market_rth_vs_overnight("NQ")
    es_market_df = analyze_market_rth_vs_overnight("ES")

    market_combined = pd.concat([nq_market_df, es_market_df], ignore_index=True)
    market_combined.to_csv(TABLES_DIR / "descomposicion_mercado_rth_vs_overnight.csv", index=False)
    print("Tabla descomposicion_mercado_rth_vs_overnight.csv guardada.")

    strat_decomp_df = analyze_strategy_bar_by_bar_decomposition()
    strat_decomp_df.to_csv(TABLES_DIR / "descomposicion_nq15_estrategia_barras.csv", index=False)
    print("Tabla descomposicion_nq15_estrategia_barras.csv guardada.")


if __name__ == "__main__":
    main()
