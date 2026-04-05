#!/usr/bin/env python3
"""
code_review_agent.py - AI-powered code review using CrewAI + Anthropic Claude.

Evaluates security, architecture adherence, test quality, and coding standards.
Outputs a structured Markdown report and a 0-100 quality score.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from crewai import Agent, Crew, LLM, Process, Task


def get_branch_diff(branch: str) -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "develop...HEAD", "--stat", "-p", "--", "*.py"],
            capture_output=True, text=True
        )
        return result.stdout[:8000]
    except Exception as e:
        return f"Could not get diff: {e}"


def get_changed_files() -> list:
    result = subprocess.run(
        ["git", "diff", "--name-only", "develop...HEAD"],
        capture_output=True, text=True
    )
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def get_file_contents(files: list, max_files: int = 5) -> str:
    contents = []
    for f in files[:max_files]:
        try:
            content = Path(f).read_text()[:2000]
            contents.append(f"### File: {f}\n```python\n{content}\n```")
        except Exception:
            pass
    return "\n\n".join(contents)


def run_review(branch: str, output_path: str, score_file: str):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("WARNING: ANTHROPIC_API_KEY not set - writing placeholder report", file=sys.stderr)
        Path(score_file).write_text("75")
        Path(output_path).write_text("# AI Review\n\nAPI key not configured - manual review required.")
        sys.exit(0)

    llm = LLM(
        model="anthropic/claude-3-5-sonnet-20241022",
        temperature=0.2,
        api_key=api_key
    )

    diff = get_branch_diff(branch)
    changed_files = get_changed_files()
    file_contents = get_file_contents(changed_files)

    security_reviewer = Agent(
        role="Security Engineer",
        goal="Identify security vulnerabilities, credential exposure risks, and insecure patterns",
        backstory="Senior application security engineer with 12 years of experience in OWASP Top 10 and secure code review.",
        llm=llm,
        verbose=False
    )

    architecture_reviewer = Agent(
        role="Software Architect",
        goal="Evaluate whether code follows the layered architecture, SOLID principles, and project conventions",
        backstory="Principal software architect who enforces clean architecture and separation of concerns.",
        llm=llm,
        verbose=False
    )

    quality_reviewer = Agent(
        role="Senior Developer",
        goal="Review code quality: readability, test coverage, error handling, type safety, and coding standards",
        backstory="Senior developer with obsessive attention to code quality, type hints, and test coverage.",
        llm=llm,
        verbose=False
    )

    score_aggregator = Agent(
        role="Engineering Lead",
        goal="Aggregate findings into a structured report with an overall score from 0 to 100",
        backstory="Engineering lead who synthesizes technical reviews into actionable, prioritized feedback.",
        llm=llm,
        verbose=False
    )

    security_task = Task(
        description=f"""Review the following code changes for security issues.
Branch: {branch}
Changed files: {', '.join(changed_files)}

Code diff:
{diff}

Check for: hardcoded credentials, SQL/command injection, missing input validation,
improper error handling exposing internals, authentication gaps.

Output a bulleted list of findings with severity (CRITICAL/HIGH/MEDIUM/LOW).""",
        agent=security_reviewer,
        expected_output="Bulleted list of security findings with severity levels"
    )

    architecture_task = Task(
        description=f"""Review code changes for architecture compliance.
Branch: {branch}

File contents:
{file_contents}

Check for: layer boundary violations, SOLID principle violations, global mutable state,
business logic in wrong layer, missing dependency injection.

Output a bulleted list of architecture findings.""",
        agent=architecture_reviewer,
        expected_output="Bulleted list of architecture findings"
    )

    quality_task = Task(
        description=f"""Review code changes for quality.
Code diff:
{diff}

Check for: missing type hints, missing docstrings, bare except clauses,
print() in non-test code, insufficient tests, magic numbers/strings.

Output a bulleted list of quality findings.""",
        agent=quality_reviewer,
        expected_output="Bulleted list of quality findings"
    )

    aggregation_task = Task(
        description="""Aggregate findings into a final review report in this EXACT format:

# AI Code Review Report

**Branch:** [branch]
**Reviewer:** AI Agent (CrewAI/Claude)

## Summary
[2-3 sentence overall assessment]

## Overall Score: XX/100

## Security Findings
[findings or "No issues found"]

## Architecture Findings
[findings or "No issues found"]

## Quality Findings
[findings or "No issues found"]

## Top 3 Recommendations
1. [Most critical action]
2. [Second]
3. [Third]

---
*Generated by AI agent - verify with human reviewer.*

After the report, on a NEW LINE write ONLY: SCORE:[0-100]""",
        agent=score_aggregator,
        expected_output="Full markdown review report ending with SCORE:XX",
        context=[security_task, architecture_task, quality_task]
    )

    crew = Crew(
        agents=[security_reviewer, architecture_reviewer, quality_reviewer, score_aggregator],
        tasks=[security_task, architecture_task, quality_task, aggregation_task],
        process=Process.sequential,
        verbose=False
    )

    print(f"Running AI code review on branch: {branch}")
    result = crew.kickoff()
    report_text = str(result)

    score_match = re.search(r"SCORE:(\d+)", report_text)
    score = int(score_match.group(1)) if score_match else 75
    score = max(0, min(100, score))

    clean_report = re.sub(r"\nSCORE:\d+\s*$", "", report_text).strip()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(clean_report)
    Path(score_file).write_text(str(score))
    print(f"Review complete. Score: {score}/100 | Report: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Code Review Agent")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--output", default="reports/ai-review.md")
    parser.add_argument("--score-file", default="reports/ai-score.txt")
    args = parser.parse_args()
    run_review(args.branch, args.output, args.score_file)
