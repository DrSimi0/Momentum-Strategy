"""Orquestador de ejecución del protocolo de evaluación de rentabilidad.

Etapas:
  --stage pre:
      Carga datos de desarrollo y validación.
      Evalúa la rejilla de parámetros en desarrollo y selecciona la configuración ganadora.
      Guarda la configuración congelada en config/strategy_frozen.yaml.
      Calcula baseline aleatorio y métricas de validación preliminares.
  --stage freeze:
      Requiere que config/acceptance.yaml, config/strategy.yaml, config/strategy_frozen.yaml
      y data/manifest.json estén commiteados y sin cambios sin guardar.
      Genera config/freeze.json con sus hashes SHA256.
  --stage holdout:
      Verifica rigurosamente config/freeze.json y git status.
      Bloquea el uso de holdout mediante reports/.holdout_used.
      Evalúa el holdout una sola vez.
      Calcula métricas lado a lado (dev, val, holdout, baselines), robustez, veredicto,
      genera gráficas y reportes (markdown y json).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.backtest.engine import BacktestConfig, CostModel, StrategyParams, run_backtest
from src.data.loader import load_bars
from src.evaluation import metrics as M
from src.evaluation import protocol as P
from src.evaluation import robustness as R
from src.evaluation.baselines import buy_and_hold, random_entry_baseline
from src.evaluation.report import generate_markdown_report, generate_plots, save_json_report
from src.evaluation.verdict import decide_verdict, evaluate_criteria, load_acceptance

ROOT = Path(__file__).resolve().parents[1]


def build_backtest_config(cfg_bt: dict) -> BacktestConfig:
    costs = CostModel(
        fee_rate=cfg_bt.get("fee_rate", 0.0005),
        slippage_rate=cfg_bt.get("slippage_rate", 0.0005),
        funding_multiplier=cfg_bt.get("funding_multiplier", 1.0),
        fee_rate_maker=cfg_bt.get("fee_rate_maker"),
        slippage_rate_maker=cfg_bt.get("slippage_rate_maker"),
        use_bnb_discount=cfg_bt.get("use_bnb_discount", False),
    )
    return BacktestConfig(
        initial_capital=cfg_bt.get("initial_capital", 10_000.0),
        risk_per_trade=cfg_bt.get("risk_per_trade", 0.01),
        max_leverage=cfg_bt.get("max_leverage", 3.0),
        atr_period=cfg_bt.get("atr_period", 14),
        maintenance_margin_rate=cfg_bt.get("maintenance_margin_rate", 0.005),
        costs=costs,
    )


def stage_pre(cfg_strategy: dict) -> None:
    print("=== Ejecutando Etapa Pre (Desarrollo y Selección) ===")
    p_dev = cfg_strategy["periods"]["development"]
    p_val = cfg_strategy["periods"]["validation"]
    
    # Cargamos barras solo hasta el inicio del holdout para no mirar el futuro
    cutoff = cfg_strategy["periods"]["holdout"][0]
    bars = load_bars(cutoff=cutoff)
    print(f"Datos cargados hasta {cutoff} (excluyendo holdout). Total barras: {len(bars)}")

    grid_cfg = cfg_strategy["strategy"]["grid"]
    grid = [
        StrategyParams(channel_n=n, atr_mult=k)
        for n in grid_cfg["channel_n"]
        for k in grid_cfg["atr_mult"]
    ]
    print(f"Evaluando rejilla de {len(grid)} configuraciones en desarrollo: {p_dev}")

    bt_cfg = build_backtest_config(cfg_strategy["backtest"])

    dev_results = {}
    for p in grid:
        res = run_backtest(bars, p, bt_cfg, p_dev[0], p_dev[1])
        r = M.daily_returns(res.equity)
        sharpe = M.sharpe_ratio(r)
        dev_results[p] = {
            "sharpe": sharpe,
            "trades": len(res.trades),
            "net_pnl": float(res.trades["net_pnl"].sum()) if len(res.trades) else 0.0,
            "expectancy_usdt": float(res.trades["net_pnl"].mean()) if len(res.trades) else 0.0,
        }
        print(f"  Config {p.key}: Sharpe={sharpe:.3f}, Trades={len(res.trades)}, NetPnL={dev_results[p]['net_pnl']:.2f}")

    best_p = R.select_best(dev_results, metric=cfg_strategy["strategy"]["selection_metric"])
    print(f"\nConfiguración seleccionada (mayor {cfg_strategy['strategy']['selection_metric']}): {best_p.key}")
    
    # Guardar configuración congelada
    frozen_path = ROOT / "config" / "strategy_frozen.yaml"
    frozen_data = {
        "selected_params": {
            "channel_n": best_p.channel_n,
            "atr_mult": best_p.atr_mult,
            "key": best_p.key,
        },
        "selection_metric": cfg_strategy["strategy"]["selection_metric"],
        "dev_sharpe": dev_results[best_p]["sharpe"],
        "n_grid_candidates": len(grid),
        "grid": [p.key for p in grid],
    }
    frozen_path.write_text(yaml.safe_dump(frozen_data, sort_keys=False), encoding="utf-8")
    print(f"Configuración guardada en {frozen_path}")


def stage_freeze() -> None:
    print("=== Ejecutando Etapa Freeze ===")
    info = P.freeze(ROOT)
    print(f"Congelado exitoso. Hashes registrados en config/freeze.json:\n{json.dumps(info, indent=2)}")


def stage_holdout(cfg_strategy: dict, acceptance: dict) -> None:
    print("=== Ejecutando Etapa Holdout ===")
    # 1. Verificar congelamiento
    freeze_info = P.verify_freeze(ROOT)
    print("Verificación de freeze.json: OK. Hashes íntegros y limpios en git.")

    # 2. Adquirir lock
    lock_path = P.acquire_holdout_lock(ROOT, {"version": acceptance.get("version")})
    print(f"Lock adquirido en {lock_path}")

    try:
        frozen_cfg = yaml.safe_load((ROOT / "config" / "strategy_frozen.yaml").read_text(encoding="utf-8"))
        best_p = StrategyParams(
            channel_n=frozen_cfg["selected_params"]["channel_n"],
            atr_mult=frozen_cfg["selected_params"]["atr_mult"],
        )
        print(f"Parámetros congelados a evaluar: {best_p.key}")

        # Cargar todas las barras (incluyendo holdout)
        bars = load_bars()
        print(f"Todas las barras cargadas. Total: {len(bars)}")

        bt_cfg = build_backtest_config(cfg_strategy["backtest"])

        p_dev = cfg_strategy["periods"]["development"]
        p_val = cfg_strategy["periods"]["validation"]
        p_oos = cfg_strategy["periods"]["holdout"]

        # Backtests
        res_dev = run_backtest(bars, best_p, bt_cfg, p_dev[0], p_dev[1])
        res_val = run_backtest(bars, best_p, bt_cfg, p_val[0], p_val[1])
        res_oos = run_backtest(bars, best_p, bt_cfg, p_oos[0], p_oos[1])

        # Métricas principales
        m_dev = M.performance_metrics(res_dev.equity, res_dev.trades, res_dev.liquidations, res_dev.start, res_dev.end)
        m_val = M.performance_metrics(res_val.equity, res_val.trades, res_val.liquidations, res_val.start, res_val.end)
        m_oos = M.performance_metrics(res_oos.equity, res_oos.trades, res_oos.liquidations, res_oos.start, res_oos.end)

        # Baselines en Holdout
        bh_oos = buy_and_hold(bars, bt_cfg, p_oos[0], p_oos[1])
        m_bh = M.performance_metrics(bh_oos.equity, bh_oos.trades, bh_oos.liquidations, bh_oos.start, bh_oos.end)

        rand_baseline = random_entry_baseline(
            bars, res_oos, bt_cfg,
            reps=cfg_strategy["evaluation"]["random_baseline_reps"],
            seed=cfg_strategy["evaluation"]["seed"],
        )

        # Retención
        dev_cagr = m_dev["cagr"]
        oos_cagr = m_oos["cagr"]
        retention = oos_cagr / dev_cagr if dev_cagr > 0 else (0.0 if oos_cagr <= 0 else 1.0)

        # Bootstrap por bloques en Holdout (Expectativa y Sharpe)
        seed = cfg_strategy["evaluation"]["seed"]
        reps = cfg_strategy["evaluation"]["bootstrap_reps"]
        
        # Bootstrap sobre R-multiples de operaciones en OOS
        r_mults = M.r_multiples(res_oos.trades) if len(res_oos.trades) else np.array([])
        bs_exp_r = R.bootstrap_ci(r_mults, np.mean, reps=reps, seed=seed) if len(r_mults) > 1 else {"lo": float("nan"), "hi": float("nan"), "point": float("nan")}
        
        # Bootstrap sobre USDT pnl
        net_pnls = res_oos.trades["net_pnl"].to_numpy(float) if len(res_oos.trades) else np.array([])
        bs_exp_usdt = R.bootstrap_ci(net_pnls, np.mean, reps=reps, seed=seed) if len(net_pnls) > 1 else {"lo": float("nan"), "hi": float("nan"), "point": float("nan")}
        
        # Bootstrap sobre Sharpe de retornos diarios
        oos_daily_r = M.daily_returns(res_oos.equity)
        bs_sharpe = R.bootstrap_ci(oos_daily_r.values, M.sharpe_ratio, reps=reps, seed=seed) if len(oos_daily_r) > 1 else {"lo": float("nan"), "hi": float("nan"), "point": float("nan")}

        # DSR (Deflated Sharpe Ratio)
        # Número de configs en la rejilla
        n_trials = frozen_cfg["n_grid_candidates"]
        # Varianza de los Sharpes en desarrollo entre las configuraciones
        grid_cfgs = [
            StrategyParams(channel_n=n, atr_mult=k)
            for n in cfg_strategy["strategy"]["grid"]["channel_n"]
            for k in cfg_strategy["strategy"]["grid"]["atr_mult"]
        ]
        dev_sharpes = []
        for p in grid_cfgs:
            r_temp = M.daily_returns(run_backtest(bars, p, bt_cfg, p_dev[0], p_dev[1]).equity)
            dev_sharpes.append(M.sharpe_ratio(r_temp) / math.sqrt(M.DAYS_PER_YEAR))  # frecuencia diaria
        sr_var = float(np.var(dev_sharpes, ddof=1)) if len(dev_sharpes) > 1 else 0.01

        dsr = M.deflated_sharpe_ratio(oos_daily_r.values, n_trials=n_trials, sr_variance=sr_var)

        # Monte Carlo Drawdown
        trade_ret_frac = (res_oos.trades["net_pnl"] / res_oos.trades["equity_at_entry"]).to_numpy(float) if len(res_oos.trades) else np.array([])
        mc_dd = R.mc_trade_order_drawdown(trade_ret_frac, reps=cfg_strategy["evaluation"]["monte_carlo_reps"], seed=seed)

        # Estrés de costos x2
        stress_res = R.cost_stress(bars, best_p, bt_cfg, p_oos[0], p_oos[1], factor=acceptance["thresholds"]["cost_stress_factor"])

        # Sensibilidad de parámetros
        sens_df = R.parameter_sensitivity(bars, best_p, bt_cfg, p_oos[0], p_oos[1], factors=cfg_strategy["evaluation"]["sensitivity_factors"])

        # Regímenes y subperiodos
        rcfg = cfg_strategy["evaluation"]["regime"]
        reg_labels = R.regime_labels(bars, lookback_days=rcfg["lookback_days"], bull=rcfg["bull_threshold"], bear=rcfg["bear_threshold"])
        reg_df = R.regime_breakdown(res_oos, reg_labels)
        sub_df = R.subperiod_breakdown(res_oos)

        # Walk-forward
        wf_cfg = cfg_strategy["evaluation"]["walk_forward"]
        wf_windows = R.walk_forward_windows(
            first_test_start=wf_cfg["first_test_start"],
            data_end=p_oos[1],
            earliest_train_start=cfg_strategy["periods"]["development"][0],
            train_months=wf_cfg["train_months"],
            test_months=wf_cfg["test_months"],
        )
        wf_df = R.walk_forward(bars, grid_cfgs, bt_cfg, wf_windows, metric="sharpe")
        wf_positive_frac = float((wf_df["test_expectancy_usdt"] > 0).mean()) if len(wf_df) else 0.0

        # Criterios y Veredicto
        oos_inputs = {
            "n_trades": m_oos["n_trades"],
            "expectancy_usdt": m_oos["expectancy_usdt"],
            "expectancy_ci_lo_r": bs_exp_r["lo"],
            "profit_factor": m_oos["profit_factor"],
            "sharpe": m_oos["sharpe"],
            "dsr": dsr,
            "max_drawdown": m_oos["max_drawdown"],
            "max_dd_duration_days": m_oos["max_dd_duration_days"],
            "retention": retention,
            "stress_expectancy_usdt": stress_res.get("expectancy_usdt", float("nan")),
            "wf_positive_frac": wf_positive_frac,
            "top5pct_share": m_oos["top5pct_share"],
            "bh_sharpe": m_bh["sharpe"],
            "bh_calmar": m_bh["calmar"],
            "calmar": m_oos["calmar"],
            "sharpe_ci_lo": bs_sharpe["lo"],
            "random_sharpe_hi": rand_baseline["p97_5"]["sharpe"],
            "liquidations": m_oos["liquidations"],
        }

        criteria = evaluate_criteria(oos_inputs, acceptance)
        verdict, reasons = decide_verdict(criteria, m_oos["n_trades"], acceptance)

        print("\n" + "=" * 50)
        print(f"VEREDICTO FINAL: {verdict}")
        for r in reasons:
            print(f"  - {r}")
        print("=" * 50 + "\n")

        # Preparar datos del reporte
        def _fmt(val, pct=False, digits=2):
            if val is None or not isinstance(val, (int, float)) or not math.isfinite(val):
                return "N/A"
            if pct:
                return f"{val * 100:.{digits}f}%"
            return f"{val:.{digits}f}"

        metrics_comparison = [
            {"name": "Retorno Total Neto", "dev": _fmt(m_dev["total_return"], True), "val": _fmt(m_val["total_return"], True), "oos": _fmt(m_oos["total_return"], True), "bh": _fmt(m_bh["total_return"], True), "rand": _fmt(rand_baseline["median"]["total_return"], True)},
            {"name": "CAGR", "dev": _fmt(m_dev["cagr"], True), "val": _fmt(m_val["cagr"], True), "oos": _fmt(m_oos["cagr"], True), "bh": _fmt(m_bh["cagr"], True), "rand": _fmt(rand_baseline["median"]["cagr"], True)},
            {"name": "Sharpe Ratio (24/7)", "dev": _fmt(m_dev["sharpe"]), "val": _fmt(m_val["sharpe"]), "oos": _fmt(m_oos["sharpe"]), "bh": _fmt(m_bh["sharpe"]), "rand": _fmt(rand_baseline["median"]["sharpe"])},
            {"name": "Sortino Ratio", "dev": _fmt(m_dev["sortino"]), "val": _fmt(m_val["sortino"]), "oos": _fmt(m_oos["sortino"]), "bh": _fmt(m_bh["sortino"]), "rand": "N/A"},
            {"name": "Calmar Ratio", "dev": _fmt(m_dev["calmar"]), "val": _fmt(m_val["calmar"]), "oos": _fmt(m_oos["calmar"]), "bh": _fmt(m_bh["calmar"]), "rand": _fmt(rand_baseline["median"]["calmar"])},
            {"name": "Max Drawdown", "dev": _fmt(m_dev["max_drawdown"], True), "val": _fmt(m_val["max_drawdown"], True), "oos": _fmt(m_oos["max_drawdown"], True), "bh": _fmt(m_bh["max_drawdown"], True), "rand": _fmt(rand_baseline["median"]["max_drawdown"], True)},
            {"name": "Duración Peor DD (días)", "dev": _fmt(m_dev["worst_dd_duration_days"], digits=0), "val": _fmt(m_val["worst_dd_duration_days"], digits=0), "oos": _fmt(m_oos["worst_dd_duration_days"], digits=0), "bh": _fmt(m_bh["worst_dd_duration_days"], digits=0), "rand": "N/A"},
            {"name": "Volatilidad Anualizada", "dev": _fmt(m_dev["ann_volatility"], True), "val": _fmt(m_val["ann_volatility"], True), "oos": _fmt(m_oos["ann_volatility"], True), "bh": _fmt(m_bh["ann_volatility"], True), "rand": _fmt(rand_baseline["median"]["ann_volatility"], True)},
            {"name": "VaR 95% diario", "dev": _fmt(m_dev["var_95"], True), "val": _fmt(m_val["var_95"], True), "oos": _fmt(m_oos["var_95"], True), "bh": _fmt(m_bh["var_95"], True), "rand": "N/A"},
            {"name": "CVaR 95% diario", "dev": _fmt(m_dev["cvar_95"], True), "val": _fmt(m_val["cvar_95"], True), "oos": _fmt(m_oos["cvar_95"], True), "bh": _fmt(m_bh["cvar_95"], True), "rand": "N/A"},
            {"name": "Número de Operaciones", "dev": str(m_dev["n_trades"]), "val": str(m_val["n_trades"]), "oos": str(m_oos["n_trades"]), "bh": str(m_bh["n_trades"]), "rand": str(len(res_oos.trades))},
            {"name": "Tasa de Acierto (Win Rate)", "dev": _fmt(m_dev["win_rate"], True), "val": _fmt(m_val["win_rate"], True), "oos": _fmt(m_oos["win_rate"], True), "bh": _fmt(m_bh["win_rate"], True), "rand": "N/A"},
            {"name": "Profit Factor", "dev": _fmt(m_dev["profit_factor"]), "val": _fmt(m_val["profit_factor"]), "oos": _fmt(m_oos["profit_factor"]), "bh": _fmt(m_bh["profit_factor"]), "rand": "N/A"},
            {"name": "Expectativa Neta (USDT/op)", "dev": _fmt(m_dev["expectancy_usdt"]), "val": _fmt(m_val["expectancy_usdt"]), "oos": _fmt(m_oos["expectancy_usdt"]), "bh": _fmt(m_bh["expectancy_usdt"]), "rand": _fmt(rand_baseline["median"]["expectancy_usdt"])},
            {"name": "Expectativa Neta (R/op)", "dev": _fmt(m_dev["expectancy_r"]), "val": _fmt(m_val["expectancy_r"]), "oos": _fmt(m_oos["expectancy_r"]), "bh": "N/A", "rand": "N/A"},
            {"name": "Ganancia Promedio (USDT)", "dev": _fmt(m_dev["avg_win"]), "val": _fmt(m_val["avg_win"]), "oos": _fmt(m_oos["avg_win"]), "bh": _fmt(m_bh["avg_win"]), "rand": "N/A"},
            {"name": "Pérdida Promedio (USDT)", "dev": _fmt(m_dev["avg_loss"]), "val": _fmt(m_val["avg_loss"]), "oos": _fmt(m_oos["avg_loss"]), "bh": _fmt(m_bh["avg_loss"]), "rand": "N/A"},
            {"name": "Concentración Top 5% Ops", "dev": _fmt(m_dev["top5pct_share"], True), "val": _fmt(m_val["top5pct_share"], True), "oos": _fmt(m_oos["top5pct_share"], True), "bh": "N/A", "rand": "N/A"},
            {"name": "Costos Totales (USDT)", "dev": _fmt(m_dev.get("cost_total_costs")), "val": _fmt(m_val.get("cost_total_costs")), "oos": _fmt(m_oos.get("cost_total_costs")), "bh": _fmt(m_bh.get("cost_total_costs")), "rand": "N/A"},
            {"name": "Costos % Ganancia Bruta", "dev": _fmt(m_dev.get("cost_costs_pct_of_gross"), True), "val": _fmt(m_val.get("cost_costs_pct_of_gross"), True), "oos": _fmt(m_oos.get("cost_costs_pct_of_gross"), True), "bh": _fmt(m_bh.get("cost_costs_pct_of_gross"), True), "rand": "N/A"},
            {"name": "Tiempo en Mercado", "dev": _fmt(m_dev["time_in_market"], True), "val": _fmt(m_val["time_in_market"], True), "oos": _fmt(m_oos["time_in_market"], True), "bh": "100.0%", "rand": _fmt(m_oos["time_in_market"], True)},
            {"name": "Apalancamiento Máximo", "dev": _fmt(m_dev["max_leverage"]), "val": _fmt(m_val["max_leverage"]), "oos": _fmt(m_oos["max_leverage"]), "bh": "1.00", "rand": _fmt(m_oos["max_leverage"])},
            {"name": "Eventos de Liquidación", "dev": str(m_dev["liquidations"]), "val": str(m_val["liquidations"]), "oos": str(m_oos["liquidations"]), "bh": str(m_bh["liquidations"]), "rand": str(int(rand_baseline["median"]["liquidations"]))},
        ]

        # Serie de equity para gráficos
        # Unir fechas comunes de OOS para graficar
        t_common = res_oos.equity["time"]
        dd_s = M.drawdown_series(res_oos.equity.set_index("time")["equity"]).values
        report_data = {
            "verdict": verdict,
            "verdict_reasons": reasons,
            "acceptance_version": acceptance.get("version"),
            "n_configs_tested": n_trials,
            "selected_strategy": best_p.key,
            "metrics_comparison": metrics_comparison,
            "criteria": [c.as_dict() for c in criteria],
            "oos_metrics": m_oos,
            "dev_metrics": m_dev,
            "val_metrics": m_val,
            "bh_metrics": m_bh,
            "random_baseline": {
                "median": rand_baseline["median"],
                "p2_5": rand_baseline["p2_5"],
                "p97_5": rand_baseline["p97_5"],
            },
            "robustness": {
                "bootstrap": {
                    "expectancy_usdt": bs_exp_usdt,
                    "expectancy_r": bs_exp_r,
                    "sharpe": bs_sharpe,
                },
                "psr": float(m_oos["psr"]),
                "dsr": float(dsr),
                "monte_carlo_drawdown": mc_dd,
                "cost_stress_x2": {
                    "expectancy_usdt": stress_res.get("expectancy_usdt"),
                    "profit_factor": stress_res.get("profit_factor"),
                    "total_return": stress_res.get("total_return"),
                    "sharpe": stress_res.get("sharpe"),
                },
                "regimes": reg_df.to_dict(orient="records"),
                "subperiods": sub_df.to_dict(orient="records"),
                "walk_forward": wf_df.to_dict(orient="records"),
            },
            "wf_positive_frac": wf_positive_frac,
            "equity_series": {
                "times": [str(x) for x in t_common],
                "net": res_oos.equity["equity"].tolist(),
                "gross": res_oos.equity["gross_equity"].tolist(),
                "buy_hold": bh_oos.equity["equity"].iloc[:len(t_common)].tolist(),
                "drawdown": dd_s.tolist(),
            },
            "trade_pnls_r": r_mults.tolist(),
            "sensitivity_grid": sens_df.to_dict(orient="records"),
        }

        # Generar gráficas y guardar reportes
        rep_dir = ROOT / "reports"
        plots = generate_plots(report_data, rep_dir)
        print(f"Gráficas generadas: {plots}")

        json_path = rep_dir / "profitability_report.json"
        save_json_report(report_data, json_path)
        print(f"Reporte JSON guardado en {json_path}")

        md_path = rep_dir / "profitability_report.md"
        generate_markdown_report(report_data, md_path)
        print(f"Reporte Markdown guardado en {md_path}")

        P.finalize_lock(lock_path, {"verdict": verdict, "reasons": reasons})
        print("Protocolo holdout concluido con éxito y lock finalizado.")

    except Exception as e:
        print(f"Error durante evaluación de holdout: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Evaluación de Rentabilidad")
    parser.add_argument("--stage", choices=["pre", "freeze", "holdout", "final"], required=True)
    args = parser.parse_args()

    cfg_strategy = yaml.safe_load((ROOT / "config" / "strategy.yaml").read_text(encoding="utf-8"))
    acceptance = load_acceptance(ROOT / "config" / "acceptance.yaml")

    if args.stage == "pre":
        stage_pre(cfg_strategy)
    elif args.stage == "freeze":
        stage_freeze()
    elif args.stage == "holdout":
        stage_holdout(cfg_strategy, acceptance)
    elif args.stage == "final":
        from src.evaluation.final_report import generate_final_report
        generate_final_report()


if __name__ == "__main__":
    main()
