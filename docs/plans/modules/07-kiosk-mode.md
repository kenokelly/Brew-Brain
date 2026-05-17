# PRD & Implementation Plan: Kiosk Mode (Module 7)

## 1. Executive Summary
Kiosk mode is a full-screen, low-interaction view for tablets or wall-mounted monitors in the brewery.

## 2. Technical Decisions
*   **Performance:** Move from standard React components to **Optimized SVG Overlays**. This prevents browser lag on low-power tablet hardware.
*   **Visibility:** Use **High-Contrast "Brewery Red"** palette for alerts, visible from across the room.

## 3. Implementation Plan
1.  **Backend Fix:** Implement a "Streaming Mode" specifically for Kiosks that reduces the packet frequency of non-essential data.
2.  **UI Upgrade:** Fully customizable "Tiles."
    *   Add a "Mash Timer" tile with audible alerts.
    *   Implement "Gesture Control" (swipe to change batches).

## 4. Pros & Cons
*   **Pros:** Hands-free monitoring; no need to touch the device with wet hands.
*   **Cons:** Very limited functionality (view only).

## 5. Stability Fixes
*   Fixes the "White Screen of Death" when the Kiosk loses Wi-Fi connection for >5 minutes.
