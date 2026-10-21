"""Criterios de aceptación y veredicto FAIL / INCONCLUSIVE / PASS a partir de config/acceptance.yaml.

Lógica (ver DECISIONS.md):
1. Si hay menos de ``inconclusive_trades_below`` operaciones fuera de muestra -> INCONCLUSIVE automático,
   salvo liquidación (evento determinista, no estadístico) -> FAIL.
2. Si falla cualquier criterio eliminatorio -> FAIL.
3. Si se cumplen todos los criterios -> PASS.
4. En otro caso -> INCONCLUSIVE (incluye los disparadores explícitos: pocas operaciones, IC que incluye 0,
   DSR bajo el umbral, y cualquier otro criterio no eliminatorio incumplido).
PASS = evidencia consistente de edge en el pasado bajo este protocolo; NO implica rentabilidad futura.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

ELIMINATORY, TRIGGER, STANDARD = "eliminatory", "inconclusive_trigger", "standard"
PRIORITY = {ELIMINATORY: 0, TRIGGER: 1, STANDARD: 2}


@dataclass
class Criterion:
    id: str
    description: str
    value: object
    threshold: str
    passed: bool
    kind: str

    def as_dict(self) -> dict:
        d = asdict(self)
        if isinstance(d["value"], float) and not math.isfinite(d["value"]):
            d["value"] = None if math.isnan(d["value"]) else str(d["value"])
        return d


def load_acceptance(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _f(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def _gt(v, t) -> bool:
    v = _f(v)
    return math.isfinite(v) and v > t or (v == math.inf and t < math.inf)


def _ge(v, t) -> bool:
    v = _f(v)
    return (math.isfinite(v) or v == math.inf) and v >= t


def _le(v, t) -> bool:
    v = _f(v)
    return math.isfinite(v) and v <= t


def evaluate_criteria(m: dict, acc: dict) -> list[Criterion]:
    """``m``: métricas fuera de muestra ya calculadas por código (ver run_evaluation.oos_inputs)."""
    t, e = acc["thresholds"], acc["eliminatory"]
    C = []
    add = lambda *a: C.append(Criterion(*a))  # noqa: E731
    add("min_trades", "Operaciones fuera de muestra", m["n_trades"], f">= {t['min_trades_oos']}",
        _ge(m["n_trades"], t["min_trades_oos"]), TRIGGER)
    add("expectancy_positive", "Expectativa neta por operación (USDT)", m["expectancy_usdt"],
        f"> {e['expectancy_net_oos_le']}", _gt(m["expectancy_usdt"], e["expectancy_net_oos_le"]), ELIMINATORY)
    add("expectancy_ci_lower", "Cota inferior IC95% expectativa (R)", m["expectancy_ci_lo_r"],
        f">= {t['expectancy_ci95_lower_min_r']}", _ge(m["expectancy_ci_lo_r"], t["expectancy_ci95_lower_min_r"]),
        STANDARD)
    add("ci_excludes_zero", "IC95% de la expectativa (R) excluye 0", m["expectancy_ci_lo_r"], "> 0",
        _gt(m["expectancy_ci_lo_r"], 0.0), TRIGGER)
    add("profit_factor", "Profit factor neto", m["profit_factor"], f">= {t['profit_factor_oos_min']}",
        _ge(m["profit_factor"], t["profit_factor_oos_min"]), STANDARD)
    add("sharpe", "Sharpe neto anualizado", m["sharpe"], f">= {t['sharpe_oos_min']}",
        _ge(m["sharpe"], t["sharpe_oos_min"]), STANDARD)
    add("deflated_sharpe", "Deflated Sharpe Ratio", m["dsr"], f">= {t['deflated_sharpe_min']}",
        _ge(m["dsr"], t["deflated_sharpe_min"]), TRIGGER)
    add("max_drawdown", "Máximo drawdown", m["max_drawdown"], f"<= {t['max_drawdown_oos_max']}",
        _le(m["max_drawdown"], t["max_drawdown_oos_max"]), STANDARD)
    add("max_dd_duration", "Duración máxima de drawdown (días)", m["max_dd_duration_days"],
        f"<= {t['max_dd_duration_days_max']}", _le(m["max_dd_duration_days"], t["max_dd_duration_days_max"]),
        STANDARD)
    add("retention", "Retención (CAGR fuera de muestra / desarrollo)", m["retention"], f">= {t['retention_min']}",
        _ge(m["retention"], t["retention_min"]), STANDARD)
    add("retention_floor", "Retención mínima eliminatoria", m["retention"], f">= {e['retention_below']}",
        _ge(m["retention"], e["retention_below"]), ELIMINATORY)
    add("cost_stress", f"Expectativa neta con costos x{t['cost_stress_factor']:g} (USDT)",
        m["stress_expectancy_usdt"], f"> {e['cost_stress_expectancy_le']}",
        _gt(m["stress_expectancy_usdt"], e["cost_stress_expectancy_le"]), ELIMINATORY)
    add("walk_forward", "Fracción de ventanas walk-forward con expectativa > 0", m["wf_positive_frac"],
        f">= {t['walk_forward_positive_frac_min']}", _ge(m["wf_positive_frac"], t["walk_forward_positive_frac_min"]),
        STANDARD)
    add("concentration", "Participación del 5% mejor de operaciones en la ganancia neta", m["top5pct_share"],
        f"<= {t['top5pct_share_max']}", _le(m["top5pct_share"], t["top5pct_share_max"]), STANDARD)
    beat_bh = _gt(_f(m["sharpe"]) - _f(m["bh_sharpe"]), 0) or _gt(_f(m["calmar"]) - _f(m["bh_calmar"]), 0)
    add("beat_buy_hold", "Supera a buy & hold en Sharpe o Calmar",
        {"sharpe": m["sharpe"], "bh_sharpe": m["bh_sharpe"], "calmar": m["calmar"], "bh_calmar": m["bh_calmar"]},
        "Sharpe > B&H o Calmar > B&H", bool(beat_bh) or not t["beat_buy_hold_risk_adjusted"], STANDARD)
    add("beat_random", "IC95% Sharpe estrategia sin solapar con IC95% aleatorio",
        {"strategy_sharpe_ci_lo": m["sharpe_ci_lo"], "random_sharpe_p97_5": m["random_sharpe_hi"]},
        "IC_lo estrategia > IC_hi aleatorio",
        _gt(_f(m["sharpe_ci_lo"]) - _f(m["random_sharpe_hi"]), 0) or not t["beat_random_no_ci_overlap"], STANDARD)
    add("zero_liquidations", "Eventos de liquidación simulada", m["liquidations"], f"<= {t['max_liquidations']}",
        _le(m["liquidations"], t["max_liquidations"]), ELIMINATORY)
    return C


def decide_verdict(criteria: list[Criterion], n_trades: int, acc: dict) -> tuple[str, list[str]]:
    failed = sorted([c for c in criteria if not c.passed], key=lambda c: PRIORITY[c.kind])
    fmt = lambda c: f"{c.description}: {_fmt(c.value)} (umbral {c.threshold})"  # noqa: E731
    below = acc["thresholds"]["inconclusive_trades_below"]
    if n_trades < below:
        liq = [c for c in failed if c.id == "zero_liquidations"]
        if liq:
            return "FAIL", [fmt(liq[0]), f"Solo {n_trades} operaciones fuera de muestra (< {below})"]
        reasons = [f"Solo {n_trades} operaciones fuera de muestra (< {below}): INCONCLUSIVE automático"]
        return "INCONCLUSIVE", reasons + [fmt(c) for c in failed if c.id != "min_trades"][:2]
    if any(c.kind == ELIMINATORY for c in failed):
        return "FAIL", [fmt(c) for c in failed][:3]
    if not failed:
        key = [c for c in criteria if c.id in ("expectancy_ci_lower", "deflated_sharpe", "profit_factor")]
        return "PASS", [fmt(c) for c in key]
    return "INCONCLUSIVE", [fmt(c) for c in failed][:3]


def _fmt(v) -> str:
    if isinstance(v, dict):
        return ", ".join(f"{k}={_fmt(x)}" for k, x in v.items())
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)
