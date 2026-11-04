"""
Heating ramp tracking for brew day.

Temperature readings are logged by hand from the G40 display. Readings that
share the same target temperature form a ramp segment (e.g. "heat strike water
to 72 °C"). For each segment we work out the heating rate in °C/min and, while
it is still climbing, an ETA to the target.

Rates from finished brews are kept in a small JSON history so a future brew day
can predict the ETA before enough live readings exist.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.config import DATA_DIR, logger

HISTORY_FILE = os.path.join(DATA_DIR, "ramp_history.json")
HISTORY_LIMIT = 50          # brews kept on disk
HISTORY_WINDOW = 5          # recent brews averaged for predictions
MIN_RISE_C = 3.0            # a segment must climb this much to count as a ramp
RATE_WINDOW = 4             # readings used for the live rate


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _minutes_between(a: str, b: str) -> float:
    return (_parse_ts(b) - _parse_ts(a)).total_seconds() / 60.0


def slope_c_per_min(readings: List[dict]) -> Optional[float]:
    """Least-squares heating rate over the readings, or None if it can't be judged."""
    if len(readings) < 2:
        return None
    t0 = readings[0]["timestamp"]
    xs = [_minutes_between(t0, r["timestamp"]) for r in readings]
    ys = [float(r["temp_c"]) for r in readings]
    if xs[-1] - xs[0] < 0.5:
        return None
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx


def split_segments(readings: List[dict]) -> List[Dict[str, Any]]:
    """Group consecutive readings with the same phase and target into segments."""
    segments: List[Dict[str, Any]] = []
    for r in readings:
        key = (r.get("phase"), r.get("target_c"))
        if segments and segments[-1]["key"] == key:
            segments[-1]["readings"].append(r)
        else:
            segments.append({"key": key, "phase": r.get("phase"),
                             "target_c": r.get("target_c"), "readings": [r]})
    for s in segments:
        rs = s["readings"]
        s["start_c"] = float(rs[0]["temp_c"])
        s["end_c"] = float(rs[-1]["temp_c"])
        s["minutes"] = round(_minutes_between(rs[0]["timestamp"], rs[-1]["timestamp"]), 1)
        rate = slope_c_per_min(rs)
        s["rate_c_per_min"] = round(rate, 2) if rate is not None else None
        s["is_ramp"] = (s["end_c"] - s["start_c"]) >= MIN_RISE_C and rate is not None and rate > 0
        del s["key"]
    return segments


def load_history() -> List[dict]:
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    except Exception as e:
        logger.warning(f"Could not read ramp history: {e}")
        return []


def historical_rate(phase: str, history: Optional[List[dict]] = None) -> Optional[Dict[str, Any]]:
    """Average ramp rate for a phase over the most recent brews that recorded one."""
    history = load_history() if history is None else history
    rates = []
    for brew in reversed(history):
        phase_rates = [s["rate_c_per_min"] for s in brew.get("ramps", [])
                       if s.get("phase") == phase and s.get("rate_c_per_min")]
        if phase_rates:
            rates.append(sum(phase_rates) / len(phase_rates))
        if len(rates) >= HISTORY_WINDOW:
            break
    if not rates:
        return None
    return {"rate_c_per_min": round(sum(rates) / len(rates), 2), "brews": len(rates)}


def ramp_summary(session: dict, history: Optional[List[dict]] = None) -> Dict[str, Any]:
    """Live ramp status for the session: segments, current rate and ETA to target."""
    readings = session.get("temp_readings", [])
    segments = split_segments(readings)
    summary: Dict[str, Any] = {"segments": segments, "current": None}
    if not segments:
        return summary

    seg = segments[-1]
    latest = seg["readings"][-1]
    target = seg["target_c"]
    live_rate = slope_c_per_min(seg["readings"][-RATE_WINDOW:])

    current: Dict[str, Any] = {
        "phase": seg["phase"],
        "temp_c": float(latest["temp_c"]),
        "target_c": target,
        "rate_c_per_min": round(live_rate, 2) if live_rate is not None else None,
        "eta_min": None,
        "eta_source": None,
        "history_brews": None,
    }

    if target is not None and float(target) > current["temp_c"]:
        remaining = float(target) - current["temp_c"]
        if live_rate is not None and live_rate > 0.05:
            current["eta_min"] = round(remaining / live_rate, 1)
            current["eta_source"] = "live"
        else:
            hist = historical_rate(seg["phase"], history)
            if hist:
                current["eta_min"] = round(remaining / hist["rate_c_per_min"], 1)
                current["eta_source"] = "history"
                current["history_brews"] = hist["brews"]
    elif target is not None:
        current["eta_min"] = 0.0
        current["eta_source"] = "reached"

    summary["current"] = current
    return summary


def save_session_ramps(session: dict) -> Optional[dict]:
    """Append this brew's ramp segments to the history file. Returns the entry saved."""
    ramps = [
        {k: s[k] for k in ("phase", "target_c", "start_c", "end_c", "minutes", "rate_c_per_min")}
        for s in split_segments(session.get("temp_readings", []))
        if s["is_ramp"]
    ]
    if not ramps:
        return None
    recipe = session.get("recipe", {})
    entry = {
        "date": session.get("started_at"),
        "batch_id": session.get("batch_id"),
        "batch_name": session.get("batch_name"),
        "volume_l": recipe.get("target_volume_l") or recipe.get("volume"),
        "ramps": ramps,
    }
    history = load_history()
    history.append(entry)
    history = history[-HISTORY_LIMIT:]
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE) or ".", exist_ok=True)
        tmp = HISTORY_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
        os.replace(tmp, HISTORY_FILE)
    except Exception as e:
        logger.error(f"Could not save ramp history: {e}")
        return None
    return entry


def write_temp_point(batch_id: str, reading: dict) -> None:
    """Best-effort copy of a reading to InfluxDB so Grafana can chart it."""
    try:
        from influxdb_client import Point
        from core.influx import write_api, INFLUX_BUCKET, INFLUX_ORG

        p = (Point("brewday_temp")
             .tag("batch_id", batch_id)
             .tag("phase", reading.get("phase") or "unknown")
             .field("temp_c", float(reading["temp_c"]))
             .time(_parse_ts(reading["timestamp"])))
        if reading.get("target_c") is not None:
            p.field("target_c", float(reading["target_c"]))
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
    except Exception as e:
        logger.warning(f"Brew day temp not written to InfluxDB: {e}")
