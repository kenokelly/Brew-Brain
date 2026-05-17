# PRD & Implementation Plan: Tap List (Module 8)

## 1. Executive Summary
The Tap List manages the inventory of finished beer. This plan integrates the "Finished Gravity" from Module 4 to automatically calculate final ABV and Calories.

## 2. Technical Decisions
*   **Inventory Tracking:** Use **Volume-Decay estimation** (integrating the time the tap is 'open' if available, or simple pour-based subtraction).
*   **Media:** Automatically generate **QR Codes** for every tap, allowing guests to see the AI-generated "Narrative Log" for that batch on their own phones.

## 3. Implementation Plan
1.  **Backend Fix:** Ensure the Tap List service is decoupled from active fermentation logic (prevents "Beer Disappearing" when a new fermentation starts).
2.  **UI Upgrade:** "Taproom View" with brewery-style menu cards.
    *   Add "Predicted Finish" dates for beers currently in the keg.

## 4. Pros & Cons
*   **Pros:** Professional guest experience; automatic ABV verification.
*   **Cons:** Requires manual logging of when a keg is "kicked."

## 5. Stability Fixes
*   Fixes the sync delay where a beer marked as "Kegged" in Brewfather takes up to an hour to appear on the Tap List.
