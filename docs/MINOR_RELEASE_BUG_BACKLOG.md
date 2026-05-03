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

## Initial Queue

- ID: BUG-001
- Title: Readiness check fails after long idle period (Bad file descriptor)
- Area: Backend / Generator
- Priority: P1
- Repro steps:
  1) Leave project/app running overnight.
  2) In the morning, click Generate, select a lab scenario.
  3) Click readiness/preflight check.
- Expected:
  - Readiness check runs preflight and reports pass/fail status for selected scenario.
- Actual:
  - Command exits immediately with fatal Python init error and no readiness result.
  - Error excerpt: `Fatal Python error: init_sys_streams ... OSError: [Errno 9] Bad file descriptor`.
- Environment:
  - macOS pathing observed (`/opt/anaconda3/bin/python3`, `/Users/edunbar/...`).
  - Triggered after extended idle session.
- Proposed fix:
  - Audit process launch path for stale/closed stdio handles after long-lived UI sessions.
  - Explicitly set `stdin=subprocess.DEVNULL` and capture stdout/stderr pipes in preflight subprocess execution.
  - Add recovery behavior: if first preflight launch fails with FD-related init error, re-spawn once with a clean process context and surface actionable UI message.
- Test/verification:
  - Add regression test around generator command invocation with controlled closed-FD simulation.
  - Manual: keep app open overnight (or simulate stale session), run preflight, confirm successful execution/result rendering.
- Status: fixed (pending overnight/long-idle verification)

- ID: BUG-002
- Title: Text does not scale with larger UI/window sizes
- Area: GUI
- Priority: P2
- Repro steps:
  1) Open app on large monitor.
  2) Maximize/full-screen window.
  3) Inspect guided learning/docs/scenario details/console text and topology labels/icons.
- Expected:
  - Text and topology rendering scale to maintain readability as viewport increases.
- Actual:
  - Widget text remains effectively fixed-size; readability worsens on large displays.
  - Topology node labels/icons appear too small relative to viewport.
- Environment:
  - Larger monitor / fullscreen usage.
- Proposed fix:
  - Introduce UI scale model (base font + DPI/viewport-aware multiplier).
  - Apply to document/detail/console widgets and topology label/icon rendering.
  - Add user-facing display scaling preference override.
- Test/verification:
  - GUI validation with multiple window sizes/DPI settings; confirm readable minimum font and topology label scale.
  - Add pytest-qt assertions for font-size changes on resize where practical.
- Status: triaged

- ID: BUG-003
- Title: Console shows character artifact boxes for some device output
- Area: GUI
- Priority: P3
- Repro steps:
  1) Open console to network node.
  2) Observe output containing extended/control characters.
- Expected:
  - Console renders characters cleanly (or safely substitutes unsupported glyphs without artifacts).
- Actual:
  - Box glyph artifacts appear for some characters; UI appears unstable/unclean.
- Environment:
  - Device console rendering path in desktop UI.
- Proposed fix:
  - Normalize decode path (UTF-8 with fallback strategy), sanitize unsupported control sequences.
  - Ensure terminal widget font supports required glyph ranges; set fallback font stack.
- Test/verification:
  - Replay captured console output containing problematic bytes and validate rendered output has no artifact boxes where avoidable.
  - Manual spot checks across IOS/ASAv/RHEL sessions.
- Status: triaged
