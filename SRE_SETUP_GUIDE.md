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

## 5. Edge AI (Optional)
Brew Brain now supports local LLM integration via Ollama for automated narrative logs and troubleshooting.

### Deployment
The Ollama service is included in `docker-compose.yml`. It will start automatically.

### Model Setup
To use the narrative features, you must pull a model (e.g., Llama 3) inside the container:
```bash
docker exec -it ollama ollama pull llama3:3b
```

### Configuration
Update `config.json` or use the Settings UI:
- `ollama_host`: `ollama` (default in docker)
- `ollama_model`: `llama3:3b` (or your preferred model)
