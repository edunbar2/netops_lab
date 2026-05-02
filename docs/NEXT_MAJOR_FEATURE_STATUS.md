# Next Major Feature Status

Branch: `local-agent/next-major-feature-roadmap`

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
Result: 0 error(s), 1 warning(s)

python -m unittest discover -s tests
Ran 35 tests - OK
```

The one validator warning is intentional:

```text
study_paths.rhel9-operations: Study path is defined but has no scenarios assigned.
```

The GUI does not currently show RHEL9 Operations because no scenarios use it yet.

### CI integration

Updated `.github/workflows/unit-tests.yml` to run:

```bash
python tools/validate_catalog.py
python -m unittest discover -s tests
```

The validator is non-strict in CI for now so planned warnings do not block patch work. Future release hardening can switch to `--strict` after RHEL9 content exists or warnings are otherwise resolved.

### Study-path content seeding

Seeded two previously empty study paths using existing mature scenarios only. No placeholder labs were added.

Current study-path usage:

```text
ccna-foundations: 170
ccnp-enterprise: 312
secure-enclave-networking: 20
network-troubleshooting: 24
rhel9-operations: 0
```

GUI-visible populated study paths now include:

- CCNA Foundations
- CCNP Enterprise
- Secure Enclave Networking
- Network Troubleshooting

RHEL9 Operations remains defined internally but hidden from the GUI filter until real content is assigned.

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

1. Build the first real RHEL9 Operations seed labs instead of using placeholders.
2. Decide whether validator CI should remain non-strict or become strict for release branches only.
3. Add a GUI/CLI action for running catalog validation from developer workflows if desired.
4. Continue toward roadmap item 4.0.2/4.0.3 content-quality improvements.
