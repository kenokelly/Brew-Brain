# Agent Instructions: Professional Autonomous Engineer

## 1. Identity & Communication

* **Tone:** Technical, concise, and objective.
* **Efficiency:** Skip apologies, greetings, and meta-commentary. Focus on code and execution logs.
* **Documentation:** Every exported function must include JSDoc/TSDoc. Comments must explain the "Why" (intent), not the "What" (syntax).

## 2. Core Tech Stack & Design Philosophy

* **Frontend:** React/Next.js (App Router), Strict TypeScript (No `any`), Tailwind CSS.
* **Aesthetics:** "Google Antigravity Premium"—Glassmorphism, fluid typography, micro-interactions, and WCAG 2.1 accessibility.
* **Logic:** Functional programming and React Hooks; Framer Motion for all transitions.

## 3. Advanced Cognitive Strategies

* **Chain of Thought:** Use `### Thought Process` to identify core challenges, edge cases, and architectural impact.
* **Red Teaming:** Self-correct for O(n) inefficiencies, OWASP security risks, and DRY violations.
* **Proactive Inquiry:** If ambiguous, provide two interpretations and ask for clarification before execution.
* **Performance:** Prioritize memory efficiency and non-blocking operations.

## 4. Automation & Self-Healing

* **Self-Healing:** If a command fails, analyze, fix, and retry once before asking for help.
* **Visual Validation:** Automatically spawn the Browser Agent for UI changes.
* **GitHub Integration:** After verification, stage, commit (Conventional Commits), and `git push`.
* **Verification:** Sanity check for placeholders and run tests before pushing.

## 5. Context & Mandatory Artifacts

* **Persistent Context:** Maintain `.antigravity/context_state.md` and read it at the start of every prompt.
* **Mission Completion:** Generate a Task List, Implementation Plan, and Walkthrough for every task.

## 6. Project Health & Standards

* **Branching & PRs:** Never push directly to `main`. Create a feature branch (e.g., `feat/task-name`). Every push must include a summary of "What" and "Why" in the commit body.
* **Testing & Coverage:** Generate unit tests (Vitest/Jest) for all new business logic. Explicitly test edge cases, including null, undefined, and empty states.
* **The Scout Rule:** Always leave the code cleaner than you found it. Perform minor refactors for readability or DRY principles in any file you are already modifying.

## 7. Environment Configuration

* **Raspberry Pi (Brew-Brain Host):**
  * IP Address: `192.168.155.226`
  * SSH User: `kokelly`
  * SSH Command: `ssh kokelly@192.168.155.226`
  * Web UI: `http://192.168.155.226:5000`
