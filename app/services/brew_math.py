"""
Deterministic brewing correction calculations.

All functions are pure math — no LLM calls, no side effects, no network I/O.
Used by BrewSessionManager to compute real-time gravity corrections on brew day.
"""


def _validate_sg(value: float, name: str) -> None:
    """Validate that a specific gravity reading is physically plausible."""
    if not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {type(value).__name__}")
    if value <= 1.0:
        raise ValueError(f"{name} must be greater than 1.000, got {value}")


def _validate_positive(value: float, name: str) -> None:
    """Validate that a value is strictly positive."""
    if not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {type(value).__name__}")
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0, got {value}")


def calculate_dme_addition(
    measured_sg: float, target_sg: float, volume_l: float
) -> float:
    """
    Calculate grams of Dry Malt Extract needed to raise gravity from measured to target.

    Formula: (target_sg - measured_sg) * volume_l * 1000 / 0.375

    DME contributes approximately 1.046 gravity points per pound per gallon,
    which translates to roughly 0.375 gravity points per gram per litre.

    Args:
        measured_sg: Current specific gravity (must be > 1.0).
        target_sg: Target specific gravity (must be > 1.0 and >= measured_sg).
        volume_l: Wort volume in litres (must be > 0).

    Returns:
        Grams of DME to add.

    Raises:
        ValueError: If inputs are invalid.
    """
    _validate_sg(measured_sg, "measured_sg")
    _validate_sg(target_sg, "target_sg")
    _validate_positive(volume_l, "volume_l")

    if target_sg < measured_sg:
        raise ValueError(
            f"target_sg ({target_sg}) must be >= measured_sg ({measured_sg}) "
            "for DME addition"
        )

    return (target_sg - measured_sg) * volume_l * 1000 / 0.375


def calculate_dilution_water(
    measured_sg: float, target_sg: float, volume_l: float
) -> float:
    """
    Calculate litres of water to add to dilute wort from measured to target gravity.

    Formula: ((measured_sg - 1.0) / (target_sg - 1.0) * volume_l) - volume_l

    Based on the principle that total dissolved extract is conserved:
    (SG - 1) * Volume = constant.

    Args:
        measured_sg: Current specific gravity (must be > 1.0 and > target_sg).
        target_sg: Target specific gravity (must be > 1.0).
        volume_l: Current wort volume in litres (must be > 0).

    Returns:
        Litres of water to add.

    Raises:
        ValueError: If inputs are invalid.
    """
    _validate_sg(measured_sg, "measured_sg")
    _validate_sg(target_sg, "target_sg")
    _validate_positive(volume_l, "volume_l")

    if target_sg > measured_sg:
        raise ValueError(
            f"target_sg ({target_sg}) must be <= measured_sg ({measured_sg}) "
            "for dilution"
        )

    water_to_add = ((measured_sg - 1.0) / (target_sg - 1.0) * volume_l) - volume_l
    return water_to_add


def calculate_boil_extension(
    measured_sg: float,
    target_sg: float,
    volume_l: float,
    boil_off_rate: float,
) -> float:
    """
    Calculate extra minutes of boiling needed to concentrate wort to target gravity.

    The total dissolved extract is conserved during boiling, so we calculate the
    target volume that would give us the desired gravity, then work out how long
    it would take to boil off the excess at the given boil-off rate.

    Args:
        measured_sg: Current specific gravity (must be > 1.0).
        target_sg: Target specific gravity (must be > 1.0 and >= measured_sg).
        volume_l: Current wort volume in litres (must be > 0).
        boil_off_rate: Boil-off rate in litres per minute (must be > 0).

    Returns:
        Extra minutes of boiling required.

    Raises:
        ValueError: If inputs are invalid.
    """
    _validate_sg(measured_sg, "measured_sg")
    _validate_sg(target_sg, "target_sg")
    _validate_positive(volume_l, "volume_l")
    _validate_positive(boil_off_rate, "boil_off_rate")

    if target_sg < measured_sg:
        raise ValueError(
            f"target_sg ({target_sg}) must be >= measured_sg ({measured_sg}) "
            "for boil extension (boiling concentrates wort)"
        )

    # Volume needed to reach target gravity while preserving total extract:
    # (measured_sg - 1) * volume_l = (target_sg - 1) * target_volume
    target_volume = (measured_sg - 1.0) / (target_sg - 1.0) * volume_l

    # How much volume must be boiled off
    volume_to_boil_off = volume_l - target_volume

    if volume_to_boil_off <= 0:
        return 0.0

    # Time = volume / rate
    extra_minutes = volume_to_boil_off / boil_off_rate
    return extra_minutes
