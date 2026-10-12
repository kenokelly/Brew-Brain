"""Drive ops/recovery/brew-brain-recovery.sh with stub commands.

Each test simulates minutes of an outage by running the script once per
"minute" with a fake clock, and checks which recovery steps fire.
"""

import os
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "ops" / "recovery" / "brew-brain-recovery.sh"

STUB = """#!/usr/bin/env bash
echo "{name} $*" >> "{calls}"
{body}
"""


@pytest.fixture
def env(tmp_path):
    calls = tmp_path / "calls.log"
    calls.touch()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    flags = tmp_path / "flags"
    flags.mkdir()

    def stub(name, body="exit 0"):
        p = bin_dir / name
        p.write_text(STUB.format(name=name, calls=calls, body=body))
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
        return str(p)

    e = dict(os.environ)
    e.update({
        "RECOVERY_STATE_DIR": str(tmp_path / "state"),
        # ping/curl succeed unless a flag file says the thing is down
        "RECOVERY_PING": stub("ping", f'[ -f "{flags}/net_down" ] && exit 1; exit 0'),
        "RECOVERY_CURL": stub("curl", f'for a in "$@"; do case "$a" in *1880*) cat "{flags}/tilt.json" 2>/dev/null || echo "[]"; exit 0;; *3001*) [ -f "{flags}/web_down" ] && exit 7;; *5000*) [ -f "{flags}/api_down" ] && exit 7;; esac; done; exit 0'),
        "RECOVERY_NMCLI": stub("nmcli"),
        "RECOVERY_SYSTEMCTL": stub("systemctl"),
        "RECOVERY_DOCKER": stub("docker"),
        "RECOVERY_LOGGER": stub("logger"),
        "RECOVERY_IP": stub("ip", 'echo "default via 192.168.155.1 dev wlan0"'),
        "RECOVERY_RADIO_PAUSE": "0",
        # 6h in production; 1h here keeps the multi-hour simulations quick
        "RECOVERY_REBOOT_WINDOW_S": "3600",
    })

    class Env:
        def run(self, minute):
            e["RECOVERY_NOW"] = str(1_800_000_000 + minute * 60)
            r = subprocess.run(["bash", str(SCRIPT)], env=e, capture_output=True, text=True)
            assert r.returncode == 0, r.stderr

        def down(self, what):
            (flags / what).touch()

        def up(self, what):
            (flags / what).unlink(missing_ok=True)

        def reports(self):
            # The Telegram message spans lines in the log; count by marker
            return calls.read_text().count("docker exec -e MSG=")

        def tilt_seen(self, minute):
            """Receiver last heard the Tilt at `minute` (None = heard nothing)."""
            f = flags / "tilt.json"
            if minute is None:
                f.write_text("[]")
            else:
                ts = (1_800_000_000 + minute * 60) * 1000
                f.write_text(f'[{{"Color": "RED", "SG": 1.0, "timeStamp": {ts}}}]')

        def calls(self, prefix):
            return [l for l in calls.read_text().splitlines() if l.startswith(prefix)]

        def clear(self):
            calls.write_text("")

    return Env()


def test_healthy_does_nothing(env):
    for m in range(5):
        env.run(m)
    assert env.calls("nmcli") == [] and env.calls("systemctl") == [] and env.calls("docker") == []


def test_network_escalation_ladder(env):
    env.down("net_down")
    for m in range(1, 16):
        env.run(m)
    nm = env.calls("nmcli")
    assert "nmcli device disconnect wlan0" in nm and "nmcli device connect wlan0" in nm   # min 3
    assert "nmcli radio wifi off" in nm and "nmcli radio wifi on" in nm                   # min 6
    sc = env.calls("systemctl")
    assert "systemctl restart NetworkManager" in sc                                     # min 10
    assert "systemctl reboot" in sc                                                     # min 15
    # Each step fires once, not every minute
    assert nm.count("nmcli radio wifi off") == 1
    assert sc.count("systemctl restart NetworkManager") == 1


