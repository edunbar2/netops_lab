# NetOps Lab Curriculum Polish Implementation Plan

> **For Hermione:** Hand this to Hephaestus as a constrained implementation prompt. Hephaestus is currently running on qwen27b, so keep execution scoped to one numbered task at a time and require validator output after each task.

**Goal:** Turn the 2026-05-04 curriculum audit findings into a small, PR-ready polish pass: refresh stale docs, fill empty study-plan sections, add explicit guided paths for underrepresented tracks, and rewrite generic guided-build content.

**Architecture:** This is a catalog/docs-only change. Source of truth is `catalogs/ccnp_encor_lab_catalog.json`; generated/staged copies under `build/packaging/data-stage/` must not be edited. Docs in `docs/` should be synchronized from catalog reality after catalog edits.

**Tech Stack:** Python JSON catalog, markdown docs, existing validators/tests.

---

## Delegation brief for Hephaestus

```text
Task: Implement the NetOps Lab curriculum polish pass described in docs/plans/2026-05-04-hephaestus-curriculum-polish-plan.md.

Relevant context:
- Repo: /home/edunbar/netops_lab
- Branch: feat/config-lab-wave1-batch-a
- Audit evidence from 2026-05-04:
  - scripts/audit_guided_content.py PASS for 447 scenarios
  - scripts/audit_labs.py --host-type alpine PASS, 0 errors / 0 warnings
  - tools/validate_catalog.py --strict PASS, 0 errors / 0 warnings
  - ./gns3_ccnp_lab_generator.py --qa-report PASS, 0 issues, 447 scenarios / 238 unique concepts
- Audit findings to fix:
  1. 10 newer Wave 1 guided-build labs still use generic content.
  2. Explicit study plans cover only 147/238 unique concepts.
  3. RHEL9 has 8 tagged scenarios but no explicit guided plan.
  4. Secure Enclave and Network Troubleshooting tracks are underrepresented in guided plans.
  5. docs/GUIDED_STUDY_PLANS.md has empty virtualization sections.
  6. docs/ENCOR_COVERAGE_MATRIX.md and docs/CURRICULUM_QA_REPORT.md are stale.

Primary objective:
- Produce a focused docs/catalog PR that improves guided study-path completeness without adding new scenario volume.

Constraints:
- Work only in /home/edunbar/netops_lab.
- Do not edit build/packaging/data-stage/*.
- Do not rename or delete scenario IDs.
- Prefer minimal JSON edits and markdown syncs.
- Use existing schema/style; inspect nearby study_plans entries before modifying.
- If uncertain whether a scenario belongs in a plan, choose the smallest reasonable curated subset and document the choice.
- Commit in small chunks only after validation passes.

Allowed tools/actions:
- Inspect files.
- Modify catalog JSON and markdown docs.
- Run local validators/tests listed in this plan.
- Commit to the current feature branch if tests pass.

Disallowed tools/actions:
- No production/system changes.
- No package installs unless blocked and explicitly approved.
- No edits to generated build/packaging/data-stage files.
- No merge to main.
- No push unless Hermione/Eric explicitly ask.

Expected output format:
- Per task: changed files, concise summary, exact validation command output, commit hash if committed.
- Final: PR-ready summary plus any residual gaps.

Risk level: 1 (repo docs/catalog edit). Security-adjacent educational content only; no real credentials or live exposure.
Aegis review required: no, unless implementation introduces real secrets, public exposure, shell execution features, or operational security controls outside the lab catalog.
User approval likely required: no for draft/branch edits; yes before push/PR merge.
```

## Qwen27b execution rules

Give Hephaestus only one task at a time. qwen27b is capable but easier to steer with narrow, concrete prompts.

Use this wrapper before each task:

```text
You are Hephaestus. Execute ONLY Task N from the plan. Do not broaden scope. Before editing, inspect the exact files named in the task. After editing, run the exact validation commands. If validation fails, fix once; if still failing, stop and report the failure with file/line details. Do not edit build/packaging/data-stage/*. Do not push.
```

Require this completion schema:

```text
Task N result:
- Files changed:
- What changed:
- Validation run:
- Validation result:
- Commit:
- Residual risk / TODO:
```

---

## Task 0: Establish clean baseline

