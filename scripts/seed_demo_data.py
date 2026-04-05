#!/usr/bin/env python3
"""
seed_demo_data.py - Seed realistic dummy data into Prometheus Pushgateway and Loki.

Populates three Grafana dashboards:
  1. AI-Augmented SDLC (existing)  - CI/CD pipeline & responsible-AI metrics
  2. AI Governance & Compliance    - rule adherence, code quality, lifecycle, security
  3. AI Adoption & ROI             - token usage, cost, productivity, ROI

Usage:
    python scripts/seed_demo_data.py              # one round, all dashboards
    python scripts/seed_demo_data.py --loop       # keep pushing for 5 min (time-series)
    python scripts/seed_demo_data.py --loop --duration 600
    PUSHGATEWAY_URL=http://... LOKI_URL=http://... python scripts/seed_demo_data.py
"""

import argparse
import json
import os
import random
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

PUSHGATEWAY_URL = os.getenv("PUSHGATEWAY_URL", "http://localhost:9091")
LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100")
JOB_NAME = "ai_sdlc_metrics"

random.seed(42)


# ---------------------------------------------------------------------------
# Push helpers
# ---------------------------------------------------------------------------

@dataclass
class MetricSet:
    labels: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)

    def to_prometheus_text(self) -> str:
        label_str = ",".join(f'{k}="{v}"' for k, v in self.labels.items())
        lines = []
        for name, value in self.metrics.items():
            if label_str:
                lines.append(f'{name}{{{label_str}}} {value}')
            else:
                lines.append(f'{name} {value}')
        return "\n".join(lines) + "\n"


