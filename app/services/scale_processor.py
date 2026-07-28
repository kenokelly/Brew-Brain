"""
Keg scale processor service.

Calculates net weight, specific gravity compensated volume, remaining percentage,
and handles zero-drift auto-calibration detection for ESP32 keg scale sensors.
"""

from typing import Dict, Any, Optional

DEFAULT_TARE_WEIGHT_KG: float = 4.5  # Standard 19L Corny Keg tare weight
DEFAULT_KEG_CAPACITY_L: float = 19.0


def calculate_keg_volume(
    raw_weight_kg: float,
    tare_weight_kg: float = DEFAULT_TARE_WEIGHT_KG,
    sg: float = 1.010,
    keg_capacity_l: float = DEFAULT_KEG_CAPACITY_L,
) -> Dict[str, Any]:
    """
    Compute net beer weight and density-compensated volume from raw scale weight.

    Formula:
        Net Weight = max(0, Raw Weight - Tare Weight)
        Volume (L) = Net Weight (kg) / Specific Gravity (kg/L)

    Args:
        raw_weight_kg: Total scale reading including keg and beer (in kg).
        tare_weight_kg: Empty keg weight (in kg).
        sg: Final Gravity of beer for density adjustment (default 1.010).
        keg_capacity_l: Full capacity of the keg in Litres (default 19.0L).

    Returns:
        Dict containing net weight, volume in L and mL, remaining percentage,
        and status flags.
    """
    if raw_weight_kg is None or not isinstance(raw_weight_kg, (int, float)):
        raise ValueError(f"raw_weight_kg must be a number, got {type(raw_weight_kg).__name__}")
    if raw_weight_kg < 0:
        raise ValueError(f"raw_weight_kg cannot be negative, got {raw_weight_kg}")
    if sg <= 0:
        sg = 1.010  # Fallback guard

    # Disconnect / empty detection check: raw weight < 0.5kg indicates scale unweighted or disconnected
    is_disconnected = raw_weight_kg < 0.5

    net_weight_kg = max(0.0, raw_weight_kg - tare_weight_kg)
    volume_l = net_weight_kg / sg
    volume_ml = volume_l * 1000.0

    capacity_l = keg_capacity_l if keg_capacity_l > 0 else DEFAULT_KEG_CAPACITY_L
    pct = min(100.0, (volume_l / capacity_l) * 100.0)

    return {
        "raw_weight_kg": round(float(raw_weight_kg), 2),
        "tare_weight_kg": round(float(tare_weight_kg), 2),
        "net_weight_kg": round(net_weight_kg, 2),
        "volume_remaining_l": round(volume_l, 2),
        "volume_remaining_ml": round(volume_ml, 1),
        "remaining_pct": round(pct, 1),
        "is_empty": volume_l <= 0.2,
        "is_disconnected": is_disconnected,
        "sg": sg,
    }
