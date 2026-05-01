#!/usr/bin/env python3
"""Print derived template requirements for a scenario."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def resolve_template_key(node, host_type):
    template = node.get("template")
    if template == "host":
        return host_type
    return template


def scenario_requirements(catalog, scenario_id, host_type):
    scenario = catalog["scenarios"][scenario_id]
    topology = catalog["topologies"][scenario["topology"]]
    required = defaultdict(lambda: {"nodes": [], "min_adapter": 0})
    for node_name, node in topology["nodes"].items():
        key = resolve_template_key(node, host_type)
        required[key]["nodes"].append(node_name)
    for link in topology.get("links", []):
        for side in ["a", "b"]:
            node_name = link[side]
            adapter = int(link[f"{side}_adapter"])
            key = resolve_template_key(topology["nodes"][node_name], host_type)
            required[key]["min_adapter"] = max(required[key]["min_adapter"], adapter + 1)
    return scenario, topology, required


def main():
    parser = argparse.ArgumentParser(description="Print required templates/adapters for a lab.")
    parser.add_argument("--catalog", default="catalogs/ccnp_encor_lab_catalog.json")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--host-type", default="alpine", choices=["alpine", "rhel9", "vpcs"])
    args = parser.parse_args()

    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    scenario, topology, required = scenario_requirements(catalog, args.scenario, args.host_type)

    print(f"Scenario: {args.scenario}")
    print(f"Title: {scenario.get('title', '')}")
    print(f"Topology: {scenario['topology']}")
    print()
    print("Required template keys:")
    for key, info in sorted(required.items()):
        print(f"- {key}: min adapters {info['min_adapter']} ; nodes {', '.join(info['nodes'])}")


if __name__ == "__main__":
    main()