def _http_push(url: str, text: str, label: str) -> bool:
    try:
        req = urllib.request.Request(
            url, data=text.encode("utf-8"), method="POST",
            headers={"Content-Type": "text/plain"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            ok = resp.status == 200
            print(f"  {'[OK]' if ok else '[!!]'} {label}: HTTP {resp.status}")
            return ok
    except Exception as exc:
        print(f"  [XX] {label}: {exc}", file=sys.stderr)
        return False


def push_metrics(metric_set: MetricSet, instance: str) -> bool:
    url = f"{PUSHGATEWAY_URL}/metrics/job/{JOB_NAME}/instance/{instance}"
    return _http_push(url, metric_set.to_prometheus_text(), instance)


def push_text(text: str, instance: str) -> bool:
    """Push raw Prometheus exposition text (supports multiple label sets per metric)."""
    url = f"{PUSHGATEWAY_URL}/metrics/job/{JOB_NAME}/instance/{instance}"
    return _http_push(url, text, instance)


def push_loki_logs(entries: list) -> bool:
    url = f"{LOKI_URL}/loki/api/v1/push"
    streams = [{
        "stream": {"job": "jenkins", "service": "pipeline"},
        "values": [[str(ts_ns), line] for ts_ns, line in entries],
    }]
    payload = json.dumps({"streams": streams}).encode("utf-8")
    try:
        req = urllib.request.Request(
            url, data=payload, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            ok = resp.status in (200, 204)
            print(f"  {'[OK]' if ok else '[!!]'} Loki logs: HTTP {resp.status}")
            return ok
    except Exception as exc:
        print(f"  [XX] Loki: {exc}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Shared jitter helper
# ---------------------------------------------------------------------------

def _jitter(value: float, pct: float = 0.05) -> float:
    return round(value * (1 + random.uniform(-pct, pct)), 3)


# ===========================================================================
# DASHBOARD 1 DATA  –  CI/CD Pipeline & Responsible-AI
# ===========================================================================

DEVELOPERS = [
    {"name": "dev1", "ai_tool": "claude_code", "branch": "feat/dev1-auth-module"},
    {"name": "dev2", "ai_tool": "cursor",       "branch": "feat/dev2-payment-api"},
]

# (build_id, dev_idx, hours_ago, success, coverage, sast_high, sast_med, secrets, score, violations, duration_s)
_BUILD_TEMPLATES = [
    ("build_042", 0, 0.5,  True,  91.2, 0, 2, 0, 8.7, 0, 142),
    ("build_041", 1, 1.0,  True,  87.4, 1, 3, 0, 7.9, 1, 178),
    ("build_040", 0, 2.5,  True,  90.1, 0, 1, 0, 9.1, 0, 135),
    ("build_039", 1, 3.0,  False, 85.0, 2, 5, 1, 6.5, 2, 210),
    ("build_038", 0, 5.0,  True,  88.7, 0, 2, 0, 8.4, 0, 158),
    ("build_037", 1, 6.5,  True,  86.3, 1, 4, 0, 7.6, 1, 191),
    ("build_036", 0, 8.0,  True,  89.5, 0, 2, 0, 8.8, 0, 149),
    ("build_035", 1, 9.0,  True,  84.8, 0, 3, 0, 7.3, 0, 185),
    ("build_034", 0, 11.0, False, 83.2, 3, 6, 0, 5.9, 3, 245),
    ("build_033", 1, 12.0, True,  85.6, 1, 3, 0, 7.8, 1, 176),
    ("build_032", 0, 14.0, True,  87.9, 0, 1, 0, 8.5, 0, 141),
    ("build_031", 1, 15.5, True,  83.4, 0, 4, 0, 7.1, 0, 195),
    ("build_030", 0, 17.0, True,  86.6, 1, 2, 0, 8.2, 1, 153),
    ("build_029", 1, 18.0, False, 80.3, 2, 7, 2, 6.0, 2, 230),
    ("build_028", 0, 20.0, True,  85.1, 0, 2, 0, 8.6, 0, 148),
    ("build_027", 1, 21.5, True,  82.7, 0, 3, 0, 7.5, 0, 182),
    ("build_026", 0, 23.0, True,  84.3, 1, 3, 0, 8.0, 1, 162),
    ("build_025", 1, 24.0, True,  81.9, 0, 4, 0, 7.2, 0, 198),
]

_AI_RATIOS_DEV1 = [0.62, 0.65, 0.67, 0.70, 0.71, 0.73, 0.75, 0.76, 0.74]
_AI_RATIOS_DEV2 = [0.48, 0.51, 0.53, 0.55, 0.57, 0.56, 0.58, 0.60, 0.62]


def build_pipeline_metric_set(
    build_id, dev, success, coverage, sast_high, sast_med,
    secret_count, ai_review_score, policy_violations, duration_s, ai_ratio,
) -> MetricSet:
    return MetricSet(
        labels={"branch": dev["branch"], "developer": dev["name"],
                "ai_tool": dev["ai_tool"], "build": build_id},
        metrics={
            "pipeline_duration_seconds":  _jitter(duration_s, 0.08),
            "pipeline_success":           1.0 if success else 0.0,
            "pipeline_failure_total":     0.0 if success else 1.0,
            "sast_findings_high":         float(sast_high),
            "sast_findings_medium":       float(sast_med),
            "secret_leak_attempts_total": float(secret_count),
            "ai_policy_violations_total": float(policy_violations),
            "test_coverage_percent":      _jitter(coverage, 0.02),
            "ai_agent_review_score":      _jitter(ai_review_score, 0.04),
            "ai_contribution_ratio":      _jitter(ai_ratio, 0.03),
            "pipeline_run_timestamp":     float(time.time()),
        },
    )


def generate_loki_log_entries(build_id, dev, success):
    now_ns = time.time_ns()
    offset_ns = 0

    def ts():
        nonlocal offset_ns
        offset_ns += random.randint(500_000_000, 3_000_000_000)
        return now_ns - (20 * 60 * 1_000_000_000) + offset_ns

    branch, tool, name = dev["branch"], dev["ai_tool"], dev["name"]
    lines = [
        (ts(), f"[Pipeline] Starting build {build_id} on branch {branch}"),
        (ts(), f"[Checkout] Cloning {branch} from gitea-server..."),
        (ts(), f"[Install]  pip install -e '.[dev]' — all deps resolved (cached)"),
        (ts(), f"[Lint]     ruff: passed  black: passed  isort: passed"),
        (ts(), f"[Detect-Secrets] No secrets found in diff"),
        (ts(), f"[SAST]     semgrep scan complete — results written to reports/semgrep.json"),
        (ts(), f"[Tests]    ......................  32 passed, 0 failed"),
        (ts(), f"[Coverage] {random.uniform(82, 92):.1f}%  (threshold: 80%)"),
        (ts(), f"[AI-Review] {tool} agent — score {random.uniform(7.0, 9.5):.1f}/10"),
        (ts(), f"[AI-Policy] metadata tags found in {random.randint(8,15)} of {random.randint(15,20)} AI-modified files"),
        (ts(), f"[Metrics]  Pushing metrics to Pushgateway — OK"),
    ]
    if success:
        lines.append((ts(), f"[Pipeline] BUILD SUCCESS -- {build_id} ({name}/{tool})"))
    else:
        stage = random.choice(["Tests", "SAST", "AI-Policy"])
        reason = random.choice(["assertion error", "2 high-severity findings", "policy violation"])
        lines.append((ts(), f"[{stage}] FAILURE -- {reason}"))
        lines.append((ts(), f"[Pipeline] BUILD FAILED -- {build_id} ({name}/{tool})"))
    return sorted(lines)


# ===========================================================================
# DASHBOARD 2 DATA  –  Governance & Compliance
# ===========================================================================

# Policy rule adherence per developer (0–1 = % builds passing that rule)
_POLICY_COMPLIANCE = {
    "dev1": {
        "CONVENTIONAL_COMMITS": 0.94,
        "HARDCODED_SECRET":     1.00,
        "BARE_EXCEPT":          0.89,
        "PRINT_STATEMENT":      0.85,
        "COMMENTED_CODE":       0.91,
        "AI_TAG_MISSING":       0.87,
        "PROTECTED_FILE":       1.00,
    },
    "dev2": {
        "CONVENTIONAL_COMMITS": 0.81,
        "HARDCODED_SECRET":     0.95,
        "BARE_EXCEPT":          0.75,
        "PRINT_STATEMENT":      0.79,
        "COMMENTED_CODE":       0.83,
        "AI_TAG_MISSING":       0.70,
        "PROTECTED_FILE":       0.97,
    },
}

# Cumulative blocking violations over sprint (per rule per developer)
_GUARDRAIL_VIOLATIONS = {
    "dev1": {
        "CONVENTIONAL_COMMITS": 1,
        "BARE_EXCEPT":          2,
        "PRINT_STATEMENT":      3,
        "COMMENTED_CODE":       2,
        "AI_TAG_MISSING":       3,
    },
    "dev2": {
        "CONVENTIONAL_COMMITS": 5,
        "BARE_EXCEPT":          6,
        "PRINT_STATEMENT":      6,
        "COMMENTED_CODE":       4,
        "AI_TAG_MISSING":       9,
    },
}

# Code quality scores per developer
_CODE_QUALITY = {
    "dev1": {"score": 87.5, "type_hints": 92.0, "docstrings": 78.5, "flagged_snippets": 2},
    "dev2": {"score": 79.3, "type_hints": 83.5, "docstrings": 67.0, "flagged_snippets": 6},
}

# Lifecycle stage pass rate per developer (fraction of builds where that stage passed)
_LIFECYCLE = {
    "dev1": {
        "checkout":    1.00,
        "secret_scan": 0.94,
        "sast":        0.92,
        "ai_policy":   0.88,
        "tests":       0.94,
        "push_metrics":1.00,
    },
    "dev2": {
        "checkout":    1.00,
        "secret_scan": 0.88,
        "sast":        0.83,
        "ai_policy":   0.78,
        "tests":       0.89,
        "push_metrics":1.00,
    },
}

_SECURITY = {
    "dev1": {"pii_incidents": 0, "compliance_pct": 96.4, "defect_leakage": 1},
    "dev2": {"pii_incidents": 1, "compliance_pct": 91.1, "defect_leakage": 3},
}


def build_governance_text(dev_name: str, jitter_pct: float = 0.0) -> str:
    j = jitter_pct
    lines = []

    # Policy rule adherence (one series per rule)
    for rule, rate in _POLICY_COMPLIANCE[dev_name].items():
        v = min(_jitter(rate, j), 1.0) if j else rate
        lines.append(f'policy_rule_adherence{{rule="{rule}",developer="{dev_name}"}} {v:.3f}')

    # Guardrail violation counts (per rule)
    for rule, count in _GUARDRAIL_VIOLATIONS[dev_name].items():
        delta = random.randint(-1, 1) if j else 0
        lines.append(
            f'guardrail_blocking_violations_total{{rule="{rule}",developer="{dev_name}"}} {max(0, count+delta)}'
        )

    # Code quality
    cq = _CODE_QUALITY[dev_name]
    lines.append(f'code_quality_score{{developer="{dev_name}"}} {_jitter(cq["score"], j):.1f}')
    lines.append(f'code_quality_type_hints_percent{{developer="{dev_name}"}} {_jitter(cq["type_hints"], j):.1f}')
    lines.append(f'code_quality_docstrings_percent{{developer="{dev_name}"}} {_jitter(cq["docstrings"], j):.1f}')
    lines.append(f'flagged_ai_snippets_total{{developer="{dev_name}"}} {cq["flagged_snippets"]}')

    # Lifecycle stage pass rates
    for stage, rate in _LIFECYCLE[dev_name].items():
        v = min(_jitter(rate, j), 1.0) if j else rate
        lines.append(f'lifecycle_stage_pass_rate{{stage="{stage}",developer="{dev_name}"}} {v:.3f}')

    lc_pct = sum(_LIFECYCLE[dev_name].values()) / len(_LIFECYCLE[dev_name]) * 100
    lines.append(f'lifecycle_compliance_percent{{developer="{dev_name}"}} {_jitter(lc_pct, j):.1f}')

    # Security / compliance
    sec = _SECURITY[dev_name]
    lines.append(f'pii_scan_findings_total{{developer="{dev_name}"}} {sec["pii_incidents"]}')
    lines.append(f'compliance_adherence_percent{{developer="{dev_name}"}} {_jitter(sec["compliance_pct"], j):.1f}')
    lines.append(f'defect_leakage_total{{developer="{dev_name}"}} {sec["defect_leakage"]}')

    return "\n".join(lines) + "\n"


# ===========================================================================
# DASHBOARD 3 DATA  –  Adoption & ROI
# ===========================================================================

# Token usage per developer per sprint (~10 builds in 2 weeks)
_TOKEN_USAGE = {
    "dev1": {"model": "claude-sonnet-4-5", "tokens_per_build": 68_500, "sprint_total": 754_000},
    "dev2": {"model": "cursor-claude",     "tokens_per_build": 51_200, "sprint_total": 563_000},
}

# Cost estimates  (claude-sonnet-4-5: ~$3/MTok in + $15/MTok out, avg ~$0.53/build)
_COST = {
    "dev1": {"sprint_cost": 5.72, "cost_per_build": 0.52, "sprint": "2026-Q2-S1"},
    "dev2": {"sprint_cost": 4.29, "cost_per_build": 0.39, "sprint": "2026-Q2-S1"},
}

# Productivity signals
_PRODUCTIVITY = {
    "dev1": {
        "productivity_ratio": 0.72,   # AI-commits / total commits
        "time_saved_hours":   4.2,    # estimated per sprint
        "success_rate":       88.9,   # build success rate %
        "ai_commits":         13,
        "human_commits":       5,
    },
    "dev2": {
        "productivity_ratio": 0.61,
        "time_saved_hours":   3.1,
        "success_rate":       83.3,
        "ai_commits":          11,
        "human_commits":        7,
    },
}

_ROI = {
    "adoption_rate_pct": 85.0,     # % of developers on the team using AI tools
    "roi_estimate_usd":  2840.0,   # net value (time saved * hourly rate − tool cost)
}


def build_adoption_text(dev_name: str, jitter_pct: float = 0.0) -> str:
    j = jitter_pct
    dev = next(d for d in DEVELOPERS if d["name"] == dev_name)
    tu = _TOKEN_USAGE[dev_name]
    cost = _COST[dev_name]
    prod = _PRODUCTIVITY[dev_name]

    lines = [
        f'ai_tokens_consumed_total{{developer="{dev_name}",model="{tu["model"]}"}} {tu["sprint_total"]}',
        f'ai_tokens_per_build_avg{{developer="{dev_name}"}} {_jitter(float(tu["tokens_per_build"]), j):.0f}',
        f'ai_estimated_cost_usd{{developer="{dev_name}",sprint="{cost["sprint"]}"}} {_jitter(cost["sprint_cost"], j):.2f}',
        f'ai_cost_per_build_usd{{developer="{dev_name}"}} {_jitter(cost["cost_per_build"], j):.3f}',
        f'ai_productivity_ratio{{developer="{dev_name}",ai_tool="{dev["ai_tool"]}"}} {_jitter(prod["productivity_ratio"], j):.3f}',
        f'estimated_time_saved_hours{{developer="{dev_name}"}} {_jitter(prod["time_saved_hours"], j):.1f}',
        f'build_success_rate_percent{{ai_tool="{dev["ai_tool"]}",developer="{dev_name}"}} {_jitter(prod["success_rate"], j):.1f}',
        f'ai_commits_total{{developer="{dev_name}",ai_tool="{dev["ai_tool"]}"}} {prod["ai_commits"]}',
        f'human_commits_total{{developer="{dev_name}",ai_tool="{dev["ai_tool"]}"}} {prod["human_commits"]}',
    ]
    return "\n".join(lines) + "\n"


def build_global_adoption_text(jitter_pct: float = 0.0) -> str:
    j = jitter_pct
    total_tokens = sum(d["sprint_total"] for d in _TOKEN_USAGE.values())
    total_cost = sum(d["sprint_cost"] for d in _COST.values())
    total_saved = sum(d["time_saved_hours"] for d in _PRODUCTIVITY.values())
    lines = [
        f'ai_adoption_rate_percent {_jitter(_ROI["adoption_rate_pct"], j):.1f}',
        f'ai_roi_estimate_usd {_jitter(_ROI["roi_estimate_usd"], j):.1f}',
        f'ai_sprint_tokens_total {total_tokens}',
        f'ai_sprint_cost_total_usd {_jitter(total_cost, j):.2f}',
        f'estimated_sprint_hours_saved {_jitter(total_saved, j):.1f}',
    ]
    return "\n".join(lines) + "\n"


# ===========================================================================
# Main seeding logic
# ===========================================================================

def seed_all() -> None:

    # ── Dashboard 1: CI/CD pipeline metrics ──────────────────────────────
    print("\n-- Pushing CI/CD pipeline metrics to Pushgateway --")
    ai_ratio_counters = {0: 0, 1: 0}
    for (build_id, dev_idx, _, success, coverage,
         sast_high, sast_med, secrets, score, violations, duration) in _BUILD_TEMPLATES:
        dev = DEVELOPERS[dev_idx]
        ratio_idx = min(ai_ratio_counters[dev_idx], len(_AI_RATIOS_DEV1) - 1)
        ai_ratio = _AI_RATIOS_DEV1[ratio_idx] if dev_idx == 0 else _AI_RATIOS_DEV2[ratio_idx]
        ai_ratio_counters[dev_idx] += 1
        ms = build_pipeline_metric_set(
            build_id, dev, success, coverage, sast_high, sast_med,
            secrets, score, violations, float(duration), ai_ratio,
        )
        push_metrics(ms, instance=f"{dev['name']}_{build_id}")

    # ── Dashboard 2: Governance & Compliance ─────────────────────────────
    print("\n-- Pushing governance & compliance metrics --")
    for dev_name in ["dev1", "dev2"]:
        push_text(build_governance_text(dev_name), instance=f"governance_{dev_name}")

    # ── Dashboard 3: Adoption & ROI ──────────────────────────────────────
    print("\n-- Pushing adoption & ROI metrics --")
    for dev_name in ["dev1", "dev2"]:
        push_text(build_adoption_text(dev_name), instance=f"adoption_{dev_name}")
    push_text(build_global_adoption_text(), instance="adoption_global")

    # ── Loki logs ─────────────────────────────────────────────────────────
    print("\n-- Pushing pipeline logs to Loki --")
    all_entries = []
    for (build_id, dev_idx, _, success, *_rest) in _BUILD_TEMPLATES:
        all_entries.extend(generate_loki_log_entries(build_id, DEVELOPERS[dev_idx], success))
    all_entries.sort()
    push_loki_logs(all_entries)


def seed_loop(total_seconds: int) -> None:
    start = time.time()
    interval = 20
    round_num = 0
    print(f"\n-- Loop mode: pushing every {interval}s for {total_seconds}s (Ctrl+C to stop) --")

    while (time.time() - start) < total_seconds:
        round_num += 1
        elapsed = int(time.time() - start)
        print(f"\n[Round {round_num}]  elapsed={elapsed}s")

        # Vary pipeline metrics to build time-series curves
        for (build_id, dev_idx, _, success, coverage,
             sast_high, sast_med, secrets, score, violations, duration) in _BUILD_TEMPLATES[:6]:
            dev = DEVELOPERS[dev_idx]
            trend = round_num * 0.3
            ms = build_pipeline_metric_set(
                build_id, dev, success,
                min(coverage + trend, 98.0),
                max(sast_high - round_num // 5, 0),
                max(sast_med  - round_num // 3, 0),
                secrets,
                min(score + trend * 0.05, 10.0),
                max(violations - round_num // 4, 0),
                max(float(duration) - round_num * 2, 60.0),
                min(0.62 + round_num * 0.01, 0.85),
            )
            push_metrics(ms, instance=f"{dev['name']}_{build_id}")

        # Vary governance and adoption metrics with jitter
        for dev_name in ["dev1", "dev2"]:
            push_text(build_governance_text(dev_name, jitter_pct=0.03),
                      instance=f"governance_{dev_name}")
            push_text(build_adoption_text(dev_name, jitter_pct=0.04),
                      instance=f"adoption_{dev_name}")
        push_text(build_global_adoption_text(jitter_pct=0.02), instance="adoption_global")

        remaining = total_seconds - int(time.time() - start)
        print(f"  Next push in {interval}s  ({remaining}s remaining)")
        time.sleep(interval)

    print("\n-- Loop complete --")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Grafana demo data (all dashboards)")
    parser.add_argument("--loop", action="store_true",
                        help="Keep pushing to build time-series trends")
    parser.add_argument("--duration", type=int, default=300,
                        help="Loop duration in seconds (default 300)")
    args = parser.parse_args()

    print(f"Pushgateway : {PUSHGATEWAY_URL}")
    print(f"Loki        : {LOKI_URL}")

    seed_all()

    if args.loop:
        seed_loop(args.duration)
    else:
        print(
            "\nDone. All panels should populate within ~15 s (one Prometheus scrape interval).\n"
            "For time-series trends run:  python scripts/seed_demo_data.py --loop\n"
        )


if __name__ == "__main__":
    main()
