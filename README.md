# NetOps Labs

**Hands-on infrastructure training for networking, Linux, and security.**

NetOps Labs is the 4.0 successor to NetOps Labs. It keeps the existing GNS3-driven networking workflow while reorganizing the catalog around study paths, lab types, domains, and operational skills instead of treating exams as the primary filter.

Existing 3.x generated labs and local metadata remain supported.

## 4.0.0 stable release

4.0.0 keeps the PySide6/Qt interface as the default GUI for NetOps Labs. The legacy Tk/ttkbootstrap GUI is still included as a fallback, but the Qt interface is the normal 3.0 path.

Launch the default Qt GUI:

```bash
python3 gns3_ccnp_lab_gui_qt.py
```

Launch the legacy Tk GUI if needed:

```bash
python3 gns3_ccnp_lab_gui.py
```

Install and launch the default Qt GUI:

```bash
python3 install.py --launch-gui
```

Install and launch the legacy Tk GUI:

```bash
python3 install.py --launch-gui --legacy-tk
```

The 4.0.0 release establishes the NetOps Labs identity and moves the primary catalog model to Study Path, Domain, Lab Type, Difficulty, and Platform-style metadata. Exam alignment is still retained for certification-oriented learners, but it is no longer the primary catalog concept.

## 1.9.2 lab confidence and guided learning foundation

1.9.2 adds the first version of the in-app **Lab Workspace**. After generating a lab, the GUI can load the generated documents, topology map, progressive hints, generation summary, and starter/answer configs directly inside the application. This is groundwork for the larger 2.0 guided-learning milestone while still keeping the generator workflow familiar.

Generated labs now include:

- `topology_map.md`: a device/interface map for comparing GNS3 links against generated configs.
- `metadata.json`: machine-readable lab metadata used by the Lab Workspace.
- improved `hints.md`: progressive hints intended to guide investigation without giving away the answer immediately.

Advanced users still have access to blank topology generation under **Advanced Tools**. Blank topology output now also includes `topology_map.md`, `generation_summary.md`, and `metadata.json`.

# NetOps Labs

## 1.8.1 IOL link/interface alignment fix

1.8.1 fixes IOL/IOU link creation so GNS3 links are attached to the same physical interfaces that the generated configs use. This addresses labs such as `bgp_wrong_remote_as`, where the ISP router could be linked on Ethernet1/0, Ethernet2/0, and Ethernet3/0 while the generated config was applied to Ethernet0/1, Ethernet0/2, and Ethernet0/3.

Key additions:

- IOL logical interface index 0 now maps to Ethernet0/0, 1 to Ethernet0/1, 2 to Ethernet0/2, 3 to Ethernet0/3, and 4 to Ethernet1/0 when creating GNS3 links.
- Preflight adapter checks now account for IOL/IOU adapter modules and ports.
- Catalog validation now checks IOL link/interface alignment to catch future mismatches before release.

## 1.8.0 reliability and feedback release

1.8.0 focuses on usability, clarity, and confidence before generation. It adds a preflight readiness check, a GUI **Check Readiness** action, a generated `generation_summary.md`, and more verbose mentor-style lab guidance. The generated student documents now spend more time explaining how to approach the problem, what to verify first, and when to use hints or the answer key.

## 1.7.3 GUI startup theme persistence fix

1.7.3 fixes GUI startup theme application. Themes selected through `install.py` or `scripts/setup_environment.py` are now applied during initial GUI startup instead of appearing selected in Settings while the window still launches visually as `darkly` until manually toggled.

## 1.7.2 installer and endpoint push default release

1.7.2 adds a root-level `install.py` first-run installer and changes the default behavior so supported endpoint configs are pushed automatically, matching the existing default for Cisco device config push.

Highlights:

- Adds root-level `install.py` for dependency installation, local config creation, template discovery, readiness checks, and optional GUI launch.
- Defaults supported endpoint config push to enabled in the GUI, CLI, and generated local app config.
- Adds `--no-push-endpoints` as a clearer alias for `--skip-endpoints`.
- Adds `first_time_walkthrough.md` to each generated lab.
- Expands `student_brief.md` with procedural, non-answer-giving troubleshooting guidance.
- Expands `answer_key.md` with root-cause explanation, why the fault breaks the lab, detailed fault analysis, corrective action, verification steps, expected outcomes, and grading criteria.
- Keeps `scripts/setup_environment.py` as the lower-level setup helper behind the installer.

