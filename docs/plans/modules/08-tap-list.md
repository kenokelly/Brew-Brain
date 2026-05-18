# PRD & Functional Spec: Tap List (Module 8)

## 1. Executive Summary
The Tap List module manages the "Finished Beer" lifecycle. It tracks what is currently on draft, estimates keg levels, and provides guest-facing information. Like all other modules, the UI must be entirely driven by an API backend, allowing easy integration with digital pour systems or the Kiosk display.

## 2. Dev Team & Persona
*   **System Analyst:** Designs the Volume-Decay estimation logic.
*   **Product UX/UI Designer:** Designs the digital Taproom Menu cards and QR codes.

## 3. Functional Specifications

### 3.1 Keg Volume Estimation
*   Since physical flow-meters are not installed, the system estimates keg volume based on time. A keg is marked as "Tapped" with a total volume (e.g., 19L). 
*   The UI must provide specific pour decrement buttons based on standard UK glass sizes: **1 Pint (568ml)**, **2/3 Pint (379ml)**, **1/2 Pint (284ml)**, and **1/3 Pint (189ml)**.
*   Alternatively, the brewer can enter an estimated percentage override.

### 3.2 Dynamic ABV & Calorie Calculation
*   When a batch finishes fermentation (Module 4), its final Original Gravity (OG) and Final Gravity (FG) are logged. 
*   The Tap List API must dynamically calculate the accurate ABV and estimated Calories-per-pint based on these exact metrics, rather than relying on the "Predicted" recipe values.

### 3.3 QR Code Generation
*   The backend generates a base64 encoded QR code PNG for each active tap.
*   Scanning the code routes the user to a public `GET /api/taplist/public/<tap_id>` endpoint which serves a read-only narrative of the beer.

### 3.4 Tap Initialization (Admin Flow)
*   To set up a new keg, the user enters an administrative flow where they select a finished batch from the Brew-Brain history (Module 4) or directly from Brewfather.
*   They assign the batch to a specific physical tap (e.g., Tap 1-4).
*   They specify the starting **Keg Volume** (Standard Corny Keg is 19L, Half Corny is 9.5L, Commercial sizes are 30L/50L). 
*   The system automatically links the final gravity data from the selected batch to lock in the ABV and Calorie calculations.

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

### `POST /api/taplist/<tap_id>/init`
**Request:**
```json
{
  "batch_id": "bf_batch_123xyz",
  "keg_volume_l": 19.0
}
```
**Response:** `{"status": "success", "message": "Tap 1 initialized with 19L of Hop Storm IPA."}`

### `POST /api/taplist/<tap_id>/pour`
**Request:** `{"amount_ml": 568}` (1 UK Pint)
**Response:** `{"status": "success", "new_remaining_pct": 72}`

## 5. UI Requirements (API-Driven)
*   **Taproom Menu View:** A clean, card-based interface displaying the beer color (calculated from SRM), ABV, and a visual keg-level indicator.
*   **QR Modal:** Clicking a tap card expands it to show the full QR code for printing or display.
