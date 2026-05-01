
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

# Deployment Guide

1.6.1 includes a master setup script for first-run environment setup.

## Recommended setup

Run:

```bash
python3 scripts/setup_environment.py
```

The script asks for:

```text
GNS3 server URL
Default endpoint host type
Generated lab output directory
GUI theme selected from a numbered list
```

Then it creates:

```text
config/app_config.local.json
config/template_overrides.local.json
local_templates_raw.json
local_templates_summary.json
```

It also runs a readiness check when template discovery succeeds.

## Manual setup option

Manual setup is still available if you prefer to edit files yourself.

Create a local app config:

```bash
cp config/app_config.example.json config/app_config.local.json
```

Edit:

```json
"gns3_server": "http://your-gns3-server"
```

Create local template overrides:

```bash
cp config/template_overrides.example.json config/template_overrides.local.json
```

Then update template IDs and settings to match your GNS3 server.

## Scripted template-only setup

If you only want to discover templates and generate override mappings:

```bash
python3 scripts/discover_gns3_templates.py \
  --server http://your-gns3-server \
  --out-dir .
```

Then:

```bash
python3 scripts/generate_template_mapping.py \
  --templates local_templates_raw.json \
  --out config/template_overrides.local.json
```

The mapping script creates `config/template_overrides.local.json`; you do not need to copy the example override file first when using this path.

## Print lab requirements

```bash
python3 scripts/print_lab_requirements.py \
  --catalog catalogs/ccnp_encor_lab_catalog.json \
  --scenario ccna_ip_static_route_missing
```

## Check environment readiness

```bash
python3 scripts/check_environment_readiness.py \
  --catalog catalogs/ccnp_encor_lab_catalog.json \
  --template-overrides config/template_overrides.local.json
```

## Generator config loading

The generator reads configuration in this order:

```text
Command-line arguments
config/app_config.local.json
Environment variable GNS3_SERVER for server URL only
Built-in safe defaults
```

No personal GNS3 server URL is included.

## Local files are intentionally durable

Do not edit example files directly. Edit local files:

```text
config/app_config.local.json
config/template_overrides.local.json
```

These local files are intended to survive future package updates.


## 1.6.3 theme selection

The setup helper now lists the expanded GUI theme set in numbered columns. Users can select a theme by number or by name. The added light/structured themes include `morph`, `journal`, `lumen`, `united`, `cerulean`, and `simplex`; earthy/foresty options include `forest`, `earth`, and `moss`.

## 1.7.1 setup, themes, and validation

Use `scripts/setup_environment.py` for first-run configuration. The script displays the curated 1.7 theme list in numbered columns and accepts either a number or theme name.

The GUI Settings tab also includes **Validate Catalog**, which runs `scripts/validate_catalog.py` against the selected catalog before a release or local catalog edit.


## 1.7.1 generated learner artifacts

The generator now writes `first_time_walkthrough.md` alongside the existing lab files. This walkthrough is intended for new learners or stuck learners and does not disclose the exact fix. It provides a troubleshooting sequence, topic-specific diagnostic commands, and a recommended verification workflow.

The generated `answer_key.md` is now a full explanation artifact rather than a short root-cause note. It describes what is wrong, why it causes the observed issue, what to change, and how to verify the corrected state.


## 1.7.3 startup theme fix

The GUI now applies the selected installer/setup theme during startup, including custom theme overrides, instead of requiring a manual theme toggle after launch.

## 1.7.2 first-run installer

The recommended first-run path is now the root-level installer:

```bash
python3 install.py
```

The installer can install Python requirements, run the setup wizard, create `config/app_config.local.json`, discover templates from the configured GNS3 server, create `config/template_overrides.local.json`, run the readiness check, and optionally launch the GUI.

For non-interactive or scripted use:

```bash
python3 install.py --server http://localhost:3080 --host-type alpine --theme darkly --yes
```

Endpoint push is now enabled by default. Normal generation starts nodes, pushes Cisco device configs, and pushes supported endpoint configs where a console driver exists. To generate endpoint setup files without pushing them automatically, use either spelling:

```bash
python3 gns3_ccnp_lab_generator.py --scenario <scenario_id> --no-push-endpoints
python3 gns3_ccnp_lab_generator.py --scenario <scenario_id> --skip-endpoints
```

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
