# Brew Brain Development Guidelines

These core principles must be strictly adhered to by the AI coding agent and human architects during the development of Brew Brain.

## 1. Consistent Code Formatting & Automated Linting
Consistency is vital. Use `black` and `flake8` for Python (Flask backend) and `prettier` for Next.js (Web UI). 

## 2. Self-Documenting Code (DRY & Descriptive Naming)
Prioritize readable code over excessive comments. Avoid cryptic abbreviations. Adhere to the DRY (Don't Repeat Yourself) principle.

## 3. Documentation-as-Code
Keep documentation in the same repository as the code (`/docs`). Outdated documentation is worse than no documentation—include documentation review in all PRs.

## 4. Comprehensive Project & API Documentation
*   **README.md**, **Docstrings**, **API Documentation**, and **Architectural Documentation**.
*   **Release Notes & End-to-End User Guide:** Every deployment MUST be accompanied by updated release notes and a living user guide explaining the *why* behind the design.

## 5. The "Why" Over "What" (Meaningful Comments)
Code explains *how*; comments should explain the *why* or intent behind complex logic. 

## 6. Proper Error Handling
Handle exceptions gracefully. Provide informative error messages and logging. Avoid empty catch blocks.

## 7. Efficient Use of Data Structures and Algorithms
Optimize for efficiency, especially given the edge-computing target (Raspberry Pi). Profiling and benchmarking code can help identify performance bottlenecks.

## 8. Version Control and Collaboration
Commit often. Write meaningful commit messages. Use strict code review practices.

## 9. Security Best Practices (The CISO Gate)
Sanitize user input, avoid hardcoding secrets, apply RBAC. Keep dependencies updated. This aligns directly with the "CISO Gate" requirements in our CI/CD pipeline.

## 10. Code Testing & Refactoring
Write unit, integration, and e2e tests. Periodically refactor code to improve its structure and adhere to the Single Responsibility Principle (SRP).
