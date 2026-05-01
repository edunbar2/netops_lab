#!/usr/bin/env python3
"""Validate catalog metadata for the GNS3 CCNP Lab Generator."""
from __future__ import annotations
import argparse, json, sys
from collections import Counter
from pathlib import Path
from typing import Any

VALID_DIFFICULTIES = {"intro", "easy", "medium", "hard", "capstone"}
VALID_LAB_TYPES = {"troubleshooting", "configure", "configuration", "verification", "skill-check", "blank", "design", "interpretation", "hardening", "design-interpretation"}
REQUIRED_SCENARIO_FIELDS = ["title", "primary_exam", "domain", "topic", "difficulty", "lab_type", "topology"]
REQUIRED_TOPOLOGY_FIELDS = ["nodes"]

def norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")


def is_iou_template(template: dict[str, Any]) -> bool:
    return str(template.get("template_type") or "").lower() == "iou"


def iou_interface_name_for_index(index: int) -> str:
    return f"Ethernet{index // 4}/{index % 4}"


def validate_iol_interface_alignment(catalog: dict[str, Any], topology_id: str, topology: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    templates = catalog.get("templates", {})
    for node_name, node in topology.get("nodes", {}).items():
        template_key = node.get("template")
        if template_key == "host":
            continue
        template = templates.get(template_key, {})
        if not is_iou_template(template):
            continue
        configured = {
            str(item.get("name", "")).strip()
            for item in node.get("vars", {}).get("interfaces", [])
            if str(item.get("name", "")).strip()
        }
        linked_indices: set[int] = set()
        for link in topology.get("links", []):
            if link.get("a") == node_name:
                linked_indices.add(int(link["a_adapter"]))
            if link.get("b") == node_name:
                linked_indices.add(int(link["b_adapter"]))
        for logical_index in sorted(linked_indices):
            expected_name = iou_interface_name_for_index(logical_index)
            if expected_name in configured:
                continue
            old_direct_adapter_name = f"Ethernet{logical_index}/0"
            old_qemu_style_name = f"Ethernet0/{logical_index}"
            if old_direct_adapter_name in configured or old_qemu_style_name in configured:
                errors.append(
                    f"Topology {topology_id!r} node {node_name!r} links logical IOL index {logical_index}, "
                    f"which maps to {expected_name}, but the catalog appears to configure a different physical interface."
                )
    return errors

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GNS3 CCNP lab catalog metadata.")
    parser.add_argument("--catalog", default="catalogs/ccnp_encor_lab_catalog.json")
    args = parser.parse_args()
    catalog_path = Path(args.catalog)
    if not catalog_path.exists():
        print(f"FAIL: catalog not found: {catalog_path}")
        return 2
    with catalog_path.open("r", encoding="utf-8") as handle:
        catalog = json.load(handle)
    scenarios = catalog.get("scenarios", {})
    topologies = catalog.get("topologies", {})
    errors: list[str] = []
    warnings: list[str] = []
    tag_counter: Counter[str] = Counter()

    if not isinstance(scenarios, dict) or not scenarios:
        errors.append("Catalog has no scenarios dictionary.")
    if not isinstance(topologies, dict) or not topologies:
        errors.append("Catalog has no topologies dictionary.")

    for topology_id, topology in topologies.items():
        for field in REQUIRED_TOPOLOGY_FIELDS:
            if field not in topology or topology.get(field) in (None, "", [], {}):
                errors.append(f"Topology {topology_id!r} missing required field {field!r}.")
        errors.extend(validate_iol_interface_alignment(catalog, topology_id, topology))

    default_count = 0
    legacy_count = 0
    for scenario_id, scenario in scenarios.items():
        for field in REQUIRED_SCENARIO_FIELDS:
            if field not in scenario or scenario.get(field) in (None, "", [], {}):
                errors.append(f"Scenario {scenario_id!r} missing required field {field!r}.")
        topology_id = scenario.get("topology")
        if topology_id and topology_id not in topologies:
            errors.append(f"Scenario {scenario_id!r} references missing topology {topology_id!r}.")
        difficulty = norm(scenario.get("difficulty"))
        if difficulty and difficulty not in VALID_DIFFICULTIES:
            warnings.append(f"Scenario {scenario_id!r} has uncommon difficulty {scenario.get('difficulty')!r}.")
        lab_type = norm(scenario.get("lab_type"))
        if lab_type and lab_type not in VALID_LAB_TYPES:
            warnings.append(f"Scenario {scenario_id!r} has uncommon lab_type {scenario.get('lab_type')!r}.")
        tags = scenario.get("tags", [])
        if not isinstance(tags, list):
            errors.append(f"Scenario {scenario_id!r} tags field is not a list.")
            tags = []
        for tag in tags:
            tag_counter[norm(tag)] += 1
        is_legacy = bool(scenario.get("legacy_variant"))
        legacy_count += int(is_legacy)
        default_count += int(not is_legacy)
        sid_norm = norm(scenario_id)
        if any(token in sid_norm for token in ["iosv", "iosvl2", "legacy"]) and not is_legacy:
            warnings.append(f"Scenario {scenario_id!r} looks legacy by ID but is not marked legacy_variant.")

    one_off_tags = sorted(tag for tag, count in tag_counter.items() if count == 1 and tag)
    if one_off_tags:
        warnings.append(f"One-off tags present ({len(one_off_tags)}): {', '.join(one_off_tags[:20])}" + (" ..." if len(one_off_tags) > 20 else ""))

    print(f"Catalog: {catalog_path}")
    print(f"Scenarios checked: {len(scenarios)}")
    print(f"Topologies checked: {len(topologies)}")
    print(f"Default scenarios: {default_count}")
    print(f"Legacy scenarios: {legacy_count}")
    if warnings:
        print("\nWARNINGS:")
        for warning in warnings:
            print(f"- {warning}")
    if errors:
        print("\nFAILURES:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("\nPASS: catalog metadata validation completed without blocking errors.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
