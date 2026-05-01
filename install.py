#!/usr/bin/env python3
"""First-run installer for NetOps Labs.

The installer is intentionally conservative: it installs Python dependencies on
request, creates local config files, discovers GNS3 templates when the server is
reachable, and runs the readiness check. Bundled example files are not modified.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
REQUIREMENTS = APP_DIR / "requirements.txt"
SETUP_SCRIPT = APP_DIR / "scripts" / "setup_environment.py"
QT_GUI_SCRIPT = APP_DIR / "gns3_ccnp_lab_gui_qt.py"
TK_GUI_SCRIPT = APP_DIR / "gns3_ccnp_lab_gui.py"


def yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "Y/n" if default else "y/N"
    value = input(f"{prompt} [{suffix}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes"}


def run(cmd: list[str], *, check: bool = True) -> int:
    print("\n$ " + " ".join(cmd))
    completed = subprocess.run(cmd, cwd=str(APP_DIR), check=False)
    if check and completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return completed.returncode


def install_requirements(skip: bool, assume_yes: bool) -> None:
    if skip or not REQUIREMENTS.exists():
        return
    should_install = assume_yes or yes_no("Install/update Python requirements now?", True)
    if not should_install:
        print("Skipping dependency installation.")
        return
    run([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)])


def run_setup(args: argparse.Namespace) -> None:
    if not SETUP_SCRIPT.exists():
        raise SystemExit(f"Missing setup helper: {SETUP_SCRIPT}")

    cmd = [sys.executable, str(SETUP_SCRIPT)]
    if args.server:
        cmd.extend(["--server", args.server])
    if args.host_type:
        cmd.extend(["--host-type", args.host_type])
    if args.output_dir:
        cmd.extend(["--output-dir", args.output_dir])
    if args.theme:
        cmd.extend(["--theme", args.theme])
    if args.overwrite:
        cmd.append("--overwrite")
    if args.no_template_discovery:
        cmd.append("--no-template-discovery")
    if args.no_readiness:
        cmd.append("--no-readiness")

    run(cmd)


def launch_gui_if_requested(launch_gui: bool, assume_yes: bool, legacy_tk: bool = False) -> None:
    gui_script = TK_GUI_SCRIPT if legacy_tk else QT_GUI_SCRIPT
    label = "legacy Tk GUI" if legacy_tk else "PySide6 Qt GUI"
    if not gui_script.exists():
        print(f"Requested {label}, but {gui_script.name} was not found.")
        return
    should_launch = launch_gui or (not assume_yes and yes_no(f"Launch the {label} now?", False))
    if not should_launch:
        return
    print(f"\nLaunching {label}...")
    subprocess.Popen([sys.executable, str(gui_script)], cwd=str(APP_DIR))

def run_environment_check() -> int:
    """Conservative installer check mode."""
    print("NetOps Labs installer check")
    checks = []
    checks.append(("requirements.txt", REQUIREMENTS.exists()))
    checks.append(("setup_environment.py", SETUP_SCRIPT.exists()))
    checks.append(("Qt GUI", QT_GUI_SCRIPT.exists()))
    checks.append(("legacy Tk GUI", TK_GUI_SCRIPT.exists()))
    checks.append(("catalog", (APP_DIR / "catalogs" / "ccnp_encor_lab_catalog.json").exists()))
    local_cfg = APP_DIR / "config" / "app_config.local.json"
    example_cfg = APP_DIR / "config" / "app_config.example.json"
    checks.append(("example config", example_cfg.exists()))
    if local_cfg.exists():
        try:
            json.loads(local_cfg.read_text(encoding="utf-8"))
            checks.append(("local config JSON", True))
        except Exception as exc:
            print(f"WARN: local config exists but is not valid JSON: {exc}")
            checks.append(("local config JSON", False))
    else:
        print("WARN: config/app_config.local.json does not exist yet. Run install.py normally or use --repair.")
        checks.append(("local config", False))
    for label, ok in checks:
        print(f"{'PASS' if ok else 'WARN'}: {label}")
    return 0 if all(ok for _label, ok in checks if _label not in {"local config"}) else 1


def run_repair(args: argparse.Namespace) -> int:
    """Repair mode re-runs setup without reinstalling packages unless requested separately."""
    print("Repairing local configuration and readiness state...")
    args.no_template_discovery = getattr(args, "no_template_discovery", False)
    args.no_readiness = getattr(args, "no_readiness", False)
    run_setup(args)
    return run_environment_check()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install and configure NetOps Labs for first use."
    )
    parser.add_argument("--server", default=None, help="GNS3 server URL, for example http://localhost:3080")
    parser.add_argument("--host-type", choices=["alpine", "rhel9", "vpcs"], default=None)
    parser.add_argument("--output-dir", default=None, help="Generated lab output directory")
    parser.add_argument("--theme", default=None, help="GUI theme name")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing local config files")
    parser.add_argument("--skip-pip-install", action="store_true", help="Do not install Python requirements")
    parser.add_argument("--no-template-discovery", action="store_true", help="Skip GNS3 template discovery")
    parser.add_argument("--no-readiness", action="store_true", help="Skip environment readiness check")
    parser.add_argument("--launch-gui", action="store_true", help="Launch the GUI after setup")
    parser.add_argument("--check", action="store_true", help="Check local install/config state and exit")
    parser.add_argument("--repair", action="store_true", help="Re-run setup and readiness checks without changing bundled files")
    parser.add_argument("--legacy-tk", action="store_true", help="Launch the legacy Tk GUI instead of the PySide6 Qt GUI")
    parser.add_argument("-y", "--yes", action="store_true", help="Accept installer defaults where possible")
    args = parser.parse_args()

    print("NetOps Labs 4.0.0 installer")
    print("=================================")
    print(f"Application directory: {APP_DIR}")
    print(f"Python: {sys.executable}")

    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 or newer is recommended for this package.")

    if args.check:
        return run_environment_check()
    if args.repair:
        return run_repair(args)

    install_requirements(args.skip_pip_install, args.yes)
    run_setup(args)
    launch_gui_if_requested(args.launch_gui, args.yes, args.legacy_tk)

    print("\nInstall/setup complete.")
    print("Default GUI for the 3.0 line is the PySide6 Qt interface: python3 gns3_ccnp_lab_gui_qt.py")
    print("Legacy Tk GUI remains available with: python3 gns3_ccnp_lab_gui.py")
    print("Default generation behavior now starts nodes, pushes Cisco configs, and pushes supported endpoint configs.")
    print("Disable endpoint push with --no-push-endpoints / --skip-endpoints or by clearing it in the GUI settings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
