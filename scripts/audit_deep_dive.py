"""Script de auditoría exhaustiva y rigurosa punto por punto."""
import json
import numpy as np
import pandas as pd
from src.analysis.grid_search import partition_data_60_20_20
from src.analysis.robustness import compute_deflated_sharpe_ratio
from src.analysis.walk_forward import run_walk_forward_analysis
from src.backtest.engine_sma_confluence import StrategyParams, AssetCosts, run_sma_confluence_backtest

# 1. Cargar datos
df_es = pd.read_parquet('data/processed/ES_4h.parquet')
df_nq = pd.read_parquet('data/processed/NQ_4h.parquet')
df_btc = pd.read_parquet('data/processed/BTC_USDT_4h.parquet')
df_eth = pd.read_parquet('data/processed/ETH_USDT_4h.parquet')

train_es, val_es, test_es = partition_data_60_20_20(df_es)
train_nq, val_nq, test_nq = partition_data_60_20_20(df_nq)
train_btc, val_btc, test_btc = partition_data_60_20_20(df_btc)
train_eth, val_eth, test_eth = partition_data_60_20_20(df_eth)

costs_es = AssetCosts(asset_type='futures', multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5)
costs_nq = AssetCosts(asset_type='futures', multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5)
costs_btc = AssetCosts(asset_type='crypto', multiplier=1.0, commission_per_side=0.0005, slippage_per_side=0.0002, funding_rate_8h=0.0001)
costs_eth = AssetCosts(asset_type='crypto', multiplier=1.0, commission_per_side=0.0005, slippage_per_side=0.0003, funding_rate_8h=0.0001)

# P-2: Tabla por activo en periodo test
p_fut_conf = StrategyParams(num_smas=3, fast_sma=20, mid_sma=100, slow_sma=150, macd_fast=16, macd_slow=35, macd_signal=9, rsi_period=14, atr_k=2.0, tp_m=2.0)
p_fut_solo = StrategyParams(num_smas=3, fast_sma=20, mid_sma=100, slow_sma=150, use_macd=False, use_rsi=False, atr_k=2.0, tp_m=2.0)
p_cry_solo = StrategyParams(num_smas=2, fast_sma=21, slow_sma=200, use_macd=False, use_rsi=False, atr_k=3.0, tp_m=2.0)
p_cry_conf = StrategyParams(num_smas=2, fast_sma=21, slow_sma=200, macd_fast=16, macd_slow=35, macd_signal=9, rsi_period=21, atr_k=2.0, tp_m=2.0)

# Correr
r_es = run_sma_confluence_backtest(test_es, p_fut_conf, costs_es)
r_es_solo = run_sma_confluence_backtest(test_es, p_fut_solo, costs_es)
r_nq = run_sma_confluence_backtest(test_nq, p_fut_conf, costs_nq)
r_nq_solo = run_sma_confluence_backtest(test_nq, p_fut_solo, costs_nq)
r_btc = run_sma_confluence_backtest(test_btc, p_cry_solo, costs_btc)
r_eth = run_sma_confluence_backtest(test_eth, p_cry_solo, costs_eth)

# Time in market
def get_market_exposure(res, df_test):
    total_bars = len(df_test)
    held_bars = sum(t['bars_held'] for t in res['trades'])
    return held_bars / total_bars if total_bars > 0 else 0.0

# Buy & Hold
def get_bnh(df_test, costs):
    p0 = df_test['close'].iloc[0]
    p1 = df_test['close'].iloc[-1]
    gross_ret = (p1 / p0) - 1.0
    if costs.asset_type == 'futures':
        notional0 = p0 * costs.multiplier
        pnl = (p1 - p0) * costs.multiplier - (costs.commission_per_side * 2) - (costs.slippage_per_side * 2 * costs.tick_size * costs.multiplier)
        ret = pnl / notional0
    else:
        pnl = 10000.0 * gross_ret - (10000.0 * (costs.commission_per_side * 2 + costs.slippage_per_side * 2))
        ret = pnl / 10000.0
    return pnl, ret

