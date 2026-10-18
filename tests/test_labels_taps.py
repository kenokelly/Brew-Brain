"""Keg label page and kiosk tap QR links."""

from unittest.mock import patch

from flask import Flask

CONFIG = {"batch_name": "PGBM <Hazy>", "og": 1.042, "target_fg": 1.008,
          "start_date": "2026-10-18", "yeast_strain": "US-05", "taps": {}}


def _client(bp, prefix=""):
    app = Flask(__name__)
    app.register_blueprint(bp, url_prefix=prefix or None)
    return app.test_client()


def test_label_renders_batch_with_escaped_name():
    from api.labels import labels_bp
    with patch("api.labels.get_config", side_effect=CONFIG.get), \
         patch("services.status.get_status_dict", return_value={"sg": 1.010}):
        res = _client(labels_bp, "/api/label").get("/api/label")
    body = res.get_data(as_text=True)
    assert res.status_code == 200
    assert "PGBM &lt;Hazy&gt;" in body
    assert "ABV: 4.2%" in body and "FG: 1.010" in body
    assert "US-05" in body


def test_tap_qr_links_keep_the_browser_port():
    from api.taps import taps_bp
    with patch("services.taps.get_tap_list", return_value=[]) as tap_list:
        _client(taps_bp, "/api").get("/api/taps", headers={"X-Forwarded-Host": "192.168.155.24:3001"})
    assert tap_list.call_args[0][0] == "http://192.168.155.24:3001"
