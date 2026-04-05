#!/usr/bin/env python3
"""
metrics_exporter.py - Push AI SDLC pipeline metrics to Prometheus Pushgateway.

Called by Jenkins pipeline stages and also usable standalone to export
AI contribution metrics from git history.

Usage:
    python scripts/metrics_exporter.py --job build_123 --branch feat/dev1-auth
    python scripts/metrics_exporter.py --from-git-history --days 7
"""

import argparse
import os
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Optional


PUSHGATEWAY_URL = os.getenv("PUSHGATEWAY_URL", "http://localhost:9091")
JOB_NAME = "ai_sdlc_metrics"


@dataclass
class MetricSet:
    """A set of metrics to push."""
    labels: dict[str, str] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)

    def to_prometheus_text(self) -> str:
        label_str = ",".join(f'{k}="{v}"' for k, v in self.labels.items())
        lines = []
        for name, value in self.metrics.items():
            if label_str:
                lines.append(f'{name}{{{label_str}}} {value}')
            else:
                lines.append(f'{name} {value}')
        return "\n".join(lines) + "\n"


def push_metrics(metric_set: MetricSet, instance: str = "default") -> bool:
    """Push a MetricSet to the Pushgateway."""
    url = f"{PUSHGATEWAY_URL}/metrics/job/{JOB_NAME}/instance/{instance}"
    payload = metric_set.to_prometheus_text().encode("utf-8")
    try:
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={"Content-Type": "text/plain"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                print(f"  [OK] Metrics pushed to {url}")
                return True
            else:
                print(f"  !_  Pushgateway returned {resp.status}", file=sys.stderr)
                return False
    except Exception as e:
        print(f"  X Failed to push metrics: {e}", file=sys.stderr)
        return False


def collect_git_ai_metrics(branch: str, days: int = 7) -> MetricSet:
    """Analyse git log to count AI-assisted vs human commits."""
    since = f"--since={days} days ago"
    result = subprocess.run(
        ["git", "log", since, "--format=%B---COMMIT---", f"origin/{branch}"],
        capture_output=True, text=True
    )
    commits = [c.strip() for c in result.stdout.split("---COMMIT---") if c.strip()]

    ai_assisted = sum(1 for c in commits if "AI-ASSISTED" in c or "AI-GENERATED" in c)
    human_only = len(commits) - ai_assisted

    claude_commits = sum(1 for c in commits if "claude" in c.lower())
    cursor_commits = sum(1 for c in commits if "cursor" in c.lower())

    return MetricSet(
        labels={"branch": branch, "period_days": str(days)},
        metrics={
            "ai_commits_total": ai_assisted,
            "human_commits_total": human_only,
            "ai_contribution_ratio": round(ai_assisted / max(len(commits), 1), 3),
            "claude_code_commits_total": claude_commits,
            "cursor_commits_total": cursor_commits,
        }
    )


def collect_pipeline_metrics(
    branch: str,
    developer: str,
    ai_tool: str,
    duration_seconds: float,
    success: bool,
    coverage: Optional[float] = None,
    sast_high: int = 0,
    sast_medium: int = 0,
    secret_count: int = 0,
    ai_review_score: Optional[float] = None,
    policy_violations: int = 0,
) -> MetricSet:
    """Collect all pipeline metrics into a single MetricSet."""
    labels = {
        "branch": branch,
        "developer": developer,
        "ai_tool": ai_tool,
    }
    metrics = {
        "pipeline_duration_seconds": duration_seconds,
        "pipeline_success": 1.0 if success else 0.0,
        "pipeline_failure_total": 0.0 if success else 1.0,
        "sast_findings_high": float(sast_high),
        "sast_findings_medium": float(sast_medium),
        "secret_leak_attempts_total": float(secret_count),
        "ai_policy_violations_total": float(policy_violations),
        "pipeline_run_timestamp": float(time.time()),
    }
    if coverage is not None:
        metrics["test_coverage_percent"] = coverage
    if ai_review_score is not None:
        metrics["ai_agent_review_score"] = ai_review_score

    return MetricSet(labels=labels, metrics=metrics)


def main():
    parser = argparse.ArgumentParser(description="AI SDLC Metrics Exporter")
    parser.add_argument("--job", default="manual", help="Job/build identifier")
    parser.add_argument("--branch", default="develop", help="Git branch")
    parser.add_argument("--developer", default="unknown", help="Developer name")
    parser.add_argument("--ai-tool", default="unknown", choices=["claude_code", "cursor", "unknown"])
    parser.add_argument("--duration", type=float, default=0.0, help="Pipeline duration in seconds")
    parser.add_argument("--success", action="store_true", help="Mark pipeline as successful")
    parser.add_argument("--coverage", type=float, help="Test coverage percentage")
    parser.add_argument("--sast-high", type=int, default=0)
    parser.add_argument("--sast-medium", type=int, default=0)
    parser.add_argument("--secret-count", type=int, default=0)
    parser.add_argument("--review-score", type=float, help="AI review score 0-100")
    parser.add_argument("--policy-violations", type=int, default=0)
    parser.add_argument("--from-git-history", action="store_true", help="Export AI ratio from git history")
    parser.add_argument("--days", type=int, default=7, help="Days of history for --from-git-history")
    args = parser.parse_args()

    print(f"Exporting metrics to {PUSHGATEWAY_URL}...")

    if args.from_git_history:
        git_metrics = collect_git_ai_metrics(args.branch, args.days)
        push_metrics(git_metrics, instance=f"git_history_{args.branch.replace('/', '_')}")

    pipeline_metrics = collect_pipeline_metrics(
        branch=args.branch,
        developer=args.developer,
        ai_tool=args.ai_tool,
        duration_seconds=args.duration,
        success=args.success,
        coverage=args.coverage,
        sast_high=args.sast_high,
        sast_medium=args.sast_medium,
        secret_count=args.secret_count,
        ai_review_score=args.review_score,
        policy_violations=args.policy_violations,
    )
    push_metrics(pipeline_metrics, instance=args.job)


if __name__ == "__main__":
    main()
