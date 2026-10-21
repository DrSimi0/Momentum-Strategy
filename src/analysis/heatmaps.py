"""Generación de mapas de calor de estabilidad de parámetros (SMA Rápida vs SMA Lenta).
Permite diferenciar visual y cuantitativamente entre mesetas estables y picos aislados (sobreajuste).
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

FIGURES_DIR = Path("reports/figures")


def generate_stability_heatmap(
    grid_results: List[dict],
    asset_name: str,
    timeframe: str,
    fixed_num_smas: int = 2,
    metric: str = "sharpe",
    output_filename: str = None,
) -> Path:
    """Construye y guarda el mapa de calor de SMA rápida vs SMA lenta para las configuraciones probadas."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    if output_filename is None:
        clean_name = asset_name.replace("-", "_")
        output_filename = f"heatmap_stability_{clean_name}_{timeframe}.png"

    out_path = FIGURES_DIR / output_filename

    # Extraer datos relevantes
    rows = []
    for item in grid_results:
        p = item["params"]
        if p.get("num_smas") == fixed_num_smas:
            rows.append({
                "fast_sma": p["fast_sma"],
                "slow_sma": p["slow_sma"],
                "metric_val": item.get(metric, 0.0),
            })

    if not rows:
        return out_path

    df_map = pd.DataFrame(rows)
    # Pivotar promediando sobre otras variantes (MACD, RSI, ATR) para medir robustez intrínseca
    pivot = df_map.groupby(["slow_sma", "fast_sma"])["metric_val"].mean().unstack()

    plt.figure(figsize=(8, 6))
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    
    im = plt.imshow(pivot.values, cmap="RdYlGn", aspect="auto", origin="lower")
    plt.colorbar(im, label=f"{metric.upper()} Promedio")
    
    plt.xticks(range(len(pivot.columns)), pivot.columns, fontsize=11)
    plt.yticks(range(len(pivot.index)), pivot.index, fontsize=11)
    plt.xlabel("Periodo SMA Rápida", fontsize=12, fontweight="bold")
    plt.ylabel("Periodo SMA Lenta", fontsize=12, fontweight="bold")
    plt.title(f"Mapa de Estabilidad Paramétrica - {asset_name} ({timeframe})\n(Meseta = Robusto, Pico Aislado = Sobreajuste)", fontsize=12)

    # Anotar valores en cada celda
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.iloc[i, j]
            if not np.isnan(val):
                text_color = "white" if abs(val) > (pivot.values.max() * 0.7) else "black"
                plt.text(j, i, f"{val:.2f}", ha="center", va="center", color=text_color, fontsize=10, fontweight="bold")

    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path
