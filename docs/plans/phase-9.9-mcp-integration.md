# PRD & Implementation Plan: Phase 9.9 & MCP Integration

## 1. Executive Summary
This phase focuses on upgrading Brew-Brain's scientific engine by integrating the **Model Context Protocol (MCP)** for brewing intelligence and implementing a professional-grade **Mash pH Prediction** module inspired by the user's customized Bru'n Water model and the external `brewing-mcp` resource.

---

## 2. Objective & Impact
*   **MCP Integration:** Allow Brew-Brain to expose its data and reasoning via the Model Context Protocol, enabling it to act as a "knowledge provider" for other AI agents in the homelab.
*   **Mash pH Prediction:** Move beyond simple water profiles to predict the chemical outcome of the mash based on specific grain bills, water ions, and acid additions. This is the "Holy Grail" of brewing science accuracy.

---

## 3. Key Intelligence Ingested
Based on analysis of `BrunWater-Ken.xlsm`:
*   **Target Profile:** Hazy Pale v061225 (High Chloride focus).
*   **Mineral Precision:** Use the specific ion contribution rates identified in the model (e.g., Gypsum providing 232mg Ca and 557mg SO4 per gram).
*   **Acid Buffering:** Integrate Lactic Acid (88%) titration logic for pH adjustment.

---

## 4. Proposed Solution (Technical Architecture)

### 4.1 MCP Server Implementation
*   **Module:** `app/services/mcp.py`.
*   **Function:** Implement an MCP-compliant server that exposes `get_fermentation_status`, `get_brew_advice`, and `calculate_water_adjustment` as tools.
*   **Waste Management:** The MCP server will share the existing Flask/Eventlet thread pool to avoid spawning extra persistent processes.

### 4.2 Mash pH Logic (Phase 9.9)
*   **Module:** `app/services/mash_chemistry.py`.
*   **Physics:** Implement the Kolbach formula for residual alkalinity and its effect on mash pH.
*   **Grain Data:** Map grain colors (EBC) to their specific buffering capacity (acidity contribution).

---

## 5. Implementation Steps
1.  **Phase 9.9 (Mash pH):**
    *   Create `mash_chemistry.py` with grain buffering models.
    *   Implement `predict_mash_ph(water_profile, grain_bill, acid_additions)`.
2.  **MCP Integration:**
    *   Add `mcp-python-sdk` to `requirements.txt`.
    *   Implement `app/mcp/server.py` to expose Brew-Brain's intelligence.
3.  **UI Integration:**
    *   Add a "Mash Prediction" card to the dashboard.
4.  **Verification:**
    *   Compare Brew-Brain predictions against the `BrunWater-Ken.xlsm` baseline for the "Hazy Pale" batch.

---

## 6. Pros & Cons
*   **Pros:** Scientific parity with industry-standard Excel models; automated intelligence sharing via MCP.
*   **Cons:** Higher complexity in recipe input (requires grain types/colors); MCP adds a dependency layer.
