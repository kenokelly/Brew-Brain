# PRD & Functional Spec: Kiosk Mode (Module 7)

## 1. Executive Summary
Kiosk mode is a high-visibility, zero-interaction display designed for wall-mounted tablets in the brewery. It is API-driven and highly optimized to run continuously without crashing lower-end hardware (like older iPads or Raspberry Pi displays).

## 2. Dev Team & Persona
*   **Product UX/UI Designer:** Designs the high-contrast, scalable SVG overlays.
*   **Lead Software Developer:** Builds the lightweight "Streaming Mode" API endpoints to minimize packet payload.

## 3. Functional Specifications

### 3.1 SVG Overlay Architecture
*   Instead of rendering complex React components with `framer-motion` (which taxes old tablet CPUs), the backend will serve a streamlined data payload, and the frontend will use simple SVG graphics to display tanks and gauges.

### 3.2 "Streaming Mode" API
*   Kiosks do not need second-by-second updates for a 2-week fermentation. The Kiosk frontend must request data using a specific `?mode=kiosk` flag.
*   The backend will throttle updates to this socket/endpoint to once every 60 seconds to preserve network and browser memory.

### 3.3 Visual Alerts
*   If a tank goes "out of range" (e.g., temperature spikes above target + 2°C), the specific tile must turn "Brewery Red" to catch the brewer's eye from across the room.

## 4. API Contracts

### `GET /api/kiosk/tanks`
**Response:**
```json
{
  "status": "success",
  "refresh_interval_ms": 60000,
  "data": [
    {
      "tank_id": "F1",
      "status": "active",
      "temp_c": 19.5,
      "temp_target": 19.0,
      "alert": true,
      "sg": 1.012
    }
  ]
}
```

## 5. UI Requirements (API-Driven)
*   **Gesture Support:** Simple left/right swipe to cycle between Tanks, Tap List, and Environment (Fridge temps).
*   **Mash Timer Overlay:** If an active brew day is detected, a massive countdown timer overtakes the top half of the screen.
