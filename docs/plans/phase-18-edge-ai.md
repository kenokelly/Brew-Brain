# PRD & Implementation Plan: Phase 18 - Edge AI Refinement

## Background & Motivation
With the successful stabilization of the Raspberry Pi environment and the initial rollout of the Ollama-based Brewmaster AI (Phase 15), we have a functional local LLM. However, the AI's advice is currently based on limited context (current SG, Temp, and basic yeast metadata). To make the "Intelligent Fermentation System" truly autonomous, the AI needs granular fermentation context—specifically gravity velocity, temperature variance, and detailed yeast characteristics—to provide highly accurate, proactive advice (e.g., predicting stalls before they happen, suggesting exact diacetyl rest timings).

## Scope & Impact
This phase focuses on enhancing the `ai.py` and `yeast.py` modules on the backend, without requiring major UI changes. The impact will be a significantly smarter `AdviceWidget` and more detailed responses from the `/api/ai/chat` endpoint. 

## Proposed Solution
1. **Yeast Metadata Expansion:** Enhance `services/yeast.py` to include a richer dataset of common yeast strains, their ideal temperature ranges, attenuation targets, and known behaviors (e.g., "high krausen", "diacetyl producer").
2. **Context-Aware Prompts (Optimized):** Refactor `get_proactive_advice` and `generate_chat_response` in `services/ai.py` to inject real-time derived metrics (velocity, days in phase) calculated by `features.py`. **Constraint:** The injected context must be strictly limited (e.g., using summary statistics rather than raw data arrays) to prevent expanding the LLM context window, which would spike RAM usage on the Pi.
3. **AI Predictive Alerting:** Introduce a lightweight check that allows the AI to flag impending issues (like a stalled fermentation) based on velocity trends, feeding into the existing Telegram notification system.
4. **Waste Management & Pi Resource Control:** Implement strict memory management around the Ollama calls. This includes using a unified `/api/generate` call with `keep_alive=0` (or a very short TTL) to ensure the LLM model is immediately unloaded from RAM after generating advice, preventing long-term memory leaks or "waste" on the Pi.

## Alternatives Considered
- **Cloud-based LLM (e.g., OpenAI API):** Rejected. While it would provide "smarter" base reasoning, it violates the project's offline-first, edge-compute philosophy on the Raspberry Pi.
- **Keeping LLM loaded in RAM:** Rejected due to the Pi's 8GB RAM limit. The `llama3:3b` model consumes ~2-3GB; keeping it resident would starve the Flask API and Celery workers.

## Implementation Steps
1. **Enhance `yeast.py`:** Add detailed dictionaries for popular yeast strains (SafAle US-05, WLP001, etc.) including `flocculation`, `attenuation_range`, and `temp_range`.
2. **Refactor `ai.py` Prompts & Resource Controls:**
   - Update `get_proactive_advice` to fetch the 24-hour gravity velocity from `features.calculate_sg_velocity`.
   - Modify the `system_prompt` to be extremely concise.
   - **Crucial:** Add `"keep_alive": "5m"` or `"0"` to the Ollama JSON payload to enforce memory cleanup (waste management).
3. **Integrate Telegram AI Alerts:** 
   - Add logic in `worker.py` or `notifications.py` to trigger an AI summary when a critical anomaly is detected, rather than just sending the raw error string.
4. **Testing:** Write unit tests in `test_ai_service.py` to mock the Ollama endpoint and verify that the prompts are constructed with the correct dynamic variables and the `keep_alive` parameter is present.

## Verification & Testing
- Run `pytest brew-brain/tests/test_ai_service.py` to ensure prompt generation logic is sound.
- Run `mypy` and `ruff` to adhere to Phase 13.3 standards.
- Deploy to the Pi and monitor `/api/ai/advice` latency to ensure the added context doesn't push Ollama inference times beyond acceptable limits (target < 30s).

## Migration & Rollback
- **Rollback:** In case of severe latency or context window overflow, revert `ai.py` to the previous commit (Phase 15.3 state).