- Adds `scripts/validate_catalog.py` for catalog metadata validation.
- Adds a **Validate Catalog** button in the GUI Settings tab.
- Replaces duplicate generated-folder buttons with a single output-area artifact group: **Open Generated Lab Folder**, **Open Lab README**, and **Open Lab Configs**.
- Audits themes: keeps distinct dark themes, reduces built-in light themes to `minty`, `sandstone`, and `morph`, adds custom softer light themes, and adds custom dark green/brown themes.

Current release: **2.0.0**

NetOps Labs creates hands-on infrastructure labs with a networking-first workflow and room for Linux and security study paths. The current release keeps the mature GNS3 project generation and management features while introducing the study-path catalog foundation for future Secure Enclave Networking and RHEL9 Operations content.

The application can create troubleshooting labs, configure-from-requirements skill checks, guided study paths, generated starter/answer configurations, and optional endpoint configuration.

## What this project provides

- A data-driven catalog of GNS3 topologies and lab scenarios.
- ENCOR-focused troubleshooting labs across infrastructure, security, network assurance, automation, virtualization, architecture, and skill checks.
- Guided study plans, including an ENCOR skill-check path.
- A cross-platform GUI for selecting exams, scenarios, topologies, and run options.
- A CLI for automation, listing scenarios, generating projects, and running catalog QA.
- Cisco IOS/IOL/IOSv configuration push over telnet.
- Endpoint auto-push for VPCS, Alpine, and RHEL9 endpoint templates.
- Generated learner artifacts: requirements, hints, expected results, verification steps, grading criteria, and answer keys.
- Richer `student_brief.md` files with scenario context, suggested approach, hints, expected results, and a first-time/stuck walkthrough.
- Template preflight checks to catch adapter-count mismatches before project creation.

## 1.4.0 catalog size

```text
Templates:                14
Topologies:               54
Unique lab concepts:      213
Scenario entries:         422
Legacy/fallback entries:  209
```

Unique lab concepts by exam tag:

```text
CCNA:   85
ENCOR:  158
ENARSI: 39
```

The **unique lab concepts** count is the curriculum count. Scenario entries include IOSv/IOL fallback variants and should not be treated as separate curriculum items.

## Requirements

### GNS3

- GNS3 server reachable over HTTP.
- GNS3 templates matching the catalog template keys.
- Telnet consoles enabled for automatic configuration push.
- Adequate CPU and memory for the selected images.

### Python

Python 3 is required. For first-run setup, use the installer:

```bash
python3 install.py
```

For manual dependency installation only:

```bash
python3 -m pip install -r requirements.txt
```

On Ubuntu or Linux systems where Python 3 is located at `/usr/bin/python3`, the included Linux CLI launcher uses that path directly.

## Recommended GNS3 templates

The catalog supports multiple image families. The current recommended baseline is:

```text
iol2       Layer 2 switching, at least 4 Ethernet adapters
iol3       Routing, at least 8 Ethernet adapters for large/capstone labs
iosv       Legacy router fallback, 4 adapters
iosvl2     Legacy switch fallback, 16 adapters
asav       Firewall/security labs, 8 adapters
cat8000v   IOS-XE edge/router labs, 8 adapters
csr1000v   IOS-XE router labs, 8 adapters
nxosv9000  NX-OS/vPC labs, 10 adapters
vpcs       Endpoint auto-configuration
alpine     Linux endpoint auto-push support
rhel9      Linux endpoint auto-push support
```

The generator checks live GNS3 template data before project creation and reports clear errors when a selected topology needs more Ethernet adapters than a template exposes.

## 1.6.2 GUI sizing and legacy deployments

1.6.2 increases the default GUI window size so the added helper panel and lab action buttons are visible by default. It also renames the old IOSv/IOL filter to **Legacy deployments**. The toggle now switches between current default labs and older IOSv/IOSvL2 or fallback IOL variants marked with `legacy_variant`; it does not mix default and legacy labs in the same view.

Catalog review found no IOSv scenarios marked as non-legacy, so IOSv remains a compatibility fallback rather than the normal recommended path.

## 1.6.1 setup helper and lab-folder access

1.6.1 adds a master setup helper and improves access to generated lab content.

```bash
python3 scripts/setup_environment.py
```

The GUI now includes generated-lab artifact shortcuts so users can open the latest lab folder, README, or config directory after generation.

## 1.6.0 deployment/configuration changes

1.6.0 removes personal/environment-specific defaults from the application.

