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
- [ ] **Infrastructure Initialization:** Ensure `docker-compose.yml` is robust and handles all volume mounts.
- [ ] **Connectivity & Security:** Harden the Raspberry Pi network exposure.
- [ ] **CI/CD Pipeline Setup:** GitHub Actions for building multi-arch images (amd64/arm64).

### Sprint A: Hardening & Data Modeling (Backend)
- [x] **SSRF Fix in Sourcing:** Sanitise tag input and restrict outbound requests.
- [x] **Lightweight Alternatives:** Removed Pandas from core requirements to improve Pi stability.
- [ ] **Persistence:** Migrate ML model states to a persistent store.

### Sprint B: The "Offline-First" Mobile Client
- [x] **PWA Support:** Currently implemented as a Next.js PWA.
- [ ] **Native Mobile App:** Evaluate Flutter transition for deeper hardware integration.

### Sprint C: Pro-Grade Features
- [x] **FG Prediction:** Gradient Boosting and Physics-informed ML models.
- [x] **Anomaly Detection:** Rule-based and Z-score statistical detection.
- [ ] **Hardware Integration:** Deepen Tilt signal health monitoring.
- [ ] **Web Dashboard:** Refine "Mission Control" UI via WebSocket telemetry.

### Sprint D: The Board Operations Scheduler
- [ ] **Automated Telemetry:** Implement an application-level task scheduler to trigger daily diff reports at 08:30 AM (Weekdays) and 11:00 AM (Weekends).

### Sprint E: Documentation & Release Management
- [ ] **Enforced Documentation Gate:** Integrate documentation checks into the CI/CD pipeline. 

### Sprint M: Mobile-First Evolution (PWA to Native)
- [ ] **Phase 1 (PWA):** Refactor web UI with a responsive framework (e.g., Tailwind CSS).
- [ ] **Phase 2 (Adaptive Mobile):** Use Capacitor/Hybrid bridge to wrap the PWA into installable .apk or .ipa files.
- [ ] **Phase 3 (Native Optimization):** Implement Native Modules (Biometrics, Camera, Haptics) for platform-specific optimization.

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
