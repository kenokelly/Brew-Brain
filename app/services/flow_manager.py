"""
Flow meter pour manager service.

Converts flow sensor pulses to volume, applies noise thresholds, reconciles pours
against active tap volume, and triggers low-keg volume alerts.
"""

from typing import Dict, Any, Optional
from services.taps import pour_tap, get_config

DEFAULT_K_FACTOR: float = 5880.0  # Default pulses/L for YF-S401 sensor
MINIMUM_POUR_THRESHOLD_ML: float = 15.0  # Noise filter threshold in mL


def process_pour_event(
    tap_id: str,
    pulse_count: int,
    volume_ml: Optional[float] = None,
    duration_sec: float = 0.0,
    k_factor: float = DEFAULT_K_FACTOR,
) -> Dict[str, Any]:
    """
    Process a flow meter pour event.

    Args:
        tap_id: Tap identifier (e.g. 'tap_1' or 'tap1').
        pulse_count: Number of hall-effect pulses counted.
        volume_ml: Explicit volume in mL (if pre-calculated by firmware), else derived from pulses.
        duration_sec: Duration of pour in seconds.
        k_factor: Sensor pulses per Liter factor (default 5880.0).

    Returns:
        Dict detailing the pour status, volume, new remaining %, and alert status.
    """
    if not tap_id:
        raise ValueError("tap_id is required")

    # Derive volume if not supplied
    if volume_ml is None or volume_ml <= 0:
        if k_factor <= 0:
            k_factor = DEFAULT_K_FACTOR
        volume_ml = (float(pulse_count) / k_factor) * 1000.0

    # Noise filter threshold check
    if volume_ml < MINIMUM_POUR_THRESHOLD_ML:
        return {
            "status": "ignored",
            "reason": f"Pour volume ({round(volume_ml, 1)}mL) below noise threshold ({MINIMUM_POUR_THRESHOLD_ML}mL)",
            "volume_ml": round(volume_ml, 1),
            "pulse_count": pulse_count,
        }

    # Decrement volume on tap
    pour_result = pour_tap(tap_id, volume_ml)

    if "error" in pour_result:
        return {
            "status": "error",
            "error": pour_result["error"],
            "volume_ml": round(volume_ml, 1),
        }

    new_pct = pour_result.get("new_remaining_pct", 0.0)
    is_low_volume = new_pct < 10.0

    return {
        "status": "success",
        "tap_id": tap_id,
        "volume_ml": round(volume_ml, 1),
        "duration_sec": round(float(duration_sec), 1),
        "pulse_count": pulse_count,
        "new_remaining_pct": new_pct,
        "is_low_volume_alert": is_low_volume,
    }
