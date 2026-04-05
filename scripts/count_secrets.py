#!/usr/bin/env python3
"""count_secrets.py - Count detect-secrets findings and write to reports/secret_count.txt."""
import json
from pathlib import Path

try:
    data = json.loads(Path("reports/secrets.json").read_text())
    # detect-secrets format: {"results": {"file.py": [finding, ...], ...}}
    results = data.get("results", {})
    count = sum(len(findings) for findings in results.values())
except Exception:
    count = 0

Path("reports/secret_count.txt").write_text(str(count))
print(f"Secrets found: {count}")
exit(1 if count > 0 else 0)
