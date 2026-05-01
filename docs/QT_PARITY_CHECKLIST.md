# Qt Feature Parity Checklist

This checklist tracks the 2.0 PySide6 GUI migration against the mature 1.9.x/Tk workflow.

## Migrated in 2.0.0-beta2

- Scenario browser with cascading filters.
- Default / Legacy / All deployment selector.
- Practical Topic filter that also recognizes broad topical tags.
- Scenario search across title, symptom, tags, verification commands, and metadata.
- Scenario detail panel with symptom, topology, faults, hints, and verification commands.
- Readiness check for the selected scenario.
- Lab generation from the GUI.
- Generation options for project name, host type, start nodes, Cisco config push, endpoint config push, and verification output.
- Output panel controls for opening the Lab Workspace, opening the output folder, and clearing output.
- Lab Workspace document viewer with answer-key reveal prompt.
- Lab Workspace config viewer.
- Lab Workspace side-by-side starter versus answer-key config viewer.
- Lab Workspace topology-map table view.
- Advanced Tools tab with blank topology generation.
- Advanced Tools tab with offline lab audit launcher.
- Settings page for GNS3 server, output directory, Qt theme, host type, push defaults, verification default, Linux endpoint credentials, and timeouts.
- Persistent settings saved to `config/app_config.local.json`.
- Qt theme variants for dark, forest/earth, and softer light modes.
- Legacy Tk GUI retained as fallback.

## Still deferred toward beta/2.0 final

- Full Guided Learning Mode with persistent progress state.
- Student / Instructor / Explorer learning modes.
- Richer markdown rendering beyond Qt's built-in markdown view.
- Highlighted config diff rather than side-by-side config viewing only.
- Open project directly in GNS3 Web UI.
- In-GUI installer repair/check workflow.
- Formal audit report viewer with sortable pass/warn/fail rows.
- Scenario-aware learning metadata expansion across the catalog.


## 2.0.0-beta2

- Restored the Qt Exam filter and placed it before Deployment mode in the primary scenario filter bar.
- Kept the Default/Legacy/All deployment selector, but demoted it behind Exam because exam scope is usually the learner's first filter.
- Simplified Topic vs Tag UX: Topic remains the curated learner-facing dropdown; raw tags remain searchable but no longer occupy a top-level Qt dropdown.
- Added exam values to the Qt scenario table and search haystack.
