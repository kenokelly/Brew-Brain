# Agent Instructions: Context & Automation

## 1. Context & Artifact Management

* **Persistent Context:** After every prompt execution, you must summarize the changes made, the current state of the application, and any pending technical debt. Save this summary into a file named `.antigravity/context_state.md`.
* **Artifact Retention:** Ensure all generated artifacts (code snippets, diagrams, or plans) are explicitly saved to the workspace. Do not rely on ephemeral chat history for project-critical logic.
* **State Awareness:** At the start of every new prompt, read `.antigravity/context_state.md` to ensure continuity of logic and style.

## 2. GitHub Integration & Workflow

* **Automatic Commits:** Upon the successful completion of a task and its verification, you are authorized to stage all changes.
* **Commit Messages:** Use conventional commit formatting (e.g., `feat:`, `fix:`, `docs:`). Include a brief description of what was accomplished in the prompt session.
* **Push Policy:** Immediately following a successful commit, execute a `git push` to the current remote branch on GitHub.
* **Post-Execution Report:** Once the push is confirmed, provide the user with the commit hash and a link to the updated repository or PR if applicable.

## 3. Verification Before Push

* Before pushing to GitHub, perform a quick sanity check of the changed files to ensure no "placeholder" code or unfinished comments remain.
* If a test suite exists, run the relevant tests and only proceed with the push if they pass.

# Agent Instructions: Professional Stack & Automation

## 1. Core Tech Stack & Patterns

* **Frontend:** React/Next.js using the **App Router** exclusively.
* **Typing:** Use **Strict TypeScript**. Every interface and type must be explicitly defined; avoid `any` at all costs.
* **Styling:** Use **Tailwind CSS** for all UI components. Follow mobile-first responsive design patterns.
* **Animation:** Use **Framer Motion** for all UI transitions, hover states, and page entries to ensure a premium feel.
* **Logic:** Prioritize **Functional Programming** and React Hooks. Do not use Class-based components unless maintaining legacy code.

## 2. Error Handling & Quality

* **Resilience:** Implement **Explicit Error Boundaries** for major UI segments.
* **Logic Safety:** Use `try/catch` blocks for all asynchronous operations and side effects, providing meaningful, user-friendly error messages.
* **Logging:** No `console.log` in production-ready code. Use a dedicated logging utility (e.g., a custom `logger` module) for error tracking.

## 3. Context & Automation (Workflow)

* **Context State:** After every execution, update `.antigravity/context_state.md` with a summary of changes and technical debt.
* **GitHub Integration:** 1. Once a task is verified, stage changes and commit using **Conventional Commits** (e.g., `feat:`, `fix:`).
    2. Perform a `git push` to the current remote branch automatically.
* **Verification:** Run a build check or relevant tests before pushing to ensure the main branch remains stable.
