# STEP-BY-STEP SETUP GUIDE
# AI-Governed SDLC — Proof of Concept
# ============================================================
# Audience : Engineering Directors, Architects, Senior Developers
# Platform : Windows 10/11 (WSL2 + Docker Desktop)
# Est. Time : 2–3 hours for full setup, 20 min for demo run
# ============================================================

=======================================================================
SECTION 0 — WHAT YOU ARE BUILDING
=======================================================================

This PoC creates a fully local, observable AI-assisted SDLC on your
Windows machine with the following components:

  COMPONENT              TOOL              PORT
  ─────────────────────────────────────────────
  Local Git Server       Gitea             3000
  CI/CD Pipeline         Jenkins (CasC)    8080
  Metrics Database       Prometheus        9090
  Log Aggregation        Loki              3100
  Observability UI       Grafana (3 dash)  3001
  Metrics Ingestion      Pushgateway       9091
  AI Tool - Dev 1        Claude Code       (CLI)
  AI Tool - Dev 2        Cursor AI         (GUI)
  AI Review Agent        CrewAI + Claude   (CLI)
  AI Test Agent          CrewAI + Claude   (CLI)

Data flow:
  Developer pushes code → Gitea webhook → Jenkins pipeline →
  detect-secrets + Semgrep SAST + AI Policy Check →
  pytest + coverage → Metrics pushed to Prometheus Pushgateway →
  Grafana shows 3 dashboards (SDLC, Adoption/ROI, Governance)
  AI agents run code review and generate tests via make targets


=======================================================================
NOTE ON PATHS
=======================================================================

All steps below use C:\demo\ai-sdlc-poc as the example project path.
Replace it with the actual folder where you placed the project.

  Example:  C:\demo\ai-sdlc-poc   or   C:\Users\you\projects\ai-sdlc-poc

Set a variable at the start of your session to keep things consistent:

  PowerShell:   $PROJECT = "C:\demo\ai-sdlc-poc"
  Git Bash:     PROJECT="C:/demo/ai-sdlc-poc"

Then substitute $PROJECT wherever the steps show C:\demo\ai-sdlc-poc.


=======================================================================
SECTION 1 — SYSTEM SETUP  (one-time per machine, requires Admin)
=======================================================================

These steps install tools at the machine level. You only need to run
them once. They are not tied to any specific project folder.

STEP 1.1 — Open PowerShell as Administrator
─────────────────────────────────────────────
Right-click the Start button → "Windows PowerShell (Admin)"
Or search "PowerShell" → Right-click → "Run as administrator"


STEP 1.2 — Run the automated setup script
──────────────────────────────────────────
Navigate to the project folder and run:

  Set-ExecutionPolicy Bypass -Scope Process -Force
  .\scripts\setup_dev_environment.ps1 -AnthropicApiKey "sk-ant-YOUR-KEY"

  ▶ Replace sk-ant-YOUR-KEY with your real key from https://console.anthropic.com
  ▶ This installs: Chocolatey, Git, Node.js, Python 3.11, Docker Desktop,
    VS Code, Java 11, Claude Code CLI, Poetry, Semgrep, detect-secrets

  If you prefer manual installation, install each tool below:

  choco install git -y
  choco install nodejs-lts -y
  choco install python311 -y
  choco install docker-desktop -y
  choco install vscode -y
  choco install openjdk11 -y
  npm install -g @anthropic-ai/claude-code
  pip install poetry semgrep detect-secrets pre-commit


STEP 1.3 — Install Cursor AI (manual)
───────────────────────────────────────
  1. Go to https://cursor.sh
  2. Click Download for Windows
  3. Run the installer (CursorSetup.exe)
  4. After install, open Cursor and sign in or skip
  NOTE: Cursor is a full IDE, not a CLI tool


STEP 1.4 — Configure Docker Desktop
─────────────────────────────────────
  1. Launch Docker Desktop from the Start Menu
  2. Wait for it to fully start (whale icon in system tray turns solid)
  3. Click the gear icon (Settings)
  4. General → Check "Use the WSL 2 based engine"
  5. Resources → WSL Integration → Enable integration with your distro
  6. Click "Apply & Restart"
  7. Verify: open a new PowerShell and run:
       docker run hello-world
     You should see "Hello from Docker!"


