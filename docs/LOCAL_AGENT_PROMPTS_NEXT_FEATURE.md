# Local Agent Prompts - Next Major Feature Work

Branch: `local-agent/next-major-feature-roadmap`

Use these prompts with the local model at `http://localhost:8080/api/v1/chat`.

## Operating rules

You are assisting on NetOps Labs, a Python/PySide6/GNS3 lab generation application.

Priorities:
1. Preserve existing 3.x and 4.0 compatibility.
2. Avoid destabilizing the PySide6 GUI.
3. Prefer small, testable changes.
4. Add or update tests for new behavior.
5. Keep public release versioning strict `major.minor.patch`.
6. Do not remove historical GNS3 CCNP Labs references when they are useful for migration/compatibility notes.

Current strategic priority:
- Build catalog validation tooling before expanding study paths/content.

Roadmap-aligned immediate target:
- Add a local catalog validator that checks NetOps Labs 4.x metadata quality and legacy compatibility.

## Prompt 1 - Validator design

Review the project shape conceptually:
- Root generator: `gns3_ccnp_lab_generator.py`
- Qt GUI: `gns3_ccnp_lab_gui_qt.py`
- Catalog: `catalogs/ccnp_encor_lab_catalog.json`
- Existing tests: `tests/`
- Packaging helper: `tools/build_packages.py`

Design a `tools/validate_catalog.py` script and tests for it.

Required validator behavior:
- Load a catalog JSON file, defaulting to `catalogs/ccnp_encor_lab_catalog.json`.
- Validate top-level catalog shape: required keys `templates`, `topologies`, `scenarios`, `study_paths`.
- Validate every scenario has required metadata or can be legacy-normalized safely.
- Required/normalized scenario metadata:
  - `study_paths`
  - `domains` or fallback derivation from existing `domain`
  - `lab_type`
  - `difficulty`
  - `platforms` or fallback derivation from topology/template/deployment metadata
  - `estimated_minutes` where possible, but do not fail legacy content just because it is missing
  - `exam_alignment`
- Validate values are consistent enough for UI filters:
  - known study paths must be defined in top-level `study_paths`
  - lab type values should be normalized to supported canonical values
  - difficulty values should be normalized to supported canonical values
  - platforms should be lower-case tokens
- Validate references:
  - scenario topology exists in `topologies`
  - topology template references exist in `templates` where detectable
- Detect common answer leakage risks in student-facing scenario fields:
  - title or visible symptom text contains exact root-cause phrases, obvious broken commands, or answer markers
  - this should warn by default, not hard fail initially
- Produce clear actionable output.
- Exit nonzero only for errors by default; warnings should not fail unless `--strict` is passed.
- Include CLI flags:
  - `--catalog PATH`
  - `--strict`
  - `--json`
  - `--quiet`
- Avoid importing PySide6 or making network calls.

Deliverables requested from you:
1. Proposed module structure/classes/functions.
2. CLI behavior and exit-code policy.
3. Test plan.
4. Specific implementation notes for legacy compatibility.

Return concise but precise guidance. Do not generate a massive patch.

## Prompt 2 - Content expansion planning

After the validator exists, plan the first minimal content expansion for the empty study paths:
- `secure-enclave-networking`
- `rhel9-operations`
- `network-troubleshooting`

Output a small, testable plan. Do not propose dozens of labs at once. Prioritize 2-3 seed labs per path and describe what metadata/schema support they need.

## Prompt 3 - Code review checklist

Review any proposed implementation against:
- backwards compatibility
- CLI usability
- test coverage
- packaging impact
- no unnecessary dependency additions
- no PySide6 import from CLI tools
- clear warnings/errors
