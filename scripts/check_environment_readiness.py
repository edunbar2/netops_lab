#!/usr/bin/env python3
"""Check lab readiness from catalog plus local template mappings."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from urllib.request import urlopen


def fetch_templates(server):
    with urlopen(server.rstrip("/") + "/v2/templates", timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def template_adapter_count(template):
    if not template:
        return 0
    return int(template.get("ethernet_adapters") or template.get("adapters") or 0)


def resolve_template_key(node, host_type):
    return host_type if node.get("template") == "host" else node.get("template")


def derive_requirements(catalog, scenario_id, host_type):
    sc = catalog["scenarios"][scenario_id]
    topo = catalog["topologies"][sc["topology"]]
    required = defaultdict(int)
    for link in topo.get("links", []):
        for side in ["a", "b"]:
            node_name = link[side]
            key = resolve_template_key(topo["nodes"][node_name], host_type)
            required[key] = max(required[key], int(link[f"{side}_adapter"]) + 1)
    for node_name, node in topo.get("nodes", {}).items():
        key = resolve_template_key(node, host_type)
        required[key] = max(required[key], 1)
    return required


def main():
    parser = argparse.ArgumentParser(description="Check which labs are runnable with the current template mapping.")
    parser.add_argument("--catalog", default="catalogs/ccnp_encor_lab_catalog.json")
    parser.add_argument("--template-overrides", default="config/template_overrides.local.json")
    parser.add_argument("--host-type", default="alpine", choices=["alpine", "rhel9", "vpcs"])
    parser.add_argument("--scenario", default=None)
    args = parser.parse_args()

    catalog = load_json(args.catalog)
    overrides = {}
    if Path(args.template_overrides).exists():
        data = load_json(args.template_overrides)
        overrides = data.get("templates", data)

    templates = dict(catalog.get("templates", {}))
    for key, value in overrides.items():
        if isinstance(value, dict) and key in templates:
            merged = dict(templates[key])
            for field, field_value in value.items():
                if field_value not in ("", None) and field not in ("notes", "description"):
                    merged[field] = field_value
            templates[key] = merged

    scenario_ids = [args.scenario] if args.scenario else sorted(catalog["scenarios"])
    runnable = warning = not_runnable = 0

    for sid in scenario_ids:
        if sid not in catalog["scenarios"]:
            print(f"{sid}: unknown scenario")
            continue
        reqs = derive_requirements(catalog, sid, args.host_type)
        issues = []
        warnings = []
        for key, min_adapters in sorted(reqs.items()):
            tmpl = templates.get(key)
            if not tmpl or tmpl.get("mapping_status") == "missing":
                issues.append(f"missing template {key}")
                continue
            adapters = template_adapter_count(tmpl)
            if adapters and adapters < min_adapters:
                issues.append(f"{key} needs {min_adapters} adapters, found {adapters}")
            if tmpl.get("console_type") not in (None, "telnet", "none"):
                warnings.append(f"{key} console_type is {tmpl.get('console_type')}, config push expects telnet")
            if key == "rhel9" and "-cpu host" not in str(tmpl.get("options", "")):
                warnings.append("rhel9 should include QEMU option -cpu host")

        status = "ready"
        if issues:
            status = "not_runnable"
            not_runnable += 1
        elif warnings:
            status = "warning"
            warning += 1
        else:
            runnable += 1

        print(f"{sid}: {status}")
        for item in issues:
            print(f"  - {item}")
        for item in warnings:
            print(f"  - warning: {item}")

    print()
    print(f"Ready: {runnable}")
    print(f"Warnings: {warning}")
    print(f"Not runnable: {not_runnable}")


if __name__ == "__main__":
    main()