```text
No default GNS3 server URL is bundled.
User settings belong in config/app_config.local.json.
Template mappings belong in config/template_overrides.local.json.
Example config files are provided and should be copied before editing.
```

Fresh setup is recommended for 1.6.0.

```bash
cp config/app_config.example.json config/app_config.local.json
cp config/template_overrides.example.json config/template_overrides.local.json
```

Set your GNS3 server in `config/app_config.local.json`:

```json
"gns3_server": "http://your-gns3-server"
```

Deployment helper scripts:

```text
scripts/discover_gns3_templates.py
scripts/generate_template_mapping.py
scripts/print_lab_requirements.py
scripts/check_environment_readiness.py
```

See:

```text
UPGRADE_NOTICE_1.6.0.md
docs/DEPLOYMENT_GUIDE.md
docs/ENVIRONMENT_READINESS.md
```

## 1.5.0 GUI polish and theme support

1.5.0 adds a theme selector, beginner-friendly filtering, active filter summaries, clear search, copy CLI command actions, open output folder actions, generation confirmation summaries, and study-plan table polish.

## 1.4.3 Study Plans button visibility fix

1.4.3 keeps the Study Plans action buttons visible at the default GUI size by moving them above the expanding plan details text area and adding a scrollbar to the details pane.

## 1.4.2 template baseline update

1.4.2 updates the bundled template metadata and documentation from the current GNS3 `/v2/templates` API output. The key changes are IOL2 with 8 Ethernet adapters and the RHEL9 `-cpu host` QEMU requirement.

## 1.4.1 GUI sizing fix

1.4.1 increases the default GUI size and changes the main content/output area to a resizable vertical pane so the redesigned 1.4 interface is less likely to be cut off on launch.

## GUI redesign in 1.4.0

The GUI is now organized around the way users normally work:

```text
Labs              Search and filter scenarios.
Study Plans       Follow ordered curriculum paths.
Blank Topologies  Generate nodes and links without a scenario.
Settings          Configure paths, server, host type, and push options.
```

The Labs tab provides a searchable table and filters for study path, deployment, domain, topic, difficulty, and lab type. Exam alignment remains available in scenario details and generated metadata.

The Study Plans tab shows ordered lab sequences. Plans are intended to progress by exam domain and then by prerequisite/difficulty. For example, BGP labs should follow the routing and IGP foundations they depend on.

The Blank Topologies tab is the advanced workflow for users who want topology-only projects with no faults or answer keys.

See `docs/GUI_USER_GUIDE.md` for details.

## Quick start: GUI

Linux:

```bash
./launch_gui_linux.sh
```

macOS:

```bash
./launch_gui_macos.command
```

Windows:

```text
launch_gui_windows.bat
```

From the GUI, select the GNS3 server URL, catalog, study plan or scenario filters, run options, and output directory. Then select **Generate**.

The GUI includes study-plan selection, endpoint push selection, and Linux endpoint credential fields.

## Quick start: CLI

Run CLI commands through Python or through the included CLI launchers. Do not pass CLI flags to the GUI launcher.

Linux:

```bash
./run_cli_linux.sh --qa-report
./run_cli_linux.sh --coverage
./run_cli_linux.sh --list-study-plan encor-skill-checks
ccna-core
ccna-complete
```

macOS:

```bash
./run_cli_macos.command --qa-report
./run_cli_macos.command --coverage
./run_cli_macos.command --list-study-plan encor-skill-checks
ccna-core
ccna-complete
```

Windows:

```text
run_cli_windows.bat --qa-report
run_cli_windows.bat --coverage
run_cli_windows.bat --list-study-plan encor-skill-checks
ccna-core
ccna-complete
```

Direct Python invocation also works:

```bash
python3 ./gns3_ccnp_lab_generator.py --qa-report
python3 ./gns3_ccnp_lab_generator.py --coverage
python3 ./gns3_ccnp_lab_generator.py --list-study-plan encor-skill-checks
ccna-core
ccna-complete
```

## Common CLI examples

Generate a lab:

```bash
python3 ./gns3_ccnp_lab_generator.py --server http://gns3.example.local --scenario l3_ospf_area_mismatch
```

Generate and push Cisco configs:

```bash
python3 ./gns3_ccnp_lab_generator.py --server http://gns3.example.local --scenario l3_ospf_area_mismatch --push-config
```

Generate with VPCS endpoint push:

```bash
python3 ./gns3_ccnp_lab_generator.py \
  --server http://gns3.example.local \
  --scenario skill_encor_eigrp_advanced \
  --host-type vpcs \
  --push-config \
  --push-endpoints
```

