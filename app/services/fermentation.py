"""
Fermentation progress: velocity, phase, ETA-to-FG and the recipe step timeline.

Feeds the beta dashboard (`/api/fermentation/summary`, `/api/fermentation/history`)
and the schedule/phase tracker that writes to the autopilot journal.

The math is kept in pure functions (no Influx/config access) so it can be unit
tested directly; `get_fermentation_summary()` / `get_fermentation_history()`
do the I/O and delegate.
"""

import bisect
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# Velocity thresholds, in gravity points (0.001 SG) dropped per day
ACTIVE_PTS_PER_DAY = 1.5
MOVING_PTS_PER_DAY = 0.5
VELOCITY_WINDOW_H = 24
HISTORY_MAX_POINTS = 360


# ---------------------------------------------------------------------------
# Brewfather schedule parsing
# ---------------------------------------------------------------------------

def _ms_or_date_to_iso(v: Any) -> Optional[str]:
    if v is None or v == "":
        return None
    try:
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v / 1000, tz=timezone.utc).isoformat()
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except (ValueError, TypeError, OSError):
        return None


def parse_brewfather_schedule(batch: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    """Extract ([{name, type, temp, days}], start_iso) from a Brewfather batch.

    A batch-level `fermentation` profile overrides the recipe's. `stepTemp` is
    always °C in the Brewfather API; `ramp` (days) is added to the step length
    because the ramp happens inside the step window.
    """
    recipe = batch.get("recipe") or {}
    profile = batch.get("fermentation") or recipe.get("fermentation") or {}
    steps: List[Dict[str, Any]] = []
    for raw in profile.get("steps") or []:
        try:
            days = float(raw.get("stepTime") or 0) + float(raw.get("ramp") or 0)
            temp = raw.get("stepTemp")
            steps.append({
                "name": raw.get("name") or raw.get("type") or f"Step {len(steps) + 1}",
                "type": raw.get("type") or "",
                "temp": round(float(temp), 1) if temp is not None else None,
                "days": round(days, 2),
            })
        except (TypeError, ValueError):
            continue

    start = (_ms_or_date_to_iso(batch.get("fermentationStartDate"))
             or _ms_or_date_to_iso(batch.get("brewDate"))
             or "")
    return steps, start


# ---------------------------------------------------------------------------
# Pure math
# ---------------------------------------------------------------------------

def velocity_pts_per_day(points: Sequence[Tuple[float, float]]) -> Optional[float]:
    """Least-squares slope of (unix_seconds, sg) in gravity points per day.

    Negative = gravity falling. None if there isn't enough spread to fit.
    A regression rather than an endpoint diff so one noisy Tilt reading
    doesn't swing the number.
    """
    if len(points) < 3:
        return None
    ts = [p[0] for p in points]
    if ts[-1] - ts[0] < 3 * 3600:
        return None
    n = len(points)
    mean_t = sum(ts) / n
    mean_sg = sum(p[1] for p in points) / n
    num = sum((t - mean_t) * (sg - mean_sg) for t, sg in points)
    den = sum((t - mean_t) ** 2 for t in ts)
    if den == 0:
        return None
    return num / den * 86400 * 1000


def attenuation_pct(og: float, sg: float) -> float:
    if og <= 1.0:
        return 0.0
    return max(0.0, (og - sg) / (og - 1.0) * 100)


def abv_pct(og: float, sg: float) -> float:
    return max(0.0, (og - sg) * 131.25)


def classify_phase(velocity: Optional[float], sg: Optional[float], og: float,
                   target_fg: float, hours_since_start: Optional[float]) -> str:
    """One-word state for the fermentation card.

    LAG / ACTIVE / SLOWING / STABLE / STALLED / NO DATA. STALLED needs the
    beer to still be well above target *and* under ~70% attenuation — gravity
    that's flat at 1.017 against a 1.012 target is finishing, not stuck.
    """
    if sg is None or velocity is None:
        return "NO DATA"
    drop = -velocity
    att = attenuation_pct(og, sg)
    if hours_since_start is not None and hours_since_start < 48 and drop < ACTIVE_PTS_PER_DAY and att < 15:
        return "LAG"
    if drop >= ACTIVE_PTS_PER_DAY:
        return "ACTIVE"
    if drop >= MOVING_PTS_PER_DAY:
        return "SLOWING"
    if sg > target_fg + 0.005 and att < 70:
        return "STALLED"
    return "STABLE"


def eta_days_to_fg(sg: Optional[float], target_fg: float, velocity: Optional[float]) -> Optional[float]:
    if sg is None:
        return None
    remaining = (sg - target_fg) * 1000
    if remaining <= 0.5:
        return 0.0
    if velocity is None or -velocity < 0.2:
        return None
    return round(remaining / -velocity, 1)


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.strptime(s, "%Y-%m-%d")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def build_schedule(steps: List[Dict[str, Any]], start: Optional[datetime],
                   now: datetime) -> Optional[Dict[str, Any]]:
    """Lay the recipe steps out on the calendar and locate `now` in them."""
    if not steps or start is None:
        return None
    laid_out = []
    cursor = start
    current = len(steps)  # past the end by default
    for i, s in enumerate(steps):
        end = cursor + timedelta(days=float(s.get("days") or 0))
        laid_out.append({**s, "start": cursor.isoformat(), "end": end.isoformat()})
        if current == len(steps) and now < end:
            current = i
        cursor = end
    if now < start:
        current = -1

    def days_until(dt_iso: str) -> float:
        return round((datetime.fromisoformat(dt_iso) - now).total_seconds() / 86400, 1)

    nxt = laid_out[current + 1] if current + 1 < len(laid_out) else None
    crash = next((s for s in laid_out[max(current + 1, 0):]
                  if "crash" in f"{s.get('name', '')} {s.get('type', '')}".lower()), None)
    return {
        "steps": laid_out,
        "current_index": current,
        "current": laid_out[current] if 0 <= current < len(laid_out) else None,
        "next": nxt,
        "days_to_next": days_until(nxt["start"]) if nxt else None,
        "days_to_crash": days_until(crash["start"]) if crash else None,
        "days_to_end": max(0.0, days_until(laid_out[-1]["end"])),
        "end": laid_out[-1]["end"],
    }


def target_temp_at(schedule: Optional[Dict[str, Any]], t: datetime) -> Optional[float]:
    if not schedule:
        return None
    for s in schedule["steps"]:
        if datetime.fromisoformat(s["start"]) <= t < datetime.fromisoformat(s["end"]):
            return s.get("temp")
    return None


def add_velocity_series(series: List[Dict[str, Any]], window_h: float = 12) -> None:
    """Annotate each point with the trailing-window velocity (pts/day)."""
    times = [p["ts"] for p in series]
    for i, p in enumerate(series):
        if p.get("sg") is None:
            p["velocity"] = None
            continue
        j = bisect.bisect_left(times, p["ts"] - window_h * 3600)
        if j >= i:
            p["velocity"] = None
            continue
        prev = series[j]
        dt = p["ts"] - prev["ts"]
        if prev.get("sg") is None or dt < 3600:
            p["velocity"] = None
        else:
            p["velocity"] = round((p["sg"] - prev["sg"]) / (dt / 86400) * 1000, 2)


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def _measurement() -> str:
    from core.config import get_config
    return "test_readings" if get_config("test_mode") else "calibrated_readings"


def _batch_start() -> Optional[datetime]:
    from core.config import get_config
    return _parse_iso(get_config("ferm_start")) or _parse_iso(get_config("start_date"))


def _query_sg_temp(start: datetime, every: Optional[str] = None) -> List[Dict[str, Any]]:
    """[{ts, sg, temp}] from Influx since `start`, optionally windowed."""
    from core.influx import query_api, INFLUX_BUCKET
    agg = f' |> aggregateWindow(every: {every}, fn: mean, createEmpty: false)' if every else ""
    q = (
        f'from(bucket: "{INFLUX_BUCKET}")'
        f' |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})'
        f' |> filter(fn: (r) => r["_measurement"] == "{_measurement()}")'
        f' |> filter(fn: (r) => r["_field"] == "sg" or r["_field"] == "temp")'
        f'{agg}'
    )
    by_ts: Dict[float, Dict[str, Any]] = {}
    for table in query_api.query(q):
        for r in table.records:
            ts = r.get_time().timestamp()
            row = by_ts.setdefault(ts, {"ts": ts, "sg": None, "temp": None})
            row[r.get_field()] = r.get_value()
    return [by_ts[k] for k in sorted(by_ts)]


def get_fermentation_summary(now: Optional[datetime] = None) -> Dict[str, Any]:
    from core.config import get_config
    from services.status import get_status_dict

    now = now or datetime.now(timezone.utc)
    status = get_status_dict()
    og = float(get_config("og") or 1.050)
    target_fg = float(get_config("target_fg") or 1.010)
    sg = status.get("sg")
    start = _batch_start()

    velocity = None
    try:
        recent = _query_sg_temp(now - timedelta(hours=VELOCITY_WINDOW_H))
        velocity = velocity_pts_per_day([(p["ts"], p["sg"]) for p in recent if p["sg"] is not None])
    except Exception as e:
        logger.warning(f"Velocity query failed: {e}")

    hours = (now - start).total_seconds() / 3600 if start else None
    schedule = build_schedule(get_config("ferm_steps") or [], start, now)
    current_step = schedule["current"] if schedule else None
    step_target = current_step.get("temp") if current_step else None
    target_temp = get_config("target_temp") or step_target
    temp = status.get("temp")

    last_sync = status.get("last_sync")
    last_age_min = None
    if last_sync:
        seen = _parse_iso(last_sync)
        if seen:
            last_age_min = round((now - seen).total_seconds() / 60, 1)

    return {
        "batch_name": get_config("batch_name"),
        "style": get_config("style"),
        "yeast": get_config("yeast_strain"),
        "brew_active": bool(get_config("brew_active")),
        "test_mode": bool(get_config("test_mode")),
        "og": og,
        "target_fg": target_fg,
        "sg": sg,
        "temp": temp,
        "temp_unit": status.get("temp_unit", "C"),
        "target_temp": target_temp,
        "temp_delta": round(temp - target_temp, 1) if temp is not None and target_temp is not None else None,
        "velocity": round(velocity, 2) if velocity is not None else None,
        "phase": classify_phase(velocity, sg, og, target_fg, hours),
        "attenuation": round(attenuation_pct(og, sg), 1) if sg else None,
        "abv": round(abv_pct(og, sg), 2) if sg else None,
        "eta_days": eta_days_to_fg(sg, target_fg, velocity),
        "day": int(hours // 24) + 1 if hours is not None and hours >= 0 else None,
        "start": start.isoformat() if start else None,
        "schedule": schedule,
        "sensor": {
            "rssi": status.get("rssi"),
            "last_reading": last_sync,
            "last_reading_age_min": last_age_min,
            "pi_temp": status.get("pi_temp"),
        },
    }


def _window_for(span_s: float) -> str:
    minutes = max(10, int(span_s / 60 / HISTORY_MAX_POINTS))
    return f"{minutes}m"


def get_fermentation_history(now: Optional[datetime] = None) -> Dict[str, Any]:
    from core.config import get_config

    now = now or datetime.now(timezone.utc)
    start = _batch_start() or (now - timedelta(days=14))
    # Brewfather can give a future start (batch planned, not yet pitched)
    # or an ancient one; keep the query bounded either way.
    start = max(min(start, now - timedelta(hours=6)), now - timedelta(days=60))
    series = _query_sg_temp(start, every=_window_for((now - start).total_seconds()))

    og = float(get_config("og") or 1.050)
    schedule = build_schedule(get_config("ferm_steps") or [], _batch_start(), now)
    fixed_target = get_config("target_temp")
    add_velocity_series(series)
    for p in series:
        t = datetime.fromtimestamp(p["ts"], tz=timezone.utc)
        p["t"] = t.isoformat()
        p["target"] = fixed_target or target_temp_at(schedule, t)
        p["abv"] = round(abv_pct(og, p["sg"]), 2) if p.get("sg") else None
        if p.get("sg") is not None:
            p["sg"] = round(p["sg"], 4)
        if p.get("temp") is not None:
            p["temp"] = round(p["temp"], 2)

    return {"start": start.isoformat(), "og": og, "points": series}


# ---------------------------------------------------------------------------
# Journal tracker (Celery Beat)
# ---------------------------------------------------------------------------

_PHASE_NOTES = {
    "ACTIVE": "fermentation active, gravity falling {drop:.1f} pts/day at {sg:.4f}",
    "SLOWING": "fermentation slowing, {drop:.1f} pts/day at {sg:.4f} ({att:.0f}% attenuation)",
    "STABLE": "gravity stable at {sg:.4f} ({drop:.1f} pts/day). Likely done, take a hydrometer FG to confirm",
    "STALLED": "gravity flat at {sg:.4f} with only {att:.0f}% attenuation. Check yeast and beer temp",
}


def _fmt_temp(t: Any) -> str:
    return f" @ {t:g}°C" if isinstance(t, (int, float)) else ""


def track_progress(now: Optional[datetime] = None) -> List[str]:
    """Log step changes, upcoming steps and phase changes to the journal.

    Runs every 15 minutes. State is keyed to the batch so a new Brewfather
    sync starts fresh. A phase must be seen on two consecutive runs before
    it's logged, so velocity noise near a threshold doesn't flap the log.
    Returns the texts logged (for tests/diagnostics).
    """
    from core.config import get_config
    from services.journal import add_entry, get_state, set_state

    if not get_config("brew_active"):
        return []

    now = now or datetime.now(timezone.utc)
    s = get_fermentation_summary(now)
    name = s.get("batch_name") or "Batch"
    batch_key = f"{name}|{s.get('start')}"
    state = get_state("tracker") or {}
    if state.get("batch") != batch_key:
        state = {"batch": batch_key}
    logged: List[str] = []

    def log(text: str, kind: str, level: str = "info") -> None:
        full = f"{name}: {text}"
        if add_entry(full, kind=kind, level=level, dedupe_minutes=24 * 60):
            logged.append(full)

    sched = s.get("schedule")
    if sched:
        idx = sched["current_index"]
        total = len(sched["steps"])
        if "step" in state and idx != state["step"]:
            if 0 <= idx < total:
                cur = sched["current"]
                log(f"next → {cur['name']}{_fmt_temp(cur.get('temp'))} (step {idx + 1}/{total})", "step")
            elif idx >= total:
                log("fermentation schedule complete, ready to package", "step")
        state["step"] = idx

        nxt, days = sched.get("next"), sched.get("days_to_next")
        if nxt and days is not None and 0 <= days <= 1 and state.get("warned_next") != idx:
            hours = max(1, round((datetime.fromisoformat(nxt["start"]) - now).total_seconds() / 3600))
            log(f"{nxt['name']}{_fmt_temp(nxt.get('temp'))} in {hours}h", "step")
            state["warned_next"] = idx

    phase = s.get("phase")
    if phase and phase not in ("NO DATA", "LAG"):
        if phase == state.get("phase"):
            state.pop("pending", None)
        elif state.get("pending") == phase:
            note = _PHASE_NOTES.get(phase)
            if note and s.get("sg") and s.get("velocity") is not None:
                level = "warning" if phase == "STALLED" else "info"
                log(note.format(drop=-s["velocity"], sg=s["sg"], att=s.get("attenuation") or 0), "phase", level)
            state["phase"] = phase
            state.pop("pending", None)
        else:
            state["pending"] = phase

    set_state("tracker", state)
    return logged
