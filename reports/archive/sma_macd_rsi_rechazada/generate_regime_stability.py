"""Análisis de estabilidad paramétrica a través de 3 regímenes macroeconómicos históricos
para ES y NQ (2010 a 2026).
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

from src.backtest.engine_sma_confluence import StrategyParams, AssetCosts, run_sma_confluence_backtest
from scripts.run_preregistered_evaluation import generate_preregistered_grid

FIGURES_DIR = Path("reports/figures")
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def main():
    costs_es = AssetCosts(asset_type="futures", multiplier=50.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5)
    costs_nq = AssetCosts(asset_type="futures", multiplier=20.0, tick_size=0.25, commission_per_side=2.0, slippage_per_side=0.5)

    df_es = pd.read_parquet("data/processed/ES_4h.parquet")
    df_nq = pd.read_parquet("data/processed/NQ_4h.parquet")
    grid = generate_preregistered_grid()

    regimes = [
        ("Regimen_1_2010_2016", "2010-06-07", "2016-12-31", "Régimen 1: 2010-2016 (QE / ZIRP / Baja Vol)"),
        ("Regimen_2_2017_2020", "2017-01-01", "2020-12-31", "Régimen 2: 2017-2020 (Guerra Comercial / Covid)"),
        ("Regimen_3_2021_2026", "2021-01-01", "2026-10-19", "Régimen 3: 2021-2026 (Inflación / Suba de Tasas)"),
    ]

    for sym, df, costs in [("ES", df_es, costs_es), ("NQ", df_nq, costs_nq)]:
        regime_sharpes = []
        labels = [f"C{i+1}" for i in range(len(grid))]

        for reg_id, s_d, e_d, title in regimes:
            sub_df = df[(df["ts_event"] >= s_d) & (df["ts_event"] <= e_d)].copy().reset_index(drop=True)
            sharpes = []
            for p in grid:
                r = run_sma_confluence_backtest(sub_df, p, costs)
                sharpes.append(r["sharpe"] if not np.isnan(r["sharpe"]) else 0.0)
            regime_sharpes.append(sharpes)

        # Matriz (3 regímenes x 32 combinaciones)
        mat = np.array(regime_sharpes)

        plt.figure(figsize=(14, 5))
        plt.imshow(mat, aspect="auto", cmap="RdYlGn", vmin=-2.0, vmax=2.0)
        plt.colorbar(label="Sharpe Anualizado")
        plt.yticks(range(3), [r[3] for r in regimes], fontsize=10, fontweight="bold")
        plt.xticks(range(len(grid)), labels, rotation=90, fontsize=8)
        plt.title(f"Estabilidad Paramétrica Multirégimen (2010-2026) - {sym}", fontsize=13, fontweight="bold")
        plt.xlabel("Combinación Pre-registrada (1 a 32)", fontsize=11)
        plt.tight_layout()

        fig_path = FIGURES_DIR / f"regime_stability_{sym}.png"
        plt.savefig(fig_path, dpi=200)
        plt.close()
        print(f"Guardado {fig_path}")


if __name__ == "__main__":
    main()
