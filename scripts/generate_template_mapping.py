#!/usr/bin/env python3
"""Generate catalog template override suggestions from GNS3 templates."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CATALOG_KEYS = {
    "iol2": ["iol2", "iol-l2", "ioll2", "l2"],
    "iol3": ["iol3", "iol-l3", "ioll3", "l3"],
    "iosv": ["iosv " , "iosv"],
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


def load_templates(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "templates" in data:
        return data["templates"]
    return data


def template_score(key, template):
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


def normalize(key, template):
    result = {k: v for k, v in template.items() if k in {
        "name", "template_id", "template_type", "category", "compute_id",
        "adapters", "ethernet_adapters", "serial_adapters", "console_type",
        "port_name_format", "first_port_name", "adapter_type",
        "hda_disk_interface", "ram", "cpus", "options"
    } and v is not None}
    if key == "rhel9":
        result.setdefault("options", "-cpu host")
        result.setdefault("default_username", "cloud-user")
        result.setdefault("default_password", "redhat")
    return result


def main():
    parser = argparse.ArgumentParser(description="Generate template_overrides.local.json from GNS3 template data.")
    parser.add_argument("--templates", required=True, help="Path to local_templates_raw.json or summary JSON.")
    parser.add_argument("--out", default="config/template_overrides.local.json")
    args = parser.parse_args()

    templates = load_templates(args.templates)
    output = {
        "schema_version": 1,
        "generated_from": args.templates,
        "templates": {}
    }

    for key in CATALOG_KEYS:
        scored = sorted(((template_score(key, t), t) for t in templates), key=lambda x: x[0], reverse=True)
        best_score, best = scored[0] if scored else (0, None)
        if best and best_score > 0:
            output["templates"][key] = normalize(key, best)
            output["templates"][key]["mapping_status"] = "matched" if best_score >= 10 else "matched_with_low_confidence"
        else:
            output["templates"][key] = {"mapping_status": "missing"}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote template mapping: {out}")
    print("Review mappings before using them with the generator.")


if __name__ == "__main__":
    main()
