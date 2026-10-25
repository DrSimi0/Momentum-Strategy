"""Script de Reconciliación Definitiva, Generación de Tablas Trade por Trade y Análisis Forense."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.strategies.intraday_ema200_strategy import (
    IntradayEma200Params,
    run_ema200_backtest,
)
from src.backtest.engine_sma_confluence import AssetCosts

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLES_DIR = PROJECT_ROOT / "reports" / "auditoria_intradia" / "tables"
TABLES_DIR.mkdir(parents=True, exist_ok=True)

costs = AssetCosts(
    asset_type="futures",
    multiplier=20.0,
    tick_size=0.25,
    commission_per_side=2.0,
    slippage_per_side=0.5,
    annualization_factor=252.0,
)

# Cargar dataset continuo de NQ 5m
df = pd.read_parquet(PROCESSED_DIR / "NQ_5m.parquet")
df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
df = df.sort_values("ts_event").reset_index(drop=True)

# -----------------------------------------------------------------------------
# 1. Backtest Solo Largos (Continuo 2010-2026)
# -----------------------------------------------------------------------------
p_long = IntradayEma200Params(
    trend_ema_period=200,
    atr_k=2.5,
    tp_m=3.0,
    trigger_type="price_cross",
    moc_close_time="15:50",
    use_volatility_filter=True,
    allow_short=False,
)
res_long = run_ema200_backtest(df, p_long, costs)
trades_long = res_long["trades"]
t_df = pd.DataFrame(trades_long)
t_df["entry_dt"] = pd.to_datetime(t_df["entry_date"], utc=True)
t_df["exit_dt"] = pd.to_datetime(t_df["exit_date"], utc=True)
t_df["year"] = t_df["entry_dt"].dt.year

# Reconciliación 2010 a 2021-10-20
cut_hist = pd.Timestamp("2021-10-20 00:00:00", tz="UTC")
trades_hist_df = t_df[t_df["entry_dt"] < cut_hist].copy().reset_index(drop=True)
trades_hist_df.to_csv(TABLES_DIR / "reconciliacion_trades_2010_2021_trade_by_trade.csv", index=False)

print(f"Reconciliación Histórica: {len(trades_hist_df)} trades, PnL total ${trades_hist_df['net_pnl_usd'].sum():,.2f}")

# -----------------------------------------------------------------------------
# 2. Análisis de Discrepancia en Test ($16,204 vs $16,926)
# -----------------------------------------------------------------------------
split_end = pd.Timestamp("2024-10-19 23:59:59", tz="UTC")
end_test = pd.Timestamp("2026-10-19 23:59:59", tz="UTC")

# Con dataset continuo (cifra oficial)
trades_test_cont = t_df[(t_df["entry_dt"] >= split_end) & (t_df["entry_dt"] <= end_test)].copy().reset_index(drop=True)
pnl_test_cont = trades_test_cont["net_pnl_usd"].sum()

# Con dataset truncado sin warm-up
df_trunc = df[df["ts_event"] >= split_end].copy().reset_index(drop=True)
res_trunc = run_ema200_backtest(df_trunc, p_long, costs)
trades_test_trunc = res_trunc["trades"]
t_trunc_df = pd.DataFrame(trades_test_trunc)
pnl_test_trunc = t_trunc_df["net_pnl_usd"].sum() if len(t_trunc_df) > 0 else 0.0

diff_pnl = pnl_test_trunc - pnl_test_cont
print(f"Test Continuo: {len(trades_test_cont)} trades, PnL ${pnl_test_cont:,.2f}")
print(f"Test Truncado: {len(trades_test_trunc)} trades, PnL ${pnl_test_trunc:,.2f}")
print(f"Diferencia: ${diff_pnl:,.2f} omitida por falta de warm-up en las primeras 200 barras.")

# Guardar trades del test continuo
trades_test_cont.to_csv(TABLES_DIR / "trades_test_continuo_oficial.csv", index=False)

# -----------------------------------------------------------------------------
# 3. Backtest Simétrica (Largos + Cortos)
# -----------------------------------------------------------------------------
p_sym = IntradayEma200Params(
    trend_ema_period=200,
    atr_k=2.5,
    tp_m=3.0,
    trigger_type="price_cross",
    moc_close_time="15:50",
    use_volatility_filter=True,
    allow_short=True,
)
res_sym = run_ema200_backtest(df, p_sym, costs)
trades_sym = res_sym["trades"]
t_sym_df = pd.DataFrame(trades_sym)
t_sym_df["entry_dt"] = pd.to_datetime(t_sym_df["entry_date"], utc=True)

trades_sym_test = t_sym_df[(t_sym_df["entry_dt"] >= split_end) & (t_sym_df["entry_dt"] <= end_test)].copy().reset_index(drop=True)
longs_sym = trades_sym_test[trades_sym_test["direction"] == "LONG"]
shorts_sym = trades_sym_test[trades_sym_test["direction"] == "SHORT"]

print(f"Simétrica Test: {len(trades_sym_test)} trades (Longs: {len(longs_sym)}, Shorts: {len(shorts_sym)})")
print(f"PnL Simétrica Test: Longs ${longs_sym['net_pnl_usd'].sum():,.2f} | Shorts ${shorts_sym['net_pnl_usd'].sum():,.2f} | Total ${trades_sym_test['net_pnl_usd'].sum():,.2f}")

trades_sym_test.to_csv(TABLES_DIR / "trades_simetrica_test_trade_by_trade.csv", index=False)

# -----------------------------------------------------------------------------
# 4. Análisis Trade por Trade de 2022
# -----------------------------------------------------------------------------
t_2022 = t_df[t_df["year"] == 2022].copy().sort_values("net_pnl_usd", ascending=False).reset_index(drop=True)
t_2022.to_csv(TABLES_DIR / "analisis_trades_2022_completo.csv", index=False)

# -----------------------------------------------------------------------------
# 5. Métricas en R, % Nocional y Fricción vs ATR por Año
# -----------------------------------------------------------------------------
df["year"] = df["ts_event"].dt.year
friction_records = []
fixed_cost = 9.0  # $4 comision + $5 slippage (0.5 ticks * 0.25 * 20 * 2)

for yr in sorted(t_df["year"].unique()):
    sub_t = t_df[t_df["year"] == yr]
    sub_df = df[df["year"] == yr]

    avg_price = sub_df["close"].mean()
    hl_mean = (sub_df["high"] - sub_df["low"]).mean()
    cost_pts = fixed_cost / 20.0  # 0.45 puntos
    cost_pct_bar = (cost_pts / hl_mean * 100.0) if hl_mean > 0 else 0.0

    # R y % de Nocional
    notionals_pct = []
    r_multiples = []

    for _, tr in sub_t.iterrows():
        entry_p = tr["entry_price"]
        notional_usd = entry_p * 20.0
        ret_pct = tr["net_pnl_usd"] / notional_usd * 100.0
        notionals_pct.append(ret_pct)

    friction_records.append({
        "year": yr,
        "n_trades": len(sub_t),
        "pnl_usd": sub_t["net_pnl_usd"].sum(),
        "win_rate_pct": (sub_t["net_pnl_usd"] > 0).mean() * 100.0 if len(sub_t) > 0 else 0.0,
        "avg_notional_ret_pct": np.mean(notionals_pct) if notionals_pct else 0.0,
        "avg_nq_index_pts": avg_price,
        "avg_bar_range_pts": hl_mean,
        "fixed_cost_pts": cost_pts,
        "cost_pct_of_bar_range": cost_pct_bar,
    })

df_friction = pd.DataFrame(friction_records)
df_friction.to_csv(TABLES_DIR / "desglose_costos_friccion_vs_atr_anual.csv", index=False)
print("Tablas y análisis de reconciliación exportados con éxito a:", TABLES_DIR)
