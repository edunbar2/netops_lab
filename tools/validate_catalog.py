#!/usr/bin/env python3
"""Validate NetOps Labs catalog metadata and references.

This tool is intentionally standalone: it does not import PySide6, does not make
network calls, and does not mutate catalog files. It is designed to support the
4.x transition from exam-first metadata to study-path-first catalog metadata
while remaining tolerant of valid 3.x-era catalog shapes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REQUIRED_TOP_LEVEL_KEYS = ("templates", "topologies", "scenarios", "study_paths")

CANONICAL_LAB_TYPES = {"build", "troubleshoot", "verify", "mixed", "hardening", "explore"}
LEGACY_LAB_TYPES = {
    "troubleshooting": "troubleshoot",
    "skill-check": "build",
    "skill_check": "build",
    "interpretation": "explore",
    "design-interpretation": "explore",
    "design_interpretation": "explore",
}

CANONICAL_DIFFICULTIES = {"beginner", "intermediate", "advanced"}
LEGACY_DIFFICULTIES = {
    "intro": "beginner",
    "easy": "beginner",
    "medium": "intermediate",
    "hard": "advanced",
    "capstone": "advanced",
}

PLATFORM_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# Logical catalog placeholders that are resolved by generation options rather than
# direct top-level GNS3 template keys. Existing 3.x/4.0 catalogs use `host` for
# endpoint nodes that can become VPCS, Alpine, or RHEL9 at generation time.
LOGICAL_TEMPLATE_KEYS = {"host"}
LEAKAGE_PATTERNS = (
    re.compile(r"\broot\s+cause\b", re.IGNORECASE),
    re.compile(r"\banswer\s*[:=]", re.IGNORECASE),
    re.compile(r"\bsolution\s*[:=]", re.IGNORECASE),
    re.compile(r"\bfix\s*[:=]", re.IGNORECASE),
    re.compile(r"\bset\s+.+\s+back\s+to\b", re.IGNORECASE),
    re.compile(r"\bconfigured\s+(?:in|with|as)\s+.+\s+instead\s+of\b", re.IGNORECASE),
)
STUDENT_FACING_FIELDS = ("title", "description", "symptom", "scenario", "student_brief")


@dataclass
class Issue:
    level: str
    path: str
    message: str
    suggestion: str = ""


@dataclass
class ValidationReport:
    catalog_path: str
    errors: List[Issue] = field(default_factory=list)
    warnings: List[Issue] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def add(self, level: str, path: str, message: str, suggestion: str = "") -> None:
        issue = Issue(level=level, path=path, message=message, suggestion=suggestion)
        if level == "error":
            self.errors.append(issue)
        else:
            self.warnings.append(issue)

    def ok(self, strict: bool = False) -> bool:
        return not self.errors and (not strict or not self.warnings)

    def to_json_dict(self, strict: bool = False) -> Dict[str, Any]:
        return {
            "status": "ok" if self.ok(strict=strict) else "fail",
            "catalog_path": self.catalog_path,
            "errors": [asdict(issue) for issue in self.errors],
            "warnings": [asdict(issue) for issue in self.warnings],
            "stats": self.stats,
        }


class CatalogValidator:
    def __init__(self, catalog_path: Path | str) -> None:
        self.catalog_path = Path(catalog_path)
        self.catalog: Dict[str, Any] = {}
        self.report = ValidationReport(catalog_path=str(self.catalog_path))
        self._validated_topologies: set[str] = set()

    def load(self) -> None:
        with self.catalog_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("Catalog JSON must be an object at the top level.")
        self.catalog = data

    def run(self) -> ValidationReport:
        self.validate_top_level_shape()
        self.validate_scenarios()
        self.validate_study_path_coverage()
        self.report.stats.setdefault("error_count", len(self.report.errors))
        self.report.stats.setdefault("warning_count", len(self.report.warnings))
        return self.report

    @property
    def templates(self) -> Dict[str, Any]:
        value = self.catalog.get("templates", {})
        return value if isinstance(value, dict) else {}

    @property
    def topologies(self) -> Dict[str, Any]:
        value = self.catalog.get("topologies", {})
        return value if isinstance(value, dict) else {}

    @property
    def scenarios(self) -> Dict[str, Any]:
        value = self.catalog.get("scenarios", {})
        return value if isinstance(value, dict) else {}

    @property
    def study_paths(self) -> Dict[str, Any]:
        value = self.catalog.get("study_paths", {})
        return value if isinstance(value, dict) else {}

    def validate_top_level_shape(self) -> None:
        for key in REQUIRED_TOP_LEVEL_KEYS:
            if key not in self.catalog:
                self.report.add("error", key, f"Missing required top-level key '{key}'.")
            elif not isinstance(self.catalog[key], dict):
                self.report.add("error", key, f"Top-level key '{key}' must be an object/dictionary.")
        self.report.stats.update(
            {
                "template_count": len(self.templates),
                "topology_count": len(self.topologies),
                "scenario_count": len(self.scenarios),
                "study_path_count": len(self.study_paths),
            }
        )

    def validate_study_path_coverage(self) -> None:
        usage = {key: 0 for key in self.study_paths}
        for scenario in self.scenarios.values():
            if not isinstance(scenario, dict):
                continue
            for study_path in as_list(scenario.get("study_paths")):
                if study_path in usage:
                    usage[study_path] += 1
        for study_path, count in sorted(usage.items()):
            if count == 0:
                self.report.add(
                    "warning",
                    f"study_paths.{study_path}",
                    "Study path is defined but has no scenarios assigned.",
                    "Assign existing relevant scenarios or add seed labs before promoting this path in the UI.",
                )
        self.report.stats["study_path_usage"] = usage

    def validate_scenarios(self) -> None:
        normalized_lab_type_count = 0
        normalized_difficulty_count = 0
        legacy_domain_count = 0
        derived_platform_count = 0

        for scenario_id, scenario in self.scenarios.items():
            path = f"scenarios.{scenario_id}"
            if not isinstance(scenario, dict):
                self.report.add("error", path, "Scenario entry must be an object.")
                continue

            study_paths = as_list(scenario.get("study_paths"))
            if not study_paths:
                self.report.add(
                    "error",
                    f"{path}.study_paths",
                    "Scenario is missing study_paths metadata.",
                    "Add at least one top-level study_paths key such as 'ccna-foundations'.",
                )
            for study_path in study_paths:
                if study_path not in self.study_paths:
                    self.report.add(
                        "error",
                        f"{path}.study_paths",
                        f"Unknown study path '{study_path}'.",
                        "Define the study path under top-level study_paths or correct the scenario metadata.",
                    )

            domains = as_list(scenario.get("domains"))
            if not domains and scenario.get("domain"):
                domains = as_list(scenario.get("domain"))
                legacy_domain_count += 1
            if not domains:
                self.report.add(
                    "warning",
                    f"{path}.domains",
                    "Scenario lacks domains/domain metadata for UI filtering.",
                    "Add domains: ['routing'] style metadata.",
                )

            lab_type = str(scenario.get("lab_type", "")).strip()
            normalized_lab_type = normalize_lab_type(lab_type)
            if not lab_type:
                self.report.add("warning", f"{path}.lab_type", "Missing lab_type metadata.", "Use build, troubleshoot, verify, mixed, hardening, or explore.")
            elif normalized_lab_type is None:
                self.report.add("warning", f"{path}.lab_type", f"Unrecognized lab_type '{lab_type}'.", "Normalize to a supported 4.x lab type.")
            elif lab_type != normalized_lab_type:
                normalized_lab_type_count += 1

            difficulty = str(scenario.get("difficulty", "")).strip()
            normalized_difficulty = normalize_difficulty(difficulty)
            if not difficulty:
                self.report.add("warning", f"{path}.difficulty", "Missing difficulty metadata.", "Use beginner, intermediate, or advanced.")
            elif normalized_difficulty is None:
                self.report.add("warning", f"{path}.difficulty", f"Unrecognized difficulty '{difficulty}'.", "Normalize to beginner, intermediate, or advanced.")
            elif difficulty != normalized_difficulty:
                normalized_difficulty_count += 1

            topology_id = scenario.get("topology") or scenario.get("topology_id")
            topology = None
            if not topology_id:
                self.report.add("error", f"{path}.topology", "Scenario is missing topology/topology_id reference.")
            elif topology_id not in self.topologies:
                self.report.add("error", f"{path}.topology", f"Referenced topology '{topology_id}' does not exist.")
            else:
                topology = self.topologies[topology_id]
                if topology_id not in self._validated_topologies:
                    self.validate_topology_templates(topology_id, topology, f"topologies.{topology_id}")
                    self._validated_topologies.add(topology_id)

            platforms = as_list(scenario.get("platforms"))
            if not platforms:
                platforms = derive_platforms(topology)
                if platforms:
                    derived_platform_count += 1
                else:
                    self.report.add("warning", f"{path}.platforms", "Missing platforms metadata and unable to derive it from topology.")
            for platform in platforms:
                if not isinstance(platform, str) or not PLATFORM_TOKEN_RE.match(platform):
                    self.report.add("warning", f"{path}.platforms", f"Platform value '{platform}' should be a lower-case token.")

            if "estimated_minutes" not in scenario:
                self.report.add("warning", f"{path}.estimated_minutes", "Missing estimated_minutes metadata.", "Add a reasonable integer estimate when touching this scenario.")
            elif not is_reasonable_minutes(scenario.get("estimated_minutes")):
                self.report.add("warning", f"{path}.estimated_minutes", "estimated_minutes should be a reasonable integer between 1 and 480.")

            exam_alignment = as_list(scenario.get("exam_alignment")) or as_list(scenario.get("exam_blueprints"))
            if not exam_alignment:
                self.report.add("warning", f"{path}.exam_alignment", "Missing exam_alignment/exam_blueprints compatibility metadata.")

            self.check_student_facing_leakage(scenario_id, scenario)

        self.report.stats.update(
            {
                "legacy_domain_fallbacks": legacy_domain_count,
                "legacy_lab_type_values": normalized_lab_type_count,
                "legacy_difficulty_values": normalized_difficulty_count,
                "derived_platform_values": derived_platform_count,
            }
        )

    def validate_topology_templates(self, topology_id: str, topology: Any, path: str) -> None:
        if not isinstance(topology, dict):
            self.report.add("error", path, f"Topology '{topology_id}' must be an object.")
            return
        nodes = topology.get("nodes", {})
        if isinstance(nodes, dict):
            items = nodes.items()
        elif isinstance(nodes, list):
            items = ((str(index), node) for index, node in enumerate(nodes))
        else:
            self.report.add("warning", f"{path}.nodes", "Topology nodes should be an object or list.")
            return
        for node_name, node in items:
            if not isinstance(node, dict):
                continue
            template_key = node.get("template") or node.get("template_key")
            if template_key and template_key not in self.templates and template_key not in LOGICAL_TEMPLATE_KEYS:
                self.report.add(
                    "error",
                    f"{path}.nodes.{node_name}.template",
                    f"Node references unknown template '{template_key}'.",
                    "Define the template under top-level templates or correct the node template key.",
                )

    def check_student_facing_leakage(self, scenario_id: str, scenario: Dict[str, Any]) -> None:
        for field_name in STUDENT_FACING_FIELDS:
            value = scenario.get(field_name)
            if not isinstance(value, str):
                continue
            for pattern in LEAKAGE_PATTERNS:
                if pattern.search(value):
                    self.report.add(
                        "warning",
                        f"scenarios.{scenario_id}.{field_name}",
                        f"Potential answer leakage detected by pattern '{pattern.pattern}'.",
                        "Keep root-cause/fix details in answer_key, not student-facing text.",
                    )
                    break


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        return [value]
    return [value]


def normalize_token(value: str) -> str:
    return str(value).strip().lower().replace(" ", "-")


def normalize_lab_type(value: str) -> Optional[str]:
    if not value:
        return None
    token = normalize_token(value)
    if token in CANONICAL_LAB_TYPES:
        return token
    return LEGACY_LAB_TYPES.get(token)


def normalize_difficulty(value: str) -> Optional[str]:
    if not value:
        return None
    token = normalize_token(value)
    if token in CANONICAL_DIFFICULTIES:
        return token
    return LEGACY_DIFFICULTIES.get(token)


def derive_platforms(topology: Any) -> List[str]:
    if not isinstance(topology, dict):
        return []
    explicit = as_list(topology.get("platforms"))
    if explicit:
        return [str(item).lower() for item in explicit if item]
    platforms = {"gns3"}
    nodes = topology.get("nodes", {})
    node_values: Iterable[Any]
    if isinstance(nodes, dict):
        node_values = nodes.values()
    elif isinstance(nodes, list):
        node_values = nodes
    else:
        node_values = []
    for node in node_values:
        if not isinstance(node, dict):
            continue
        template = normalize_token(node.get("template", ""))
        if template.startswith("iol"):
            platforms.add("cisco-iol")
        elif "iosv" in template:
            platforms.add("cisco-iosv")
        elif "rhel" in template:
            platforms.add("rhel9")
        elif "alpine" in template:
            platforms.add("alpine")
    return sorted(platforms)


def is_reasonable_minutes(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return False
    return 1 <= minutes <= 480


def render_text_report(report: ValidationReport, strict: bool = False, quiet: bool = False) -> str:
    lines: List[str] = []
    if not quiet:
        lines.append(f"Catalog: {report.catalog_path}")
        lines.append(
            "Stats: "
            + ", ".join(f"{key}={value}" for key, value in sorted(report.stats.items()) if not key.endswith("_count"))
        )
    for issue in report.errors:
        lines.append(format_issue(issue))
    for issue in report.warnings:
        lines.append(format_issue(issue))
    if not quiet:
        lines.append(
            f"Result: {len(report.errors)} error(s), {len(report.warnings)} warning(s)"
            + (" [strict]" if strict else "")
        )
    return "\n".join(line for line in lines if line)


def format_issue(issue: Issue) -> str:
    message = f"[{issue.level.upper()}] {issue.path}: {issue.message}"
    if issue.suggestion:
        message += f" Suggestion: {issue.suggestion}"
    return message


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate NetOps Labs catalog metadata and references.")
    parser.add_argument("--catalog", default="catalogs/ccnp_encor_lab_catalog.json", help="Catalog JSON path.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Emit machine-readable JSON.")
    parser.add_argument("--quiet", action="store_true", help="Suppress informational text output.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    validator = CatalogValidator(args.catalog)
    try:
        validator.load()
        report = validator.run()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        failure = {
            "status": "error",
            "catalog_path": args.catalog,
            "errors": [{"level": "error", "path": args.catalog, "message": str(exc), "suggestion": ""}],
            "warnings": [],
            "stats": {},
        }
        if args.json_output:
            print(json.dumps(failure, indent=2))
        else:
            print(f"[ERROR] {args.catalog}: {exc}", file=sys.stderr)
        return 2

    if args.json_output:
        print(json.dumps(report.to_json_dict(strict=args.strict), indent=2))
    else:
        output = render_text_report(report, strict=args.strict, quiet=args.quiet)
        if output:
            print(output)

    return 0 if report.ok(strict=args.strict) else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
