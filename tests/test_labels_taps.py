"""Keg label page and kiosk tap QR links."""

from unittest.mock import patch

from flask import Flask

INFO = {"recipe_name": "PGBM Hazy Pale 23L", "batch_no": 44, "brewer": "Ken", "abv": 4.5, "ibu": 14.2,
        "srm": 2.6, "hops": ["Magnum", "Galaxy"], "dry_hops": ["Galaxy"],
        "malts": ["Pilsner Malt", "Flaked Wheat"], "carbonation": 2.6}
CONFIG = {"batch_name": "Batch", "og": 1.042, "target_fg": 1.008, "style": "Hazy IPA",
          "start_date": "2026-10-18", "yeast_strain": "Safale US-05", "taps": {}, "label_info": INFO}


def _client(bp, prefix=""):
    app = Flask(__name__)
    app.register_blueprint(bp, url_prefix=prefix or None)
    return app.test_client()


def _label(sg, cfg=CONFIG, query=""):
    from api.labels import labels_bp
    with patch("api.labels.get_config", side_effect=cfg.get), \
         patch("services.status.get_status_dict", return_value={"sg": sg}):
        res = _client(labels_bp, "/api/label").get("/api/label" + query)
    assert res.status_code == 200
    return res.get_data(as_text=True)


def test_label_uses_recipe_name_when_batch_is_generic():
    body = _label(1.036)
    assert "<h1>PGBM Hazy Pale</h1>" in body
    assert "Batch #44" in body and "Galaxy (dry hop)" in body and "Safale US-05" in body


def test_label_shows_target_abv_mid_ferment_and_measured_when_done():
    assert ">4.5<" in _label(1.036) and ">target<" in _label(1.036)
    done = _label(1.009)
    assert ">4.3<" in done and ">target<" not in done


def test_label_escapes_and_accepts_overrides():
    body = _label(1.036, query="?name=%3Cb%3EGold%3C/b%3E")
    assert "&lt;b&gt;Gold&lt;/b&gt;" in body


def test_display_name():
    from services.labels import display_name
    assert display_name("Batch", "PGBM Hazy Pale 23L") == "PGBM Hazy Pale"
    assert display_name("Batch 44", "Black IPA 20 L") == "Black IPA"
    assert display_name("Christmas Stout", "Stout 23L") == "Christmas Stout"


def test_tap_qr_links_keep_the_browser_port():
    from api.taps import taps_bp
    with patch("services.taps.get_tap_list", return_value=[]) as tap_list:
        _client(taps_bp, "/api").get("/api/taps", headers={"X-Forwarded-Host": "192.168.155.24:3001"})
    assert tap_list.call_args[0][0] == "http://192.168.155.24:3001"
