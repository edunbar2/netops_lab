# Next Major Feature Roadmap

```yaml
agent_readable: true
project: NetOps Labs
target_branch: local-agent/next-major-feature-roadmap
roadmap_version: 2026-05-02
release_type: feature
current_status: pr-prep
primary_goal: catalog-quality-foundation-and-study-path-seeding
```

## 1. Feature Objective

Prepare the next feature release by adding a standalone catalog validation foundation, wiring it into CI, and making the 4.x study-path model safer to extend.

The feature should remain compatible with existing 3.x/4.0 catalog metadata and must not require PySide6, GNS3, network access, or local agent state to validate catalog quality.

## 2. Completed Work

### 2.1 Catalog Validator

Status: `complete`

Added `tools/validate_catalog.py`.

Capabilities:

- validates required top-level catalog sections: `templates`, `topologies`, `scenarios`, `study_paths`
- validates scenario study-path references
- validates scenario topology references
- validates topology node template references
- allows known logical endpoint placeholders such as `host`
- supports legacy-compatible normalization counters for:
  - singular `domain`
  - legacy lab types such as `troubleshooting`, `skill-check`, `interpretation`
  - legacy difficulties such as `intro`, `easy`, `medium`, `hard`, `capstone`
- warns on optional quality metadata gaps such as missing `estimated_minutes`
- warns on defined but empty study paths
- warns on common student-facing answer leakage patterns
- emits human-readable text by default
- emits machine-readable JSON with `--json`
- supports strict warning failure with `--strict`

Primary commands:

```bash
python tools/validate_catalog.py
python tools/validate_catalog.py --json
python tools/validate_catalog.py --strict
python tools/validate_catalog.py --catalog catalogs/ccnp_encor_lab_catalog.json
```

### 2.2 Tests

Status: `complete`

Added `tests/test_validate_catalog.py`.

Coverage includes:

- valid legacy-compatible catalog behavior
- missing required top-level keys
- unknown study paths
- missing topology references
- missing template references
- optional metadata warnings
- platform derivation from topology templates
- answer-leakage warning detection
- empty study-path warnings
- CLI exit-code behavior
- current bundled catalog has no validation errors

### 2.3 CI Integration

Status: `complete`

Updated `.github/workflows/unit-tests.yml` so pull requests run:

```bash
python tools/validate_catalog.py
python -m unittest discover -s tests
```

Current CI mode is non-strict because the catalog intentionally defines `rhel9-operations` before real RHEL9 seed labs are assigned.

### 2.4 Study-Path Seeding

Status: `complete`

Seeded existing mature scenarios into these study paths without adding placeholder labs:

- `secure-enclave-networking`
- `network-troubleshooting`

Current validator-reported study-path usage:

```text
ccna-foundations: 170
ccnp-enterprise: 312
secure-enclave-networking: 20
network-troubleshooting: 24
rhel9-operations: 0
```

### 2.5 Local Agent Hygiene

Status: `complete`

Updated `.gitignore` so local pi agent state and local generated artifacts are not included in the project.

Important ignored paths/patterns:

```gitignore
.pi/
.pi/**
generated_labs/
local_templates_*.json
netops roadmap.rtf
```

## 3. Current Verification Snapshot

Last local verification:

```text
python tools/validate_catalog.py
Result: 0 error(s), 1 warning(s)

python -m unittest discover -s tests
Ran 35 tests - OK
```

Known warning:

```text
study_paths.rhel9-operations: Study path is defined but has no scenarios assigned.
```

Disposition: acceptable for this feature PR. The GUI remains driven by populated scenario metadata, and no placeholder RHEL9 labs were added.

## 4. Pull Request Scope

Recommended PR title:

```text
Add catalog validation and seed study-path coverage
```

Recommended PR summary:

- Add standalone catalog metadata/reference validator with text and JSON output.
- Add validator unit tests and CI integration.
- Seed Secure Enclave Networking and Network Troubleshooting study paths from existing mature scenarios.
- Document local-agent prompts, status, and roadmap for future agent-assisted work.
- Keep `.pi` and local generated artifacts out of the project.

Files expected in the PR:

```text
.github/pull_request_template.md
.github/workflows/unit-tests.yml
.gitignore
CHANGELOG.md
catalogs/ccnp_encor_lab_catalog.json
docs/LOCAL_AGENT_PROMPTS_NEXT_FEATURE.md
docs/NEXT_MAJOR_FEATURE_ROADMAP.md
docs/NEXT_MAJOR_FEATURE_STATUS.md
tests/test_validate_catalog.py
tools/validate_catalog.py
```

Files not expected in the PR:

```text
.pi/**
generated_labs/**
local_templates_raw.json
local_templates_summary.json
netops roadmap.rtf
```

## 5. Release Readiness Checklist

```yaml
catalog_validator: complete
validator_tests: complete
ci_integration: complete
study_path_seeding: complete
changelog_updated: complete
roadmap_updated: complete
gitignore_agent_state: complete
unit_tests_pass: complete
catalog_validation_errors: 0
catalog_validation_warnings: 1
manual_gns3_required: false
manual_gns3_reason: metadata-validation-and-ci-only-change-no-live-gns3-behavior-change
pr_ready: true
```

## 6. Follow-Up Roadmap

### 6.1 RHEL9 Operations Seed Labs

Status: `next`

Add real RHEL9 Operations labs instead of placeholders. Candidate starter topics:

1. service reachability and firewall basics
2. log review and systemd troubleshooting
3. basic network configuration and DNS validation

Acceptance criteria:

- at least 2 real `rhel9-operations` scenarios
- no answer leakage in student-facing fields
- validator warning for empty `rhel9-operations` is resolved
- CI can optionally move to `python tools/validate_catalog.py --strict`

### 6.2 Strict Catalog Validation for Release Branches

Status: `planned`

After RHEL9 seed content exists, consider switching release-branch CI to strict validation.

Acceptance criteria:

- `python tools/validate_catalog.py --strict` exits `0`
- all warnings are either fixed or explicitly downgraded by policy

### 6.3 Developer UX for Catalog Validation

Status: `planned`

Potential additions:

- GUI Settings action: `Validate Catalog`
- CLI convenience command wrapping `tools/validate_catalog.py`
- JSON report artifact in CI

### 6.4 Catalog Metadata Normalization

Status: `planned`

Gradually normalize legacy catalog fields while preserving compatibility:

- convert singular `domain` to `domains`
- convert legacy `lab_type` values to canonical values
- convert legacy `difficulty` values to canonical values
- add `estimated_minutes` where missing

## 7. Agent Handoff Notes

For future agents:

1. Do not include `.pi` contents in commits.
2. Do not commit generated lab output unless a user explicitly requests fixture data.
3. Keep catalog validator standalone; do not import PySide6 or perform network calls.
4. Preserve 3.x/4.0 catalog compatibility while improving 4.x metadata quality.
5. Treat the current RHEL9 Operations warning as known and acceptable until real RHEL9 seed labs are added.
6. Run both verification commands before updating PR status:

```bash
python tools/validate_catalog.py
python -m unittest discover -s tests
```
