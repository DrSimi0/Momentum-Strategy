"""Inferencia estadística no paramétrica para estrategias cuantitativas.
Implementa Bootstrap estacionario (Politis-Romano), prueba de permutación y corrección de Holm-Bonferroni.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


def stationary_bootstrap_indices(
    n: int,
    block_prob: float = 0.1,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """Genera índices de remuestreo según el Bootstrap Estacionario de Politis & Romano (1994).
    
    Args:
        n: Longitud de la serie.
        block_prob: Probabilidad geométrica de iniciar un nuevo bloque (1 / longitud_media_bloque).
        rng: Generador de números aleatorios NumPy.
    """
    if rng is None:
        rng = np.random.default_rng()

    indices = np.empty(n, dtype=int)
    # Primer índice aleatorio uniforme en [0, n)
    indices[0] = rng.integers(0, n)

    # Variables aleatorias Bernoulli y uniformes para el resto
    new_block = rng.random(n - 1) < block_prob
    random_starts = rng.integers(0, n, size=n - 1)

    for i in range(1, n):
        if new_block[i - 1]:
            indices[i] = random_starts[i - 1]
        else:
            # Continuar bloque en círculo cerrado
            indices[i] = (indices[i - 1] + 1) % n

    return indices


def bootstrap_sharpe_distribution(
    daily_returns: np.ndarray,
    n_reps: int = 10000,
    expected_block_len: float = 10.0,
    annualization_factor: float = 252.0,
    seed: int = 20260421,
) -> Tuple[float, Tuple[float, float], float]:
    """Calcula el Sharpe observado, su intervalo de confianza del 95% y el p-valor unilateral centrado bajo H0.
    
    H0: Media de retorno <= 0.
    El p-valor se obtiene centrando la serie: r_centrada = r - mean(r).
    
    Returns:
        (observed_sharpe, (ci_lower, ci_upper), p_value_h0)
    """
    n = len(daily_returns)
    if n < 5:
        return (0.0, (0.0, 0.0), 1.0)

    mean_obs = np.mean(daily_returns)
    std_obs = np.std(daily_returns, ddof=1)
    obs_sharpe = float((mean_obs / std_obs) * np.sqrt(annualization_factor)) if std_obs > 1e-12 else 0.0

    # Serie centrada para evaluar el p-valor bajo H0: mean <= 0
    centered_returns = daily_returns - mean_obs

    rng = np.random.default_rng(seed)
    block_prob = 1.0 / expected_block_len

    boot_sharpes_raw = np.empty(n_reps, dtype=float)
    boot_sharpes_centered = np.empty(n_reps, dtype=float)

    for b in range(n_reps):
        idx = stationary_bootstrap_indices(n, block_prob=block_prob, rng=rng)
        
        sample_raw = daily_returns[idx]
        s_std = np.std(sample_raw, ddof=1)
        boot_sharpes_raw[b] = (np.mean(sample_raw) / s_std * np.sqrt(annualization_factor)) if s_std > 1e-12 else 0.0

        sample_cent = centered_returns[idx]
        sc_std = np.std(sample_cent, ddof=1)
        boot_sharpes_centered[b] = (np.mean(sample_cent) / sc_std * np.sqrt(annualization_factor)) if sc_std > 1e-12 else 0.0

    # Intervalo de confianza al 95% percentil
    ci_lower = float(np.percentile(boot_sharpes_raw, 2.5))
    ci_upper = float(np.percentile(boot_sharpes_raw, 97.5))

    # P-valor unilateral centrado: P(Sharpe_centrado >= observed_sharpe)
    p_value = float(np.mean(boot_sharpes_centered >= obs_sharpe))

    return (obs_sharpe, (ci_lower, ci_upper), p_value)


def permutation_test_signals(
    signals: np.ndarray,
    target_returns: np.ndarray,
    n_reps: int = 10000,
    annualization_factor: float = 252.0,
    seed: int = 20260421,
) -> float:
    """Prueba de permutación (A4): permuta aleatoriamente el orden temporal de las señales.
    
    Rompe cualquier relación causal entre la señal y el retorno objetivo r13.
    Retorna el p-valor: proporción de réplicas permutadas cuyo Sharpe supera al observado.
    """
    valid = (~np.isnan(signals)) & (~np.isnan(target_returns))
    sig = signals[valid]
    ret = target_returns[valid]
    n = len(sig)

    if n < 5:
        return 1.0

    # Rendimiento observado
    obs_pnl = sig * ret
    std_obs = np.std(obs_pnl, ddof=1)
    obs_sharpe = (np.mean(obs_pnl) / std_obs * np.sqrt(annualization_factor)) if std_obs > 1e-12 else 0.0

    rng = np.random.default_rng(seed)
    perm_count = 0

    for _ in range(n_reps):
        perm_sig = rng.permutation(sig)
        perm_pnl = perm_sig * ret
        p_std = np.std(perm_pnl, ddof=1)
        perm_sharpe = (np.mean(perm_pnl) / p_std * np.sqrt(annualization_factor)) if p_std > 1e-12 else 0.0
        if perm_sharpe >= obs_sharpe:
            perm_count += 1

    return float(perm_count / n_reps)


def holm_bonferroni_correction(p_values: Dict[str, float]) -> Dict[str, Dict[str, float]]:
    """Aplica la corrección paso a paso de Holm-Bonferroni a un diccionario de p-valores.
    
    Controla la tasa de error por familia (FWER) al nivel nominal alpha.
    
    Returns:
        Diccionario con {nombre_prueba: {"raw_p": p, "adjusted_p": p_adj, "reject_h0": bool}}.
    """
    m = len(p_values)
    if m == 0:
        return {}

    sorted_tests = sorted(p_values.items(), key=lambda kv: kv[1])
    adjusted = {}
    cum_max = 0.0

    for rank, (name, p_raw) in enumerate(sorted_tests):
        # Multiplicador de Holm: (m - rank)
        mult = m - rank
        p_candidate = min(1.0, mult * p_raw)
        # Garantizar monotonicidad del p-valor ajustado
        cum_max = max(cum_max, p_candidate)
        p_adj = min(1.0, cum_max)
        adjusted[name] = {
            "raw_p": float(p_raw),
            "adjusted_p": float(p_adj),
            "rank": rank + 1,
            "reject_h0": bool(p_adj <= 0.05),
        }

    return adjusted
