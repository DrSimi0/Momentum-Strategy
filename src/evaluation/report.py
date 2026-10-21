"""Generación de reportes (.md, .json) y gráficas según especificaciones."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def generate_plots(report_data: dict, out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    plots = []

    # 1. Equity curves (Net, Gross, Buy & Hold) for out-of-sample (holdout)
    fig, ax = plt.subplots(figsize=(10, 5))
    eq = report_data.get("equity_series", {})
    if "times" in eq and "net" in eq:
        t = pd.to_datetime(eq["times"])
        ax.plot(t, eq["net"], label="Net Equity (Strategy)", color="#1f77b4", lw=1.8)
        if "gross" in eq:
            ax.plot(t, eq["gross"], label="Gross Equity", color="#aec7e8", linestyle="--")
        if "buy_hold" in eq:
            ax.plot(t, eq["buy_hold"], label="Buy & Hold (1x Perp)", color="#ff7f0e", alpha=0.8)
        ax.set_title("Curva de Equity: Neta, Bruta y Buy & Hold (Holdout)")
        ax.set_ylabel("Equity (USDT)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        p1 = out_dir / "equity_curves.png"
        fig.tight_layout()
        fig.savefig(p1, dpi=150)
        plt.close(fig)
        plots.append(str(p1.name))

    # 2. Drawdown
    fig, ax = plt.subplots(figsize=(10, 4))
    if "times" in eq and "drawdown" in eq:
        t = pd.to_datetime(eq["times"])
        ax.fill_between(t, np.array(eq["drawdown"]) * 100, 0, color="crimson", alpha=0.4)
        ax.plot(t, np.array(eq["drawdown"]) * 100, color="firebrick", lw=1.2)
        ax.set_title("Evolución del Drawdown (%) (Holdout)")
        ax.set_ylabel("Drawdown %")
        ax.grid(True, alpha=0.3)
        p2 = out_dir / "drawdown.png"
        fig.tight_layout()
        fig.savefig(p2, dpi=150)
        plt.close(fig)
        plots.append(str(p2.name))

    # 3. Distribución de retornos por operación (en R o USDT)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    trade_pnls = report_data.get("trade_pnls_r", [])
    if len(trade_pnls) > 0:
        ax.hist(trade_pnls, bins=25, color="steelblue", edgecolor="black", alpha=0.7)
        ax.axvline(0, color="black", linestyle="--", alpha=0.7)
        ax.axvline(np.mean(trade_pnls), color="green", linestyle="-", label=f"Media: {np.mean(trade_pnls):.2f}R")
        ax.set_title("Distribución de Retornos por Operación (Múltiplos de R)")
        ax.set_xlabel("PnL (R)")
        ax.set_ylabel("Frecuencia")
        ax.legend()
        ax.grid(True, alpha=0.3)
        p3 = out_dir / "trade_return_dist.png"
        fig.tight_layout()
        fig.savefig(p3, dpi=150)
        plt.close(fig)
        plots.append(str(p3.name))

    # 4. Sensibilidad de parámetros
    sens = report_data.get("sensitivity_grid", [])
    if len(sens) > 0:
        df_sens = pd.DataFrame(sens)
        fig, ax = plt.subplots(figsize=(8, 5))
        # Pivot table of sharpe or expectancy
        pivot = df_sens.pivot(index="channel_n", columns="atr_mult", values="sharpe")
        im = ax.imshow(pivot.values, cmap="viridis", aspect="auto")
        ax.set_xticks(np.arange(len(pivot.columns)))
        ax.set_yticks(np.arange(len(pivot.index)))
        ax.set_xticklabels([f"{c:g}" for c in pivot.columns])
        ax.set_yticklabels(pivot.index)
        ax.set_xlabel("Multiplicador ATR (k)")
        ax.set_ylabel("Período Donchian (N)")
        ax.set_title("Sensibilidad de Parámetros: Sharpe Ratio")
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                val = pivot.values[i, j]
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        color="white" if val < pivot.values.mean() else "black")
        fig.colorbar(im, ax=ax, label="Sharpe")
        p4 = out_dir / "parameter_sensitivity.png"
        fig.tight_layout()
        fig.savefig(p4, dpi=150)
        plt.close(fig)
        plots.append(str(p4.name))

    return plots


def save_json_report(data: dict, out_file: Path) -> None:
    # Serialize cleanly
    def _default(obj):
        if isinstance(obj, (np.floating, float)):
            return None if np.isnan(obj) else float(obj)
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        if isinstance(obj, (pd.Timestamp, pd.Period)):
            return str(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(data, indent=2, default=_default), encoding="utf-8")


def generate_markdown_report(data: dict, out_file: Path) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)

    v = data["verdict"]
    reasons = data["verdict_reasons"]
    crit = data["criteria"]
    metrics_table = data["metrics_comparison"]
    version = data.get("acceptance_version", "1.0.0")
    n_configs = data.get("n_configs_tested", 9)

    verdict_badge = {
        "PASS": "🟢 **PASS**",
        "INCONCLUSIVE": "🟡 **INCONCLUSIVE**",
        "FAIL": "🔴 **FAIL**"
    }.get(v, v)

    md = []
    md.append(f"# Reporte de Evaluación de Rentabilidad: {verdict_badge}\n")
    md.append("> **Declaración obligatoria:**")
    md.append("> El resultado **PASS** significa *'evidencia consistente de edge en el pasado bajo este protocolo'*, **NUNCA** *'rentable en el futuro'*. De igual manera, un resultado **FAIL** o **INCONCLUSIVE** dictamina de forma vinculante que bajo las reglas estrictas fijadas, la estrategia no ofrece certeza estadística de rentabilidad neta transferible a producción.\n")

    md.append("## 1. Veredicto y Motivos Principales")
    md.append(f"**Veredicto Final:** `{v}`\n")
    md.append("**3 Motivos Principales:**")
    for r in reasons[:3]:
        md.append(f"- {r}")
    md.append("\n---\n")

    md.append("## 2. Tabla Comparativa de Métricas Lado a Lado")
    md.append("| Métrica | Desarrollo | Validación | Holdout (OOS) | Buy & Hold | Baseline Aleatorio (Mediana) |")
    md.append("|---|---|---|---|---|---|")
    for row in metrics_table:
        md.append(f"| {row['name']} | {row['dev']} | {row['val']} | {row['oos']} | {row['bh']} | {row['rand']} |")
    md.append("\n---\n")

    md.append("## 3. Criterios de Aceptación y Evaluación")
    md.append(f"*Versión de umbrales usada: `{version}`*  ")
    md.append(f"*Total de configuraciones probadas: `{n_configs}`*  \n")
    md.append("| Criterio | Tipo | Valor Observado | Umbral | Resultado |")
    md.append("|---|---|---|---|---|")
    for c in crit:
        status = "✅ CUMPLE" if c["passed"] else "❌ INCUMPLE"
        val_str = str(c["value"])
        if isinstance(c["value"], float):
            val_str = f"{c['value']:.4g}"
        elif isinstance(c["value"], dict):
            val_str = ", ".join(f"{k}: {v:.4g}" if isinstance(v, float) else f"{k}: {v}" for k, v in c["value"].items())
        md.append(f"| {c['description']} | `{c['kind']}` | {val_str} | {c['threshold']} | {status} |")
    md.append("\n---\n")

    md.append("## 4. Gráficas de Evaluación")
    md.append("![Curvas de Equity](equity_curves.png)")
    md.append("![Drawdown](drawdown.png)")
    md.append("![Distribución de Retornos](trade_return_dist.png)")
    md.append("![Sensibilidad de Parámetros](parameter_sensitivity.png)")
    md.append("\n---\n")

    md.append("## 5. Análisis de Robustez y Subperiodos")
    md.append("### Bootstrap por Bloques (IC 95%)")
    bs = data.get("robustness", {}).get("bootstrap", {})
    md.append(f"- **Expectativa por operación (USDT):** {bs.get('expectancy_usdt', {}).get('point', 'N/A')} [IC95%: {bs.get('expectancy_usdt', {}).get('lo', 'N/A')} a {bs.get('expectancy_usdt', {}).get('hi', 'N/A')}]")
    md.append(f"- **Sharpe diario anualizado:** {bs.get('sharpe', {}).get('point', 'N/A')} [IC95%: {bs.get('sharpe', {}).get('lo', 'N/A')} a {bs.get('sharpe', {}).get('hi', 'N/A')}]")
    md.append(f"- **Probabilistic Sharpe Ratio (PSR):** {data.get('robustness', {}).get('psr', 'N/A'):.4g}")
    md.append(f"- **Deflated Sharpe Ratio (DSR):** {data.get('robustness', {}).get('dsr', 'N/A'):.4g}")

    md.append("\n### Monte Carlo de Orden de Operaciones")
    mc = data.get("robustness", {}).get("monte_carlo_drawdown", {})
    md.append(f"- **Drawdown observado:** {mc.get('observed', 0)*100:.2f}% | **Mediana MC (p50):** {mc.get('p50', 0)*100:.2f}% | **Percentil 95 (p95):** {mc.get('p95', 0)*100:.2f}% | **Percentil 99 (p99):** {mc.get('p99', 0)*100:.2f}%")

    md.append("\n### Desglose por Régimen de Mercado")
    reg = data.get("robustness", {}).get("regimes", [])
    if reg:
        md.append("| Régimen | Días | Sharpe Anual. | N Ops | Win Rate | Expectativa (USDT) | Profit Factor | PnL Neto |")
        md.append("|---|---|---|---|---|---|---|---|")
        for r in reg:
            wr = f"{r.get('win_rate', 0)*100:.1f}%" if r.get('win_rate') is not None else "-"
            md.append(f"| {r['regime']} | {r['days']} | {r.get('sharpe_daily_ann', 0):.2f} | {r.get('n_trades', 0)} | {wr} | {r.get('expectancy_usdt', 0):.2f} | {r.get('profit_factor', 0):.2f} | {r.get('net_pnl', 0):.2f} |")

    md.append("\n### Desglose por Subperiodos Anuales")
    sub = data.get("robustness", {}).get("subperiods", [])
    if sub:
        md.append("| Año | Retorno Total | Sharpe | Max Drawdown | N Ops | Win Rate | Expectativa (USDT) | PnL Neto |")
        md.append("|---|---|---|---|---|---|---|---|")
        for s in sub:
            wr = f"{s.get('win_rate', 0)*100:.1f}%" if s.get('win_rate') is not None else "-"
            md.append(f"| {s['year']} | {s.get('total_return', 0)*100:.2f}% | {s.get('sharpe', 0):.2f} | {s.get('max_drawdown', 0)*100:.2f}% | {s.get('n_trades', 0)} | {wr} | {s.get('expectancy_usdt', 0):.2f} | {s.get('net_pnl', 0):.2f} |")

    md.append("\n### Walk-Forward Consistencia")
    wf = data.get("robustness", {}).get("walk_forward", [])
    if wf:
        md.append(f"- **Fracción de ventanas positivas:** {data.get('wf_positive_frac', 0)*100:.1f}%")
        md.append("| Test Start | Test End | Param Seleccionado | Train Sharpe | Test Sharpe | Test Exp (USDT) | Test Trades |")
        md.append("|---|---|---|---|---|---|---|")
        for w in wf:
            md.append(f"| {w.get('test_start')} | {w.get('test_end')} | {w.get('selected')} | {w.get('train_sharpe', 0):.2f} | {w.get('test_sharpe', 0):.2f} | {w.get('test_expectancy_usdt', 0):.2f} | {w.get('test_n_trades', 0)} |")

    md.append("\n---\n")

    md.append("## 6. Limitaciones del Protocolo y Aspectos No Comprobados")
    md.append("- **Impacto de mercado:** El modelo asume ejecución al precio de mercado +/- 5 bps fijos. Para capitales mayores o libros con poca liquidez en rupturas rápidas, el impacto puede elevarse drásticamente.")
    md.append("- **Calidad del modelo de deslizamiento:** No modela latencia de websocket ni colas en libro L2; se adopta un deslizamiento estándar de 5 bps conservador para Binance USDT-M perp en BTC.")
    md.append("- **Funding rate dinámico:** Si bien se utilizaron registros históricos reales del contrato BTCUSDT, en estrés severo del mercado el funding puede divergir más allá del multiplicador estático x2 evaluado.")
    md.append("- **Apalancamiento y liquidación:** Se simuló liquidación estricta por margen de mantenimiento (0.5%), asumiendo margen cruzado y sin considerar tarifas por ADL (Auto-Deleverage).")

    out_file.write_text("\n".join(md), encoding="utf-8")
