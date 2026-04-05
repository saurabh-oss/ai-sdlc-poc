#!/usr/bin/env python3
"""
ai_policy_check.py - Validates that commits from AI-assisted developers
comply with the project guardrail policies defined in CLAUDE.md / .cursorrules.

Checks:
  1. Commit message follows Conventional Commits format
  2. No bare `except:` clauses introduced
  3. No `print()` statements in non-test code
  4. No hardcoded credential patterns
  5. No commented-out code blocks (heuristic)
  6. AI-ASSISTED tag present when AI tool detected
  7. Files not in ignore lists are the only ones modified
"""

import argparse
import re
import subprocess
import sys
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


CONVENTIONAL_COMMIT_RE = re.compile(
    r'^(feat|fix|chore|docs|refactor|test|ci|style|perf|build|revert)(\(.+\))?: .{1,100}$'
)

HARDCODED_SECRET_PATTERNS = [
    re.compile(r'(?i)(api_key|secret|password|token|passwd|pwd)\s*=\s*["\'][^"\']{8,}["\']'),
    re.compile(r'(?i)sk-[a-zA-Z0-9]{20,}'),
    re.compile(r'(?i)Bearer\s+[a-zA-Z0-9\-_.]{20,}'),
    re.compile(r'(?i)ghp_[a-zA-Z0-9]{36}'),
    re.compile(r'(?i)-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----'),
]

PROTECTED_FILES = [
    'docker-compose.yml',
    'docker-compose.yaml',
    'monitoring/',
    'grafana/',
    'jenkins/',
]


@dataclass
class PolicyViolation:
    rule: str
    file: str
    line: int
    message: str
    severity: str = "ERROR"  # ERROR blocks, WARNING does not


def get_changed_files() -> List[str]:
    result = subprocess.run(
        ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
        capture_output=True, text=True
    )
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def get_commit_message() -> str:
    result = subprocess.run(
        ['git', 'log', '-1', '--format=%B'],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def get_diff_lines(filepath: str) -> List[tuple]:
    """Returns list of (line_number, line_content) for added lines."""
    result = subprocess.run(
        ['git', 'diff', 'HEAD~1', 'HEAD', '--', filepath],
        capture_output=True, text=True
    )
    lines = []
    line_num = 0
    for line in result.stdout.splitlines():
        if line.startswith('@@'):
            match = re.search(r'\+(\d+)', line)
            if match:
                line_num = int(match.group(1)) - 1
        elif line.startswith('+') and not line.startswith('+++'):
            line_num += 1
            lines.append((line_num, line[1:]))
        elif not line.startswith('-'):
            line_num += 1
    return lines


def check_commit_message(commit_msg: str) -> List[PolicyViolation]:
    violations = []
    first_line = commit_msg.splitlines()[0] if commit_msg else ""
    if not CONVENTIONAL_COMMIT_RE.match(first_line):
        violations.append(PolicyViolation(
            rule="CONVENTIONAL_COMMITS",
            file="commit message",
            line=0,
            message=f"Commit message '{first_line}' does not follow Conventional Commits format "
                    f"(feat/fix/chore/docs/refactor/test/ci: description)"
        ))
    return violations


def check_protected_files(changed_files: List[str]) -> List[PolicyViolation]:
    violations = []
    for f in changed_files:
        for protected in PROTECTED_FILES:
            if f == protected or f.startswith(protected):
                violations.append(PolicyViolation(
                    rule="PROTECTED_FILE",
                    file=f,
                    line=0,
                    message=f"File '{f}' is protected and must not be modified by developers. "
                            f"Infrastructure changes require DevOps review."
                ))
    return violations


def check_python_file(filepath: str, lines: List[tuple]) -> List[PolicyViolation]:
    violations = []
    is_test = 'test' in filepath.lower()

    for line_num, content in lines:
        # Check hardcoded secrets
        for pattern in HARDCODED_SECRET_PATTERNS:
            if pattern.search(content):
                violations.append(PolicyViolation(
                    rule="HARDCODED_SECRET",
                    file=filepath,
                    line=line_num,
                    message=f"Potential hardcoded credential detected: '{content.strip()[:60]}'"
                ))
                break

        # Check bare except
        if re.match(r'^\s*except\s*:', content):
            violations.append(PolicyViolation(
                rule="BARE_EXCEPT",
                file=filepath,
                line=line_num,
                message="Bare `except:` clause - catch specific exceptions only"
            ))

        # Check print statements (not in tests)
        if not is_test and re.match(r'^\s*print\s*\(', content):
            violations.append(PolicyViolation(
                rule="PRINT_STATEMENT",
                file=filepath,
                line=line_num,
                message="Use `logging` module instead of `print()` in production code",
                severity="WARNING"
            ))

        # Check large commented-out code blocks (heuristic: line of commented code)
        if re.match(r'^\s*#\s+(def |class |import |from |if |for |while |return )', content):
            violations.append(PolicyViolation(
                rule="COMMENTED_CODE",
                file=filepath,
                line=line_num,
                message="Commented-out code detected - remove dead code before committing",
                severity="WARNING"
            ))

    return violations


def check_ai_tag(commit_msg: str, changed_files: List[str]) -> List[PolicyViolation]:
    """Warn if significant Python changes lack AI-ASSISTED tag."""
    py_files = [f for f in changed_files if f.endswith('.py')]
    if len(py_files) >= 3 and 'AI-ASSISTED' not in commit_msg:
        return [PolicyViolation(
            rule="AI_TAG_MISSING",
            file="commit message",
            line=0,
            message="Large change (3+ Python files) without AI-ASSISTED tag. "
                    "If AI tools were used, add tag per governance requirements.",
            severity="WARNING"
        )]
    return []


def main():
    parser = argparse.ArgumentParser(description='AI Policy Compliance Checker')
    parser.add_argument('--branch', default='HEAD', help='Branch being checked')
    parser.add_argument('--strict', action='store_true', help='Treat warnings as errors')
    args = parser.parse_args()

    logger.info("Running AI Policy Check for branch: %s", args.branch)

    all_violations: List[PolicyViolation] = []

    commit_msg = get_commit_message()
    changed_files = get_changed_files()

    logger.info("Commit: %s", commit_msg[:80])
    logger.info("Changed files: %s", changed_files)

    # Run checks
    all_violations.extend(check_commit_message(commit_msg))
    all_violations.extend(check_protected_files(changed_files))
    all_violations.extend(check_ai_tag(commit_msg, changed_files))

    for filepath in changed_files:
        if filepath.endswith('.py'):
            diff_lines = get_diff_lines(filepath)
            all_violations.extend(check_python_file(filepath, diff_lines))

    # Report
    errors = [v for v in all_violations if v.severity == "ERROR"]
    warnings = [v for v in all_violations if v.severity == "WARNING"]

    for v in all_violations:
        prefix = "X ERROR" if v.severity == "ERROR" else "!_  WARN"
        logger.info("%s [%s] %s:%d - %s", prefix, v.rule, v.file, v.line, v.message)

    logger.info("Summary: %d error(s), %d warning(s)", len(errors), len(warnings))

    if errors or (args.strict and warnings):
        logger.error("AI Policy Check FAILED - fix errors before merging")
        sys.exit(1)

    logger.info("AI Policy Check PASSED [OK]")
    sys.exit(0)


if __name__ == '__main__':
    main()