print('--- PUNTOS 2 Y 3: TABLA AUDITADA ---')
for name, res, df_t, c in [
    ('ES Confluencia', r_es, test_es, costs_es),
    ('ES Solo-SMA', r_es_solo, test_es, costs_es),
    ('NQ Confluencia', r_nq, test_nq, costs_nq),
    ('NQ Solo-SMA', r_nq_solo, test_nq, costs_nq),
    ('BTC Solo-SMA', r_btc, test_btc, costs_btc),
    ('ETH Solo-SMA', r_eth, test_eth, costs_eth),
]:
    exp = get_market_exposure(res, df_t)
    bnh_pnl, bnh_ret = get_bnh(df_t, c)
    print(f"{name:15} | Trades: {res['n_trades']:3} | WR: {res['win_rate']*100:5.1f}% | PF: {res['profit_factor']:5.2f} | Exp/trade: ${res['avg_expectancy_usd']:8.2f} | PnL: ${res['net_pnl_usd']:10.2f} | Sharpe: {res['sharpe']:5.2f} | ExpTime: {exp*100:5.1f}% | BnH PnL: ${bnh_pnl:10.2f} ({bnh_ret*100:5.1f}%)")

def to_utc_naive_floor(dt_val):
    t = pd.to_datetime(dt_val)
    if t.tz is not None:
        t = t.tz_convert('UTC').tz_localize(None)
    return t.floor('D')

# P-6: Correlación estricta solo en días con posición abierta simultánea y estrés
common_start = max(test_es['ts_event'].min(), test_btc['ts_event'].min())
common_end = min(test_es['ts_event'].max(), test_btc['ts_event'].max())
c_s = to_utc_naive_floor(common_start)
c_e = to_utc_naive_floor(common_end)
dt_idx = pd.date_range(c_s, c_e, freq='D')

def get_daily_pnl_and_in_market(res, df_t, name):
    s_pnl = pd.Series(0.0, index=dt_idx)
    s_active = pd.Series(False, index=dt_idx)
    for t in res['trades']:
        en = to_utc_naive_floor(t['entry_date'])
        ex = to_utc_naive_floor(t['exit_date'])
        act_s = max(en, dt_idx[0])
        act_e = min(ex, dt_idx[-1])
        if act_s <= act_e:
            act_range = pd.date_range(act_s, act_e, freq='D')
            s_active.loc[act_range] = True
        if ex in dt_idx:
            s_pnl.loc[ex] += t['net_pnl_usd']
    return s_pnl, s_active

pnl_es, act_es = get_daily_pnl_and_in_market(r_es, test_es, 'ES')
pnl_nq, act_nq = get_daily_pnl_and_in_market(r_nq, test_nq, 'NQ')
pnl_btc, act_btc = get_daily_pnl_and_in_market(r_btc, test_btc, 'BTC')
pnl_eth, act_eth = get_daily_pnl_and_in_market(r_eth, test_eth, 'ETH')

act_fut = act_es | act_nq
act_cry = act_btc | act_eth
both_active = act_fut & act_cry

pnl_fut = 0.5 * pnl_es + 0.5 * pnl_nq
pnl_cry = 0.5 * pnl_btc + 0.5 * pnl_eth

corr_all = pnl_fut.corr(pnl_cry)
corr_active_only = pnl_fut[both_active].corr(pnl_cry[both_active])
print(f"\n--- PUNTO 6: CORRELACIÓN ESTRICTA ---")
print(f"Días comunes totales: {len(dt_idx)}")
print(f"Días con AMBAS subcarteras activas simultáneamente: {both_active.sum()}")
print(f"Correlación global: {corr_all:.4f}")
print(f"Correlación SOLO en días con posición simultánea abierta: {corr_active_only:.4f}")

# Estrés: días donde Futuros cayó más de 1 std o Cripto cayó más de 1 std
stress_fut = pnl_fut < -pnl_fut.std()
stress_cry = pnl_cry < -pnl_cry.std()
stress_days = stress_fut | stress_cry
print(f"Días de estrés (caída > 1 std en alguna subcartera): {stress_days.sum()}")
corr_stress = pnl_fut[stress_days].corr(pnl_cry[stress_days])
print(f"Correlación en días de estrés: {corr_stress:.4f}")

