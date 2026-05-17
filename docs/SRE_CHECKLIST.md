# SRE Post-Deployment Verification Checklist

This checklist must be executed and verified after every production deployment to the Raspberry Pi to ensure core functions are online and performant.

## 1. Core Infrastructure Health
- [ ] **Disk Space:** Run `df -h`. Ensure root partition has >2GB free.
- [ ] **Database Writes:** Verify InfluxDB logs (`docker logs influxdb`). Ensure no "no space left on device" errors.
- [ ] **Retention Policies:** Run `influx bucket list`. Ensure the `fermentation` bucket has a retention policy (default: 30d).

## 2. Network & Routing
- [ ] **Internal DNS:** Exec into `brew-brain-web` and `wget http://brew-brain:5000/api/status`. If 502, check if `brew-brain` IP has changed and update `/etc/hosts` if necessary.
- [ ] **Socket.io Handshake:** Open the browser console. Verify `socket.io` connection is established (no 404/502).
- [ ] **Nginx Upstream:** Verify `docker logs brew-brain-web` for any `connect() failed (111: Connection refused)`.

## 3. API Functional Tests
- [ ] **Core Status:** `curl -s http://localhost:5000/api/status`. Verify JSON response.
- [ ] **Calculators:** 
  ```bash
  curl -X POST http://localhost:5000/api/calculator/ibu -H "Content-Type: application/json" -d '{"alpha_acid": 12.5, "weight_grams": 50, "boil_time_mins": 60, "boil_gravity": 1.050, "batch_volume_liters": 23}'
  ```
- [ ] **Water Chemistry:**
  ```bash
  curl -X POST http://localhost:5000/api/water/calculate -H "Content-Type: application/json" -d '{"target_profile": "west_coast", "volume_liters": 23.0}'
  ```

## 4. Edge AI (Ollama)
- [ ] **Model Presence:** `docker exec ollama ollama list`. Verify `llama3` is present.
- [ ] **Inference Test:**
  ```bash
  docker exec brew-brain curl -X POST http://ollama:11434/api/generate -d '{"model": "llama3", "prompt": "hi", "stream": false, "keep_alive": 0}'
  ```
- [ ] **Memory Management:** Monitor RAM usage during inference. Ensure model is dropped from RAM after completion (`keep_alive: 0` verification).

## 5. Mobile & PWA
- [ ] **Service Worker:** Verify `sw.js` is loading correctly in the browser.
- [ ] **Offline Fallback:** Disable network and verify the UI shows cached data.
