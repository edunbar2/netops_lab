# PySide6 GUI Prototype

This package includes an experimental PySide6/Qt GUI backend for evaluating the 2.0 direction. The existing Tk/ttkbootstrap GUI remains the stable interface.

## Why this exists

The 2.0 roadmap focuses on usability, clarity, and guided learning. The current Tk GUI can continue to serve the generator workflow, but richer workflows such as document viewing, topology-map tables, config viewing, side-by-side comparisons, and guided lab progression are easier to express in a more application-oriented GUI framework.

The PySide6 prototype is intended to validate whether Qt is a better foundation before replacing anything in the main GUI.

## Install prototype dependencies

```bash
python3 -m pip install -r requirements-pyside6.txt
```

This installs the normal project requirements plus PySide6.

## Launch options

Stable GUI:

```bash
python3 gns3_ccnp_lab_gui.py
```

Experimental Qt GUI:

```bash
python3 gns3_ccnp_lab_gui_qt.py
```

Convenience launchers are also included:

```bash
./launch_qt_gui_linux.sh
./launch_qt_gui_macos.command
launch_qt_gui_windows.bat
```

## Prototype scope

The Qt GUI currently validates these workflows:

- Scenario browsing with deployment/domain/topic/difficulty/type/tag/search filters.
- Readiness check for a selected scenario.
- Lab generation through the existing generator script.
- Lab Workspace view for generated documents.
- Config viewer for starter, answer-key, or blank-topology config sets.
- Topology-map table based on generated `metadata.json`.
- Blank topology generation under Advanced Tools.
- Offline lab audit launcher.

## Intentional limitations

This is not yet a full replacement for the stable GUI.

Known prototype limitations:

- Theme support is handled with a simple Qt stylesheet, not the full curated Tk theme system.
- Some advanced settings are summarized but not all are editable.
- The Lab Workspace is read-only.
- Config diff and progressive guided-learning state tracking are not implemented yet.
- The stable Tk GUI remains the recommended production interface.

## 2.0 evaluation questions

Use this prototype to decide whether PySide6 should become the 2.0 GUI foundation:

1. Does the scenario browser feel cleaner than the Tk version?
2. Does the Lab Workspace scale better for generated docs and configs?
3. Is the topology-map table useful enough to become a first-class view?
4. Would side-by-side config comparison fit naturally in this backend?
5. Is PySide6 packaging acceptable on the target systems?

If those answers are positive, the next step is to split shared generator/catalog/workspace logic into a small app service layer so both GUI backends can call the same core code during the transition.
