"""Water test mode: calibration maths, alert gating and the API."""

from unittest.mock import MagicMock, patch

import pytest

from services import fermentation as ferm


# ---------------------------------------------------------------------------
# Calibration maths
# ---------------------------------------------------------------------------

def test_waiting_until_enough_readings():
    assert ferm.water_test_calibration([0.993] * 5, 0.0)["status"] == "waiting"


def test_ready_suggests_offset_to_read_1000():
    cal = ferm.water_test_calibration([0.993, 0.994, 0.993] * 10, 0.0)
    assert cal["status"] == "ready"
    assert cal["suggested_offset"] == pytest.approx(0.007, abs=0.0005)
    assert cal["settled"] is True


def test_already_calibrated():
    cal = ferm.water_test_calibration([0.993] * 30, 0.007)
    assert cal["status"] == "calibrated"
    assert cal["calibrated_mean"] == pytest.approx(1.000)


def test_implausible_offset_is_refused():
    """1.040 in water (2026-10-11) is a tilted Tilt, not a calibration error."""
    cal = ferm.water_test_calibration([1.040] * 30, 0.0)
    assert cal["status"] == "implausible"
    assert "floating freely" in cal["message"]


def test_still_settling():
    cal = ferm.water_test_calibration([0.990, 0.996] * 15, 0.0)
    assert cal["status"] == "settling"


# ---------------------------------------------------------------------------
# Alert gating
# ---------------------------------------------------------------------------

def test_anomaly_checks_only_tilt_health_in_water_test():
    from services import anomaly
    cfg = {"water_test": True, "brew_active": False}
    with patch.object(anomaly, "get_config", side_effect=lambda k: cfg.get(k)), \
         patch.object(anomaly, "check_signal_loss", return_value={"status": "normal"}) as sig, \
         patch.object(anomaly, "check_frozen_reading", return_value={"status": "normal"}) as frozen, \
         patch.object(anomaly, "check_stalled_fermentation") as stall, \
         patch.object(anomaly, "check_temperature_deviation") as temp, \
         patch.object(anomaly, "calculate_anomaly_score") as stat:
        res = anomaly.run_all_anomaly_checks("DEV")
    sig.assert_called_once()
    frozen.assert_called_once()
    stall.assert_not_called()
    temp.assert_not_called()
    stat.assert_not_called()
    assert res["status"] == "water_test"


def test_worker_pipeline_skipped_in_water_test():
    from services import worker
    cfg = {"water_test": True, "brew_active": True, "test_mode": False}
    with patch.object(worker, "get_config", side_effect=lambda k: cfg.get(k)), \
         patch.object(worker, "is_quiet_hours", return_value=False), \
         patch.object(worker, "query_api") as q:
        worker.check_alerts_once()
    q.query.assert_not_called()


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    from flask import Flask
    from api.fermentation import fermentation_bp
    from core import auth
    app = Flask(__name__)
    app.register_blueprint(fermentation_bp, url_prefix="/api/fermentation")
    c = app.test_client()
    c.headers = {"Authorization": f"Bearer {auth.API_TOKEN}"}
    return c


def _post(client, action):
    return client.post("/api/fermentation/water-test", json={"action": action}, headers=client.headers)


def test_start_stop_journal_and_config(client):
    cfg = {}
    with patch("core.config.set_config", side_effect=lambda k, v: cfg.__setitem__(k, v)):
        assert _post(client, "start").status_code == 200
        assert cfg["water_test"] is True
        assert _post(client, "stop").status_code == 200
        assert cfg["water_test"] is False
    from services.journal import list_entries
    texts = [e["text"] for e in list_entries()]
    assert any("Water test started" in t for t in texts)
    assert any("Water test ended" in t for t in texts)


def test_apply_offset_only_when_ready(client):
    cfg = {"water_test": True, "offset": 0.0}
    with patch("core.config.get_config", side_effect=lambda k: cfg.get(k)), \
         patch("core.config.set_config", side_effect=lambda k, v: cfg.__setitem__(k, v)), \
         patch("services.fermentation.get_water_test_calibration",
               return_value=ferm.water_test_calibration([1.040] * 30, 0.0)):
        res = _post(client, "apply_offset")
    assert res.status_code == 409 and cfg["offset"] == 0.0     # implausible: refused

    with patch("core.config.get_config", side_effect=lambda k: cfg.get(k)), \
         patch("core.config.set_config", side_effect=lambda k, v: cfg.__setitem__(k, v)), \
         patch("services.fermentation.get_water_test_calibration",
               return_value=ferm.water_test_calibration([0.993] * 30, 0.0)):
        res = _post(client, "apply_offset")
    assert res.status_code == 200
    assert cfg["offset"] == pytest.approx(0.007)


def test_apply_offset_requires_water_test(client):
    with patch("core.config.get_config", side_effect=lambda k: {"water_test": False}.get(k)):
        assert _post(client, "apply_offset").status_code == 409


def test_unknown_action(client):
    assert _post(client, "bogus").status_code == 400
