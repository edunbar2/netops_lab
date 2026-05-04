# Version Completion Checklist (Roadmap-Derived)

Scope definition from product owner (Eric):
- "Version complete" = roadmap items completed and PR ready to submit.
- Packaging handled by GitHub Actions in PR/CI.
- Bug manual verification can happen during PR review.
- Scope freezes once roadmap items are complete.

## A) Pre-next-major roadmap execution

- [x] Step A complete: Guided Network Configuration Expansion (Wave 1 implemented)
  - Evidence: `docs/CONFIG_LAB_WAVE1_TASKS.md` all 20 labs checked
  - Evidence commits: `d1937d5`, `82ce963`, `f1d98f2`

- [x] Step B code fixes complete: Minor Stabilization Release bugfixes implemented
  - BUG-001 fixed: long-idle readiness FD failure
  - BUG-002 fixed: large-display text/topology scaling
  - BUG-003 fixed: console artifact rendering
  - Evidence commits: `ac7bd18`, `59a6257`, `7995d3c`

- [ ] Step B verification pending in PR review (explicitly accepted by owner)
  - BUG-001 overnight/long-idle manual validation
  - BUG-002 multi-monitor/HiDPI manual validation
  - BUG-003 manual console checks (IOS/ASAv/RHEL)

## B) Follow-up roadmap items (Section 6)

- [x] 6.1 RHEL9 Operations Seed Labs complete and expanded
  - Current `rhel9-operations` scenario count: 8
  - Expansion commit: `6ade52e`

- [x] 6.2 Strict catalog validation complete
  - CI command: `python tools/validate_catalog.py --strict`
  - Strict validation passes with 0 errors / 0 warnings

- [ ] 6.3 Developer UX for catalog validation (planned, explicitly out-of-scope for this version)
- [ ] 6.4 Catalog metadata normalization (planned, explicitly out-of-scope for this version)

## C) PR readiness gates

- [x] Roadmap and status docs synced to current branch reality
  - `docs/NEXT_MAJOR_FEATURE_ROADMAP.md`
  - `docs/NEXT_MAJOR_FEATURE_STATUS.md`

- [x] Local validation green
  - `python tools/validate_catalog.py --strict`
  - `python -m unittest discover -s tests`

- [ ] Containerized validation run with dependencies installed (Podman)
  - Purpose: reproducible test environment with required Python deps

- [ ] PR opened with:
  - Summary of completed roadmap scope
  - Release notes summary
  - This checklist posted as a PR comment

## D) Scope freeze declaration for this version

When the unchecked items in section C are complete, this version is considered complete for PR submission and scope is frozen.