STEP 1.5 — Set your Anthropic API Key permanently
───────────────────────────────────────────────────
  In PowerShell (not as admin needed):

  [System.Environment]::SetEnvironmentVariable(
    "ANTHROPIC_API_KEY",
    "sk-ant-YOUR-KEY-HERE",
    "User"
  )

  Close and reopen PowerShell for it to take effect.
  Verify: echo $env:ANTHROPIC_API_KEY


=======================================================================
SECTION 2 — PROJECT SETUP  (run inside the project folder)
=======================================================================

These steps are per-project. Run them from within the project folder.
Sections 3 onwards also belong to project setup.

STEP 2.1 — Place the project
──────────────────────────────────────────
  1. Copy or move the ai-sdlc-poc folder to your preferred location.
       Recommended: C:\demo\ai-sdlc-poc
       (Any path works — just be consistent throughout all later steps)
  2. Open PowerShell and navigate there:
       cd C:\demo\ai-sdlc-poc    # replace with your actual path


STEP 2.2 — Install Python dependencies
────────────────────────────────────────
  cd C:\demo\ai-sdlc-poc    # replace with your actual path
  python -m poetry install

  IMPORTANT — this requires two machine-level settings to be correct:

  a) REQUESTS_CA_BUNDLE must point to the certifi bundle.
     Set it once permanently (run this in PowerShell, not as admin):

       [System.Environment]::SetEnvironmentVariable(
         "REQUESTS_CA_BUNDLE",
         "C:\Python311\Lib\site-packages\certifi\cacert.pem",
         "User"
       )

     Close and reopen PowerShell, then retry poetry install.

  b) pyproject.toml python constraint must allow your installed Python.
     If you have Python 3.14 as your system default and see:
       "Current Python version (X.Y) is not allowed by the project"
     Edit pyproject.toml line:
       python = ">=3.11,<3.15"
     Poetry will then use the .venv (Python 3.11) inside the project.

  This installs all packages from pyproject.toml including:
  FastAPI, CrewAI, Anthropic SDK, pytest, semgrep, pre-commit, etc.

  Verify: poetry run pytest app/tests/ -v
  Expected: All tests pass (4-5 tests in test_main.py)


STEP 2.3 — Set up the .env file
─────────────────────────────────
  copy .env.example .env
  notepad .env

  Update at minimum:
    ANTHROPIC_API_KEY=sk-ant-YOUR-REAL-KEY


=======================================================================
SECTION 3 — START ALL DOCKER SERVICES
=======================================================================

STEP 3.1 — Start the stack
────────────────────────────
  cd C:\demo\ai-sdlc-poc
  docker compose up -d

  First run downloads images (~2-3 GB total). Takes 3-5 minutes.
  Subsequent starts take ~30 seconds.


STEP 3.2 — Verify all services are running
────────────────────────────────────────────
  docker compose ps

  You should see STATUS = "Up" for all of:
    gitea-server
    jenkins-server
    prometheus
    loki
    promtail
    grafana
    pushgateway


STEP 3.3 — Check service URLs
───────────────────────────────
  Open a browser and verify each:

  http://localhost:3000   → Gitea  (shows "Sign In" page)
  http://localhost:8080   → Jenkins (shows setup or dashboard)
  http://localhost:9090   → Prometheus (shows graph UI)
  http://localhost:3001   → Grafana (shows login: admin/admin)
  http://localhost:9091   → Pushgateway (shows metrics page)


=======================================================================
SECTION 4 — CONFIGURE GITEA (Local Git Server)
=======================================================================

STEP 4.1 — Initial Gitea setup
────────────────────────────────
  1. Open http://localhost:3000
  2. You will see the Installation page on first visit
  3. Fill in:
       Database Type   : SQLite3
       Site Title      : AI SDLC PoC
       Admin Username  : gitadmin
       Admin Password  : Admin@1234!
       Admin Email     : admin@company.local
  4. Click "Install Gitea"
  5. You will be redirected to the dashboard


STEP 4.2 — Create Organization and Repository
───────────────────────────────────────────────
  1. Click the "+" icon top right → New Organization
       Organization Name: ai-sdlc-poc
       Visibility: Private
     Click "Create Organization"

  2. Inside the org, click "New Repository"
       Repository Name: app-repo
       Visibility: Private
       Initialize: ✓ (check "Initialize this repository")
     Click "Create Repository"


