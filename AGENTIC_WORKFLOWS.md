# AI Agentic Workflows for Brew Brain

This document outlines the actionable guidelines for how the Executive Team should interact with and structure the AI coding agent.

---

## 1. The Memory Hierarchy (`GEMINI.md`)
*   **The Rule of 500:** The root memory file MUST be kept strictly under 500 words. It is a "hot cache" of the project's absolute, non-negotiable invariants.
*   **Path-Scoped Invariants:** Specific rules belong in specific folders (e.g., `web/lib/views/UI_RULES.md`). The agent only loads what it needs.

## 2. Strategic Delegation (Sub-Agents)
*   **Grep-Work Offloading:** Never ask the main agent to perform massive codebase searches. Explicitly instruct it to spawn a sub-agent to explore and return a concise summary.
*   **Specialized Experts:** Leverage built-in skills (e.g., Python/Flask specific) before asking the agent to generate code.

## 3. Deterministic Guardrails (Verification Hooks)
*   **Verification-Before-Completion:** The agent is expressly forbidden from stating a task is complete until it runs a deterministic verification command (e.g., `pytest`, `docker compose up`) and displays the output. 
*   **TDD First:** Write the failing test, run it, *then* write the implementation.

## 4. The "Plan Mode" Workflow
*   **Research -> Strategy -> Execution:** The agent must list invariants, write an atomic plan to a `.md` file, and wait for human approval before executing code.
*   **Tutor Mode:** If a task is underspecified, the agent must enter "Tutor Mode" to ask the human architect questions, ensuring a shared mental model.

## 5. MCP (Model Context Protocol) Integration
Configure MCP servers to provide the agent with real-time awareness of the local Raspberry Pi or homelab environment.
