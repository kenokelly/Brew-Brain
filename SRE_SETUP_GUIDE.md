# 🛠️ Brew Brain Local Build & SRE Setup Guide

**Target Audience:** SRE Team / Homelab Administrator
**Objective:** Establish a $0/month "Weekend Warrior" development environment using Docker Compose and Cloudflare Tunnels.

## 1. Prerequisites
*   **Docker Engine** & **Docker Compose**
*   **Git**
*   **cloudflared** (Cloudflare Tunnel Daemon)

---

## 2. Infrastructure Setup (Docker Compose)
Brew Brain uses a multi-container stack.

1.  Use the `docker-compose.yml` file to spin up InfluxDB, Telegraf, Grafana, and the Brew Brain containers.
2.  Run `docker-compose up -d`.

---

## 3. Zero-Cost Remote Access (Cloudflare Tunnels)
To access the dashboard remotely without exposing your home network or paying for a static IP:

1.  Install & Authenticate Cloudflared: `cloudflared tunnel login`
2.  Create the tunnel: `cloudflared tunnel create brew-brain-tunnel`
3.  Route to your domain: `cloudflared tunnel route dns brew-brain-tunnel brain.yourdomain.com`
4.  Run the tunnel pointing to the local dashboard (Port 3001 for Next.js): `cloudflared tunnel run --url http://localhost:3001 brew-brain-tunnel`

---

## 4. Shutting Down
Tear down the environment when finished to save compute resources:
`docker-compose down`
*(The InfluxDB state is safely preserved in the Docker volume).*
