# CLAUDE.md — AI Coding Guardrails for Developer 1
# This file is read by Claude Code before every session.
# It defines the rules, boundaries, and standards that Claude MUST follow in this repository.

## 🔐 SECURITY GUARDRAILS (Non-Negotiable)

### Secrets & Credentials
- NEVER generate, suggest, or include hardcoded secrets, API keys, passwords, tokens, or credentials in any file
- ALWAYS use environment variables: `os.getenv("KEY_NAME")` or config management (Vault, .env files gitignored)
- If you see an existing hardcoded secret, flag it immediately and suggest remediation
- NEVER commit .env files — only .env.example with placeholder values

### Data Handling
- NEVER send, log, or expose PII (names, emails, SSNs, payment data) in plain text
- Mask or redact sensitive fields in all logging statements
- Use parameterized queries — NEVER construct SQL via string concatenation
- ALWAYS validate and sanitize all external inputs

### Network & Infrastructure
- NEVER disable TLS/SSL verification
- NEVER expose internal ports unnecessarily in Docker configs
- NEVER use `0.0.0.0` bindings in production configs without explicit approval

---

## 📏 CODING STANDARDS

### Language: Python (primary)
- Follow PEP 8 strictly
- Use type hints on all function signatures
- Maximum function length: 50 lines
- Maximum file length: 300 lines
- Docstrings required on all public functions and classes (Google style)

### General
- No commented-out dead code in commits
- No `print()` statements — use `logging` module with appropriate levels
- All exceptions must be caught specifically — no bare `except:` clauses
- Use dependency injection over global state

### Naming Conventions
- Variables/functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_prefixed`

---

## 🏗 ARCHITECTURE GUIDELINES

- Follow the existing layered architecture: `api/ → service/ → repository/ → models/`
- Do NOT introduce new external dependencies without adding to `pyproject.toml` and documenting rationale
- All new API endpoints MUST have:
  - Input validation (Pydantic models)
  - Authentication check
  - Rate limiting consideration
  - Error handling with appropriate HTTP status codes
- Database changes require a migration script — do not alter schemas directly

---

## 🧪 TESTING REQUIREMENTS

- Every new function/method MUST have at least one unit test
- Tests go in `app/tests/` mirroring the source structure
- Use `pytest` and `pytest-mock`
- Aim for >80% coverage on new code
- No mocking of the system under test — mock only external dependencies

---

## 📋 COMMIT & PR STANDARDS

- Commit messages MUST follow Conventional Commits:
  - `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `ci:`
- Every commit pushed should pass `pre-commit` hooks locally
- PR descriptions must include: **What changed**, **Why**, **How tested**
- Do NOT force-push to `develop` or `main`

---

## 🚫 PROHIBITED ACTIONS

Claude MUST NOT:
1. Modify files listed in `.claudeignore`
2. Delete or overwrite `Jenkinsfile`, `docker-compose.yml`, or any monitoring config
3. Install system packages or run `sudo` commands
4. Access or modify other developers' worktrees or branches
5. Generate code that phones home or collects telemetry without consent
6. Suggest disabling security scans or pipeline gates
7. Access `.git/` internals directly

---

## 📊 AI USAGE TRACKING

When Claude Code generates or significantly modifies code, add a comment block:
```python
# AI-ASSISTED: Claude Code | Date: YYYY-MM-DD | Reviewed: [yes/no]
```
This enables the Responsible AI metrics pipeline to track AI contribution ratios.

---

## 🔄 WORKFLOW

1. Always start by reading relevant existing code before generating new code
2. Prefer modifying existing patterns over introducing new ones
3. Run `make lint` and `make test` mentally before suggesting code
4. If unsure about a requirement, ask — do not assume and generate

---
*These guidelines are enforced both by Claude Code's behavior and validated by the Jenkins pipeline.*
