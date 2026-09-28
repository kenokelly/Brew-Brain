"""Tests for the beta dashboard's fermentation math, step timeline and journal."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from services import fermentation as ferm
from services import journal

NOW = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Brewfather parsing
# ---------------------------------------------------------------------------

def test_parse_brewfather_schedule_prefers_batch_profile_and_adds_ramp():
    batch = {
        "fermentationStartDate": int(datetime(2026, 8, 15, tzinfo=timezone.utc).timestamp() * 1000),
        "brewDate": 1,
        "fermentation": {"steps": [
            {"type": "Primary", "stepTemp": 19, "stepTime": 4},
            {"type": "Secondary", "stepTemp": 21, "stepTime": 3, "ramp": 1},
            {"type": "Cold Crash", "stepTemp": 2, "stepTime": 2},
        ]},
        "recipe": {"fermentation": {"steps": [{"type": "Ignored", "stepTemp": 1, "stepTime": 1}]}},
    }
    steps, start = ferm.parse_brewfather_schedule(batch)
    assert [s["name"] for s in steps] == ["Primary", "Secondary", "Cold Crash"]
    assert steps[1]["days"] == 4.0
    assert steps[2]["temp"] == 2.0
    assert start.startswith("2026-08-15")


def test_parse_brewfather_schedule_falls_back_to_recipe_and_brew_date():
    batch = {"brewDate": "2026-08-10", "recipe": {"fermentation": {"steps": [
        {"type": "Primary", "stepTemp": 18, "stepTime": 10}, {"bad": "step", "stepTime": "x"}]}}}
    steps, start = ferm.parse_brewfather_schedule(batch)
    assert len(steps) == 1
    assert start.startswith("2026-08-10")


def test_parse_brewfather_schedule_empty():
    assert ferm.parse_brewfather_schedule({}) == ([], "")


# ---------------------------------------------------------------------------
# Math
# ---------------------------------------------------------------------------

def _line(pts_per_day, hours=24, start_sg=1.030, n=25):
    t0 = NOW.timestamp() - hours * 3600
    return [(t0 + i * hours * 3600 / (n - 1),
             start_sg + pts_per_day / 1000 * (i * hours / (n - 1)) / 24) for i in range(n)]


def test_velocity_regression_recovers_slope():
    assert ferm.velocity_pts_per_day(_line(-6.0)) == pytest.approx(-6.0, abs=0.01)


def test_velocity_needs_enough_span_and_points():
    assert ferm.velocity_pts_per_day(_line(-6.0)[:2]) is None
    assert ferm.velocity_pts_per_day(_line(-6.0, hours=2)) is None


@pytest.mark.parametrize("velocity,sg,hours,expected", [
    (None, 1.050, 100, "NO DATA"),
    (-0.2, 1.064, 10, "LAG"),
    (-6.0, 1.040, 60, "ACTIVE"),
    (-0.9, 1.016, 150, "SLOWING"),
    # Flat at 1.017 against a 1.012 target with 72% attenuation is finishing,
    # not stuck: the false "NO FERMENTATION" case this classifier avoids.
    (-0.3, 1.017, 170, "STABLE"),
    (-0.1, 1.040, 120, "STALLED"),
])
def test_classify_phase(velocity, sg, hours, expected):
    assert ferm.classify_phase(velocity, sg, 1.065, 1.012, hours) == expected


def test_eta_days_to_fg():
    assert ferm.eta_days_to_fg(1.018, 1.012, -2.0) == 3.0
    assert ferm.eta_days_to_fg(1.012, 1.012, -2.0) == 0.0
    assert ferm.eta_days_to_fg(1.018, 1.012, -0.1) is None
    assert ferm.eta_days_to_fg(None, 1.012, -2.0) is None


def test_attenuation_and_abv():
    assert ferm.attenuation_pct(1.065, 1.015) == pytest.approx(76.9, abs=0.1)
    assert ferm.abv_pct(1.065, 1.015) == pytest.approx(6.56, abs=0.01)
    assert ferm.attenuation_pct(1.0, 1.0) == 0.0


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

STEPS = [
    {"name": "Primary", "type": "Primary", "temp": 19.0, "days": 4},
    {"name": "Secondary", "type": "Secondary", "temp": 22.0, "days": 4},
    {"name": "Soft Crash", "type": "Cold Crash", "temp": 10.0, "days": 2},
    {"name": "Cold Crash", "type": "Cold Crash", "temp": 2.0, "days": 3},
]
START = datetime(2026, 8, 15, tzinfo=timezone.utc)


def test_build_schedule_locates_current_step():
    s = ferm.build_schedule(STEPS, START, START + timedelta(days=5, hours=12))
    assert s["current_index"] == 1
    assert s["current"]["name"] == "Secondary"
    assert s["next"]["name"] == "Soft Crash"
    assert s["days_to_next"] == 2.5
    assert s["days_to_crash"] == 2.5
    assert s["days_to_end"] == 7.5


def test_build_schedule_before_and_after():
    assert ferm.build_schedule(STEPS, START, START - timedelta(days=1))["current_index"] == -1
    done = ferm.build_schedule(STEPS, START, START + timedelta(days=20))
    assert done["current_index"] == 4
    assert done["current"] is None and done["next"] is None
    assert done["days_to_end"] == 0.0


def test_build_schedule_without_steps():
    assert ferm.build_schedule([], START, NOW) is None
    assert ferm.build_schedule(STEPS, None, NOW) is None


def test_target_temp_at():
    s = ferm.build_schedule(STEPS, START, NOW)
    assert ferm.target_temp_at(s, START + timedelta(days=1)) == 19.0
    assert ferm.target_temp_at(s, START + timedelta(days=9)) == 10.0
    assert ferm.target_temp_at(s, START + timedelta(days=30)) is None


def test_add_velocity_series():
    t0 = START.timestamp()
    series = [{"ts": t0 + h * 3600, "sg": 1.050 - 0.0005 * h} for h in range(0, 25, 3)]
    ferm.add_velocity_series(series, window_h=12)
    assert series[0]["velocity"] is None
    assert series[-1]["velocity"] == pytest.approx(-12.0)


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------

def test_journal_add_list_and_dedupe():
    first = journal.add_entry("⚠️ *TEMP HIGH*\nCurrent: *24.1°C*", kind="alert", level="warning")
    assert first["text"] == "⚠️ TEMP HIGH Current: 24.1°C"
    assert journal.add_entry("⚠️ *TEMP HIGH*\nCurrent: *24.1°C*", kind="alert") is None
    journal.add_entry("dry hops in", kind="note", dedupe_minutes=0)
    entries = journal.list_entries()
    assert [e["kind"] for e in entries] == ["note", "alert"]


def test_journal_caps_entries():
    for i in range(journal.MAX_ENTRIES + 5):
        journal.add_entry(f"entry {i}", dedupe_minutes=0)
    assert len(journal.list_entries(1000)) == journal.MAX_ENTRIES
    assert journal.list_entries(1)[0]["text"] == f"entry {journal.MAX_ENTRIES + 4}"


def test_journal_state_roundtrip():
    journal.set_state("tracker", {"step": 2})
    assert journal.get_state("tracker") == {"step": 2}
    assert journal.get_state("missing") is None


def test_level_for_message():
    assert journal.level_for_message("⚠️ STALL DETECTED") == "critical"
    assert journal.level_for_message("🔥 TEMP HIGH") == "warning"
    assert journal.level_for_message("Daily report") == "info"


def test_send_telegram_message_journals_even_when_quiet(monkeypatch):
    from services import notifications
    monkeypatch.setattr(notifications, "is_quiet_hours", lambda: True)
    result = notifications.send_telegram_message("🔥 *TEMP HIGH*", category="alert")
    assert result["reason"] == "quiet_hours"
    assert journal.list_entries()[0]["text"] == "🔥 TEMP HIGH"


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------

def _summary(now, phase="ACTIVE", sg=1.030, velocity=-5.0):
    return {
        "batch_name": "Hazy Daisy", "start": START.isoformat(), "phase": phase,
        "sg": sg, "velocity": velocity, "attenuation": 50.0,
        "schedule": ferm.build_schedule(STEPS, START, now),
    }


def _run(now, cfg=None, **kw):
    cfg = {"brew_active": True, **(cfg or {})}
    with patch("core.config.get_config", side_effect=lambda k: cfg.get(k)), \
         patch.object(ferm, "get_fermentation_summary", return_value=_summary(now, **kw)):
        return ferm.track_progress(now)


def test_tracker_idle_when_brew_inactive():
    assert _run(START + timedelta(days=1), cfg={"brew_active": False}) == []


def test_tracker_logs_step_change_and_upcoming_step():
    assert _run(START + timedelta(days=2)) == []  # baseline, pending ACTIVE
    logged = _run(START + timedelta(days=3, hours=6))
    assert "Hazy Daisy: Secondary @ 22°C in 18h" in logged
    assert any("fermentation active" in t for t in logged)
    logged = _run(START + timedelta(days=4, hours=1))
    assert logged == ["Hazy Daisy: next → Secondary @ 22°C (step 2/4)"]


def test_tracker_phase_needs_two_consecutive_reads():
    t = START + timedelta(days=5)
    _run(t, phase="ACTIVE")
    _run(t + timedelta(minutes=15), phase="ACTIVE")
    assert _run(t + timedelta(minutes=30), phase="SLOWING", velocity=-1.0) == []
    assert _run(t + timedelta(minutes=45), phase="ACTIVE") == []  # flap back: nothing
    _run(t + timedelta(hours=1), phase="STABLE", sg=1.013, velocity=-0.2)
    logged = _run(t + timedelta(hours=1, minutes=15), phase="STABLE", sg=1.013, velocity=-0.2)
    assert logged and "gravity stable at 1.0130" in logged[0]
