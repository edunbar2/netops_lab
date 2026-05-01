
## 3.0.0-alpha4 PySide6 GUI stable release

The 3.0 alpha line uses the PySide6/Qt GUI as the primary interface. Start it with:

```bash
python3 gns3_ccnp_lab_gui_qt.py
```

The legacy Tk GUI remains available during the transition:

```bash
python3 gns3_ccnp_lab_gui.py
```

The Qt GUI is intended to become the foundation for guided learning, richer Lab Workspace views, topology-map tables, config inspection, validation reporting, and future side-by-side config comparison.

# GUI User Guide


## 1.7.1 learner-document changes

Generated labs now include a separate `first_time_walkthrough.md` file. This file is intentionally process-focused: it tells learners how to scope the issue, which verification commands to run, how to inspect the relevant configuration, and how to prove a fix without revealing the exact answer.

Generated `answer_key.md` files are more verbose. They now include a root-cause explanation, why the fault breaks the lab, corrective action summary, detailed fault analysis, verification procedure, expected successful outcomes, and grading criteria.

1.7.0 added curated theme support, cascading filters, legacy deployment filtering, generated-lab artifact shortcuts, and catalog validation.

## Main tabs

```text
Labs
Study Plans
Blank Topologies
Settings
```

## Themes

The Settings tab includes a curated theme selector.

Dark themes kept from ttkbootstrap because they are visually distinct:

```text
darkly       superhero    cyborg       solar        vapor
```

Existing light themes kept after the 1.7 audit:

```text
minty        sandstone    morph
```

Custom softer light themes:

```text
mist         sage         parchment    woodland
```

Custom dark green/brown themes:

```text
twilight_forest     deep_earth     evergreen
```

The selected theme is saved in `config/app_config.local.json` and applied during GUI startup. Custom theme overrides are applied after the widgets are created, so installer-selected custom themes display correctly without requiring a manual toggle.

## Labs tab

Use the Labs tab for the normal workflow. The left panel filters by search, exam, domain, topic, tag, difficulty, lab type, beginner-friendly status, and legacy deployment mode.

The **Legacy deployments** option switches the lab list between current default labs and older IOSv/IOSvL2 or fallback IOL variants marked with `legacy_variant`. When it is off, only default deployments are shown. When it is on, only legacy deployments are shown.

The **Topic** filter is intentionally broader than the raw catalog `topic` field. It also understands broad topical tags such as `routing`, `automation`, `infrastructure`, `security`, and `switching`, because the catalog uses specific lesson topics for many labs and tags for broad curriculum categories.

Filter dropdowns cascade from higher-priority filters. After selecting an exam or domain, lower-priority dropdowns only show values that still have matching labs.

Available selected-lab actions:

```text
Generate Selected Lab
Copy CLI Command
Copy Scenario ID
```

## Generated lab artifacts

After a lab is generated, the Output panel captures the generator's `Local files:` path and enables these shortcuts:

```text
Open Generated Lab Folder
Open Lab README
Open Lab Configs
```

These replace the older duplicate **Open Last Lab Folder** placement. The lab details pane now only contains selected-lab actions, while generated-artifact actions live in the Output panel.

## Study Plans tab

The Study Plans tab shows ordered study paths. Available actions include generating the selected plan lab, generating all labs in the selected plan, and copying the selected CLI command.

## Blank Topologies tab

Use Blank Topologies when you want a project with nodes and links but no scenario faults.

## Settings tab

The Settings tab contains path/server settings, generation options, the theme selector, QA report execution, and **Validate Catalog**.

## Catalog validation

Use **Validate Catalog** in the Settings tab to run `scripts/validate_catalog.py` against the selected catalog. This checks metadata consistency for required fields, topology references, legacy markers, uncommon values, and one-off tags.


## 1.7.3 startup theme fix

Themes selected by `install.py` or `scripts/setup_environment.py` now apply during GUI startup. Custom themes no longer need to be toggled manually after boot.

## 1.7.2 installer and endpoint push default

New users should run `python3 install.py` before launching the GUI. The installer creates local configuration, can discover GNS3 templates, and can run the readiness check.

The GUI now enables **Push supported endpoints** by default for new settings. Clear this checkbox if you want the generator to create files under `endpoint_setup/` without trying to push those endpoint configs over the console.

## 1.8.0 readiness and generation feedback

Version 1.8.0 adds a selected-lab readiness check before generation. In the GUI, select a lab and click **Check Readiness** to run server, output directory, template mapping, live template, and adapter/port checks without creating a project.

Generated labs now include `generation_summary.md`, which explains what was created, which automation settings were used, and what to open next. Student-facing docs are intentionally more verbose where that helps learning: the walkthrough should feel like a mentor guiding the diagnostic process, while the answer key remains the complete technical explanation.

### 1.8.1 IOL link/interface alignment fix

Version 1.8.1 fixes IOL/IOU link creation so links are attached to the same physical interfaces that the generated configs use. The generator now treats catalog link adapter values as logical IOL interface indexes: 0 = Ethernet0/0, 1 = Ethernet0/1, 2 = Ethernet0/2, 3 = Ethernet0/3, and 4 = Ethernet1/0. The readiness/catalog validation path also checks for this class of mismatch.

## 1.9.2 Lab Workspace and guided-learning foundation

Version 1.9.2 adds a **Lab Workspace** tab. When a lab is generated, the GUI captures the local lab folder and can display generated documents such as the student brief, first-time walkthrough, progressive hints, topology map, generation summary, README, and answer key. The answer key is still separated from the normal workflow and asks before revealing the full solution.

The workspace also includes a read-only config viewer. Use the config set selector to switch between starter configs, answer-key configs, or blank-topology baseline configs, then select a device to review its generated configuration. This is intended for study and review; editing and pushing configs from the workspace is deferred to a later usability milestone.

Blank topology generation remains available for advanced users under **Advanced Tools**. Blank topology output now includes `topology_map.md`, `generation_summary.md`, and `metadata.json`, but does not pretend to be a guided troubleshooting lab.

The Settings area includes **Audit Labs**, which runs `scripts/audit_labs.py` to check catalog/topology/interface consistency without contacting GNS3.


## 3.0 alpha4 lifecycle highlights

- The Qt Lab Workspace now includes a Lifecycle tab for deployed GNS3 projects.
- Users can refresh deployment status, start nodes, stop nodes, reset nodes, and delete the GNS3 project when the lab is complete.
- Delete Project removes the project from GNS3 but keeps local generated lab files by default.
