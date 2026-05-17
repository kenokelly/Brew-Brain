# PRD & Implementation Plan: Edge AI Brewmaster (Module 2)

## 1. Executive Summary
This module transforms raw data into expert narrative. This plan refines the AI to be truly proactive and resource-conscious on the Raspberry Pi 5.

## 2. Technical Decisions
*   **Model Management:** Enforce **Zero-Persistence (Keep-alive: 0)**. The model loads, answers, and dies. No memory waste.
*   **Context injection:** Instead of raw logs, inject **Derived Statistics** (Velocity, Acceleration, Days in Phase) into the LLM prompt to save tokens.

## 3. Implementation Plan
1.  **Backend Fix:** Ensure Ollama timeouts are set to 600s to support heavy inference loads on the Pi's CPU.
2.  **UI Upgrade:** A "Chat Bubble" style assistant on every page.
    *   Add "Thinking" animations to provide visual feedback during 30s+ inference times.
3.  **Proactive logic:** AI sends a Telegram "Post-Mortem" if a batch hits terminal gravity unexpectedly.

## 4. Pros & Cons
*   **Pros:** Expert advice at 0/month cost; private/offline.
*   **Cons:** Response time is 30-60s on a Pi (compared to 2s on OpenAI).

## 5. Stability Fixes
*   Implementation of the `SRE_CHECKLIST.md` AI test to catch Ollama model eviction issues.
