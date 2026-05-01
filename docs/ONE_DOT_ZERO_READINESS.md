# 1.0.0 Readiness Checklist

## Content

- [x] ENCOR infrastructure concepts are covered with representative troubleshooting labs.
- [x] ENCOR security concepts are covered with representative troubleshooting labs.
- [x] ENCOR assurance concepts are covered with representative troubleshooting labs.
- [x] ENCOR automation concepts are covered with representative troubleshooting and interpretation labs.
- [x] ENCOR architecture/design concepts have guided interpretation labs.
- [x] Configure-from-requirements skill checks are included.
- [x] A dedicated ENCOR skill-check path is included.
- [x] Controller-heavy topics are explicitly documented as excluded or simulated.

## Quality

- [x] Every scenario has a clear symptom.
- [x] Every scenario has a fault and fix summary.
- [x] Every scenario has verification commands.
- [x] Every scenario has hints.
- [x] Every scenario has expected results.
- [x] Every scenario has answer-key metadata.
- [x] Skill checks have grading criteria.
- [x] Topology link-adapter uniqueness checks passed for newly added topologies.
- [x] Scenario rendering smoke tests passed for recent content waves.
- [x] IOL and legacy/fallback variants are counted as variants, not unique concepts.

## User experience

- [x] GUI opens at a usable size.
- [x] GUI exposes study-plan selection.
- [x] GUI exposes endpoint push control.
- [x] GUI errors are shown in the output pane.
- [x] Config push uses the correct GNS3 console host when `0.0.0.0` is reported.
- [x] Template mismatch errors fail early with clear remediation.
- [x] VPCS endpoint auto-configuration is implemented and validated.
- [x] Linux endpoint auto-configuration is documented as generated/manual by default.

## Release checks

- [x] `--version` works.
- [x] `--stats` works.
- [x] `--coverage` works.
- [x] `--qa-report` works.
- [x] `--list-study-plan encor-core` works.
- [x] `--list-study-plan encor-skill-checks` works.
- [x] README, CHANGELOG, VERSION, and docs are updated.
- [x] 1.0.0 scope and known limitations are documented.

## 1.1.0 Endpoint Automation

- [x] Alpine endpoint auto-push support is implemented.
- [x] RHEL9 endpoint auto-push support is implemented.
- [x] Linux endpoint credentials are exposed through CLI flags.
- [x] Linux endpoint credentials are exposed in the GUI.
- [x] Generated student briefs include scenario story, suggested approach, and stuck walkthrough.