Generate with Alpine endpoint push:

```bash
python3 ./gns3_ccnp_lab_generator.py \
  --server http://gns3.example.local \
  --scenario skill_encor_eigrp_advanced \
  --host-type alpine \
  --push-config \
  --push-endpoints \
  --linux-endpoint-username root \
  --linux-endpoint-password ''
```

Generate with RHEL9 endpoint push:

```bash
python3 ./gns3_ccnp_lab_generator.py \
  --server http://gns3.example.local \
  --scenario skill_encor_eigrp_advanced \
  --host-type rhel9 \
  --push-config \
  --push-endpoints \
  --linux-endpoint-username root \
  --linux-endpoint-password '<password-if-required>'
```

## Endpoint configuration

Automatic endpoint push is supported for:

```text
VPCS
Alpine
RHEL9
```

VPCS uses the VPCS console command format. Alpine and RHEL9 use Linux shell setup scripts generated from the endpoint templates.

Linux endpoint push assumes the endpoint console reaches a usable shell. If your image requires a password, set it with:

```bash
--linux-endpoint-username root --linux-endpoint-password '<password>'
```

Endpoint push logs are written under:

```text
endpoint_push_logs/
```

Generated endpoint setup files are still written under:

```text
endpoint_setup/
```

## Generated lab output

Each generated lab includes:

```text
configs/                 Starter/faulty configs, retained for compatibility
starter_configs/         Starter configs intended for the learner
clean_configs/           Known-good configs, retained for compatibility
answer_key_configs/      Known-good answer configs
endpoint_setup/          Endpoint setup artifacts
requirements.md          Lab requirements
hints.md                 Learner hints
expected_results.md      Expected success indicators
verification.md          Suggested verification commands
grading_criteria.md      Skill-check grading criteria where applicable
student_brief.md         Learner-facing lab brief with story, approach, hints, and walkthrough
answer_key.md            Root cause, fix summary, and verification guidance
lab_manifest.json        Machine-readable generation metadata
```

## Student brief

The generated `student_brief.md` is the recommended starting point. It includes:

```text
Scenario story
Observed symptoms
Requirements
Suggested approach
Hints
Expected results
Topology links
Verification commands
Generated file map
First-time or stuck walkthrough
```

Use the answer key only after you have completed the lab or made a good-faith troubleshooting attempt.

## CCNA foundation labs

1.3.0 expands the CCNA-focused foundation track with smaller starter topologies and additional lower-difficulty labs across services, security, wireless interpretation, and automation.

Study plans:

```bash
python3 ./gns3_ccnp_lab_generator.py --list-study-plan ccna-core
python3 ./gns3_ccnp_lab_generator.py --list-study-plan ccna-complete
```

The CCNA starter topologies are intentionally smaller than the ENCOR topologies so learners can practice one concept at a time.

See `docs/CCNA_COVERAGE.md
docs/EXAM_TAGGING_POLICY.md` for the full list.

## Skill checks

Skill checks are configure-from-requirements labs. The ENCOR skill-check track includes:

```text
IPv6 foundation
IPv4/IPv6 dual-stack
Advanced OSPF
EIGRP advanced routing
BGP edge routing
QoS trust boundary and WAN policy
Security edge policy
Automation and assurance workflow
Enterprise WAN capstone
```

Run:

```bash
python3 ./gns3_ccnp_lab_generator.py --list-study-plan encor-skill-checks
ccna-core
ccna-complete
```

## Scope and exclusions

1.1.0 remains a non-controller ENCOR lab curriculum baseline. It intentionally excludes full controller deployments such as:

```text
Full SD-WAN controller labs
Full Catalyst Center / SD-Access controller labs
Full ISE / TrustSec controller workflows
Formal automated grading engine
```

See `docs/RELEASE_1.0_SCOPE.md` and `docs/KNOWN_LIMITATIONS.md` for details.

## Troubleshooting

### Linux endpoint push does not complete

Confirm the endpoint reached a login prompt or shell and that the username/password are correct. Then check the generated log in `endpoint_push_logs/`.

You can apply the generated setup manually from `endpoint_setup/` if console login behavior differs from the expected Alpine/RHEL9 workflow.

### CLI arguments open an editor or Electron/Chromium warning appears

Run the generator through Python:

```bash
python3 ./gns3_ccnp_lab_generator.py --qa-report
```

