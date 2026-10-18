"""Brewmaster chat runs as a background job; advice is cached."""

from unittest.mock import MagicMock, patch

import services.ai as ai


def test_advice_served_from_cache_without_calling_ollama():
    cached = {"status": "success", "advice": "Raise to 20C for a diacetyl rest.", "source": "ollama"}
    with patch.object(ai.cache, "get", return_value=cached), patch("services.ai.requests.post") as post:
        assert ai.get_proactive_advice() == cached
    post.assert_not_called()


def test_advice_single_flight_returns_pending_when_locked():
    redis = MagicMock()
    redis.set.return_value = False  # another request holds the lock
    with patch.object(ai.cache, "get", return_value=None), \
         patch.object(ai.cache, "redis_client", redis), \
         patch("services.ai.requests.post") as post:
        result = ai.get_proactive_advice()
    assert result["source"] == "pending"
    post.assert_not_called()


def _client():
    from flask import Flask
    from api.ai import ai_bp
    app = Flask(__name__)
    app.register_blueprint(ai_bp, url_prefix="/api/ai")
    return app.test_client()


def test_chat_enqueues_and_trims_history():
    task = MagicMock(id="abc123")
    with patch("services.tasks.run_chat_task.delay", return_value=task) as delay:
        res = _client().post("/api/ai/chat", json={"message": "What's brewing?", "history": [{"role": "user", "content": str(i)} for i in range(25)]})
    assert res.status_code == 202
    assert res.get_json()["data"] == {"status": "queued", "task_id": "abc123"}
    msg, history = delay.call_args.args
    assert msg == "What's brewing?" and len(history) == 10


def test_chat_rejects_empty_and_oversized():
    c = _client()
    assert c.post("/api/ai/chat", json={}).status_code == 400
    assert c.post("/api/ai/chat", json={"message": "x" * 2001}).status_code == 400


def test_chat_status_states():
    c = _client()
    for state, expected in [("PENDING", "queued"), ("STARTED", "thinking")]:
        with patch("celery.result.AsyncResult", return_value=MagicMock(state=state)):
            assert c.get("/api/ai/chat/status/t1").get_json()["data"]["status"] == expected
    done = MagicMock(state="SUCCESS")
    done.get.return_value = {"status": "success", "response": "Looks healthy."}
    with patch("celery.result.AsyncResult", return_value=done):
        assert c.get("/api/ai/chat/status/t1").get_json()["data"]["response"] == "Looks healthy."


# ---------------------------------------------------------------------------
# Batch context given to the AI
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta, timezone


def _summary(**over):
    now = datetime.now(timezone.utc)
    steps = [
        {"name": "Primary", "type": "Primary", "temp": 19.0, "days": 4,
         "start": (now - timedelta(days=5)).isoformat(), "end": (now - timedelta(days=1)).isoformat()},
        {"name": "Secondary", "type": "Secondary", "temp": 22.0, "days": 2,
         "start": (now - timedelta(days=1)).isoformat(), "end": (now + timedelta(days=1)).isoformat()},
        {"name": "Cold Crash", "type": "Cold Crash", "temp": 2.0, "days": 2,
         "start": (now + timedelta(days=1)).isoformat(), "end": (now + timedelta(days=3)).isoformat()},
    ]
    s = {
        "batch_name": "Hazy Daisy", "style": "NEIPA", "yeast": "Verdant IPA", "brew_active": True, "test_mode": False,
        "og": 1.065, "target_fg": 1.012, "sg": 1.01523, "temp": 22.22222222222222, "temp_unit": "C",
        "target_temp": 22.0, "temp_delta": 0.2, "velocity": -0.8, "phase": "SLOWING",
        "attenuation": 76.6, "abv": 6.534, "eta_days": 4.0, "day": 6,
        "schedule": {"steps": steps, "current_index": 1, "current": steps[1], "next": steps[2], "days_to_next": 1.0},
        "sensor": {"rssi": -60, "last_reading_age_min": 2.0},
    }
    s.update(over)
    return s


def _context(summary, journal=()):
    with patch("services.fermentation.get_fermentation_summary", return_value=summary), \
         patch("services.journal.list_entries", return_value=list(journal)):
        return ai.build_batch_context()


def test_batch_context_is_rounded_and_complete():
    now = datetime.now(timezone.utc)
    ctx = _context(_summary(), [{"ts": (now - timedelta(hours=3)).isoformat(), "kind": "note", "text": "Dry hops in"}])
    assert "22.22222" not in ctx                      # no raw floats
    assert "Beer temperature 22.2°C (target 22.0°C, +0.2°C off)" in ctx
    assert "Current gravity 1.015 (77% attenuation, about 6.5% ABV so far)" in ctx
    assert "Gravity falling 0.8 points/day" in ctx
    assert "Recipe step 2 of 3: Secondary at 22°C" in ctx
    assert "Next step: Cold Crash at 2°C in 1.0 days" in ctx
    assert "Day 6 since pitch" in ctx and "Verdant IPA" in ctx
    assert "3 h ago: Dry hops in" in ctx


