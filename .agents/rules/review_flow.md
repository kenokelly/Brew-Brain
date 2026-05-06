# 🔄 Antigravity Review Flow & Agent Chaining

This policy defines the autonomous loops that gate all code changes before they reach the production stack.

---

## 🛑 Review Policy: REQUIRE_APPROVAL
**Status:** ACTIVE
**Mandate:** No code shall be merged into `main` without successful completion of the chained validation loop.

---

## ⛓️ The Agent Chain

### 1. 🛡️ Security Architect (The Reviewer)
- **Trigger:** Senior Supplier finishes code modification.
- **Action:** Execute `security_scan` (secrets, dependencies, guidelines).
- **Condition:** Must return `PASS` to proceed.

### 2. 🧪 Automation Engineer (The QA)
- **Trigger:** Security Architect returns `PASS`.
- **Action:** Execute full test suite (`pytest` for API, `npm test` for Web).
- **Condition:** 100% pass rate required. Only persona allowed to trigger `BUILD`.

### 3. ✍️ Documentation Critic (The Verification)
- **Trigger:** Tests return `PASS`.
- **Action:** Audit `README.md` and `docs/` for updates relative to changed symbols.
- **Condition:** Reject PR if documentation is stale.

---

## 🔁 The Failure Loop: DevOps & SRE
- **Trigger:** `deploy_status == fail` OR `health_check == fail`.
- **Mandatory Action Sequence:**
    1.  **Capture:** Aggregate all terminal logs, container logs, and network error traces.
    2.  **Revert:** Immediately execute `agent_rollback` or `git revert` to the last stable SHA.
    3.  **Document:** Open a new 'Issue' or 'Bug' context for the **Senior Supplier** with the captured logs.
    4.  **Freeze:** **DO NOT** attempt to re-deploy until the **QA Squad** has re-verified the fix in the staging environment.
