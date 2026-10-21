"""Veredicto y protocolo de congelado/bloqueo."""
import json
import subprocess
from pathlib import Path

import pytest

from src.evaluation import protocol as P
from src.evaluation.verdict import decide_verdict, evaluate_criteria, load_acceptance

ROOT = Path(__file__).resolve().parents[1]
ACC = load_acceptance(ROOT / "config" / "acceptance.yaml")


def good() -> dict:
    """Métricas fuera de muestra que cumplen todos los criterios."""
    return dict(n_trades=80, expectancy_usdt=25.0, expectancy_ci_lo_r=0.05, profit_factor=1.6, sharpe=1.4,
                dsr=0.97, max_drawdown=0.12, max_dd_duration_days=90, retention=0.8, stress_expectancy_usdt=10.0,
                wf_positive_frac=0.7, top5pct_share=0.3, bh_sharpe=0.9, bh_calmar=0.5, calmar=1.2,
                sharpe_ci_lo=0.5, random_sharpe_hi=0.3, liquidations=0)


def verdict(**kw):
    m = good() | kw
    crit = evaluate_criteria(m, ACC)
    return decide_verdict(crit, m["n_trades"], ACC), {c.id: c for c in crit}


def test_all_pass():
    (v, reasons), crit = verdict()
    assert v == "PASS" and all(c.passed for c in crit.values()) and len(reasons) == 3


@pytest.mark.parametrize("kw", [dict(expectancy_usdt=0.0), dict(expectancy_usdt=-1.0), dict(liquidations=1),
                                dict(stress_expectancy_usdt=-0.1), dict(retention=0.2),
                                dict(retention=float("nan"))])
def test_eliminatory_fail(kw):
    (v, _), _ = verdict(**kw)
    assert v == "FAIL"


@pytest.mark.parametrize("kw", [dict(n_trades=45), dict(expectancy_ci_lo_r=-0.01), dict(dsr=0.9),
                                dict(profit_factor=1.2), dict(sharpe=0.5), dict(max_drawdown=0.35),
                                dict(max_dd_duration_days=200), dict(retention=0.4), dict(wf_positive_frac=0.5),
                                dict(top5pct_share=0.7), dict(sharpe_ci_lo=0.2),
                                dict(sharpe=0.85, bh_sharpe=0.9, calmar=0.4)])
def test_non_eliminatory_inconclusive(kw):
    (v, _), _ = verdict(**kw)
    assert v == "INCONCLUSIVE"


def test_threshold_edges():
    _, c = verdict(profit_factor=1.3, sharpe=0.8, dsr=0.95, max_drawdown=0.30, max_dd_duration_days=180,
                   retention=0.5, wf_positive_frac=0.6, top5pct_share=0.6, n_trades=50, expectancy_ci_lo_r=0.0001)
    assert all(x.passed for x in c.values())
    _, c = verdict(expectancy_ci_lo_r=-0.05)
    assert c["expectancy_ci_lower"].passed and not c["ci_excludes_zero"].passed


def test_few_trades_automatic_inconclusive():
    (v, r), _ = verdict(n_trades=20, expectancy_usdt=-5.0, stress_expectancy_usdt=-9.0)
    assert v == "INCONCLUSIVE" and "20" in r[0]
    (v, _), _ = verdict(n_trades=20, liquidations=2)
    assert v == "FAIL"


def test_infinite_profit_factor_passes():
    _, c = verdict(profit_factor=float("inf"))
    assert c["profit_factor"].passed


# ----------------------------------------------------------------------------- protocolo
def _git(cwd, *a):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    for rel in P.FROZEN_FILES:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("version: '1.0.0'\n" if rel.endswith("acceptance.yaml") else "x: 1\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    return tmp_path


def _commit(repo, msg="c"):
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", msg)


def test_freeze_requires_commit(repo):
    (repo / "config/acceptance.yaml").write_text("version: '1.0.1'\n")
    with pytest.raises(P.HoldoutRejected):
        P.freeze(repo)


def test_freeze_and_verify_ok(repo):
    info = P.freeze(repo)
    _commit(repo, "freeze")
    assert P.verify_freeze(repo)["hashes"] == info["hashes"]


def test_verify_rejects_changed_hash(repo):
    P.freeze(repo)
    _commit(repo, "freeze")
    (repo / "config/acceptance.yaml").write_text("version: '1.0.0'\nsharpe: 0.1\n")
    with pytest.raises(P.HoldoutRejected, match="hash cambiado"):
        P.verify_freeze(repo)
    _commit(repo, "cambio comprometido")  # aunque se haga commit, el hash ya no coincide
    with pytest.raises(P.HoldoutRejected, match="hash cambiado"):
        P.verify_freeze(repo)


def test_verify_rejects_uncommitted_freeze(repo):
    P.freeze(repo)
    with pytest.raises(P.HoldoutRejected):
        P.verify_freeze(repo)


def test_holdout_lock_single_use(repo):
    p = P.acquire_holdout_lock(repo, {"x": 1})
    with pytest.raises(P.HoldoutAlreadyUsed):
        P.acquire_holdout_lock(repo, {"x": 2})
    P.finalize_lock(p, {"verdict": "FAIL"})
    data = json.loads(p.read_text())
    assert data["status"] == "completed" and data["verdict"] == "FAIL" and data["x"] == 1
