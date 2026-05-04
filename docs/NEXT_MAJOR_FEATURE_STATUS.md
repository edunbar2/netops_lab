# Next Major Feature Status

Branch: `feat/config-lab-wave1-batch-a`

## Completed in this pass

### Catalog validation foundation

Added `tools/validate_catalog.py`, a standalone validator for NetOps Labs catalog quality.

Capabilities:

- Loads `catalogs/ccnp_encor_lab_catalog.json` by default.
- Checks required top-level catalog sections:
  - `templates`
  - `topologies`
  - `scenarios`
  - `study_paths`
- Validates scenario study-path references.
- Validates topology references.
- Validates topology node template references, while preserving compatibility with logical `host` endpoint placeholders.
- Tolerates current legacy values while tracking normalization counts:
  - legacy lab types such as `troubleshooting`, `skill-check`, `interpretation`
  - legacy difficulties such as `intro`, `easy`, `medium`, `hard`, `capstone`
  - legacy singular `domain`
- Warns on missing optional quality metadata such as `estimated_minutes`.
- Warns when defined study paths have no scenarios.
- Provides text and JSON output.
- Supports `--strict` for CI/release hardening.

CLI examples:

```bash
python tools/validate_catalog.py
python tools/validate_catalog.py --json
python tools/validate_catalog.py --strict
python tools/validate_catalog.py --catalog path/to/catalog.json
```

### Tests

Added `tests/test_validate_catalog.py` covering:

- valid current/legacy catalog behavior
- missing top-level keys
- unknown study paths
- missing topology references
- missing template references
- optional metadata warnings
- derived platform behavior
- answer-leakage warnings
- empty study-path warnings
- CLI exit codes
- current catalog has no validation errors

Current verification:

```text
python tools/validate_catalog.py
Result: 0 error(s), 0 warning(s)

python -m unittest discover -s tests
Ran 35 tests - OK (skipped=2)
```

RHEL9 Operations is now seeded with real scenarios and appears in validator usage output.

### CI integration

Updated `.github/workflows/unit-tests.yml` to run:

```bash
python tools/validate_catalog.py --strict
python -m unittest discover -s tests
```

The validator is now strict in CI (`python tools/validate_catalog.py --strict`) because the catalog currently runs clean at 0 errors / 0 warnings.

### Study-path content seeding

Seeded two previously empty study paths using existing mature scenarios only. No placeholder labs were added.

Current study-path usage:

```text
ccna-foundations: 175
ccnp-enterprise: 317
secure-enclave-networking: 24
network-troubleshooting: 27
rhel9-operations: 8
```

GUI-visible populated study paths include all five configured paths, including RHEL9 Operations.

## Local agent involvement

The local model at `http://localhost:8080` was used for:

1. Validator design review.
2. Content expansion planning.
3. Patch/code review.
4. Final release-risk review.

Reusable prompts were saved in:

```text
docs/LOCAL_AGENT_PROMPTS_NEXT_FEATURE.md
```

## Recommended next tasks

1. Complete manual verification and mark BUG-001/BUG-002/BUG-003 as `verified` in `docs/MINOR_RELEASE_BUG_BACKLOG.md`.
2. Prepare a stabilization release notes section summarizing Wave 1 and the three GUI/runtime fixes.
3. Add a GUI/CLI action for running catalog validation from developer workflows if desired.
4. Continue toward roadmap item 4.0.2/4.0.3 content-quality improvements.