# P-8: Estabilidad y Vecinos
print("\n--- PUNTO 8: VECINOS Y ESTABILIDAD ---")
# Vecinos Cripto (Solo-SMA 4h)
vecinos_cry = [
    (10, 200), (20, 200), (21, 200), (30, 200),
    (21, 150), (21, 100), (20, 150), (30, 150)
]
print("VECINOS CRIPTO 4h (Solo-SMA, k=3.0, m=2.0):")
for f_sma, s_sma in vecinos_cry:
    p_v = StrategyParams(num_smas=2, fast_sma=f_sma, slow_sma=s_sma, use_macd=False, use_rsi=False, atr_k=3.0, tp_m=2.0)
    rb = run_sma_confluence_backtest(test_btc, p_v, costs_btc)
    re = run_sma_confluence_backtest(test_eth, p_v, costs_eth)
    print(f"  SMA ({f_sma:2}/{s_sma:3}) | BTC: ${rb['net_pnl_usd']:8.2f} (Sh: {rb['sharpe']:4.2f}, Tr: {rb['n_trades']:2}) | ETH: ${re['net_pnl_usd']:8.2f} (Sh: {re['sharpe']:4.2f}, Tr: {re['n_trades']:2}) | Total: ${rb['net_pnl_usd']+re['net_pnl_usd']:8.2f}")

# Vecinos Futuros 4h (3 SMAs, MACD 16/35/9, RSI 14, k=2.0, m=2.0)
vecinos_fut = [
    (20, 100, 150), (20, 100, 200), (20, 50, 150),
    (30, 100, 150), (30, 100, 200), (30, 50, 150),
    (10, 100, 150), (10, 100, 200), (21, 100, 150)
]
print("\nVECINOS FUTUROS 4h (Confluencia, MACD 16/35/9, RSI 14, k=2.0, m=2.0):")
for f_sma, m_sma, s_sma in vecinos_fut:
    p_vf = StrategyParams(num_smas=3, fast_sma=f_sma, mid_sma=m_sma, slow_sma=s_sma, macd_fast=16, macd_slow=35, macd_signal=9, rsi_period=14, atr_k=2.0, tp_m=2.0)
    res_e = run_sma_confluence_backtest(test_es, p_vf, costs_es)
    res_n = run_sma_confluence_backtest(test_nq, p_vf, costs_nq)
    print(f"  SMAs ({f_sma:2}/{m_sma:3}/{s_sma:3}) | ES: ${res_e['net_pnl_usd']:9.2f} (Sh: {res_e['sharpe']:4.2f}, Tr: {res_e['n_trades']:2}) | NQ: ${res_n['net_pnl_usd']:9.2f} (Sh: {res_n['sharpe']:4.2f}, Tr: {res_n['n_trades']:2}) | Total: ${res_e['net_pnl_usd']+res_n['net_pnl_usd']:9.2f}")

# P-9: Walk-forward
print("\n--- PUNTO 9: WALK-FORWARD ---")
wf_es = run_walk_forward_analysis(df_es, p_fut_conf, costs_es, n_windows=5)
wf_nq = run_walk_forward_analysis(df_nq, p_fut_conf, costs_nq, n_windows=5)
wf_btc = run_walk_forward_analysis(df_btc, p_cry_solo, costs_btc, n_windows=5)
wf_eth = run_walk_forward_analysis(df_eth, p_cry_solo, costs_eth, n_windows=5)

for sym, wf in [('ES (Confluencia)', wf_es), ('NQ (Confluencia)', wf_nq), ('BTC (Solo-SMA)', wf_btc), ('ETH (Solo-SMA)', wf_eth)]:
    print(f"\nWalk-forward {sym} (OOS Sharpe Combinado: {wf['combined_oos_sharpe']:.2f}):")
    for w in wf['windows']:
        print(f"  Ventana {w['window']}: Train Sharpe={w['train_sharpe']:.2f} | Test OOS Sharpe={w['test_sharpe']:.2f} | Test PnL=${w['test_net_pnl']:,.2f} | Trades={w['test_trades']}")

# P-7: Deflated Sharpe
print("\n--- PUNTO 7: DEFLATED SHARPE ---")
total_tested = 30240
for sym, r, ann in [('ES Confluencia', r_es, 252), ('NQ Confluencia', r_nq, 252), ('BTC Solo-SMA', r_btc, 365), ('ETH Solo-SMA', r_eth, 365)]:
    rets = np.array([t['return'] for t in r['trades']])
    dsr = compute_deflated_sharpe_ratio(
        observed_sharpe=r['sharpe'],
        num_trials=total_tested,
        num_obs=len(rets),
        skewness=float(pd.Series(rets).skew()) if len(rets)>2 else 0.0,
        kurtosis=float(pd.Series(rets).kurt()) if len(rets)>3 else 3.0,
        annualization_factor=ann,
    )
    print(f"  {sym:18} | Sharpe={r['sharpe']:.2f} | Trades={r['n_trades']} | DSR={dsr*100:.6f}%")
