# Brew Brain Production Handoff & Architecture Spec
**Target Team:** AI Agent & Executive Architects (Pre-Seed) / Human Engineering Team (Post-Seed)
**Project:** Brew Brain

*Note: Until Pre-Seed funding is secured, this document directs the AI-assisted development workflow. Post-funding, this serves as the exact spec for the hired human engineering team.*

## 1. Production Architecture & Infrastructure Spec
*   **Hosting:** Raspberry Pi 5 (Edge) / AWS or GCP (Cloud for ML Training/Aggregation).
*   **Stack:** Flask (Backend), Next.js (Web UI), InfluxDB v2 (Time-series), Telegraf (Ingest), Grafana (Dashboarding).
*   **Database Server:** InfluxDB v2. **Crucial:** Ensure data persistence across Docker restarts.
*   **Caching/Worker:** Redis + Celery (Optional / Future) for async ML tasks.

## 2. AI-Assisted Development Task List

### Sprint 0: Pre-build & Environment Setup
- [x] **Infrastructure Initialization:** `docker-compose.yml` bind-mounts `./brain_data:/data`, `./influxdb_data`, `./grafana_data` — state survives container recreates. Verified live on the Pi.
- [~] **Connectivity & Security:** Partial — `cloudflared` tunnel avoids direct port exposure, `require_api_token` gates sensitive routes. Not a full audit (see Sprint 3.2 below, still open).
- [x] **CI/CD Pipeline Setup:** `.github/workflows/docker-publish.yml` already builds multi-arch (amd64/arm64) images via Buildx/QEMU on push to `main`. It existed but was never checked off.

### Sprint A: Hardening & Data Modeling (Backend)
- [x] **SSRF Fix in Sourcing:** Sanitise tag input and restrict outbound requests.
- [x] **Lightweight Alternatives:** Removed Pandas from core requirements to improve Pi stability.
- [x] **Persistence:** ML model state (`data/models/*.joblib`) already lives under the `./brain_data:/data` bind mount — persists across container recreates without further migration.

### Sprint B: The "Offline-First" Mobile Client
- [x] **PWA Support:** Currently implemented as a Next.js PWA.
- [x] **Native Mobile App:** Superseded by a different choice, not "evaluated and rejected" — shipped via Capacitor (iOS/Android wrapping, `web/ios`, `web/android`) rather than a Flutter rewrite. Biometric auth, haptics, and camera/barcode scanning are already wired up (see Sprint M below). If a native *rewrite* is still wanted, that's a fresh scoping conversation, not a leftover task.

### Sprint C: Pro-Grade Features
- [x] **FG Prediction:** Gradient Boosting and Physics-informed ML models.
- [x] **Anomaly Detection:** Rule-based and Z-score statistical detection.
- [~] **Hardware Integration:** Tilt signal health monitoring exists (`check_signal_loss`, auto-troubleshooting, and — as of 2026-09 — a proper alert cooldown plus a `brew_active` gate so it stays quiet between batches). "Deepen" is open-ended; treat this as ongoing, not a discrete task.
- [~] **Web Dashboard:** The main dashboard already has real-time WebSocket telemetry, system status, anomaly/advice/prediction widgets. "Refine Mission Control UI" is a design goal, not a checklist item — needs a concrete spec (what should change?) before it can be picked up as actual work.

### Sprint D: The Board Operations Scheduler
- [x] **Automated Telemetry:** Implemented via APScheduler, daily diff reports at 08:30 (Weekdays) / 11:00 (Weekends) — see TASKS.md Phase D.1/D.2.

### Sprint E: Documentation & Release Management
- [ ] **Enforced Documentation Gate:** Still not implemented. Note: `.github/workflows/lint-and-test.yml` existed but was silently broken (referenced a nonexistent `brew-brain/` subdirectory and a typo'd `python-python` input) since a repo restructure — fixed 2026-09-16, ruff/mypy now run advisory-only (682/22 pre-existing findings respectively, not addressed here) with pytest as the real hard gate.

### Sprint M: Mobile-First Evolution (PWA to Native)
- [x] **Phase 1 (PWA):** Tailwind CSS is the styling system throughout.
- [x] **Phase 2 (Adaptive Mobile):** Capacitor wraps the PWA for iOS/Android (`web/ios`, `web/android`, `@capacitor/core` etc.).
- [x] **Phase 3 (Native Optimization):** Biometric auth (`@aparajita/capacitor-biometric-auth`, gates Settings), Haptics (`@capacitor/haptics`, brew day guide), and camera/barcode scanning (`capacitor-mlkit/barcode-scanning`, inventory) are all already wired up.

---

## 3. QA, Test Plan, & Deployment Strategy

### 3.1 CI/CD Pipeline & The "CISO Gate" (GitHub Actions)
Strict **Code Review -> Build -> Verify -> Security Review -> Deploy** structure.
*   **Full Security Review (The Gate):** SAST (CodeQL) and Dependency Scanning.

### 3.2 Rollout Strategy
*   **Pre-Beta Security Audit:** Audit API tokens and JWT implementation.
*   **Edge Deployment:** Use `deploy_and_verify.sh` for remote Pi updates.

## 4. Development Guidelines
Strict adherence to the 10 core principles outlined in `DEVELOPMENT_GUIDELINES.md` is mandatory for all AI-generated code and human architects.
