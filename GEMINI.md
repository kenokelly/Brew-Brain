# Brew Brain Project Instructions (GEMINI.md)

These instructions are foundational mandates for the AI agent (Gemini CLI). They take absolute precedence over general workflows.

## Core Engineering Guidelines

### 1. Think Before Coding
- **State your assumptions out loud.**
- **If the request is ambiguous, ask for clarification.**
- **If a simpler approach exists, push back and propose it.**
- **Stop when you are confused.** Name exactly what is unclear; do not just pick one interpretation and run with it.

### 2. Simplicity First
- **Write the minimum code that solves the problem.**
- **No speculative abstractions.**
- **No flexibility nobody asked for.**
- **The test:** Would a senior engineer call this overcomplicated?

### 3. Surgical Changes
- **Touch only what the task requires.**
- **Do not "improve" neighboring code.**
- **Do not refactor what is not broken.**
- **Every changed line should trace back directly to the request.**

### 4. Goal-Driven Execution
- **Turn vague instructions into verifiable targets before writing a line.**
- **Example:** "Add validation" becomes "write tests for invalid inputs, then make them pass."
- **Verification is the only path to finality.**

### 5. End-to-End Local Verification First (Zero Blind Commits)
- **No more assumptions.** Before any code is committed or handed to the SRE team for deployment, it must be proven to work locally.
- **Mandatory Feature Proofs:** If an API endpoint is created or modified, the responsible agent *must* run a local `curl` or Python script hitting that exact endpoint. We must see a `200 OK` response before claiming it is "fixed".

### 6. Frontend-Backend Contract Enforcement
- When fixing UI bugs that interact with the backend, the agent must cross-reference both sides of the stack.
- If the frontend calls an endpoint, the backend route must be explicitly searched (`grep`) and verified to match that exact path string.

### 7. Deep QA, Not Shallow Health Checks
- The SRE team's "Frontend/API Online" check merely confirms the web server hasn't crashed. It is fundamentally inadequate for verifying feature completeness.
- **New QA Requirement:** QA agents (or the primary agent) must execute targeted integration tests for the specific feature being deployed, rather than just relying on the general test suite passing.

### 8. Batch Processing over Ping-Pong Iteration
- To reduce token burn, stop rushing single-line hotfixes through the entire deployment pipeline.
- Plan the feature, implement the frontend, implement the backend, test the integration locally, and *only then* execute a single, comprehensive deployment.
