# PRD & Functional Spec: System Settings (Module 5)

## 1. Executive Summary
The Settings module acts as the global state and configuration manager for Brew-Brain. It handles API keys, hardware toggles, and system preferences. The entire UI must be API-driven, meaning the frontend strictly reads from and writes to a central backend endpoint rather than relying on local storage.

## 2. Dev Team & Persona
*   **System Architect:** Designs the Pydantic schemas and thread-safe file operations.
*   **QA/Testing Lead:** Ensures invalid API keys or malformed JSON cannot crash the system.

## 3. Functional Specifications

### 3.1 Pydantic V2 Validation
*   All settings must be strictly typed using Pydantic V2 in `core/config.py`.
*   If a user submits `"temperature_unit": "Kelvin"` when only `"C"` or `"F"` are allowed, the API must reject it with a 422 Unprocessable Entity error before it reaches the disk.

### 3.2 Thread-Safe Storage
*   Settings are stored in `data/settings.json`.
*   Writes must use an atomic temp-file swap to prevent corruption if the Pi loses power mid-save.

### 3.3 Connectivity Tests
*   When a user inputs a Telegram Token or Brewfather API key, the backend must ping those external services to verify the key is valid *before* accepting it as the active configuration.

## 4. API Contracts

### `GET /api/settings`
**Response:**
```json
{
  "status": "success",
  "data": {
    "hardware": {
      "g40_mode": true,
      "temp_unit": "C"
    },
    "integrations": {
      "brewfather_configured": true,
      "telegram_configured": false
    }
  }
}
```

### `PATCH /api/settings`
**Request:**
```json
{
  "integrations": {
    "brewfather_api_key": "test_key",
    "brewfather_user_id": "test_id"
  }
}
```
**Response:**
```json
{
  "status": "success",
  "message": "Brewfather credentials verified and saved."
}
```

## 5. UI Requirements (API-Driven)
*   The Settings Page must fetch `GET /api/settings` on mount and populate forms.
*   "Test Connection" buttons must sit next to API key fields.
*   "Reset to Factory Defaults" button must prompt a double-confirmation modal.
