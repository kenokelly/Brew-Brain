# PRD & Functional Spec: Tap List (Module 8)

## 1. Executive Summary
The Tap List module manages the "Finished Beer" lifecycle. It tracks what is currently on draft, estimates keg levels, and provides guest-facing information. Like all other modules, the UI must be entirely driven by an API backend, allowing easy integration with digital pour systems or the Kiosk display.

## 2. Dev Team & Persona
*   **System Analyst:** Designs the Volume-Decay estimation logic.
*   **Product UX/UI Designer:** Designs the digital Taproom Menu cards and QR codes.

## 3. Functional Specifications

### 3.1 Keg Volume Estimation
*   Since physical flow-meters are not installed, the system estimates keg volume based on time. A keg is marked as "Tapped" with a total volume (e.g., 19L). 
*   The UI allows the brewer to hit a "-1 Pint" button, or just enter an estimated percentage.

### 3.2 Dynamic ABV & Calorie Calculation
*   When a batch finishes fermentation (Module 4), its final Original Gravity (OG) and Final Gravity (FG) are logged. 
*   The Tap List API must dynamically calculate the accurate ABV and estimated Calories-per-pint based on these exact metrics, rather than relying on the "Predicted" recipe values.

### 3.3 QR Code Generation
*   The backend generates a base64 encoded QR code PNG for each active tap.
*   Scanning the code routes the user to a public `GET /api/taplist/public/<tap_id>` endpoint which serves a read-only narrative of the beer.

## 4. API Contracts

### `GET /api/taplist`
**Response:**
```json
{
  "status": "success",
  "taps": [
    {
      "tap_number": 1,
      "beer_name": "Hop Storm IPA",
      "style": "American IPA",
      "abv": 6.8,
      "keg_volume_l": 19,
      "remaining_pct": 75,
      "qr_code_base64": "iVBORw0KGgoAAAANSU..."
    }
  ]
}
```

### `POST /api/taplist/<tap_id>/pour`
**Request:** `{"amount_ml": 568}` (1 UK Pint)
**Response:** `{"status": "success", "new_remaining_pct": 72}`

## 5. UI Requirements (API-Driven)
*   **Taproom Menu View:** A clean, card-based interface displaying the beer color (calculated from SRM), ABV, and a visual keg-level indicator.
*   **QR Modal:** Clicking a tap card expands it to show the full QR code for printing or display.
