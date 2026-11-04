#!/usr/bin/env bash
#
# Brew Brain self-recovery watchdog. Runs every minute (systemd timer).
#
# Network: if the Pi can't reach its gateway, escalate one step at a time
# rather than jumping straight to a reboot:
#     3 min  -> reconnect the Wi-Fi connection
#     6 min  -> toggle the Wi-Fi radio off/on
#    10 min  -> restart NetworkManager
#    15 min  -> reboot (at most MAX_REBOOTS per REBOOT_WINDOW_S, so a
#               router/ISP outage can't put the Pi in a reboot loop)
#
# App: if the Brew Brain API or web container stops answering for
# APP_FAIL_LIMIT consecutive checks, restart that container.
#
# Tilt receiver: if Node-RED stops hearing a Tilt it had been hearing,
# restart Node-RED, then Bluetooth + Node-RED (max 3 tries, 15 min apart).
#
# Afterwards: once the network and API are healthy again, send one Telegram
# message (via the app's own notifier, so it also lands in the autopilot
# journal) describing what happened and what fixed it.
#
# Every action is logged with tag "brew-brain-recovery":
#     journalctl -t brew-brain-recovery
#
# Hardware/kernel hangs are covered separately by the systemd hardware
# watchdog (see watchdog.conf), which this script can't help with.
#
# All external commands go through overridable variables so the test suite
# can drive the escalation ladder with stubs.

set -u

STATE_DIR="${RECOVERY_STATE_DIR:-/var/lib/brew-brain-recovery}"
NOW="${RECOVERY_NOW:-$(date +%s)}"

PING="${RECOVERY_PING:-ping}"
NMCLI="${RECOVERY_NMCLI:-nmcli}"
SYSTEMCTL="${RECOVERY_SYSTEMCTL:-systemctl}"
DOCKER="${RECOVERY_DOCKER:-docker}"
CURL="${RECOVERY_CURL:-curl}"
LOGGER="${RECOVERY_LOGGER:-logger}"
IP="${RECOVERY_IP:-ip}"

WIFI_IFACE="${RECOVERY_WIFI_IFACE:-wlan0}"
FALLBACK_GATEWAY="${RECOVERY_FALLBACK_GATEWAY:-192.168.155.1}"

STEP_RECONNECT=3
STEP_RADIO=6
STEP_NM_RESTART=10
STEP_REBOOT=15
MAX_REBOOTS=3
REBOOT_WINDOW_S="${RECOVERY_REBOOT_WINDOW_S:-$((6 * 3600))}"
APP_FAIL_LIMIT=3
TILT_STALE_S=$((15 * 60))       # receiver hasn't heard the Tilt for this long
TILT_MAX_RESTARTS=3             # then it's the Tilt itself (battery/range)
PYTHON="${RECOVERY_PYTHON:-python3}"
MAX_APP_RESTARTS_PER_HOUR=3

mkdir -p "$STATE_DIR"

log() { "$LOGGER" -t brew-brain-recovery -- "$*"; }

read_state() { cat "$STATE_DIR/$1" 2>/dev/null || echo "${2:-0}"; }
write_state() { echo "$2" > "$STATE_DIR/$1"; }
append_event() { echo "$1" >> "$STATE_DIR/events"; }

gateway() {
    local gw
    gw=$("$IP" route 2>/dev/null | awk '/^default/ {print $3; exit}')
    echo "${gw:-$FALLBACK_GATEWAY}"
}

network_ok() {
    "$PING" -c 2 -W 3 "$(gateway)" >/dev/null 2>&1 && return 0
    # Gateways that ignore ICMP: fall back to a public resolver
    "$PING" -c 2 -W 3 1.1.1.1 >/dev/null 2>&1
}

# Reboots within the window, oldest first, pruned as they age out
recent_reboots() {
    local f="$STATE_DIR/reboots" cutoff=$((NOW - REBOOT_WINDOW_S))
    [ -f "$f" ] || { echo 0; return; }
    awk -v c="$cutoff" '$1 >= c' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
    wc -l < "$f" | tr -d ' '
}

# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------
check_network() {
    local fails
    fails=$(read_state net_fails 0)

    if network_ok; then
        if [ "$fails" -gt 0 ]; then
            local since
            since=$(read_state net_down_since "$NOW")
            append_event "Network restored after $(( (NOW - since + 59) / 60 )) min"
            log "network restored after ${fails} failed check(s)"
            write_state report_pending 1
        fi
        write_state net_fails 0
        rm -f "$STATE_DIR/net_down_since"
        return
    fi

    fails=$((fails + 1))
    write_state net_fails "$fails"
    [ "$fails" -eq 1 ] && write_state net_down_since "$NOW"
    log "gateway unreachable (check $fails)"

    case "$fails" in
        "$STEP_RECONNECT")
            log "step 1: reconnecting $WIFI_IFACE"
            append_event "Wi-Fi lost; reconnected $WIFI_IFACE"
            "$NMCLI" device disconnect "$WIFI_IFACE" >/dev/null 2>&1
            "$NMCLI" device connect "$WIFI_IFACE" >/dev/null 2>&1
            ;;
        "$STEP_RADIO")
            log "step 2: toggling Wi-Fi radio"
            append_event "Wi-Fi radio toggled off/on"
            "$NMCLI" radio wifi off >/dev/null 2>&1
            sleep "${RECOVERY_RADIO_PAUSE:-5}"
            "$NMCLI" radio wifi on >/dev/null 2>&1
            ;;
        "$STEP_NM_RESTART")
            log "step 3: restarting NetworkManager"
            append_event "NetworkManager restarted"
            "$SYSTEMCTL" restart NetworkManager >/dev/null 2>&1
            ;;
    esac

    if [ "$fails" -ge "$STEP_REBOOT" ]; then
        local n
        n=$(recent_reboots)
        if [ "$n" -lt "$MAX_REBOOTS" ]; then
            log "step 4: rebooting (network down $fails min; reboot $((n + 1))/$MAX_REBOOTS in window)"
            append_event "Rebooted after $fails min without network"
            echo "$NOW" >> "$STATE_DIR/reboots"
            write_state report_pending 1
            write_state net_fails 0
            sync
            "$SYSTEMCTL" reboot
        elif [ $((fails % 30)) -eq 0 ]; then
            # Reboot budget spent: likely the router/ISP, not the Pi. Keep
            # nudging the Wi-Fi every 30 min instead of rebooting.
            log "reboot limit reached; reconnecting $WIFI_IFACE instead"
            "$NMCLI" device connect "$WIFI_IFACE" >/dev/null 2>&1
        fi
    fi
}

# ---------------------------------------------------------------------------
# App containers
# ---------------------------------------------------------------------------
check_app() {
    local name="$1" url="$2" key="app_fails_$1"
    local fails
    fails=$(read_state "$key" 0)

    if "$CURL" -sf -m 10 -o /dev/null "$url"; then
        if [ "$fails" -ge "$APP_FAIL_LIMIT" ]; then
            log "$name healthy again"
        fi
        write_state "$key" 0
        return
    fi

    fails=$((fails + 1))
    write_state "$key" "$fails"
    log "$name not responding (check $fails)"
    [ "$fails" -eq "$APP_FAIL_LIMIT" ] || return

    # Rate-limit restarts so a container that can't start isn't hammered
    local f="$STATE_DIR/restarts_$name" cutoff=$((NOW - 3600)) n=0
    if [ -f "$f" ]; then
        awk -v c="$cutoff" '$1 >= c' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
        n=$(wc -l < "$f" | tr -d ' ')
    fi
    # Start a fresh count either way, so a still-dead container is retried
    # every APP_FAIL_LIMIT checks (subject to the hourly limit).
    write_state "$key" 0
    if [ "$n" -ge "$MAX_APP_RESTARTS_PER_HOUR" ]; then
        log "$name restart limit reached for this hour; leaving it"
        return
    fi
    log "restarting container $name"
    append_event "Restarted $name (not responding for $fails min)"
    echo "$NOW" >> "$f"
    write_state report_pending 1
    "$DOCKER" restart "$name" >/dev/null 2>&1
}

# ---------------------------------------------------------------------------
# Tilt receiver (TiltPi Node-RED + Bluetooth scanner)
# ---------------------------------------------------------------------------
# Newest Tilt broadcast the receiver has heard, as epoch seconds; empty if it
# has heard none since it started (e.g. right after a restart, or between
# batches with no Tilt in range).
tilt_last_seen() {
    "$CURL" -s -m 5 http://localhost:1880/macid/all 2>/dev/null | "$PYTHON" -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ts = [x.get("timeStamp") for x in (d if isinstance(d, list) else []) if isinstance(x, dict) and x.get("timeStamp")]
print(int(max(ts) / 1000) if ts else "")
' 2>/dev/null
}

