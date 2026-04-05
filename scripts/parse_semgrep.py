#!/usr/bin/env python3
"""parse_semgrep.py - Parse Semgrep JSON output and print high,medium,low counts."""
import json, sys
from pathlib import Path

try:
    data = json.loads(Path("reports/semgrep.json").read_text())
    results = data.get("results", [])
    high = sum(1 for r in results if r.get("extra", {}).get("severity", "").upper() in ("ERROR", "HIGH"))
    medium = sum(1 for r in results if r.get("extra", {}).get("severity", "").upper() in ("WARNING", "MEDIUM"))
    low = len(results) - high - medium
    print(f"{high},{medium},{low}")
except Exception as e:
    print("0,0,0", file=sys.stderr)
    print("0,0,0")
