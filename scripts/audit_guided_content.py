#!/usr/bin/env python3
"""Audit guided-content readiness for the GNS3 CCNP Labs catalog.

This is an offline quality check. It does not contact GNS3 or generate projects.
It verifies that each scenario can produce guided practice steps, hints, and an
answer-key structure with the explanatory sections expected by the 3.0 guided
practice workflow.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

APP_DIR = Path(__file__).resolve().parents[1]
CATALOG = APP_DIR / "catalogs" / "ccnp_encor_lab_catalog.json"

sys.path.insert(0, str(APP_DIR))

try:
    import gns3_ccnp_lab_generator as generator
except Exception as exc:  # pragma: no cover
    print(f"ERROR: could not import generator: {exc}", file=sys.stderr)
    raise SystemExit(2)

REQUIRED_STEP_FIELDS = {"id", "title", "objective", "instructions", "completion_criteria"}
REQUIRED_ANSWER_SECTIONS = [
    "## Root Cause",
    "## Why This Caused the Reported Symptoms",
    "## How to Prove It",
    "## Corrective Action Summary",
    "## Common Wrong Fixes",
    "## Verification Procedure",
]


def load_catalog(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_scenario(sid: str, scenario: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    steps = generator.build_guided_steps_data(sid, scenario)
    hints = generator.build_hints_data(sid, scenario, steps)
    answer = generator.build_answer_key_details(scenario)
    observed = generator.observed_symptom_text(scenario)

    if len(steps) < 6:
        issues.append(f"{sid}: fewer than 6 guided steps generated")
    for idx, step in enumerate(steps, start=1):
        missing = sorted(field for field in REQUIRED_STEP_FIELDS if not step.get(field))
        if missing:
            issues.append(f"{sid}: step {idx} missing {', '.join(missing)}")
        if not step.get("what_to_look_for"):
            issues.append(f"{sid}: step {idx} missing what_to_look_for guidance")
    if len(hints) < 3:
        issues.append(f"{sid}: fewer than 3 hints generated")
    for section in REQUIRED_ANSWER_SECTIONS:
        if section not in answer:
            issues.append(f"{sid}: answer key missing section {section}")
    if not observed.lower().startswith(("users", "operators", "the help desk", "network users")):
        issues.append(f"{sid}: observed symptom is not framed as a user/operator report")
    return issues


def main() -> int:
    catalog = load_catalog(CATALOG)
    scenarios = catalog.get("scenarios", {})
    issues: List[str] = []
    for sid, scenario in sorted(scenarios.items()):
        issues.extend(audit_scenario(sid, scenario))

    print(f"Guided content audit: {len(scenarios)} scenarios checked")
    if issues:
        print(f"Issues: {len(issues)}")
        for issue in issues[:200]:
            print(f"- {issue}")
        if len(issues) > 200:
            print(f"... {len(issues) - 200} additional issue(s) omitted")
        return 1
    print("PASS: guided content structure is complete for all scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