**Objective:** Verify Hephaestus is on the intended branch with a clean or understood working tree.

**Files:** None.

**Steps:**
1. Run:
   ```bash
   git status --short --branch
   git log --oneline -3
   ```
2. Confirm branch is `feat/config-lab-wave1-batch-a`.
3. If uncommitted changes exist, stop and report them before editing.

**Verification:** No file changes.

---

## Task 1: Rewrite the 10 generic Wave 1 guided-build labs

**Objective:** Replace generic `symptom`, `expected_results`, `hints`, `answer_key`, and `coaching_notes` content for the 10 newer Wave 1 scenarios that still read like templates.

**Modify:**
- `catalogs/ccnp_encor_lab_catalog.json`

**Do not modify:**
- `build/packaging/data-stage/catalogs/ccnp_encor_lab_catalog.json`

**Scenario IDs needing targeted rewrite:**
1. `ccnp_bgp_ebgp_ibgp_localpref_med`
2. `ccnp_vrf_lite_mp_bgp_leak`
3. `ccnp_netflow_flexible_monitor_export`
4. `senk_asav_static_nat_dmz_publishing`
5. `senk_aaa_tacacs_local_fallback`
6. `senk_site2site_ipsec_ikev2_vti`
7. `rhel9_vlan_subinterfaces_nmcli`
8. `rhel9_firewalld_zones_services_richrules`
9. `nt_config_ip_sla_track_failover`
10. `nt_config_change_window_checkpoint_rollback`

**Rewrite requirements per scenario:**
- `symptom`: one lab-specific sentence that states the concrete build objective.
- `expected_results`: 2-4 lab-specific observable outcomes.
- `hints`: 3 lab-specific hints; avoid generic "verify incrementally" wording unless paired with a concrete command/technology.
- `answer_key.root_cause`: explain that the starter baseline intentionally lacks the named feature/control.
- `answer_key.fix_summary`: name the concrete controls to configure.
- `answer_key.verification`: keep existing command list unless clearly incomplete.
- `coaching_notes`: 2-3 lab-specific mistakes/teaching points.

**Content guardrails:**
- Do not add real secrets. For AAA/IPsec examples, use placeholders like `<tacacs-key>` or lab-only RFC1918/example addresses already implied by the scenario.
- Do not invent topology device names unless already present in the scenario.
- Prefer vendor-neutral learning language when exact device names are unknown.

**Validation after edit:**
```bash
python tools/validate_catalog.py --strict
python scripts/audit_guided_content.py
```
Expected: both pass; strict catalog reports 0 errors / 0 warnings.

**Commit if valid:**
```bash
git add catalogs/ccnp_encor_lab_catalog.json
git commit -m "docs: specialize Wave 1 guided build coaching content"
```

---

## Task 2: Fill ENCOR virtualization study-plan gaps

**Objective:** Populate the empty Virtualization sections in `study_plans.encor-core`, `study_plans.encor-complete`, and `docs/GUIDED_STUDY_PLANS.md`.

**Modify:**
- `catalogs/ccnp_encor_lab_catalog.json`
- `docs/GUIDED_STUDY_PLANS.md`

**Known gap:**
- `docs/GUIDED_STUDY_PLANS.md` lines 54-60 and 127-133 have `Labs:` with no entries.
- Catalog `study_plans.encor-complete.steps[].title == "Virtualization"` has `scenario_ids: []`.

**Candidate scenarios to inspect/select:**
- Search catalog for topic/domain values containing `VRF`, `GRE`, `VXLAN`, `Overlay`, `Underlay`, `Virtualization`, `Tunnel`.
- The audit noted existing unique concepts include VRF=3, GRE=3, NX-OS=2, Overlay Concepts=1.
- Include `ccnp_vrf_lite_mp_bgp_leak` if it remains valid after Task 1.

**Implementation rules:**
- Choose 3-6 stable scenario IDs for `encor-complete` virtualization.
- Choose 2-4 representative scenario IDs for `encor-core` virtualization.
- Only use scenario IDs that already exist in `catalogs/ccnp_encor_lab_catalog.json`.
- Keep IDs sorted in a reasonable learning order: basic segmentation/tunnel first, then route leaking/overlay interpretation.
- Update the markdown list to match the catalog study plan exactly.

