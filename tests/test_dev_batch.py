"""Dev batch tool: start snapshots the real batch once, restore puts it back."""

from unittest.mock import patch

from core import config as cfg
from tools import dev_batch


def test_start_and_restore_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_PATH", str(tmp_path / "config.json"))
    monkeypatch.setattr(cfg, "_config_instance", cfg.BrewBrainConfig(batch_name="IPA no 1", og=1.062, brew_active=False))
    monkeypatch.setattr(dev_batch, "SNAPSHOT", str(tmp_path / "snap.json"))

    with patch.object(cfg, "write_api"):
        dev_batch.start()
        assert cfg.get_config("batch_name") == "DEV · Water test"
        assert cfg.get_config("brew_active") is True
        assert len(cfg.get_config("ferm_steps")) == 4

        dev_batch.start()  # reset clock must not overwrite the real snapshot
        dev_batch.restore()

    assert cfg.get_config("batch_name") == "IPA no 1"
    assert cfg.get_config("og") == 1.062
    assert cfg.get_config("brew_active") is False
    assert cfg.get_config("ferm_steps") == []
    assert not (tmp_path / "snap.json").exists()
