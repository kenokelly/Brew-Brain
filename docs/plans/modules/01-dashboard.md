# PRD & Implementation Plan: Dashboard & Real-time (Module 1)

## 1. Executive Summary
The dashboard is the system's "Heartbeat." This plan addresses persistent "Offline" reports by hardening the WebSocket layer and providing a hardware-accelerated "Premium" monitoring experience.

## 2. Technical Decisions
*   **Networking:** Move from Polling-first to **WebSocket-Primary** with an explicit "Gateway Check" in the frontend to detect proxy failures before they affect the UI.
*   **Visuals:** Use **Hardware Acceleration (GPU)** via Framer Motion. This prevents the Pi's CPU from spiking when rendering complex graphs or animations.
*   **State:** Use **SWR (Stale-While-Revalidate)** to ensure the dashboard immediately shows the "Last Known Good" data while the live connection initializes.

## 3. Implementation Plan
1.  **Stability Fix:** Implement an Nginx "Resolver" check to prevent stale upstream IPs (the cause of today's 502 error).
2.  **UI Upgrade:** Glassmorphism Stat Cards with "Live Pulse" animations.
3.  **Data:** Integrate "24h Trend" sparks on every card.

## 4. Pros & Cons
*   **Pros:** Instant feedback loop; world-class visual feel; no more "False Offline" states.
*   **Cons:** Higher browser RAM usage for the client.

## 5. Stability Fixes
*   Rooting out the 502 Bad Gateway by automating the `/etc/hosts` update inside Docker during startup.
