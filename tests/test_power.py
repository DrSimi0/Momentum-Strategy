"""Pruebas unitarias para el análisis de potencia estadística contra cálculos manuales."""
import math
import numpy as np
import pytest

from src.evaluation import power_analysis as PA


def test_compute_trade_sample_stats_manual():
    # Ejemplo con 3 valores: [10, 20, 30]
    # Media = 20
    # Varianza muestral = ((10-20)^2 + (20-20)^2 + (30-20)^2) / (3 - 1) = 200 / 2 = 100 -> std = 10
    # SE = 10 / sqrt(3) = 5.77350269
    # t = 20 / (10 / sqrt(3)) = 2 * sqrt(3) = 3.4641016
    stats = PA.compute_trade_sample_stats([10.0, 20.0, 30.0])
    assert stats["n"] == 3
    assert stats["mean"] == pytest.approx(20.0)
    assert stats["std"] == pytest.approx(10.0)
    assert stats["se"] == pytest.approx(10.0 / math.sqrt(3))
    assert stats["t_stat"] == pytest.approx(2.0 * math.sqrt(3))
    assert stats["ci95_lo"] < 20.0 < stats["ci95_hi"]


def test_compute_trade_sample_stats_edge_cases():
    assert math.isnan(PA.compute_trade_sample_stats([])["mean"])
    assert math.isnan(PA.compute_trade_sample_stats([5.0])["std"])


def test_sample_size_for_significance_manual():
    # Con alpha = 0.05 (z = 1.95996398), mean = 10, std = 20
    # N* = (1.95996398 * 20 / 10)^2 = (3.91992796)^2 = 15.365835
    z = PA.Z_95_TWO_TAILED
    expected = (z * 20.0 / 10.0) ** 2
    res = PA.sample_size_for_significance(10.0, 20.0, alpha=0.05, power=0.5)
    assert res == pytest.approx(expected)

    # Con media <= 0 el tamaño de muestra requerido es infinito
    assert math.isinf(PA.sample_size_for_significance(0.0, 20.0))
    assert math.isinf(PA.sample_size_for_significance(-5.0, 20.0))


def test_sample_size_with_80pct_power():
    # Potencia 80%: (z_alpha + z_beta)^2 * (std / mean)^2
    z_alpha = PA.Z_95_TWO_TAILED
    z_beta = PA.Z_POWER_80
    expected_50 = (z_alpha * 20.0 / 10.0) ** 2
    expected_80 = ((z_alpha + z_beta) * 20.0 / 10.0) ** 2
    res_80 = PA.sample_size_for_significance(10.0, 20.0, alpha=0.05, power=0.8)
    assert res_80 == pytest.approx(expected_80)
    assert res_80 > expected_50  # Exigir 80% de potencia requiere más muestras que solo excluir 0 al 50%


def test_years_needed():
    # 3000 trades / 25 trades por año = 120 años
    assert PA.years_needed(3000.0, 25.0) == pytest.approx(120.0)
    assert math.isinf(PA.years_needed(100.0, 0.0))


def test_required_expectancy_for_sample_size():
    # std = 100, N = 100 -> mu_req = 1.95996398 * 100 / sqrt(100) = 19.5996398
    z = PA.Z_95_TWO_TAILED
    req_100 = PA.required_expectancy_for_sample_size(100.0, 100)
    assert req_100 == pytest.approx(z * 10.0)
    req_400 = PA.required_expectancy_for_sample_size(100.0, 400)
    assert req_400 == pytest.approx(z * 5.0)


def test_run_full_power_analysis_integration():
    # Simulación de trades
    pnl = [2.0, 3.0, 5.0, -1.0, 4.0, -2.0, 8.0, 1.0]
    res = PA.run_full_power_analysis(pnl, period_years=0.5)
    assert res["sample_stats"]["n"] == 8
    assert res["trades_per_year"] == pytest.approx(16.0)
    assert res["n_needed_ci95_excludes_zero"] > 0
    assert 100 in res["required_mean_by_sample_size"]
    assert 200 in res["required_mean_by_sample_size"]
    assert 500 in res["required_mean_by_sample_size"]
    assert "validation_and_conclusion" in res["comparison_with_user_reference"]
