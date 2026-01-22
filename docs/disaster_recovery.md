# Brew Brain Disaster Recovery Guide

Complete procedure for deploying Brew Brain to a new Raspberry Pi from a backup.

---

## Prerequisites

- Raspberry Pi 5 (recommended) or Pi 4
- Fresh Raspberry Pi OS (Bookworm 64-bit)
- Backup archive: `brew_brain_backup_YYYYMMDD_HHMMSS.tar.gz`
- Network access (Ethernet or WiFi configured)

---

## Quick Recovery (15-20 minutes)

If you have a backup and just want to get running:

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
logout  # Re-login

# 2. Install Node-RED
bash <(curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered)
sudo systemctl enable nodered && sudo systemctl start nodered

# 3. Clone and Restore
git clone https://github.com/kenokelly/Brew-Brain.git
cd Brew-Brain
./scripts/restore.sh /path/to/backup.tar.gz
```

---

## Full Step-by-Step Installation

### Step 1: Initial Pi Setup (5 min)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Set hostname, timezone, locale
sudo raspi-config

# Enable SSH if not already
sudo systemctl enable ssh
```

### Step 2: Install Docker (5 min)

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# IMPORTANT: Log out and back in
logout
```

Verify after re-login:

```bash
docker --version
docker compose version
```

### Step 3: Install Node-RED (TiltPi) (5 min)

```bash
bash <(curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered)
```

When prompted:

- Pi-specific nodes: **Yes**

Enable and start:

```bash
sudo systemctl enable nodered
sudo systemctl start nodered
```

Verify: Open `http://<pi-ip>:1880` in browser

### Step 4: Install TiltPi Nodes

1. Open `http://<pi-ip>:1880`
2. Menu → Manage Palette → Install
3. Search for `node-red-contrib-tilt` → Install
4. Import your backed-up flows (see restore step)

### Step 5: Clone Brew Brain

```bash
cd ~
git clone https://github.com/kenokelly/Brew-Brain.git
cd Brew-Brain
```

### Step 6: Restore from Backup

```bash
./scripts/restore.sh /path/to/brew_brain_backup_YYYYMMDD.tar.gz
```

This restores:

- InfluxDB data (historical readings)
- Grafana dashboards
- Node-RED flows
- Brew Brain configuration

### Step 7: Configure Environment (if no backup)

If starting fresh without a backup:

```bash
cp .env.example .env
nano .env
```

Add:

```ini
INFLUX_USER=admin
INFLUX_PASS=your_secure_password
INFLUX_TOKEN=your_token_here
```

### Step 8: Launch Stack

```bash
docker compose up -d --build
```

Wait for initialization:

```bash
docker compose logs -f brew-brain
```

### Step 9: Verify All Services

| Service | URL | Default Login |
| :--- | :--- | :--- |
| Dashboard | `http://<pi-ip>:5000` | None |
| Grafana | `http://<pi-ip>:3000` | admin/admin |
| Node-RED | `http://<pi-ip>:1880` | None |
| TiltPi UI | `http://<pi-ip>:1880/ui` | None |
| InfluxDB | `http://<pi-ip>:8086` | See .env |

---

## Creating Backups

### Manual Backup

```bash
cd ~/Brew-Brain
./scripts/backup.sh
```

Creates: `brew_brain_backup_YYYYMMDD_HHMMSS.tar.gz`

### Automated Backups (Recommended)

Add to crontab for weekly backups:

```bash
crontab -e
```

Add:

```bash
# Weekly backup at 3am Sunday
0 3 * * 0 cd /home/pi/Brew-Brain && ./scripts/backup.sh /home/pi/backups/ >> /home/pi/backup.log 2>&1
```

### Off-site Backup

Copy to another location:

```bash
scp brew_brain_backup_*.tar.gz user@nas:/backups/brew-brain/
```

Or use rclone for cloud storage (Google Drive, S3, etc.)

---

## What's Backed Up

| Component | Data | Location |
| :--- | :--- | :--- |
| InfluxDB | Sensor readings, config | `influxdb_data/` |
| Grafana | Dashboards, users | `grafana_data/` |
| Node-RED | TiltPi flows | `~/.node-red/flows*.json` |
| Brew Brain | Settings, taps | API `/api/backup` |

---

## Troubleshooting

### Container won't start

```bash
docker compose logs brew-brain
```

### No Tilt data

1. Check Node-RED: `http://<ip>:1880`
2. Verify Tilt is nearby and transmitting
3. Check TiltPi flow is deployed

### InfluxDB connection errors

Verify token in `.env` matches what's in InfluxDB:

```bash
docker exec -it influxdb influx auth list
```

### Grafana dashboards missing

Re-import from provisioning:

```bash
docker compose restart grafana
```

---

## Contact

For issues: <https://github.com/kenokelly/Brew-Brain/issues>