check_tilt() {
    local seen restarts last_restart age
    seen=$(tilt_last_seen)
    restarts=$(read_state tilt_restarts 0)
    last_restart=$(read_state tilt_last_restart 0)

    if [ -n "$seen" ] && [ $((NOW - seen)) -lt "$TILT_STALE_S" ]; then
        if [ "$restarts" -gt 0 ]; then
            log "Tilt heard again after $restarts receiver restart(s)"
            append_event "Tilt receiver recovered after $restarts restart(s)"
            write_state report_pending 1
        fi
        write_state tilt_restarts 0
        return
    fi

    # Never heard a Tilt and haven't intervened: nothing to recover (no
    # batch, or the Tilt is off). Signal-loss alerts are the app's job.
    if [ -z "$seen" ] && [ "$restarts" -eq 0 ]; then
        return
    fi
    [ "$restarts" -ge "$TILT_MAX_RESTARTS" ] && return

    # Stale since the last broadcast, or since our last restart if the
    # receiver has heard nothing since.
    if [ -n "$seen" ] && [ "$seen" -gt "$last_restart" ]; then
        age=$((NOW - seen))
    else
        age=$((NOW - last_restart))
    fi
    [ "$age" -ge "$TILT_STALE_S" ] || return

    restarts=$((restarts + 1))
    write_state tilt_restarts "$restarts"
    write_state tilt_last_restart "$NOW"
    write_state report_pending 1
    if [ "$restarts" -eq 1 ]; then
        log "Tilt not heard for $((age / 60)) min; restarting Node-RED"
        append_event "Tilt silent $((age / 60)) min; restarted the Tilt receiver"
        "$SYSTEMCTL" restart nodered >/dev/null 2>&1
    else
        log "Tilt still not heard; restarting Bluetooth and Node-RED (attempt $restarts/$TILT_MAX_RESTARTS)"
        append_event "Tilt still silent; restarted Bluetooth + receiver (attempt $restarts)"
        "$SYSTEMCTL" restart bluetooth >/dev/null 2>&1
        "$SYSTEMCTL" restart nodered >/dev/null 2>&1
    fi
    if [ "$restarts" -ge "$TILT_MAX_RESTARTS" ]; then
        append_event "Tilt receiver restarts didn't help: check the Tilt battery and that it's in range"
    fi
}

# ---------------------------------------------------------------------------
# Report once everything is healthy again
# ---------------------------------------------------------------------------
send_report() {
    [ "$(read_state report_pending 0)" = "1" ] || return
    [ "$(read_state net_fails 0)" = "0" ] || return
    # One message per incident: while a Tilt receiver recovery is still in
    # progress (restarted, not yet heard, tries left), wait for the outcome.
    local tr
    tr=$(read_state tilt_restarts 0)
    if [ "$tr" -gt 0 ] && [ "$tr" -lt "$TILT_MAX_RESTARTS" ]; then
        return
    fi
    "$CURL" -sf -m 10 -o /dev/null http://localhost:5000/api/health || return

    local events msg
    events=$(sed 's/^/• /' "$STATE_DIR/events" 2>/dev/null)
    msg="🛠 *Brew Brain self-recovery*
${events:-• Recovered (details in journalctl -t brew-brain-recovery)}"
    if "$DOCKER" exec -e MSG="$msg" brew-brain python -c \
        "import os; from services.notifications import send_telegram_message; send_telegram_message(os.environ['MSG'], force=True)" \
        >/dev/null 2>&1; then
        log "recovery report sent"
        rm -f "$STATE_DIR/events"
        write_state report_pending 0
    else
        log "recovery report not sent yet (app not ready); will retry"
    fi
}

check_network
# Only judge the containers when the network is up: a Wi-Fi outage isn't
# their fault, and restarting them then would just add noise.
if [ "$(read_state net_fails 0)" = "0" ]; then
    check_app brew-brain http://localhost:5000/api/health
    check_app brew-brain-web http://localhost:3001/
    check_tilt
    send_report
fi
exit 0
