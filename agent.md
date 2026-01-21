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