STEP 4.3 — Create developer accounts
───────────────────────────────────────
  1. Click top-right avatar → Site Administration
  2. User Accounts → Create User Account
       Username: dev1
       Email: dev1@company.local
       Password: Dev1Pass!
       Uncheck "require password change"
     Save

  3. Create another user:
       Username: dev2
       Email: dev2@company.local
       Password: Dev2Pass!
     Save

  4. Add both to the organization:
     Go to http://localhost:3000/org/ai-sdlc-poc/teams
     Create team "developers" with Repository permissions: Write
     Add dev1 and dev2 to the team
     Add the app-repo repository to the team


STEP 4.4 — Push the project code to Gitea
───────────────────────────────────────────
  Open Git Bash (installed with Git) or PowerShell:

  cd C:\demo\ai-sdlc-poc

  # If the folder does not yet have a git repo:
  git init
  git add .
  git commit -m "chore: initial project setup"

  # If it already has a git repo (e.g. cloned or copied with .git folder):
  # Skip the three lines above — just add the remote below.

  git remote add origin http://localhost:3000/ai-sdlc-poc/app-repo.git
  git push -u origin main

  When prompted, use credentials: gitadmin / Admin@1234!


STEP 4.5 — Create branches
────────────────────────────
  git checkout -b develop
  git push origin develop

  git checkout -b feat/dev1-auth-module
  git push origin feat/dev1-auth-module

  git checkout develop
  git checkout -b feat/dev2-payment-module
  git push origin feat/dev2-payment-module
  git checkout develop


STEP 4.6 — Set up Git Worktrees (simulate 2 developers)
─────────────────────────────────────────────────────────
  cd C:\demo\ai-sdlc-poc

  git worktree add ..\workspace-dev1 feat/dev1-auth-module
  git worktree add ..\workspace-dev2 feat/dev2-payment-module

  # Set Developer 1 identity
  cd ..\workspace-dev1
  git config user.name "Dev One (Claude Code)"
  git config user.email "dev1@company.local"

  # Copy Claude AI configs into Dev 1's workspace
  xcopy ..\ai-sdlc-poc\ai-configs\claude\CLAUDE.md .\ /Y
  xcopy "..\ai-sdlc-poc\ai-configs\claude\.claudeignore" .\ /Y
  xcopy "..\ai-sdlc-poc\ai-configs\claude\settings.json" .claude\ /Y /I

  # Set Developer 2 identity
  cd ..\workspace-dev2
  git config user.name "Dev Two (Cursor AI)"
  git config user.email "dev2@company.local"

  # Copy Cursor AI configs into Dev 2's workspace
  xcopy "..\ai-sdlc-poc\ai-configs\cursor\.cursorrules" .\ /Y
  xcopy "..\ai-sdlc-poc\ai-configs\cursor\.cursorignore" .\ /Y


STEP 4.7 — Add Gitea Webhook (triggers Jenkins on push)
─────────────────────────────────────────────────────────
  1. Go to http://localhost:3000/ai-sdlc-poc/app-repo/settings/hooks
  2. Click "Add Webhook" → Gitea
  3. Fill in:
       Target URL   : http://jenkins-server:8080/gitea-webhook/post
       HTTP Method  : POST
       Content Type : application/json
       Secret       : jenkins-webhook-secret
       Trigger On   : Push Events, Pull Request Events
  4. Click "Add Webhook"
  5. Click "Test Delivery" to verify it reaches Jenkins


=======================================================================
SECTION 5 — CONFIGURE JENKINS
=======================================================================

Jenkins uses Configuration as Code (CasC). Most setup is AUTOMATIC.
The jenkins/casc.yaml file provisions users, credentials, and settings
on first start. No setup wizard appears.

  Auto-provisioned users:
    admin / admin123   (full access)
    dev1  / dev1pass
    dev2  / dev2pass

  Auto-provisioned credentials:
    gitea-admin        → gitadmin / Admin@1234!
    anthropic-api-key  → reads ANTHROPIC_API_KEY from docker-compose env
    pushgateway-url    → http://pushgateway:9091


