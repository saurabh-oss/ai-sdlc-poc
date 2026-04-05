# AI-Governed SDLC — Proof of Concept

> **Audience:** Engineering Directors, Architects, Senior Developers  
> **Purpose:** Demonstrate a fully observable, AI-assisted Software Development Lifecycle with guardrails, automated quality gates, responsible AI metrics, and agentic developer/tester/reviewer roles — all running locally on Windows.

---

## 🏛 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     LOCAL WINDOWS WORKSTATION                        │
│                                                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────────┐   │
│  │  DEV-1       │    │  DEV-2       │    │   GITEA (Local Git) │   │
│  │  Claude Code │───▶│  Cursor AI   │───▶│   + Webhooks        │   │
│  │  Branch:     │    │  Branch:     │    └────────┬────────────┘   │
│  │  feat/dev1-* │    │  feat/dev2-* │             │                  │
│  └──────────────┘    └──────────────┘             ▼                  │
│                                          ┌─────────────────────┐   │
│  AI Config Files:                        │   JENKINS (CasC)    │   │
│  • CLAUDE.md    (guardrails)             │   Pipeline          │   │
│  • .cursorrules (guardrails)             │   • detect-secrets  │   │
│  • .claudeignore                         │   • Semgrep SAST    │   │
│  • .cursorignore                         │   • AI Policy Check │   │
│                                          │   • pytest + cov    │   │
│                                          │   • Push Metrics    │   │
│                                          └────────┬────────────┘   │
│                                                   │                  │
│                                          ┌────────▼────────────┐   │
│                                          │   OBSERVABILITY     │   │
│                                          │   Prometheus        │   │
│                                          │   Loki (Logs)       │   │
│                                          │   Grafana (3 dashboards)│ │
│                                          └─────────────────────┘   │
│                                                                       │
│  AI AGENTS (CrewAI):                                                 │
│  Code Review Agent | Test Gen Agent | Architecture Review Agent      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Business Value

| Capability | Business Outcome |
|---|---|
| AI Guardrail Configs | Reduces IP/data leakage risk; enforces standards before commit |
| Jenkins AI Policy Gate | Automated compliance — zero manual gatekeeping overhead |
| Responsible AI Metrics | Audit-ready trail of every AI-assisted change |
| AI Code Review Agent | 10x faster PR reviews; consistent quality bar |
| AI Test Generation | 60–80% test coverage achieved automatically |
| Grafana SDLC Dashboards | 3 dashboards: SDLC health, adoption/ROI, and governance/compliance |
| Jenkins Config as Code | Zero-click Jenkins provisioning via `casc.yaml` |
| Full Local Stack | Zero cloud cost for PoC; data stays on-premises |

---

## 🚀 Setup

Full setup instructions are in [STEP_BY_STEP_SETUP.md](STEP_BY_STEP_SETUP.md), organized into two phases:

**Phase 1 — System Setup** *(one-time per machine, requires Admin)*: installs Chocolatey, Git, Python 3.11, Docker Desktop, VS Code, Java 11, Claude Code CLI, Poetry, Semgrep, detect-secrets, and Cursor AI.

**Phase 2 — Project Setup** *(run from inside the project folder)*: `poetry install`, `.env` config, `docker compose up`, Gitea/Jenkins/Grafana configuration, and worktree setup for the two simulated developers.

> **Quick start** (after system setup is complete):
> ```powershell
> cd <your-project-folder>
> poetry install
> docker compose up -d
> ```

---

## ⚙️ Services

| Service | URL | Default Credentials |
|---|---|---|
| Gitea (Git Server) | http://localhost:3000 | Setup on first visit |
| Jenkins | http://localhost:8080 | admin / admin123 (via CasC) |
| Prometheus | http://localhost:9090 | None |
| Loki | http://localhost:3100 | None |
| Grafana | http://localhost:3001 | admin / admin |

---

## ⚙️ STEP — Load Grafana Dashboards

1. Browse to http://localhost:3001, log in (admin/admin)
2. Datasources are auto-provisioned — verify under Configuration → Data Sources
3. Dashboards are also auto-provisioned from `grafana/dashboards/`. Three dashboards are included:
   - **AI SDLC Dashboard** — pipeline health, SAST findings, secret leaks, test coverage
   - **Adoption & ROI Dashboard** — AI tool usage trends and developer adoption metrics
   - **Governance & Compliance Dashboard** — policy violations, guardrail enforcement, audit trail
4. If dashboards don't appear, manually import via Dashboards → Import → Upload JSON for each file in `grafana/dashboards/`

---

## 🤖 STEP 8 — Using the AI Agents

```bash
# Run code review agent on a branch
poetry run python agents/code_review_agent.py \
  --branch feat/dev1-auth-module \
  --output reports/review-dev1.md

# Run test generation agent
poetry run python agents/test_gen_agent.py \
  --source app/src/ \
  --output app/tests/generated/

# Run architecture review
poetry run python agents/arch_review_agent.py \
  --readme README.md \
  --output reports/arch-review.md
```

---

## 🔄 STEP 9 — End-to-End Flow Demo

```bash
# 1. Developer 1 makes a change (in workspace-dev1)
cd ../workspace-dev1
# Edit app/src/main.py — try committing a hardcoded secret to see guardrail trigger
echo 'DB_PASSWORD = "super-secret-password-123"' >> app/src/main.py
git add . && git commit -m "feat: add database connection"
git push origin feat/dev1-auth-module
# → Jenkins triggers, detect-secrets detects hardcoded password, pipeline BLOCKS
# → secret_leak_attempts_total metric increments in Grafana

# 2. Fix and comply
git checkout app/src/main.py   # revert the bad change
# Make a compliant change using Claude Code
claude "add a GET /api/v1/tasks/stats endpoint that returns count by status.
        Follow existing patterns, use type hints, docstring, logging. Tag as AI-ASSISTED."
git add . && git commit -m "feat: add task statistics endpoint"
git push origin feat/dev1-auth-module
# → All 6 pipeline stages pass (green)
# → Metrics pushed to Prometheus, Grafana dashboards update in real-time

# 3. Seed demo data for Grafana (optional, simulates historical metrics)
poetry run python scripts/seed_demo_data.py
```

---

## 📊 Responsible AI Metrics

| Metric | Description |
|---|---|
| `ai_suggestions_accepted_total` | AI suggestions merged to repo |
| `ai_suggestions_rejected_total` | AI suggestions discarded |
| `ai_policy_violations_total` | Guardrail config triggers |
| `sast_findings_total{severity}` | SAST findings by severity (high/medium/low) |
| `secret_leak_attempts_total` | detect-secrets findings in pipeline |
| `test_coverage_percent` | Coverage percentage from pytest-cov |
| `ai_agent_review_score` | 0–100 score from AI code review agent |
| `pipeline_duration_seconds` | End-to-end pipeline time |
| `pipeline_success_total` | Count of successful pipeline runs |

All metrics flow: Jenkins → Prometheus Pushgateway (`:9091`) → Prometheus (`:9090`) → Grafana (`:3001`)

View all three dashboards at http://localhost:3001