or use the included CLI launcher scripts. CLI flags belong to `gns3_ccnp_lab_generator.py`, not the GUI launcher.

### Template adapter errors

If a lab fails because a template lacks Ethernet adapters, edit the GNS3 template and increase Ethernet adapters. IOL3 should generally have at least 8 Ethernet adapters for the largest topologies.

### Telnet to `0.0.0.0`

When GNS3 reports a console host of `0.0.0.0`, the generator resolves it to the host portion of `--server`.

## Documentation

Useful documents:

```text
docs/LINUX_ENDPOINT_AUTO_PUSH.md
docs/ENCOR_COVERAGE_MATRIX.md
docs/GUIDED_STUDY_PLANS.md
docs/ENCOR_SKILL_CHECKS.md
docs/SKILL_CHECKS.md
docs/ENDPOINT_AUTO_CONFIG_ROADMAP.md
docs/SCENARIO_QA_METADATA.md
docs/CURRICULUM_QA_REPORT.md
docs/RELEASE_1.0_SCOPE.md
docs/ONE_DOT_ZERO_READINESS.md
docs/KNOWN_LIMITATIONS.md
```

Release history is maintained in `CHANGELOG.md`.



## 2.0.0 Guided Learning Release

The Qt GUI now includes a Guided Learning workspace with Student, Explorer, and Instructor modes. Student mode reveals hints progressively, Explorer mode keeps the workspace open for free browsing, and Instructor mode reduces friction when opening solution material. Generated labs now include `validation_report.md` to help distinguish a learner troubleshooting issue from a generated-lab consistency problem.

Installer maintenance commands:

```bash
python3 install.py --check
python3 install.py --repair
```


## 3.0.0-alpha4 Practice Workspace Foundation

This alpha begins the 3.0 practice-application transition. Generated scenario labs now include structured `content/*.json`, a schema-3.0 `lab_manifest.json`, a slim learner-focused `student_brief.md`, `project_info.md`, explicit `guided_practice.md`, structured hints, and `topology.json` for future topology visualization.


## 3.0 alpha4 highlights

- The Qt Lab Workspace now includes integrated console tabs sourced from GNS3 deployment metadata.
- The graphical topology pane and structured workspace content remain in place.
- `twilight_parchment` remains available as a dark-academia companion theme to `parchment`.


## 3.0 alpha4 lifecycle highlights

- The Qt Lab Workspace now includes a Lifecycle tab for deployed GNS3 projects.
- Users can refresh deployment status, start nodes, stop nodes, reset nodes, and delete the GNS3 project when the lab is complete.
- Delete Project removes the project from GNS3 but keeps local generated lab files by default.


## 3.0 alpha4.1 bugfix

This patch fixes several alpha4 workspace issues: theme-aware selection colors, automatic navigation to the Lab Workspace after generation, initial Guided Learning content, topology visualization rendering, and console endpoint discovery when `console_host` is omitted from GNS3 metadata.


## 3.0.0-alpha4.2 hotfix

Fixes a Qt GUI startup crash from the alpha4.1 theme-highlight patch by adding the missing `QPalette` import.


## 3.0.0-alpha4.3 hotfix

This build focuses on Qt workspace stabilization:

- The topology pane now renders visible device/link graphics from normalized topology data.
- Custom theme highlights, table headers, and group borders use separate theme roles instead of one reused tertiary color.
- The Generate page layout is less cramped on smaller macOS displays.


## 3.0 alpha4.4 fixes

- Generate-tab action buttons now use a compact grid to avoid cropped labels.
- Topology visualization now uses theme-aware background and higher-contrast link rendering.


## 3.0 alpha4.6 notes

- Topology JSON generation now writes real endpoint and adapter data for newly generated labs.
- The topology canvas uses a neutral `#343434` background with high-contrast links.
- If a topology generated in alpha4.5 still has missing device names or `None/None` adapter values, regenerate the lab with alpha4.6.


## 3.0 alpha4.7 layout note

The Qt Generate page right panel was rebalanced so Scenario Details has priority and Generation Options uses less vertical space.


## 3.0 alpha4.8 note

The Generate page right pane now prioritizes Scenario Details as the primary reading area, with generation options and action controls constrained below it.


## 3.0 alpha4.10 polish

- Improved Generate page scenario-detail scrolling and Generation Options field sizing.


## 3.0 beta1 highlights

- Guided Learning is now an explicit step-based Guided Practice workflow.
- The Lab Workspace includes a step list, progress tracking, a dedicated hints pane, and Copy Suggested Commands.
- Student / Explorer / Instructor modes remain available.


