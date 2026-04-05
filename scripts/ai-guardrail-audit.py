#!/usr/bin/env python3
"""
AI Guardrail Audit Scanner
===========================
Scans source code for:
1. AI metadata headers (tracking AI contribution)
2. Guardrail violations (forbidden patterns)
3. Policy compliance
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime


# ---- Blocking violations (will fail the build) ----------------
BLOCKING_PATTERNS = [
    (r'verify\s*=\s*False', "SSL verification disabled"),
    (r'ALLOW_ALL_ORIGINS\s*=\s*True', "CORS wildcard in production"),
    (r'DEBUG\s*=\s*True', "Debug mode enabled"),
    (r'(password|passwd|secret|api_key|token)\s*=\s*["\'][^"\']{8,}["\']',
     "Hardcoded credential detected"),
    (r'eval\s*\(', "eval() usage detected"),
    (r'exec\s*\(', "exec() usage detected"),
    (r'subprocess\.call\([^)]*shell\s*=\s*True', "Shell injection risk"),
    (r'pickle\.loads?\(', "Unsafe deserialization (pickle)"),
    (r'# nosec\b', "Security scan suppression detected"),
]

# ---- Warning violations (won't fail but will be tracked) ------
WARNING_PATTERNS = [
    (r'TODO|FIXME|HACK|XXX', "Unresolved technical debt marker"),
    (r'print\s*\(', "Raw print() in production code (use logging)"),
    (r'except\s*:', "Bare except clause (too broad)"),
    (r'except\s+Exception\s*:', "Catching base Exception (too broad)"),
    (r'time\.sleep\(', "Blocking sleep in potentially async context"),
    (r'import \*', "Wildcard import"),
]

# ---- AI metadata regex ----------------------------------------
AI_METADATA_PATTERN = re.compile(
    r'#\s*AI-ASSIST-METADATA:|#\s*AI-GENERATED:|#\s*AI-ASSIST:', re.IGNORECASE
)
AI_CONTRIBUTION_PATTERN = re.compile(
    r'ai-contribution-estimate:\s*(\d+)', re.IGNORECASE
)


def scan_file(filepath: Path) -> dict:
    """Scan a single file for guardrail compliance."""
    result = {
        "file": str(filepath),
        "has_ai_metadata": False,
        "ai_contribution_estimate": None,
        "blocking_violations": [],
        "warning_violations": [],
        "line_count": 0,
        "has_type_hints": False,
        "has_docstrings": False,
    }

    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        result["line_count"] = len(lines)

        # Check AI metadata
        if AI_METADATA_PATTERN.search(content):
            result["has_ai_metadata"] = True
            contrib_match = AI_CONTRIBUTION_PATTERN.search(content)
            if contrib_match:
                result["ai_contribution_estimate"] = int(contrib_match.group(1))

        # Check code quality indicators
        result["has_type_hints"] = bool(re.search(r'def \w+\([^)]*:\s*\w', content))
        result["has_docstrings"] = bool(re.search(r'"""', content))

        # Blocking pattern checks
        for pattern, description in BLOCKING_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                result["blocking_violations"].append({
                    "line": line_num,
                    "pattern": pattern,
                    "description": description,
                    "snippet": lines[line_num - 1].strip()[:100] if line_num <= len(lines) else "",
                })

        # Warning pattern checks (skip test files for some patterns)
        is_test_file = "test" in str(filepath).lower()
        for pattern, description in WARNING_PATTERNS:
            if is_test_file and "print" in pattern:
                continue
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                result["warning_violations"].append({
                    "line": line_num,
                    "description": description,
                })

    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description="AI guardrail audit scanner")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--developer", required=True)
    parser.add_argument("--ai-tool", required=True)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source_path = Path(args.source_dir)
    py_files = list(source_path.rglob("*.py"))

    if not py_files:
        print(f"No Python files found in {args.source_dir}")
        report = {
            "files_scanned": 0,
            "blocking_violations": [],
            "violations": [],
            "metadata_coverage": 0,
            "avg_ai_contribution": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(report, indent=2))
        sys.exit(0)

    print(f"Scanning {len(py_files)} Python files...")
    file_results = []
    all_blocking = []

    for py_file in py_files:
        result = scan_file(py_file)
        file_results.append(result)
        all_blocking.extend(result["blocking_violations"])

    # Calculate metrics
    files_with_metadata = sum(1 for r in file_results if r["has_ai_metadata"])
    metadata_coverage = (files_with_metadata / len(py_files) * 100) if py_files else 0

    contributions = [
        r["ai_contribution_estimate"]
        for r in file_results
        if r["ai_contribution_estimate"] is not None
    ]
    avg_contribution = sum(contributions) / len(contributions) if contributions else 0

    all_warnings = []
    for r in file_results:
        all_warnings.extend(r["warning_violations"])

    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "branch": args.branch,
        "developer": args.developer,
        "ai_tool": args.ai_tool,
        "files_scanned": len(py_files),
        "files_with_ai_metadata": files_with_metadata,
        "metadata_coverage": round(metadata_coverage, 1),
        "avg_ai_contribution": round(avg_contribution, 1),
        "blocking_violations": all_blocking,
        "violations": all_warnings,
        "file_details": file_results,
        "summary": {
            "total_blocking": len(all_blocking),
            "total_warnings": len(all_warnings),
            "files_with_type_hints": sum(1 for r in file_results if r["has_type_hints"]),
            "files_with_docstrings": sum(1 for r in file_results if r["has_docstrings"]),
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))

    print(f"\n{'='*50}")
    print(f"AI Guardrail Audit Results")
    print(f"Files scanned         : {len(py_files)}")
    print(f"AI metadata coverage  : {metadata_coverage:.1f}%")
    print(f"Avg AI contribution   : {avg_contribution:.1f}%")
    print(f"Blocking violations   : {len(all_blocking)}")
    print(f"Warnings              : {len(all_warnings)}")
    print(f"{'='*50}")

    if all_blocking:
        print("\n? BLOCKING VIOLATIONS:")
        for v in all_blocking:
            print(f"  [{v['description']}] {v.get('file', '')}:{v.get('line', '')}")
            print(f"    -> {v.get('snippet', '')}")
        sys.exit(1)

    print("[OK] No blocking violations found")


if __name__ == "__main__":
    main()
