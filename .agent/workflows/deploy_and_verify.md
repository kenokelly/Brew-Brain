---
description: Build, Deploy, and Verify Brew-Brain on the Raspberry Pi
---

## Deploy Modes

| Mode | Command | Use When | Time |
|------|---------|----------|------|
| **Restart Only** | `./deploy_and_verify.sh --restart-only` | Code-only changes | ~30s |
| **Incremental** | `./deploy_and_verify.sh` | Normal changes (default) | ~1-2min |
| **Full Rebuild** | `./deploy_and_verify.sh --full` | Dependency changes | ~15min |

## Quick Deploy (Code Changes)

```bash
// turbo
./deploy_and_verify.sh --restart-only
```

## Standard Deploy (Default)

```bash
// turbo
./deploy_and_verify.sh
```

## Full Rebuild (Dependency Changes)

```bash
./deploy_and_verify.sh --full
```

The script automatically:

* **Syncs** code to remote Pi
* **Builds** Docker containers (with layer caching)
* **Restarts** services (`brew-brain`, `influxdb`, `grafana`, `telegraf`)
* **Verifies** container status, API connectivity, and data integrity