## 3.0 beta1.1 polish

- Guided Practice mode selector sizing improved.
- Lab Workspace title shortened to avoid long path collisions.
- Topology redesign planning notes added.


## 3.0 beta1.2 highlights

- Bundled GNS3 symbol assets are now included in `assets/symbols/`.
- The Qt topology view uses symbols where possible and falls back to simple drawn shapes otherwise.
- Links now attach to device edges and labels are offset from the links for better readability.


## 3.0 beta1.3 topology label update

Topology link labels are now shortened in the graphical view, for example `Ethernet0/1` becomes `e0/1` and `GigabitEthernet2/4` becomes `g2/4`. Full interface names remain in the topology table and link detail pane.


## 3.0 beta1.4 highlights

- Bundled the additional GNS3 symbol library, including the `classic/` symbols.
- Topology visualization now defaults to classic symbols for routers, switches, endpoints, firewalls, and clouds.
- Added a Settings dialog to customize topology symbols per device role.
- Shape-based topology rendering remains available as a fallback when no symbol is found.


## 3.0 beta2 highlights

- Added a Practice tab for Start Practice / End Practice workflow.
- Student notes are stored as `student_notes.md` in the generated lab folder.
- Ending a session writes `practice_summary.md`.
- Practice navigation now ties together Guided Learning, Topology, Consoles, and Lifecycle.


## 3.0.0-beta2.2 note

Guided Practice button rows are now aligned so the secondary action row begins under the first action button, not under the Learning Mode controls.


## 3.0 beta3 guided-content quality

Beta3 focuses on the instructional quality of generated labs. Student briefs now frame symptoms as user/operator reports, guided steps include clearer objectives and completion criteria, and answer keys are intended to explain what happened, why it produced the reported symptoms, how to prove it, and how to fix it.


## 3.0.0-beta3.2 hotfix

Suppresses a known harmless Qt text-cursor warning that could appear in the terminal while workspace text panes were refreshed.


## 3.0 beta3.2 note

- Improved readability spacing for structured content rendered inside the Qt app, including guided practice and JSON-backed document sections.


## 3.0 beta3.3 highlights

- Student-facing symptom sections now avoid giving away root-cause clauses.
- The Generate Lab table now prioritizes scenario titles instead of backend IDs.


## 4.0.0 patch release

4.0.0 fixes a Qt worker-thread lifecycle issue that could close the application unexpectedly with `QThread: Destroyed while thread is still running`, especially when refreshing GNS3 Projects, running server actions, using consoles, or closing the app while background work was active.

This release also returns the project to clear major/minor/patch versioning. Future public builds should use versions such as `4.0.0`, `4.0.1`, and `4.1.0` rather than alpha, beta, or RC suffixes.

## 3.0.0 release

3.0.0 promotes the integrated practice workspace to a stable release. It includes guided practice, topology visualization, integrated console access, lab lifecycle controls, practice notes and summaries, and server-level GNS3 project management.

The GNS3 Projects page can refresh and inspect server-side projects, connect to generated or external projects, start or stop selected projects, delete stale projects from the GNS3 server without deleting local lab folders, and filter by all/generated/running/stopped projects. The final 3.0.0 polish pass tightened the Show filter layout so the label and dropdown render as a compact control group.

External projects display this limitation clearly: guided lab content, answer keys, and generated configs are unavailable unless the project was originally generated by this app. Lifecycle controls and console endpoints remain available when the GNS3 API exposes them.

## 3.0.0-rc2a release candidate

3.0.0-rc2a adds a top-level **GNS3 Projects** page for managing projects that already exist on the configured GNS3 server.

Use it to refresh and inspect server-side projects, connect to generated or external projects, start or stop selected projects, delete stale projects from the GNS3 server without deleting local lab folders, and filter by all/generated/running/stopped projects.

External projects display this limitation clearly: guided lab content, answer keys, and generated configs are unavailable unless the project was originally generated by this app. Lifecycle controls and console endpoints remain available when the GNS3 API exposes them.

## 3.0.0-rc1 release candidate

This release candidate freezes the 3.0 feature set for final validation. It includes the integrated practice workspace, guided practice flow, topology visualization with selectable symbols, integrated console access, lab lifecycle controls, practice notes/summaries, and the beta3 guided-content quality improvements.

RC1 should be tested against real generated labs before final 3.0.0 packaging. No major new features are planned between RC1 and final unless a blocking issue is found.