**Validation:**
```bash
python tools/validate_catalog.py --strict
./gns3_ccnp_lab_generator.py --list-study-plan encor-core
./gns3_ccnp_lab_generator.py --list-study-plan encor-complete
```
Expected: strict validation 0/0; both listed plans include virtualization labs.

**Commit if valid:**
```bash
git add catalogs/ccnp_encor_lab_catalog.json docs/GUIDED_STUDY_PLANS.md
git commit -m "docs: fill ENCOR virtualization study plan gaps"
```

---

## Task 3: Add explicit RHEL9 Operations guided study plan

**Objective:** Add a first-class guided plan for the 8 existing RHEL9-tagged scenarios.

**Modify:**
- `catalogs/ccnp_encor_lab_catalog.json`
- `docs/GUIDED_STUDY_PLANS.md`

**Plan key:** `rhel9-operations`

**Plan title:** `RHEL9 Operations Practical Path`

**Implementation rules:**
- Use only existing RHEL9 scenarios.
- Inspect catalog for scenario IDs where `study_tracks`/tags/path/topic/domain imply RHEL9 or Linux endpoint operations.
- Include the known Wave 1 IDs:
  - `rhel9_nmcli_static_ip_dns`
  - `rhel9_vlan_subinterfaces_nmcli`
  - `rhel9_firewalld_zones_services_richrules`
- Include the five Step 3 RHEL9 labs noted in working context if present:
  - systemd recovery
  - rsyslog forwarding queues
  - chrony hardening
  - SELinux context recovery
  - Podman systemd autostart
- Organize into 3-4 steps, for example:
  1. Network identity and addressing
  2. Service recovery and logging
  3. Time/security policy hardening
  4. Container service operations

**Docs:**
- Add a `## RHEL9 Operations Practical Path` section to `docs/GUIDED_STUDY_PLANS.md` with matching steps and IDs.
- Add CLI usage example:
  ```bash
  ./gns3_ccnp_lab_generator.py --list-study-plan rhel9-operations
  ```

**Validation:**
```bash
python tools/validate_catalog.py --strict
./gns3_ccnp_lab_generator.py --list-study-plan rhel9-operations
```
Expected: strict validation 0/0; CLI prints the new plan and all referenced scenario IDs.

**Commit if valid:**
```bash
git add catalogs/ccnp_encor_lab_catalog.json docs/GUIDED_STUDY_PLANS.md
git commit -m "docs: add RHEL9 operations guided study path"
```

---

## Task 4: Add Secure Enclave and Network Troubleshooting guided plans

**Objective:** Make underrepresented `study_paths` visible as explicit guided plans.

**Modify:**
- `catalogs/ccnp_encor_lab_catalog.json`
- `docs/GUIDED_STUDY_PLANS.md`

**Plan keys:**
- `secure-enclave-networking`
- `network-troubleshooting`

**Implementation rules:**
- Use only existing scenarios.
- For Secure Enclave, inspect/select scenarios from ASAv, AAA, ACLs, CoPP, access-edge security, management-plane restrictions, audit readiness, secure baseline validation, and SENK-prefixed labs.
- For Network Troubleshooting, inspect/select incident-style scenarios across L2, routing, services, assurance, and security. Prefer troubleshooting/fault labs over build labs unless a build lab is explicitly useful as a capstone.
- Keep each plan small and curated: 4-6 steps, 1-4 scenario IDs per step.
- Do not try to include every scenario. This is a usable guided path, not a catalog dump.

**Suggested Secure Enclave structure:**
1. Access-edge controls
2. Management-plane and AAA hardening
3. Firewall/NAT policy validation
4. Encrypted transport / site-to-site controls
5. Audit-ready baseline validation

**Suggested Troubleshooting structure:**
1. L2 and endpoint reachability incidents
2. Routing adjacency/path incidents
3. Services and assurance incidents
4. Security policy incidents
5. Capstone operational troubleshooting

**Validation:**
```bash
python tools/validate_catalog.py --strict
./gns3_ccnp_lab_generator.py --list-study-plan secure-enclave-networking
./gns3_ccnp_lab_generator.py --list-study-plan network-troubleshooting
```
Expected: strict validation 0/0; both plans list without missing scenario errors.

