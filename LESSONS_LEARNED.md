# 🧠 Brew Brain Lessons Learned & Continuous Improvement

This document is a living repository of failures, successes, and insights gathered by all teams.

**The Mandate:** We do not hide failures. We document them, extract the lesson, and immediately adapt our processes or code to ensure we never make the same mistake twice. This document MUST be reviewed daily by the Board.

---

## 📝 The Ledger

### 2026-03-19
*   **Submitter:** CTO
*   **The Incident:** Raspberry Pi 5 instability due to heavy containers (Playwright).
*   **The Root Cause:** Browser automation is too resource-intensive for the Pi's ARM architecture.
*   **The Lesson & Action:** Fully removed Playwright and replaced with `requests` + `BeautifulSoup`. Refined Phase 5 of the Master Plan.

### 2026-03-19
*   **Submitter:** CEO
*   **The Incident:** Security risk identified in the sourcing module (SSRF).
*   **The Root Cause:** Unsanitized user-provided tags were being used in outbound network requests.
*   **The Lesson & Action:** Sanitized tag input and restricted outbound requests to known-good domains. Implemented the "CISO Gate" philosophy.

### 2026-05-06
*   **Submitter:** AI Agent (directed by CTO)
*   **The Incident:** Sourcing service instability and slow sequential price fetching.
*   **The Root Cause:** Sequential network requests and fragile CSS selectors caused timeouts and failed price extraction. Missing imports/globals in previous refactoring.
*   **The Lesson & Action:** Implemented `ThreadPoolExecutor` for concurrency, JSON-LD for robust parsing, and a TTL-based Circuit Breaker for domain safety. Standardized on "CISO Gate" input sanitization.

### 2026-05-15
*   **Submitter:** AI Agent (directed by CEO)
*   **The Incident:** Need for higher precision and reduced complexity in agent-driven modifications.
*   **The Root Cause:** Vague instructions and "just-in-case" code additions were leading to over-engineering and lack of traceability.
*   **The Lesson & Action:** Formally adopted four Core Engineering Guidelines: Think Before Coding, Simplicity First, Surgical Changes, and Goal-Driven Execution. These are now mandated in `GEMINI.md` to enforce surgical precision and simplicity in all future development.

### 2026-05-15
*   **Submitter:** AI Agent
*   **The Incident:** Automated tests failed to collect due to "services is not a package" and "ModuleNotFoundError".
*   **The Root Cause:** Inconsistent import paths (mixing `from app.services` and `from services`) and missing `__init__.py` files in refactored directories. This caused circular confusion for the Python interpreter when `app/` was added to `PYTHONPATH`.
*   **The Lesson & Action:** Standardized on absolute imports starting from the `app.` prefix and ensured all subdirectories contain `__init__.py`. Adopted a "run from root" policy for all verification commands.

---
*(Add new entries below this line)*
