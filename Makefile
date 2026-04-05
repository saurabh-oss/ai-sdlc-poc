# Makefile - AI-SDLC PoC Developer Shortcuts
# Usage: make <target>

PYTHON = .venv/Scripts/python.exe
BRANCH := $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)

.PHONY: help install lint test test-cov clean up down logs policy-check review

# -- Default ---------------------------------------------------
help:
	@echo ""
	@echo "  AI-Governed SDLC - Developer Commands"
	@echo "  ======================================="
	@echo "  make install        Install all Python dependencies"
	@echo "  make up             Start all Docker services"
	@echo "  make down           Stop all Docker services"
	@echo "  make logs           Tail all service logs"
	@echo "  make lint           Run flake8 + mypy"
	@echo "  make test           Run pytest"
	@echo "  make test-cov       Run pytest with coverage report"
	@echo "  make policy-check   Run AI policy compliance check"
	@echo "  make secret-scan    Run Trufflehog secret scan"
	@echo "  make sast           Run Semgrep SAST scan"
	@echo "  make review         Run AI code review agent"
	@echo "  make gen-tests      Run AI test generation agent"
	@echo "  make clean          Remove build artifacts"
	@echo ""

# -- Setup -----------------------------------------------------
install:
	pip install poetry
	poetry install
	poetry run pre-commit install

# -- Docker ----------------------------------------------------
up:
	docker compose up -d
	@echo ""
	@echo "  Services available:"
	@echo "  Gitea:      http://localhost:3000"
	@echo "  Jenkins:    http://localhost:8080"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana:    http://localhost:3001"
	@echo "  Pushgw:     http://localhost:9091"
	@echo ""

down:
	docker compose down

logs:
	docker compose logs -f --tail=50

# -- Quality Gates (mirrors Jenkins pipeline) ------------------
lint:
	poetry run flake8 app/ --max-line-length=120
	poetry run mypy app/ --ignore-missing-imports

test:
	poetry run pytest app/tests/ -v

test-cov:
	poetry run pytest app/tests/ \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=html:reports/htmlcov \
		--junit-xml=reports/junit.xml
	@echo "Coverage report: reports/htmlcov/index.html"

policy-check:
	$(PYTHON) scripts/ai_policy_check.py --branch HEAD

secret-scan:
	@if not exist reports mkdir reports
	poetry run detect-secrets scan \
		--exclude-files '\.env\.example$$' \
		--exclude-files '\.secrets\.baseline$$' \
		> reports/secrets.json 2>/dev/null || true
	$(PYTHON) scripts/count_secrets.py

sast:
	@if not exist reports mkdir reports
	semgrep --config "p/python" --config "p/owasp-top-ten" --json --output reports/semgrep.json app/
	$(PYTHON) scripts/parse_semgrep.py

# -- AI Agents -------------------------------------------------
review:
	@if not exist reports mkdir reports
	$(PYTHON) agents/code_review_agent.py \
		--branch $(BRANCH) \
		--output reports/ai-review.md \
		--score-file reports/ai-score.txt
	@cat reports/ai-review.md

gen-tests:
	$(PYTHON) agents/test_gen_agent.py \
		--source app/src/ \
		--output app/tests/generated/

arch-review:
	$(PYTHON) agents/arch_review_agent.py \
		--output reports/arch-review.md
	@cat reports/arch-review.md

# -- Cleanup ---------------------------------------------------
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .coverage dist build reports/htmlcov
	@echo "Clean done"
