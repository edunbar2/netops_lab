#!/usr/bin/env python3
"""Export raw and summarized GNS3 template data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import urlopen


def fetch_json(url: str):
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


def main():
    parser = argparse.ArgumentParser(description="Discover GNS3 templates and write raw/summary JSON.")
    parser.add_argument("--server", required=True, help="GNS3 server URL, for example http://gns3.local")
    parser.add_argument("--out-dir", default=".", help="Output directory. Default: current directory.")
    parser.add_argument("--raw-name", default="local_templates_raw.json")
    parser.add_argument("--summary-name", default="local_templates_summary.json")
    args = parser.parse_args()

    server = args.server.rstrip("/")
    templates = fetch_json(f"{server}/v2/templates")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    raw_path = out / args.raw_name
    summary_path = out / args.summary_name

    raw_path.write_text(json.dumps(templates, indent=2), encoding="utf-8")
    summary_path.write_text(json.dumps([summarize_template(t) for t in templates], indent=2), encoding="utf-8")

    print(f"Templates discovered: {len(templates)}")
    print(f"Raw output: {raw_path}")
    print(f"Summary output: {summary_path}")


if __name__ == "__main__":
    main()
