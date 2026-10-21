"""Script para analizar configuraciones con PnL positivo dividiendo Futuros y Cripto,
encontrar similitudes y proponer optimizaciones específicas por clase de activo.
"""
import pandas as pd
import numpy as np
from src.backtest.engine_sma_confluence import StrategyParams, AssetCosts, run_sma_confluence_backtest
from src.analysis.grid_search import generate_parameter_combinations, partition_data_60_20_20

def main():
    combos = generate_parameter_combinations()
    costs_es = AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5)
    costs_nq = AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5)
    costs_btc = AssetCosts(asset_type="crypto", multiplier=1.0, commission_per_side=0.0005, slippage_per_side=0.0002, funding_rate_8h=0.0001)
    costs_eth = AssetCosts(asset_type="crypto", multiplier=1.0, commission_per_side=0.0005, slippage_per_side=0.0003, funding_rate_8h=0.0001)

    # 1. FUTUROS EN 4H
    df_es_4h = pd.read_parquet("data/processed/ES_4h.parquet")
    df_nq_4h = pd.read_parquet("data/processed/NQ_4h.parquet")

    train_es, val_es, test_es = partition_data_60_20_20(df_es_4h)
    train_nq, val_nq, test_nq = partition_data_60_20_20(df_nq_4h)

    # Buscar configuraciones con PnL positivo en ambos futuros en Validación
    pos_futures_val = []
    for p in combos:
        r_es = run_sma_confluence_backtest(val_es, p, costs_es)
        if r_es["net_pnl_usd"] > 0:
            r_nq = run_sma_confluence_backtest(val_nq, p, costs_nq)
            if r_nq["net_pnl_usd"] > 0:
                pos_futures_val.append({
                    "params": p,
                    "es_val_pnl": r_es["net_pnl_usd"],
                    "es_val_sharpe": r_es["sharpe"],
                    "nq_val_pnl": r_nq["net_pnl_usd"],
                    "nq_val_sharpe": r_nq["sharpe"],
                    "total_val_pnl": r_es["net_pnl_usd"] + r_nq["net_pnl_usd"],
                })

    df_pos_fut = pd.DataFrame(pos_futures_val)
    print(f"Total combinaciones con PnL > 0 en ES y NQ simultáneamente en Validación (4h): {len(df_pos_fut)}")

    if not df_pos_fut.empty:
        # Analizar características comunes
        num_smas_dist = [x["params"].num_smas for x in pos_futures_val]
        macd_dist = [(x["params"].macd_fast, x["params"].macd_slow) for x in pos_futures_val]
        slow_sma_dist = [x["params"].slow_sma for x in pos_futures_val]
        rsi_dist = [x["params"].rsi_period for x in pos_futures_val]
        atr_k_dist = [x["params"].atr_k for x in pos_futures_val]
        tp_m_dist = [x["params"].tp_m for x in pos_futures_val]

        print("\n--- PATRONES EN FUTUROS GANADORES (4h) ---")
        print("Num SMAs:", pd.Series(num_smas_dist).value_counts(normalize=True).to_dict())
        print("Slow SMA:", pd.Series(slow_sma_dist).value_counts(normalize=True).to_dict())
        print("MACD (fast, slow):", pd.Series(macd_dist).value_counts(normalize=True).to_dict())
        print("RSI Period:", pd.Series(rsi_dist).value_counts(normalize=True).to_dict())
        print("ATR k:", pd.Series(atr_k_dist).value_counts(normalize=True).to_dict())
        print("TP m:", pd.Series(tp_m_dist).value_counts(normalize=True).to_dict())

    # 2. CRIPTO EN 4H Y 1H
    df_btc_4h = pd.read_parquet("data/processed/BTC_USDT_4h.parquet")
    df_eth_4h = pd.read_parquet("data/processed/ETH_USDT_4h.parquet")
    train_btc, val_btc, test_btc = partition_data_60_20_20(df_btc_4h)
    train_eth, val_eth, test_eth = partition_data_60_20_20(df_eth_4h)

    pos_crypto_val = []
    for p in combos:
        r_b = run_sma_confluence_backtest(val_btc, p, costs_btc)
        if r_b["net_pnl_usd"] > 0:
            r_e = run_sma_confluence_backtest(val_eth, p, costs_eth)
            if r_e["net_pnl_usd"] > 0:
                pos_crypto_val.append({
                    "params": p,
                    "btc_val_pnl": r_b["net_pnl_usd"],
                    "btc_val_sharpe": r_b["sharpe"],
                    "eth_val_pnl": r_e["net_pnl_usd"],
                    "eth_val_sharpe": r_e["sharpe"],
                    "total_val_pnl": r_b["net_pnl_usd"] + r_e["net_pnl_usd"],
                })

    df_pos_crypto = pd.DataFrame(pos_crypto_val)
    print(f"\nTotal combinaciones con PnL > 0 en BTC y ETH simultáneamente en Validación (4h): {len(df_pos_crypto)}")

    if not df_pos_crypto.empty:
        num_smas_dist_c = [x["params"].num_smas for x in pos_crypto_val]
        macd_dist_c = [(x["params"].macd_fast, x["params"].macd_slow) for x in pos_crypto_val]
        slow_sma_dist_c = [x["params"].slow_sma for x in pos_crypto_val]
        rsi_dist_c = [x["params"].rsi_period for x in pos_crypto_val]
        atr_k_dist_c = [x["params"].atr_k for x in pos_crypto_val]
        tp_m_dist_c = [x["params"].tp_m for x in pos_crypto_val]

        print("\n--- PATRONES EN CRIPTO GANADORES (4h) ---")
        print("Num SMAs:", pd.Series(num_smas_dist_c).value_counts(normalize=True).to_dict())
        print("Slow SMA:", pd.Series(slow_sma_dist_c).value_counts(normalize=True).to_dict())
        print("MACD (fast, slow):", pd.Series(macd_dist_c).value_counts(normalize=True).to_dict())
        print("RSI Period:", pd.Series(rsi_dist_c).value_counts(normalize=True).to_dict())
        print("ATR k:", pd.Series(atr_k_dist_c).value_counts(normalize=True).to_dict())
        print("TP m:", pd.Series(tp_m_dist_c).value_counts(normalize=True).to_dict())

    # 3. EVALUACIÓN DE HIPÓTESIS UNIFICADAS EN TEST FINAL
    print("\n=======================================================")
    print("EVALUACIÓN DE OPTIMIZACIONES BASADAS EN SIMILITUDES (TEST FINAL)")
    print("=======================================================")

    # Futuros: 3 SMAs (20, 100, 150), MACD Lento (16, 35, 9), RSI 14, ATR k=2.0, TP m=2.0
    p_fut_opt = StrategyParams(num_smas=3, fast_sma=20, mid_sma=100, slow_sma=150, macd_fast=16, macd_slow=35, macd_signal=9, rsi_period=14, atr_k=2.0, tp_m=2.0)
    r_es = run_sma_confluence_backtest(test_es, p_fut_opt, costs_es)
    r_nq = run_sma_confluence_backtest(test_nq, p_fut_opt, costs_nq)
    print(f"FUTUROS 4h (3 SMAs 20/100/150, MACD 16/35/9, RSI 14):")
    print(f"  ES: PnL = ${r_es['net_pnl_usd']:,.2f} | Sharpe = {r_es['sharpe']:.2f} | Trades = {r_es['n_trades']} | WinRate = {r_es['win_rate']*100:.1f}%")
    print(f"  NQ: PnL = ${r_nq['net_pnl_usd']:,.2f} | Sharpe = {r_nq['sharpe']:.2f} | Trades = {r_nq['n_trades']} | WinRate = {r_nq['win_rate']*100:.1f}%")
    print(f"  TOTAL FUTUROS PnL = ${r_es['net_pnl_usd'] + r_nq['net_pnl_usd']:,.2f}")

    # Cripto Confluencia: 2 SMAs (21, 200), MACD Lento (16, 35, 9), RSI 21, ATR k=2.0, TP m=2.0
    p_cry_confl = StrategyParams(num_smas=2, fast_sma=21, slow_sma=200, macd_fast=16, macd_slow=35, macd_signal=9, rsi_period=21, atr_k=2.0, tp_m=2.0)
    r_b_c = run_sma_confluence_backtest(test_btc, p_cry_confl, costs_btc)
    r_e_c = run_sma_confluence_backtest(test_eth, p_cry_confl, costs_eth)
    print(f"\nCRIPTO 4h (Confluencia: 2 SMAs 21/200, MACD 16/35/9, RSI 21):")
    print(f"  BTC: PnL = ${r_b_c['net_pnl_usd']:,.2f} | Sharpe = {r_b_c['sharpe']:.2f} | Trades = {r_b_c['n_trades']} | WinRate = {r_b_c['win_rate']*100:.1f}%")
    print(f"  ETH: PnL = ${r_e_c['net_pnl_usd']:,.2f} | Sharpe = {r_e_c['sharpe']:.2f} | Trades = {r_e_c['n_trades']} | WinRate = {r_e_c['win_rate']*100:.1f}%")

    # Cripto Tendencial Pura (Solo-SMA 21/200, ATR k=3.0, TP m=2.0)
    p_cry_trend = StrategyParams(num_smas=2, fast_sma=21, slow_sma=200, use_macd=False, use_rsi=False, atr_k=3.0, tp_m=2.0)
    r_b_t = run_sma_confluence_backtest(test_btc, p_cry_trend, costs_btc)
    r_e_t = run_sma_confluence_backtest(test_eth, p_cry_trend, costs_eth)
    print(f"\nCRIPTO 4h (Solo-SMA 21/200 Tendencial Puro, sin MACD ni RSI):")
    print(f"  BTC: PnL = ${r_b_t['net_pnl_usd']:,.2f} | Sharpe = {r_b_t['sharpe']:.2f} | Trades = {r_b_t['n_trades']} | WinRate = {r_b_t['win_rate']*100:.1f}%")
    print(f"  ETH: PnL = ${r_e_t['net_pnl_usd']:,.2f} | Sharpe = {r_e_t['sharpe']:.2f} | Trades = {r_e_t['n_trades']} | WinRate = {r_e_t['win_rate']*100:.1f}%")


if __name__ == "__main__":
    main()
