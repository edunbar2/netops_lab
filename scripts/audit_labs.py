#!/usr/bin/env python3
"""Offline lab consistency auditor for GNS3 CCNP lab catalog.

This tool does not contact GNS3. It checks catalog/topology consistency and catches
interface/link mismatches before labs are generated.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

APP_DIR = Path(__file__).resolve().parents[1]


def is_iou_template(template: Dict[str, Any]) -> bool:
    return str(template.get("template_type") or "").lower() == "iou"


def iou_interface_name_for_index(index: int) -> str:
    return f"Ethernet{index // 4}/{index % 4}"


def interface_name_for_template(template: Dict[str, Any], logical_index: int) -> str:
    if is_iou_template(template):
        return iou_interface_name_for_index(logical_index)
    return f"Ethernet{logical_index}/0"


def interface_name_from_node_vars(node: Dict[str, Any], logical_index: int) -> str | None:
    vars_obj = node.get("vars", {}) if isinstance(node.get("vars", {}), dict) else {}
    interfaces = vars_obj.get("interfaces", []) or []
    if 0 <= logical_index < len(interfaces):
        entry = interfaces[logical_index]
        if isinstance(entry, dict) and entry.get("name"):
            return str(entry["name"])
    return None


def resolve_node_template_key(node: Dict[str, Any], host_type: str) -> str:
    key = node.get("template")
    return host_type if key == "host" else str(key or "")


def configured_interface_names(node: Dict[str, Any]) -> Set[str]:
    names: Set[str] = set()
    vars_obj = node.get("vars", {}) if isinstance(node.get("vars", {}), dict) else {}
    for entry in vars_obj.get("interfaces", []) or []:
        if isinstance(entry, dict) and entry.get("name"):
            names.add(str(entry["name"]))
    for section in ["vlans", "loopbacks", "svis"]:
        for entry in vars_obj.get(section, []) or []:
            if isinstance(entry, dict) and entry.get("name"):
                names.add(str(entry["name"]))
    return names


def should_review_node(node: Dict[str, Any]) -> bool:
    template = str(node.get("template", ""))
    if template in {"host", "vpcs", "alpine", "rhel9"}:
        return False
    return bool(node.get("push_config", True))


def audit_scenario(sid: str, scenario: Dict[str, Any], catalog: Dict[str, Any], host_type: str) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    topology_id = scenario.get("topology")
    topology = catalog.get("topologies", {}).get(topology_id)
    if not topology:
        return [{"severity": "error", "scenario": sid, "message": f"references missing topology {topology_id!r}"}]

    nodes = topology.get("nodes", {})
    templates = catalog.get("templates", {})
    for link in topology.get("links", []) or []:
        for side in ("a", "b"):
            node_name = link.get(side)
            if node_name not in nodes:
                issues.append({"severity": "error", "scenario": sid, "message": f"link references unknown node {node_name!r}"})
                continue
            node = nodes[node_name]
            if not should_review_node(node):
                continue
            logical_raw = link.get(f"{side}_adapter")
            if logical_raw is None:
                issues.append({"severity": "error", "scenario": sid, "message": f"link endpoint {node_name} is missing logical adapter index"})
                continue
            template_key = resolve_node_template_key(node, host_type)
            template = templates.get(template_key, {})
            expected_interface = interface_name_from_node_vars(node, int(logical_raw)) or interface_name_for_template(template, int(logical_raw))
            configured = configured_interface_names(node)
            # If a device has explicit interface metadata, linked interfaces should appear in it.
            # Empty metadata is allowed for devices/templates that configure interfaces elsewhere.
            if configured and expected_interface not in configured:
                issues.append({
                    "severity": "warning",
                    "scenario": sid,
                    "message": f"{node_name} link uses {expected_interface}, but topology vars list {', '.join(sorted(configured))}",
                })
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit generated lab consistency without contacting GNS3.")
    parser.add_argument("--catalog", default=str(APP_DIR / "catalogs" / "ccnp_encor_lab_catalog.json"))
    parser.add_argument("--host-type", default="alpine", choices=["alpine", "rhel9", "vpcs"])
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a text report.")
    args = parser.parse_args()

    catalog_path = Path(args.catalog)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    scenarios = catalog.get("scenarios", {})
    issues: List[Dict[str, str]] = []
    seen_messages: Set[str] = set()
    for sid, scenario in scenarios.items():
        for issue in audit_scenario(sid, scenario, catalog, args.host_type):
            key = f"{issue['severity']}|{issue['scenario']}|{issue['message']}"
            if key not in seen_messages:
                issues.append(issue)
                seen_messages.add(key)

    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]

    if args.json:
        print(json.dumps({"scenarios_checked": len(scenarios), "errors": errors, "warnings": warnings}, indent=2))
    else:
        print(f"Catalog: {catalog_path}")
        print(f"Host type: {args.host_type}")
        print(f"Scenarios audited: {len(scenarios)}")
        print(f"Errors: {len(errors)}")
        print(f"Warnings: {len(warnings)}")
        if errors or warnings:
            print("\nFindings:")
            for item in issues[:200]:
                print(f"- {item['severity'].upper()} {item['scenario']}: {item['message']}")
            if len(issues) > 200:
                print(f"... {len(issues) - 200} additional findings omitted from text output; use --json for full results.")
        else:
            print("PASS: no blocking lab consistency issues found.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
