"""Script de reconciliación forense y análisis de R / Nocional / ATR."""
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

costs = AssetCosts(
    asset_type="futures",
    multiplier=20.0,
    tick_size=0.25,
    commission_per_side=2.0,
    slippage_per_side=0.5,
    annualization_factor=252.0,
)

df = pd.read_parquet(PROJECT_ROOT / "data" / "processed" / "NQ_5m.parquet")
df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
df = df.sort_values("ts_event").reset_index(drop=True)

params = IntradayEma200Params(
    trend_ema_period=200,
    atr_k=2.5,
    tp_m=3.0,
    trigger_type="price_cross",
    moc_close_time="15:50",
    use_volatility_filter=True,
    allow_short=False,
)

res = run_ema200_backtest(df, params, costs)
trades = res["trades"]

t_df = pd.DataFrame(trades)
t_df["entry_dt"] = pd.to_datetime(t_df["entry_date"], utc=True)
t_df["exit_dt"] = pd.to_datetime(t_df["exit_date"], utc=True)
t_df["year"] = t_df["entry_dt"].dt.year

# 1. Reconciliación 2010-2021
cut_hist = pd.Timestamp("2021-10-20 00:00:00", tz="UTC")
t_hist = t_df[t_df["entry_dt"] < cut_hist]
print("=" * 60)
print(f"RECONCILIACIÓN 2010 - 2021-10:")
print(f"Total trades antes de 2021-10-20: {len(t_hist)}")
print(f"PnL Total antes de 2021-10-20: ${t_hist['net_pnl_usd'].sum():,.2f}")
print("Desglose por ano:")
for yr, g in t_df[t_df["entry_dt"] < cut_hist].groupby("year"):
    print(f"  {yr}: {len(g)} trades | PnL: ${g['net_pnl_usd'].sum():,.2f}")

# 2. Análisis 2022
t_2022 = t_df[t_df["year"] == 2022].sort_values("net_pnl_usd", ascending=False)
print("=" * 60)
print(f"ANÁLISIS 2022 (Total trades: {len(t_2022)}):")
print(f"PnL Total 2022: ${t_2022['net_pnl_usd'].sum():,.2f}")
print(f"Win Rate 2022: {(t_2022['net_pnl_usd'] > 0).mean()*100:.1f}%")
print("Top 5 mejores trades 2022:")
for _, r in t_2022.head(5).iterrows():
    print(f"  {r['entry_dt'].strftime('%Y-%m-%d %H:%M')} -> {r['exit_dt'].strftime('%H:%M')} | PnL: ${r['net_pnl_usd']:,.2f} | Razón: {r['exit_reason']}")
top5_sum = t_2022.head(5)["net_pnl_usd"].sum()
print(f"Suma Top 5 trades: ${top5_sum:,.2f} ({top5_sum / t_2022['net_pnl_usd'].sum() * 100:.1f}% del total del año)")
print(f"PnL sin el Top 5: ${t_2022['net_pnl_usd'].sum() - top5_sum:,.2f}")

# 3. Retornos en R y % de Nocional y Costo como % de ATR por año
print("=" * 60)
print("MÉTRICAS EN R, % DE NOCIONAL Y COSTO COMO % DE ATR POR AÑO:")

# Calcular ATR medio por año sobre df
df["year"] = df["ts_event"].dt.year
annual_metrics = []

fixed_cost_rt = 2.0 * costs.commission_per_side + 2.0 * costs.slippage_per_side * costs.tick_size * costs.multiplier  # $9.00

for yr in sorted(t_df["year"].unique()):
    sub_t = t_df[t_df["year"] == yr]
    sub_df = df[df["year"] == yr]

    # Stop Loss en puntos para cada trade = 2.5 * ATR de entrada
    # Calculamos R de cada trade: R = (exit_price - entry_price) / (stop_distance)
    r_multiples = []
    pct_notionals = []
    cost_pct_atrs = []

    for _, tr in sub_t.iterrows():
        entry_p = tr["entry_price"]
        exit_p = tr["exit_price"]
        gross_pts = exit_p - entry_p
        
        # Distancia de stop en puntos deducida del net PnL o ratio
        # En la estrategia: stop_dist = 2.5 * cur_atr
        # PnL bruto = gross_pts * 20
        # PnL neto = gross_pts * 20 - 9.0
        # Si SL = 2.5 * ATR -> 1R en $ = 2.5 * ATR * 20
        # R_net = net_pnl / (1R_usd)
        notional = entry_p * 20.0
        ret_notional = tr["net_pnl_usd"] / notional * 100.0
        pct_notionals.append(ret_notional)

    # Rango medio diario de NQ en puntos y ATR promedio
    avg_price = sub_df["close"].mean()
    # Estimar ATR en puntos promedio del año (aproximación basada en High - Low de 5m)
    hl_mean = (sub_df["high"] - sub_df["low"]).mean()
    # Costo fijo de $9 = 0.45 puntos de NQ
    cost_pts = fixed_cost_rt / costs.multiplier  # 0.45 puntos
    cost_pct_hl = (cost_pts / hl_mean) * 100.0 if hl_mean > 0 else 0.0

    annual_metrics.append({
        "year": yr,
        "n_trades": len(sub_t),
        "pnl_usd": sub_t["net_pnl_usd"].sum(),
        "avg_notional_pnl_pct": np.mean(pct_notionals) if pct_notionals else 0.0,
        "avg_nq_price": avg_price,
        "cost_pts": cost_pts,
        "cost_pct_bar_range": cost_pct_hl,
    })

df_metrics_r = pd.DataFrame(annual_metrics)
print(df_metrics_r.to_string(index=False))
