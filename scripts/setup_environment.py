#!/usr/bin/env python3
"""Interactive setup helper for GNS3 CCNP Lab Generator.

This script creates local config files and can discover/map GNS3 templates.
It does not modify bundled example files.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


APP_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = APP_DIR / "config"
APP_CONFIG_EXAMPLE = CONFIG_DIR / "app_config.example.json"
APP_CONFIG_LOCAL = CONFIG_DIR / "app_config.local.json"
TEMPLATE_OVERRIDES_LOCAL = CONFIG_DIR / "template_overrides.local.json"
LOCAL_TEMPLATES_RAW = APP_DIR / "local_templates_raw.json"
LOCAL_TEMPLATES_SUMMARY = APP_DIR / "local_templates_summary.json"

THEME_OPTIONS = [
    "darkly",
    "superhero",
    "cyborg",
    "solar",
    "vapor",
    "minty",
    "sandstone",
    "morph",
    "mist",
    "sage",
    "parchment",
    "twilight_parchment",
    "woodland",
    "twilight_forest",
    "deep_earth",
    "evergreen",
]


def print_numbered_columns(items: list[str], columns: int = 3) -> None:
    rows = (len(items) + columns - 1) // columns
    for row in range(rows):
        parts = []
        for col in range(columns):
            idx = row + col * rows
            if idx < len(items):
                parts.append(f"{idx + 1:>2}. {items[idx]:<14}")
        print("  ".join(parts).rstrip())


def prompt_choice(text: str, options: list[str], default: str) -> str:
    print(f"\n{text}:")
    print_numbered_columns(options)
    while True:
        value = input(f"Select a number or name [{default}]: ").strip()
        if not value:
            return default
        if value.isdigit():
            idx = int(value) - 1
            if 0 <= idx < len(options):
                return options[idx]
        lowered = value.lower()
        matches = [option for option in options if option.lower() == lowered]
        if matches:
            return matches[0]
        print(f"Invalid selection. Choose 1-{len(options)} or one of: {', '.join(options)}")


def prompt(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value or default


def prompt_yes_no(text: str, default: bool = True) -> bool:
    default_text = "Y/n" if default else "y/N"
    value = input(f"{text} [{default_text}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes"}


def fetch_templates(server: str):
    url = server.rstrip("/") + "/v2/templates"
    with urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def summarize_template(t):
    return {
        "name": t.get("name"),
        "template_id": t.get("template_id"),
        "template_type": t.get("template_type"),
        "category": t.get("category"),
        "compute_id": t.get("compute_id"),
        "adapters": t.get("adapters"),
        "ethernet_adapters": t.get("ethernet_adapters"),
        "serial_adapters": t.get("serial_adapters"),
        "console_type": t.get("console_type"),
        "port_name_format": t.get("port_name_format"),
        "first_port_name": t.get("first_port_name"),
        "adapter_type": t.get("adapter_type"),
        "hda_disk_interface": t.get("hda_disk_interface"),
        "ram": t.get("ram"),
        "cpus": t.get("cpus"),
        "options": t.get("options"),
    }


CATALOG_KEYS = {
    "iol2": ["iol2", "iol-l2", "ioll2", "l2"],
    "iol3": ["iol3", "iol-l3", "ioll3", "l3"],
    "iosv": ["iosv ", "iosv"],
    "iosvl2": ["iosvl2", "iosv-l2"],
    "asav": ["asav", "asa"],
    "cat8000v": ["8000v", "cat8000v", "catalyst 8000"],
    "csr1000v": ["csr1000v", "csr 1000v"],
    "nxosv9000": ["nx-osv", "nxosv", "9000v", "nx-os"],
    "alpine": ["alpine"],
    "rhel9": ["rhel9", "rhel 9", "red hat enterprise linux 9"],
    "vpcs": ["vpcs"],
    "cloud": ["cloud"],
    "nat": ["nat"],
    "ethernet_switch": ["ethernet switch"],
}


def template_score(key: str, template: dict) -> int:
    name = str(template.get("name", "")).lower()
    ttype = str(template.get("template_type", "")).lower()
    score = 0
    for needle in CATALOG_KEYS[key]:
        if needle in name:
            score += 10
    if key in {"iol2", "iol3"} and ttype == "iou":
        score += 3
    if key in {"iosv", "iosvl2", "asav", "cat8000v", "csr1000v", "nxosv9000", "rhel9"} and ttype == "qemu":
        score += 3
    if key == "alpine" and ttype == "docker":
        score += 3
    if key == "vpcs" and ttype == "vpcs":
        score += 5
    return score


def normalize_template(key: str, template: dict) -> dict:
    fields = {
        "name", "template_id", "template_type", "category", "compute_id",
        "adapters", "ethernet_adapters", "serial_adapters", "console_type",
        "port_name_format", "first_port_name", "adapter_type",
        "hda_disk_interface", "ram", "cpus", "options"
    }
    result = {k: v for k, v in template.items() if k in fields and v is not None}
    if key == "rhel9":
        result.setdefault("options", "-cpu host")
        result.setdefault("default_username", "cloud-user")
        result.setdefault("default_password", "redhat")
    return result


def generate_mapping(templates: list[dict]) -> dict:
    output = {
        "schema_version": 1,
        "generated_by": "scripts/setup_environment.py",
        "templates": {}
    }
    for key in CATALOG_KEYS:
        scored = sorted(((template_score(key, t), t) for t in templates), key=lambda x: x[0], reverse=True)
        best_score, best = scored[0] if scored else (0, None)
        if best and best_score > 0:
            output["templates"][key] = normalize_template(key, best)
            output["templates"][key]["mapping_status"] = "matched" if best_score >= 10 else "matched_with_low_confidence"
        else:
            output["templates"][key] = {"mapping_status": "missing"}
    return output


def write_app_config(server: str, host_type: str, output_dir: str, theme: str, overwrite: bool) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if APP_CONFIG_LOCAL.exists() and not overwrite:
        print(f"Leaving existing config unchanged: {APP_CONFIG_LOCAL}")
        return

    if APP_CONFIG_EXAMPLE.exists():
        config = json.loads(APP_CONFIG_EXAMPLE.read_text(encoding="utf-8"))
    else:
        config = {"schema_version": 1}

    config.update({
        "gns3_server": server,
        "catalog_path": "catalogs/ccnp_encor_lab_catalog.json",
        "generator_path": "gns3_ccnp_lab_generator.py",
        "output_dir": output_dir,
        "host_type": host_type,
        "theme": theme,
        "auto_config": True,
        "push_config": True,
        "push_endpoints": True,
        "verify": False,
        "template_overrides_path": "config/template_overrides.local.json",
    })
    APP_CONFIG_LOCAL.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"Wrote {APP_CONFIG_LOCAL}")


def write_template_files(server: str, overwrite: bool) -> None:
    if TEMPLATE_OVERRIDES_LOCAL.exists() and not overwrite:
        print(f"Leaving existing template overrides unchanged: {TEMPLATE_OVERRIDES_LOCAL}")
        return

    print(f"Connecting to {server.rstrip('/')}/v2/templates")
    templates = fetch_templates(server)

    LOCAL_TEMPLATES_RAW.write_text(json.dumps(templates, indent=2), encoding="utf-8")
    LOCAL_TEMPLATES_SUMMARY.write_text(json.dumps([summarize_template(t) for t in templates], indent=2), encoding="utf-8")
    print(f"Wrote {LOCAL_TEMPLATES_RAW}")
    print(f"Wrote {LOCAL_TEMPLATES_SUMMARY}")

    mapping = generate_mapping(templates)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_OVERRIDES_LOCAL.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    print(f"Wrote {TEMPLATE_OVERRIDES_LOCAL}")
    print("Review template_overrides.local.json before relying on it in production.")


def run_readiness(host_type: str) -> None:
    script = APP_DIR / "scripts" / "check_environment_readiness.py"
    catalog = APP_DIR / "catalogs" / "ccnp_encor_lab_catalog.json"
    if not script.exists():
        return
    print("\nRunning readiness check...")
    subprocess.call([
        sys.executable,
        str(script),
        "--catalog", str(catalog),
        "--template-overrides", str(TEMPLATE_OVERRIDES_LOCAL),
        "--host-type", host_type,
    ], cwd=str(APP_DIR))


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive first-run setup for GNS3 CCNP Lab Generator.")
    parser.add_argument("--server", default=None, help="GNS3 server URL, for example http://gns3.local")
    parser.add_argument("--host-type", default=None, choices=["alpine", "rhel9", "vpcs"])
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--theme", default=None)
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing local config/template override files.")
    parser.add_argument("--no-template-discovery", action="store_true", help="Only create app_config.local.json.")
    parser.add_argument("--no-readiness", action="store_true", help="Do not run readiness check at the end.")
    args = parser.parse_args()

    print("GNS3 CCNP Lab Generator setup")
    print("This script creates local config files. Bundled example files are not modified.\n")

    server = args.server or prompt("GNS3 server URL", "http://localhost:3080")
    host_type = args.host_type or prompt("Default endpoint host type (alpine/rhel9/vpcs)", "alpine")
    if host_type not in {"alpine", "rhel9", "vpcs"}:
        raise SystemExit("Invalid host type.")
    output_dir = args.output_dir or prompt("Generated lab output directory", "generated_labs")
    if args.theme:
        theme = args.theme
        if theme not in THEME_OPTIONS:
            raise SystemExit(f"Invalid theme. Choose one of: {', '.join(THEME_OPTIONS)}")
    else:
        theme = prompt_choice("GUI theme", THEME_OPTIONS, "darkly")

    overwrite = args.overwrite
    if not overwrite and (APP_CONFIG_LOCAL.exists() or TEMPLATE_OVERRIDES_LOCAL.exists()):
        overwrite = prompt_yes_no("Local config files already exist. Overwrite them?", False)

    write_app_config(server, host_type, output_dir, theme, overwrite)

    if not args.no_template_discovery:
        try:
            write_template_files(server, overwrite)
        except URLError as exc:
            print(f"Template discovery failed: {exc}")
            print("You can run this later after confirming the GNS3 server is reachable.")
        except Exception as exc:
            print(f"Template discovery failed: {exc}")
            print("You can still edit config/template_overrides.local.json manually.")

    if not args.no_readiness and TEMPLATE_OVERRIDES_LOCAL.exists():
        run_readiness(host_type)

    print("\nSetup complete.")
    print(f"App config: {APP_CONFIG_LOCAL}")
    print(f"Template overrides: {TEMPLATE_OVERRIDES_LOCAL}")


if __name__ == "__main__":
    main()