**Commit if valid:**
```bash
git add catalogs/ccnp_encor_lab_catalog.json docs/GUIDED_STUDY_PLANS.md
git commit -m "docs: add secure enclave and troubleshooting study paths"
```

---

## Task 5: Refresh stale curriculum report docs from current catalog reality

**Objective:** Update stale summary docs so they match current audit numbers and no longer describe the older 0.17.0 / 291-298 scenario state.

**Modify:**
- `docs/ENCOR_COVERAGE_MATRIX.md`
- `docs/CURRICULUM_QA_REPORT.md`

**Known stale values:**
- Current audit: 447 scenarios / 238 unique concepts.
- `docs/CURRICULUM_QA_REPORT.md` currently says 298 scenario entries / 151 unique concepts.
- `docs/ENCOR_COVERAGE_MATRIX.md` currently says 291 scenario entries / 147 unique concepts.

**Implementation rules:**
- Regenerate or compute counts from `catalogs/ccnp_encor_lab_catalog.json`; do not hand-wave.
- Update summary sections and any release/version wording so the docs read as current-state reports, not old 0.17.0 snapshots.
- Keep the docs concise. Do not add a massive scenario list.
- If an existing tool already produces the matrix/report, use it; otherwise write a one-off local Python snippet to compute counts, then update markdown manually.

**Suggested commands for discovery:**
```bash
python - <<'PY'
import json
from collections import Counter
with open('catalogs/ccnp_encor_lab_catalog.json') as f:
    data=json.load(f)
sc=data['scenarios']
items=sc.values() if isinstance(sc, dict) else sc
concepts={s.get('concept_id') or s.get('id') for s in items}
print('Scenario entries:', len(list(items)))
print('Unique concepts:', len(concepts))
PY
./gns3_ccnp_lab_generator.py --qa-report
```

**Validation:**
```bash
python tools/validate_catalog.py --strict
./gns3_ccnp_lab_generator.py --qa-report
```
Expected: strict validation 0/0; QA report still 0 issues.

**Commit if valid:**
```bash
git add docs/ENCOR_COVERAGE_MATRIX.md docs/CURRICULUM_QA_REPORT.md
git commit -m "docs: refresh curriculum QA and coverage reports"
```

---

## Task 6: Final full validation and PR-ready handoff

**Objective:** Prove the polish pass did not break catalog integrity or tests.

**Run:**
```bash
python tools/validate_catalog.py --strict
python scripts/audit_guided_content.py
python scripts/audit_labs.py --host-type alpine
./gns3_ccnp_lab_generator.py --qa-report
python -m unittest discover -s tests
```

**Expected:**
- Strict catalog validation: 0 errors / 0 warnings.
- Guided content audit: PASS.
- Lab audit: PASS, 0 errors / 0 warnings.
- QA report: 0 issues.
- Unit tests: pass. Existing skipped tests are acceptable if unchanged.

**Final report to Hermione:**
```text
Curriculum polish complete.
Commits:
- <hash> docs: specialize Wave 1 guided build coaching content
- <hash> docs: fill ENCOR virtualization study plan gaps
- <hash> docs: add RHEL9 operations guided study path
- <hash> docs: add secure enclave and troubleshooting study paths
- <hash> docs: refresh curriculum QA and coverage reports

Validation:
- python tools/validate_catalog.py --strict: <result>
- python scripts/audit_guided_content.py: <result>
- python scripts/audit_labs.py --host-type alpine: <result>
- ./gns3_ccnp_lab_generator.py --qa-report: <result>
- python -m unittest discover -s tests: <result>

Residual gaps:
- <only if any>
```

---

## Hermione review checklist

Before accepting Hephaestus output:
- Verify `git diff --stat origin/feat/config-lab-wave1-batch-a...HEAD` or equivalent contains only intended docs/catalog files.
- Verify no `build/packaging/data-stage/*` files were modified.
- Re-run at least:
  ```bash
  python tools/validate_catalog.py --strict
  python scripts/audit_guided_content.py
  ./gns3_ccnp_lab_generator.py --qa-report
  ```
- Spot-check the 10 generic scenario IDs to confirm generic phrases are gone.
- Confirm `docs/GUIDED_STUDY_PLANS.md` no longer has empty `Labs:` sections for virtualization.
