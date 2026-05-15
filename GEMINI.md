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