def test_batch_context_flags_implausible_and_stale_data():
    ctx = _context(_summary(velocity=5.6, sensor={"rssi": None, "last_reading_age_min": 300}, brew_active=False))
    assert "RISING 5.6 points/day" in ctx
    assert "no hydrometer reading in the last hour" in ctx
    assert "Brew Active is off" in ctx


def test_chat_prompt_carries_batch_context():
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"response": "Looks healthy."}
    with patch.object(ai, "build_batch_context", return_value="Batch: Hazy Daisy\nCurrent gravity 1.015"), \
         patch("services.ai.requests.post", return_value=resp) as post:
        out = ai.generate_chat_response("How's it going?")
    assert out["status"] == "success"
    system = post.call_args.kwargs["json"]["system"]
    assert "Current gravity 1.015" in system and "Don't invent" in system


def test_chat_fallback_includes_batch_summary_when_ollama_down():
    with patch.object(ai, "build_batch_context", return_value="Current gravity 1.015"), \
         patch("services.ai.requests.post", side_effect=ConnectionError("down")):
        out = ai.generate_chat_response("Hi")
    assert out["status"] == "fallback" and "Current gravity 1.015" in out["response"]


def test_batch_context_collapses_repeated_journal_alerts():
    now = datetime.now(timezone.utc).isoformat()
    repeats = [{"ts": now, "kind": "alert", "text": f"📊 STATISTICAL ANOMALY: DEV Z-Score: {40 + i}"} for i in range(6)]
    other = [{"ts": now, "kind": "note", "text": "Tilt moved to the fermenter"}]
    ctx = _context(_summary(), repeats + other)
    assert ctx.count("STATISTICAL ANOMALY") == 1
    assert "Tilt moved to the fermenter" in ctx


def _cfg(**values):
    return lambda key: values.get(key)


def test_advice_is_fixed_text_when_data_is_simulated_or_water_test():
    with patch.object(ai, "get_config", side_effect=_cfg(test_mode=True)), \
         patch("services.ai.requests.post") as post:
        assert "Simulated data is on" in ai.get_proactive_advice()["advice"]
    with patch.object(ai, "get_config", side_effect=_cfg(water_test=True)), \
         patch("services.ai.requests.post") as post:
        assert "Water test running" in ai.get_proactive_advice(refresh=True)["advice"]
    post.assert_not_called()


def test_refresh_skips_the_cache():
    cached = {"status": "success", "advice": "old", "source": "ollama"}
    fresh = {"status": "success", "advice": "new", "source": "ollama"}
    with patch.object(ai, "get_config", side_effect=_cfg()), \
         patch.object(ai.cache, "get", return_value=cached), \
         patch.object(ai.cache, "set"), \
         patch.object(ai.cache, "redis_client", None), \
         patch.object(ai, "_generate_proactive_advice", return_value=dict(fresh)):
        assert ai.get_proactive_advice()["advice"] == "old"
        assert ai.get_proactive_advice(refresh=True)["advice"] == "new"


def test_batch_plan_takes_the_fermentation_part_of_the_notes():
    notes = ("Targets: OG 1.042. Water: all RO. Fermentation: 20 C to 1.020 or lower; "
             "25 C diacetyl rest with Galaxy dry hop; 0 C, carbonate to 2.6 vols.")
    with patch.object(ai, "get_config", side_effect=_cfg(batch_notes=notes)):
        plan = ai._batch_plan()
    assert plan.startswith("20 C to 1.020")
    assert "25 C diacetyl rest" in plan and "Targets" not in plan


def test_plain_text_drops_markdown_but_keeps_bold():
    assert ai._plain_text("## Now\n- **Hold** at *20 C*") == "Now\n**Hold** at 20 C"


def test_batch_context_skips_events_before_log_start():
    from datetime import datetime, timezone
    from unittest.mock import patch
    from services import ai
    summary = {"og": 1.042, "target_fg": 1.008, "sg": 1.035, "brew_active": True,
               "sensor": {"last_reading_age_min": 2}}
    entries = [
        {"ts": "2026-10-18T19:00:00+00:00", "text": "Log restarted"},
        {"ts": "2026-10-18T12:00:00+00:00", "text": "TILT SIGNAL LOSS: IPA no 1"},
    ]
    with patch("services.fermentation.get_fermentation_summary", return_value=summary), \
         patch("services.fermentation._log_start", return_value=datetime(2026, 10, 18, 15, tzinfo=timezone.utc)), \
         patch("services.journal.list_entries", return_value=entries):
        ctx = ai.build_batch_context()
    assert "Log restarted" in ctx
    assert "SIGNAL LOSS" not in ctx


def test_chat_prompt_explains_the_app():
    from unittest.mock import patch, MagicMock
    from services import ai
    res = MagicMock(status_code=200)
    res.json.return_value = {"response": "ok"}
    with patch.object(ai, "build_batch_context", return_value="Batch: X"), \
         patch.object(ai, "_llm_post", return_value=res) as post:
        ai.generate_chat_response("how do I turn brew active on")
    system = post.call_args[0][1]["system"]
    assert "Brew Alerts slider" in system
    assert "Proactive Advice" in system
