"""
Hop creep analyzer service.

Detects kinetic signatures of secondary enzymatic hop creep (dextrin breakdown)
and calculates predicted final gravity offsets and duration extensions.
"""

from typing import List, Dict, Any, Optional

# Enzymatic activity index by hop variety (higher = stronger diastatic activity)
ENZYMATIC_HOP_INDEX: Dict[str, float] = {
    "amarillo": 1.4,
    "cascade": 1.3,
    "centennial": 1.3,
    "citra": 1.2,
    "simcoe": 1.2,
    "mosaic": 1.1,
    "chinook": 1.1,
    "saaz": 0.8,
    "hallertau": 0.7,
}


def get_hop_enzymatic_index(hop_variety: str) -> float:
    """Return the relative enzymatic strength factor for a hop variety."""
    if not hop_variety:
        return 1.0
    key = hop_variety.lower().strip()
    for name, factor in ENZYMATIC_HOP_INDEX.items():
        if name in key:
            return factor
    return 1.0


def detect_hop_creep_signature(velocity_readings: List[float], current_sg: float, og: float) -> bool:
    """
    Detect if active hop creep is occurring based on SG velocity and current attenuation.

    Args:
        velocity_readings: List of recent 24h SG velocity readings (SG/day).
        current_sg: Latest specific gravity reading.
        og: Original gravity of the batch.

    Returns:
        True if hop creep signature (secondary drop < -0.001 SG/day after high attenuation) is detected.
    """
    if not velocity_readings or og <= 1.0:
        return False

    # Calculate apparent attenuation
    apparent_attenuation = (og - current_sg) / (og - 1.0) if og > 1.0 else 0.0

    # Hop creep typically occurs when attenuation is already high (> 75%)
    if apparent_attenuation < 0.75:
        return False

    # Check if recent velocity exhibits a secondary downward shift (< -0.001 SG/day)
    recent_velocity = velocity_readings[-1] if velocity_readings else 0.0
    return recent_velocity < -0.001


def calculate_hop_creep_offset(dry_hop_additions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate predicted FG offset and duration extension from dry hop additions.

    Args:
        dry_hop_additions: List of dicts or DryHopAddition objects.

    Returns:
        Dict with gravity_offset (float), time_extension_days (float), and creep_detected (bool).
    """
    if not dry_hop_additions:
        return {
            "creep_detected": False,
            "gravity_offset": 0.0,
            "time_extension_days": 0.0,
        }

    total_offset = 0.0
    total_time_ext = 0.0

    for addition in dry_hop_additions:
        # Handle dict or object
        if hasattr(addition, "dosage_g_l"):
            dosage = getattr(addition, "dosage_g_l", 0.0)
            temp = getattr(addition, "temperature_c", 20.0)
            variety = getattr(addition, "hop_variety", "")
        elif isinstance(addition, dict):
            dosage = addition.get("dosage_g_l", 0.0)
            temp = addition.get("temperature_c", 20.0)
            variety = addition.get("hop_variety", "")
        else:
            continue

        if dosage <= 0:
            continue

        idx = get_hop_enzymatic_index(variety)

        # Temperature multiplier: warm dry-hopping (15-22°C) has higher enzymatic activity than cold (0-4°C)
        if temp < 5.0:
            temp_factor = 0.15
        elif temp < 14.0:
            temp_factor = 0.5
        else:
            temp_factor = 1.0

        # Base offset: ~0.0002 SG drop per g/L of dry hops, scaled by variety index and temp factor
        addition_offset = -0.0002 * dosage * idx * temp_factor
        addition_time = (dosage / 2.5) * idx * temp_factor  # Days of additional fermentation

        total_offset += addition_offset
        total_time_ext += addition_time

    # Clamp offsets to physically plausible bounds (-0.004 max drop, 7 days max extension)
    clamped_offset = max(-0.004, round(total_offset, 4))
    clamped_time = max(0.0, min(7.0, round(total_time_ext, 1)))

    return {
        "creep_detected": clamped_offset < -0.0005,
        "gravity_offset": clamped_offset,
        "time_extension_days": clamped_time,
    }
