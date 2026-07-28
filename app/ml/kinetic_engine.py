"""
Yeast pitch kinetics engine.

Calculates viability decay, pitch density per degree Plato, and estimated
fermentation lag phase duration for ML model feature matrices.
"""

import math
from typing import Dict, Any, Optional


def calculate_viability_decay(
    yeast_age_days: int,
    decay_constant: float = 0.008,
) -> float:
    """
    Calculate yeast viability percentage based on age in days.

    Formula:
        Viability (%) = 100 * exp(-lambda * days)
        where lambda approx 0.008 (approx 20% loss per 30 days at 4°C)

    Args:
        yeast_age_days: Days elapsed since manufacture or harvest.
        decay_constant: Viability decay constant (default 0.008).

    Returns:
        Viability percentage clamped between 5.0% and 100.0%.
    """
    if yeast_age_days <= 0:
        return 100.0

    viability = 100.0 * math.exp(-decay_constant * float(yeast_age_days))
    return max(5.0, min(100.0, round(viability, 1)))


def calculate_pitch_density(
    cells_billions: float,
    volume_liters: float,
    og: float = 1.050,
) -> float:
    """
    Calculate pitching density in million cells per mL per degree Plato.

    Formula:
        Plato approx (OG - 1.0) * 250
        Pitch Density (M cells / mL / °P) = cells_billions / (volume_liters * Plato)

    Args:
        cells_billions: Total yeast cells pitched (in billions).
        volume_liters: Wort batch volume in liters.
        og: Original Gravity (default 1.050).

    Returns:
        Pitching density in million cells / mL / °P.
    """
    if cells_billions <= 0 or volume_liters <= 0:
        return 0.0

    plato = max(1.0, (og - 1.0) * 250.0)
    pitch_density = float(cells_billions) / (float(volume_liters) * plato)
    return round(pitch_density, 3)


def estimate_lag_phase_hours(
    viability_pct: float = 95.0,
    pitch_density: float = 0.75,
) -> float:
    """
    Estimate fermentation lag phase duration in hours based on viability and pitch density.

    Args:
        viability_pct: Estimated viability percentage (0 - 100%).
        pitch_density: Pitching rate density (million cells/mL/°P).

    Returns:
        Estimated lag phase duration in hours.
    """
    base_lag = 12.0

    # Viability penalty: lower viability increases lag phase
    viability_factor = 1.0 + max(0.0, (100.0 - viability_pct) / 50.0)

    # Pitch density factor: target ~0.75. Underpitching increases lag, overpitching shortens lag
    if pitch_density > 0:
        density_factor = 0.75 / max(0.2, pitch_density)
    else:
        density_factor = 1.5

    lag_hours = base_lag * viability_factor * density_factor
    return max(4.0, min(72.0, round(lag_hours, 1)))
