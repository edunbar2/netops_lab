# Minor Release Bug Backlog (Stabilization)

## Purpose
Track defects and polish work for the pre-next-major minor release.

## Triage Rules
Priority:
- P0: data loss, broken core workflow, crash
- P1: major functional degradation
- P2: moderate usability/reliability issues
- P3: minor polish

Status:
- new
- triaged
- in-progress
- blocked
- fixed
- verified

## Bug Template
- ID:
- Title:
- Area: (GUI / Generator / Catalog / Packaging / Docs)
- Priority: (P0-P3)
- Repro steps:
- Expected:
- Actual:
- Environment:
- Proposed fix:
- Test/verification:
- Status:

## Desktop GUI Validation Strategy
Primary for PySide6 app:
- pytest + pytest-qt (QtBot) for deterministic widget-level tests.

Secondary fallback:
- image/OS-level automation only where Qt hooks are insufficient.

Web surfaces:
- Playwright.

## Initial Queue
- (empty)
