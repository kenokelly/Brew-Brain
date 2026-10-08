#!/usr/bin/env bash
# Install (or update) Brew Brain self-recovery on the Pi. Idempotent; run as
# root:  sudo ops/recovery/install.sh        Remove: sudo ops/recovery/install.sh --uninstall
set -euo pipefail
cd "$(dirname "$0")"

if [ "${1:-}" = "--uninstall" ]; then
    systemctl disable --now brew-brain-recovery.timer 2>/dev/null || true
    rm -f /etc/systemd/system/brew-brain-recovery.{service,timer} /usr/local/sbin/brew-brain-recovery \
          /etc/systemd/system.conf.d/brew-brain-watchdog.conf /etc/sysctl.d/90-brew-brain-panic.conf
    systemctl daemon-reload
    echo "Brew Brain self-recovery removed (state kept in /var/lib/brew-brain-recovery)."
    exit 0
fi

install -m 0755 brew-brain-recovery.sh /usr/local/sbin/brew-brain-recovery
install -m 0644 brew-brain-recovery.service brew-brain-recovery.timer /etc/systemd/system/
install -d /etc/systemd/system.conf.d
install -m 0644 watchdog.conf /etc/systemd/system.conf.d/brew-brain-watchdog.conf
install -m 0644 90-brew-brain-panic.conf /etc/sysctl.d/90-brew-brain-panic.conf

# Wi-Fi power saving drops the Pi off the network (2026-09-29 incident)
nmcli -t -f NAME,TYPE con show | awk -F: '$2 == "802-11-wireless" {print $1}' | while read -r c; do
    nmcli con modify "$c" 802-11-wireless.powersave 2 || true
done
iw dev wlan0 set power_save off 2>/dev/null || true

# Persistent journal so the cause of the next outage survives the reboot
install -d /etc/systemd/journald.conf.d
printf "[Journal]\nStorage=persistent\nSystemMaxUse=100M\n" > /etc/systemd/journald.conf.d/brew-brain.conf
install -d /var/log/journal

sysctl -q --system
systemctl daemon-reload
systemctl daemon-reexec          # picks up RuntimeWatchdogSec without a reboot
systemctl restart systemd-journald
systemctl enable --now brew-brain-recovery.timer

echo "Brew Brain self-recovery installed:"
systemctl show -p RuntimeWatchdogUSec | sed 's/^/  /'
echo "  kernel.panic = $(sysctl -n kernel.panic)"
systemctl list-timers brew-brain-recovery.timer --no-pager | sed -n 2p | sed 's/^/  next check: /'