STEP 5.1 — Verify Jenkins started correctly
─────────────────────────────────────────────
  1. Open http://localhost:8080
  2. Log in: admin / admin123
  3. If plugins are still installing, wait ~3-4 minutes then refresh

  Plugins installed automatically from jenkins/plugins.txt:
    workflow-aggregator, git, gitea, prometheus, pipeline-stage-view,
    configuration-as-code, generic-webhook-trigger, ws-cleanup, etc.


STEP 5.2 — Create the Pipeline Job (one-time manual step)
───────────────────────────────────────────────────────────
  1. Dashboard → New Item
  2. Name: ai-sdlc-pipeline
  3. Type: Pipeline → OK
  4. In the job configuration:

     General:
       ✓ Discard old builds → Max # builds to keep: 50

     Pipeline:
       Definition : Pipeline script from SCM
       SCM        : Git
       Repository URL: http://gitea-server:3000/ai-sdlc-poc/app-repo.git
       Credentials: gitea-admin
       Branch     : */feat/* */develop */main
       Script Path: Jenkinsfile

  5. Click Save
  6. Click "Build Now" once to verify the pipeline runs

  The pipeline runs 6 stages:
    1. Checkout          — clone repo, create reports/ dir
    2. Secret Scan       — detect-secrets with baseline comparison
    3. SAST              — Semgrep with python + owasp-top-ten rules
    4. AI Policy Check   — validates AI guardrail compliance
    5. Tests             — pytest with coverage (XML + HTML)
    6. Push Metrics      — sends all metrics to Prometheus Pushgateway


STEP 5.3 — Troubleshoot: CasC not applied
───────────────────────────────────────────
  If Jenkins still shows the setup wizard:
    docker compose down jenkins-server
    docker compose up -d jenkins-server
    docker compose logs jenkins-server | grep -i casc

  Verify CASC_JENKINS_CONFIG is set:
    docker exec jenkins-server env | grep CASC


=======================================================================
SECTION 6 — CONFIGURE GRAFANA DASHBOARD
=======================================================================

STEP 6.1 — Log in
───────────────────
  Open http://localhost:3001
  Username: admin  Password: admin
  Click "Skip" when prompted to change password (or change it)