def test_brief_blip_triggers_nothing(env):
    env.down("net_down")
    env.run(1)
    env.run(2)
    env.up("net_down")
    env.run(3)
    assert env.calls("nmcli") == [] and env.calls("systemctl") == []


def test_reboot_limit_prevents_reboot_loop(env):
    """Router/ISP down for the whole window: at most 3 reboots."""
    env.down("net_down")
    for m in range(1, 60):
        env.run(m)
    assert env.calls("systemctl").count("systemctl reboot") == 3


def test_reboot_budget_recovers_after_window(env):
    env.down("net_down")
    for m in range(1, 60):
        env.run(m)
    env.clear()
    for m in range(125, 141):  # well past the window
        env.run(m)
    assert "systemctl reboot" in env.calls("systemctl")


def test_app_restarted_after_three_failed_checks(env):
    env.down("api_down")
    env.run(1)
    env.run(2)
    assert env.calls("docker") == []
    env.run(3)
    assert "docker restart brew-brain" in env.calls("docker")


def test_app_restart_rate_limited(env):
    env.down("web_down")
    for m in range(1, 40):
        env.run(m)
    assert env.calls("docker").count("docker restart brew-brain-web") == 3


def test_containers_not_restarted_during_network_outage(env):
    env.down("net_down")
    env.down("api_down")
    for m in range(1, 8):
        env.run(m)
    assert not any("restart" in c for c in env.calls("docker"))


def test_report_sent_once_after_recovery(env):
    env.down("net_down")
    for m in range(1, 5):
        env.run(m)
    env.up("net_down")
    env.run(5)
    assert env.reports() == 1
    env.run(6)
    assert env.reports() == 1


def test_report_waits_for_api(env):
    env.down("net_down")
    for m in range(1, 5):
        env.run(m)
    env.up("net_down")
    env.down("api_down")
    env.run(5)
    assert env.reports() == 0
    env.up("api_down")
    env.run(6)
    assert env.reports() == 1


# ---------------------------------------------------------------------------
# Tilt receiver
# ---------------------------------------------------------------------------

def test_tilt_heard_recently_does_nothing(env):
    for m in range(1, 30):
        env.tilt_seen(m)
        env.run(m)
    assert not [c for c in env.calls("systemctl") if "nodered" in c or "bluetooth" in c]


def test_no_tilt_ever_heard_does_nothing(env):
    """Between batches: nothing to recover."""
    env.tilt_seen(None)
    for m in range(1, 60):
        env.run(m)
    assert env.calls("systemctl") == []


def test_tilt_silent_escalates_then_gives_up(env):
    env.tilt_seen(0)                         # last heard at minute 0
    for m in range(1, 15):
        env.run(m)
    assert env.calls("systemctl") == []      # under 15 min: wait
    env.run(15)
    assert env.calls("systemctl") == ["systemctl restart nodered"]
    env.tilt_seen(None)                      # restarted receiver hears nothing
    for m in range(16, 30):
        env.run(m)
    assert len(env.calls("systemctl")) == 1  # waits 15 min after a restart
    env.run(30)
    assert env.calls("systemctl")[1:] == ["systemctl restart bluetooth", "systemctl restart nodered"]
    for m in range(31, 120):
        env.run(m)
    sc = env.calls("systemctl")
    assert sc.count("systemctl restart nodered") == 3   # capped
    assert sc.count("systemctl restart bluetooth") == 2
    assert env.reports() == 1                           # one message, at give-up


def test_tilt_back_resets_and_reports(env):
    env.tilt_seen(0)
    for m in range(1, 16):
        env.run(m)                           # restart at 15
    env.tilt_seen(17)
    env.run(18)
    assert env.reports() == 1
    env.tilt_seen(18)
    env.clear()
    for m in range(19, 30):
        env.tilt_seen(m)
        env.run(m)
    assert env.calls("systemctl") == []