STEP 6.2 — Verify datasources (auto-provisioned)
──────────────────────────────────────────────────
  Configuration (gear icon) → Data Sources
  You should already see:
    ✓ Prometheus (http://prometheus:9090) — green checkmark
    ✓ Loki       (http://loki:3100)      — green checkmark

  If not, click "Add data source" and add them manually with those URLs.


STEP 6.3 — Verify auto-provisioned dashboards
──────────────────────────────────────────────
  Dashboards are provisioned automatically from grafana/dashboards/.
  Click the grid icon (Dashboards) → Browse to find them.

  Three dashboards are included:

  1. AI SDLC Dashboard (ai-sdlc-dashboard.json)
     • AI Review Score gauge
     • Test Coverage gauge
     • Secret Leak Attempts (red counter)
     • SAST Findings by severity
     • Pipeline duration over time
     • AI vs Human commit ratio
     • Per-developer build history

  2. Adoption & ROI Dashboard (adoption-roi-dashboard.json)
     • AI tool usage by developer and tool type
     • Suggestions accepted vs rejected trend
     • Estimated time savings and ROI metrics

  3. Governance & Compliance Dashboard (governance-compliance-dashboard.json)
     • Policy violation counts and trends
     • Guardrail enforcement heatmap
     • AI audit trail events

  If dashboards don't appear automatically, import manually:
    Dashboards → Import → Upload JSON file for each


STEP 6.4 — Seed demo data (optional)
───────────────────────────────────────
  To populate Grafana with historical demo data before a live demo:

  poetry run python scripts/seed_demo_data.py

  This pushes a set of simulated historical metrics to the Pushgateway
  so all dashboard panels show populated charts immediately.


=======================================================================
SECTION 7 — COPY AI CONFIGS INTO DEVELOPER WORKSPACES
=======================================================================

STEP 7.1 — Developer 1 workspace (Claude Code)
────────────────────────────────────────────────
  The CLAUDE.md file is the primary guardrail for Claude Code.
  It must be in the ROOT of the workspace Claude Code opens.

  cd C:\demo\workspace-dev1

  Copy these files here:
    CLAUDE.md           ← Claude reads this on startup
    .claudeignore       ← Files Claude must not access

  The settings.json goes into the .claude/ subfolder:
    mkdir .claude
    copy ..\ai-sdlc-poc\ai-configs\claude\settings.json .claude\settings.json

  To use Claude Code in this workspace:
    claude                        ← starts interactive session
    claude "add input validation to the auth module"
    claude --print "review this file for security issues"


STEP 7.2 — Developer 2 workspace (Cursor AI)
─────────────────────────────────────────────
  The .cursorrules file is read by Cursor automatically
  when it is in the root of the open folder.

  cd C:\demo\workspace-dev2

  Files needed:
    .cursorrules       ← Cursor reads this on every prompt
    .cursorignore      ← Files Cursor won't index

  To use Cursor in this workspace:
    1. Open Cursor AI application
    2. File → Open Folder → select C:\demo\workspace-dev2
    3. Cursor will automatically pick up .cursorrules
    4. Open the AI chat panel (Ctrl+L) and start coding


=======================================================================
SECTION 8 — END-TO-END DEMO WALKTHROUGH
=======================================================================

This walks through a complete demonstration scenario from code change
to Grafana dashboard update.

DEMO A — Blocked commit (secret in code)
─────────────────────────────────────────
  cd C:\demo\workspace-dev1

  # Simulate a developer accidentally hardcoding a secret
  echo 'DB_PASSWORD = "super-secret-password-123"' >> app\src\main.py

  git add .
  git commit -m "feat: add database connection"
  git push origin feat/dev1-auth-module

  EXPECTED RESULT:
    Jenkins pipeline triggers via webhook
    Stage "Secret Scan" → detect-secrets detects hardcoded password
    Pipeline FAILS and blocks the merge
    Metric secret_leak_attempts_total increments in Grafana
    Build marked RED in Jenkins


DEMO B — Compliant commit (passes all gates)
─────────────────────────────────────────────
  # Revert the bad change
  git checkout app\src\main.py

  # Make a proper compliant change using Claude Code
  cd C:\demo\workspace-dev1
  claude "add a GET /api/v1/tasks/stats endpoint that returns count by status.
          Follow the existing patterns, use proper type hints, add docstring,
          do not use print(), use logging instead. Tag as AI-ASSISTED."

  # Review what Claude generated, then commit
  git add .
  git commit -m "feat: add task statistics endpoint"
  git push origin feat/dev1-auth-module

  EXPECTED RESULT:
    All pipeline stages pass (green)
    AI Agent Code Review runs and posts score to Grafana
    Test coverage metric updates
    Pipeline duration metric visible in Grafana


DEMO C — Run AI agents manually
─────────────────────────────────
  cd C:\demo\ai-sdlc-poc

  # Code review agent
  make review
  # Output: reports/ai-review.md with score

  # Test generation agent
  make gen-tests
  # Output: app/tests/generated/test_main_generated.py

  # Architecture review agent
  make arch-review
  # Output: reports/arch-review.md


DEMO D — View everything in Grafana
─────────────────────────────────────
  Open http://localhost:3001
  Navigate to Dashboards → Browse

  After running the demos above you will see in the AI SDLC Dashboard:
    • AI Review Score: numeric gauge (0-100)
    • Test Coverage: gauge with red/yellow/green thresholds
    • Secret Leak Attempts: should show 1 from Demo A
    • SAST Findings: bar chart by severity
    • Pipeline Duration: time series chart
    • Build history table with developer and AI tool columns

  Also check:
    • Adoption & ROI Dashboard for tool usage trends
    • Governance & Compliance Dashboard for policy violation counts

  To pre-populate with historical demo data:
    poetry run python scripts/seed_demo_data.py


=======================================================================
SECTION 9 — RUNNING THE AI AGENTS STANDALONE
=======================================================================

All agents require ANTHROPIC_API_KEY to be set.

Code Review Agent:
  poetry run python agents/code_review_agent.py \
    --branch feat/dev1-auth-module \
    --output reports/review.md \
    --score-file reports/score.txt

  cat reports/review.md

Test Generation Agent:
  poetry run python agents/test_gen_agent.py \
    --source app/src/ \
    --output app/tests/generated/

Architecture Review Agent:
  poetry run python agents/arch_review_agent.py \
    --output reports/arch-review.md

Push custom metrics manually:
  poetry run python scripts/metrics_exporter.py \
    --branch feat/dev1-auth-module \
    --developer "Dev One" \
    --ai-tool claude_code \
    --duration 45.2 \
    --coverage 82.5 \
    --success


=======================================================================
SECTION 10 — MAKE COMMAND REFERENCE
=======================================================================

  make install        Install all Python dependencies via Poetry + pre-commit
  make up             docker compose up -d (start all services)
  make down           docker compose down (stop all services)
  make logs           Tail all container logs
  make lint           Run flake8 + mypy on app/
  make test           Run pytest
  make test-cov       Run pytest with coverage (HTML report in reports/htmlcov)
  make policy-check   Run AI policy compliance check locally
  make secret-scan    Run detect-secrets locally (outputs reports/secrets.json)
  make sast           Run Semgrep SAST locally (outputs reports/semgrep.json)
  make review         Run AI code review agent on current branch
  make gen-tests      Run AI test generation agent
  make arch-review    Run AI architecture review agent
  make clean          Remove build artifacts and cache

  NOTE: make commands use .venv/Scripts/python.exe directly.
  Ensure you have run `make install` (or `poetry install`) first.


=======================================================================
SECTION 11 — TROUBLESHOOTING
=======================================================================

PROBLEM: docker compose up fails / containers exit immediately
  SOLUTION:
    docker compose logs <service-name>
    Most common cause: Docker Desktop not running or WSL2 not enabled
    Fix: Open Docker Desktop, wait for it to fully start, then retry

PROBLEM: Jenkins cannot connect to Gitea
  SOLUTION:
    Use container name "gitea-server" not "localhost" in Jenkins config
    Both are on the same Docker network (ai-sdlc-net)
    Verify: docker exec jenkins-server curl http://gitea-server:3000

PROBLEM: poetry install fails with "Application Control policy has blocked this file"
  SOLUTION:
    Windows AppLocker or WDAC is blocking poetry.exe directly.
    Run Poetry through the Python interpreter instead -- this bypasses
    the executable block since python.exe is on the allow-list:

      python -m poetry install

    All other poetry commands work the same way:
      python -m poetry run pytest
      python -m poetry run python agents/code_review_agent.py ...
      python -m poetry env info

    To avoid typing this every session, add an alias in your PowerShell profile:
      Add-Content $PROFILE "`nfunction poetry { python -m poetry @args }"


PROBLEM: poetry install fails with "All attempts to connect to pypi.org failed"
  NOTE: This error is misleading. The real cause is almost always one of:

  CAUSE A — Missing TLS certificate bundle (most common on Windows)
    Run poetry install with -vvv and look for:
      "Could not find a suitable TLS CA certificate bundle"
    Fix: set REQUESTS_CA_BUNDLE permanently in your user environment:

      [System.Environment]::SetEnvironmentVariable(
        "REQUESTS_CA_BUNDLE",
        "C:\Python311\Lib\site-packages\certifi\cacert.pem",
        "User"
      )

    Close and reopen PowerShell, then retry.

  CAUSE B — Python version mismatch
    Poetry runs under a newer Python (e.g. 3.14) but pyproject.toml
    caps at <=3.13. Fix: edit pyproject.toml and change:
      python = ">=3.11,<=3.13"
    to:
      python = ">=3.11,<3.15"
    The project .venv uses Python 3.11 and all dependencies still work.

  CAUSE C — Corrupt Poetry HTTP cache (Permission denied on cache files)
    Run poetry install -vvv and look for "[Errno 13] Permission denied"
    pointing to a path under AppData\Local\pypoetry\Cache.
    Fix: clear the cache
      poetry cache clear --all pypi
    Or delete the folder manually in Explorer and retry.

PROBLEM: semgrep pip install fails with PyYAML wheel build error
  ("'build_ext' object has no attribute 'cython_sources'")
  SOLUTION:
    This is a Cython/setuptools compatibility issue on Python 3.11+.
    Install PyYAML from a pre-built binary first, then semgrep:

      pip install PyYAML --only-binary :all:
      pip install semgrep --only-binary :all:

    The setup script (scripts/setup_dev_environment.ps1) already handles
    this automatically. Run it again if semgrep was not installed.

PROBLEM: Semgrep or detect-secrets not found in Jenkins container
  SOLUTION:
    The Jenkins Dockerfile installs both via pip.
    To reinstall manually:
    docker exec -u root jenkins-server pip3 install semgrep detect-secrets

PROBLEM: Anthropic API key errors in agents
  SOLUTION:
    Verify key is set: echo $env:ANTHROPIC_API_KEY (PowerShell)
    Key must start with sk-ant-
    Get a key at: https://console.anthropic.com

PROBLEM: Grafana shows "No data" on panels
  SOLUTION:
    Run at least one Jenkins build to push metrics
    Or push test metrics manually:
      poetry run python scripts/metrics_exporter.py --success --branch test
    Check Prometheus has data: http://localhost:9090/graph
      Query: pipeline_success_total

PROBLEM: pre-commit hooks fail on Windows
  SOLUTION:
    git config core.autocrlf false
    poetry run pre-commit install --install-hooks
    poetry run pre-commit run --all-files

PROBLEM: Claude Code cannot find CLAUDE.md
  SOLUTION:
    CLAUDE.md must be in the directory where you run `claude`
    cd C:\demo\workspace-dev1
    ls CLAUDE.md  ← should exist
    claude        ← now run it


=======================================================================
SECTION 12 — PROJECT FILE REFERENCE
=======================================================================

ai-sdlc-poc/
│
├── README.md                    Architecture overview + quick reference
├── STEP_BY_STEP_SETUP.md        This file
├── docker-compose.yml           All services definition
├── Jenkinsfile                  Full CI/CD pipeline (8 stages)
├── Makefile                     Developer shortcuts
├── pyproject.toml               Python dependencies (Poetry)
├── .env.example                 Environment variable template
├── .gitignore                   Git ignore rules
├── .pre-commit-config.yaml      Pre-commit hooks (secrets, lint, policy)
│
├── ai-configs/
│   ├── claude/
│   │   ├── CLAUDE.md            Claude Code guardrails (copy to workspace root)
│   │   ├── .claudeignore        Files Claude must not touch
│   │   └── settings.json        Claude Code permissions & audit config
│   └── cursor/
│       ├── .cursorrules         Cursor AI guardrails (copy to workspace root)
│       └── .cursorignore        Files Cursor must not index
│
├── app/
│   ├── src/
│   │   ├── __init__.py
│   │   └── main.py              FastAPI Task Management Service (sample app)
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py          Shared pytest fixtures
│       └── test_main.py         Full test suite for the sample app
│
├── agents/
│   ├── code_review_agent.py     CrewAI: Senior engineer + security reviewer
│   ├── test_gen_agent.py        CrewAI: QA engineer generating pytest tests
│   └── arch_review_agent.py     CrewAI: Architect reviewing design patterns
│
├── scripts/
│   ├── ai_policy_check.py       Jenkins stage: validates AI guardrail compliance
│   ├── parse_semgrep.py         Jenkins stage: parses Semgrep JSON output
│   ├── count_secrets.py         Jenkins stage: counts detect-secrets findings
│   ├── metrics_exporter.py      Pushes metrics to Prometheus Pushgateway
│   ├── ai_guardrail_audit.py    Full audit report of AI tool usage
│   ├── seed_demo_data.py        Populates Grafana with historical demo metrics
│   ├── setup_webhook_trigger.ps1 Automates Gitea webhook configuration
│   └── setup_dev_environment.ps1 Windows one-click bootstrap
│
├── jenkins/
│   ├── Dockerfile               Custom Jenkins image with Python + tools
│   ├── plugins.txt              Jenkins plugin list for auto-install
│   └── casc.yaml                Jenkins Configuration as Code (users, creds, settings)
│
├── monitoring/
│   ├── prometheus.yml           Prometheus scrape config
│   ├── loki/config.yml          Loki log aggregation config
│   └── promtail/config.yml      Promtail log shipper config (reads Jenkins logs)
│
├── grafana/
│   ├── dashboards/
│   │   ├── ai-sdlc-dashboard.json          Main SDLC health dashboard
│   │   ├── adoption-roi-dashboard.json     AI tool adoption & ROI metrics
│   │   └── governance-compliance-dashboard.json  Policy & audit dashboard
│   └── provisioning/
│       ├── dashboards/dashboards.yml
│       └── datasources/datasources.yml  Auto-provisions Prometheus + Loki
│
└── reports/
    └── .gitkeep                 Placeholder — runtime reports go here


=======================================================================
END OF SETUP GUIDE
=======================================================================
