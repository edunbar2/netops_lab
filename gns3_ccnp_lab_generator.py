#!/usr/bin/python3
"""
NetOps Labs modular lab generator v9.

Fully modular design:
- GNS3 templates are data in JSON.
- Topologies are data in JSON.
- Per-node config templates and variables are data in JSON.
- Scenarios are data in JSON.
- Faults can be injected by modifying structured variables before rendering,
  or by applying text patches after rendering as an escape hatch.

Dependency install:
    /usr/bin/python3 -m pip install -r requirements.txt
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import ipaddress
import json
import os
import random
import re
import socket
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

APP_VERSION = "4.0.1"

import requests

try:
    import telnetlib3
except ImportError:
    telnetlib3 = None

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
except ImportError:
    Environment = None
    FileSystemLoader = None
    StrictUndefined = None


GNS3_DEFAULT = os.environ.get("GNS3_SERVER", "")
DEFAULT_CATALOG_NAMES = ["catalogs/ccnp_encor_lab_catalog.json", "ccnp_encor_lab_catalog.json"]
DEFAULT_TEMPLATE_DIRS = ["config_templates"]
DEFAULT_APP_CONFIG_NAMES = ["config/app_config.local.json", "app_config.local.json"]
DEFAULT_TEMPLATE_OVERRIDE_NAMES = ["config/template_overrides.local.json", "template_overrides.local.json"]
_API_SESSION: Optional[requests.Session] = None


class ProgressReporter:
    """Emit simple flushed progress lines for CLI and GUI subprocess readers."""

    def __init__(self, total_steps: int):
        self.total_steps = max(1, int(total_steps))
        self.current_step = 0

    def step(self, message: str) -> None:
        self.current_step += 1
        print(f"[{self.current_step}/{self.total_steps}] {message}", flush=True)

    def detail(self, message: str) -> None:
        print(f"  - {message}", flush=True)


def find_optional_file(path: Optional[str], default_names: List[str]) -> Optional[Path]:
    if path:
        p = Path(path)
        if not p.exists():
            print(f"Configured file not found: {p}", file=sys.stderr)
            raise SystemExit(2)
        return p

    script_dir = Path(__file__).resolve().parent
    cwd = Path.cwd()
    for name in default_names:
        for p in [cwd / name, script_dir / name]:
            if p.exists():
                return p
    return None


def load_json_file(path: Path, label: str) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"{label} has invalid JSON: {path}", file=sys.stderr)
        print(exc, file=sys.stderr)
        raise SystemExit(2) from exc


def load_app_config(path: Optional[str]) -> Dict[str, Any]:
    p = find_optional_file(path, DEFAULT_APP_CONFIG_NAMES)
    if not p:
        return {}
    data = load_json_file(p, "App config")
    data["_config_path"] = str(p)
    return data


def apply_template_overrides(catalog: Dict[str, Any], path: Optional[str]) -> None:
    p = find_optional_file(path, DEFAULT_TEMPLATE_OVERRIDE_NAMES)
    if not p:
        return
    data = load_json_file(p, "Template overrides")
    overrides = data.get("templates", data)
    if not isinstance(overrides, dict):
        print(f"Template overrides file must contain an object or a 'templates' object: {p}", file=sys.stderr)
        raise SystemExit(2)

    for key, override in overrides.items():
        if not isinstance(override, dict):
            continue
        if key not in catalog.get("templates", {}):
            print(f"Warning: template override key {key!r} is not present in the catalog; ignoring.", file=sys.stderr)
            continue
        merged = dict(catalog["templates"][key])
        for field, value in override.items():
            if field in ("notes", "description"):
                continue
            if value in ("", None):
                continue
            merged[field] = value
        catalog["templates"][key] = merged

    catalog["_template_overrides_path"] = str(p)


def require_server_url(args: argparse.Namespace) -> None:
    if getattr(args, "server", None):
        return
    print("GNS3 server URL is required.", file=sys.stderr)
    print("Set it with --server, GNS3_SERVER, or config/app_config.local.json.", file=sys.stderr)
    print("Example: cp config/app_config.example.json config/app_config.local.json", file=sys.stderr)
    raise SystemExit(2)


# -----------------------------
# General utilities
# -----------------------------

def deep_get(obj: Any, path: str) -> Any:
    current = obj
    for part in path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        else:
            current = current[part]
    return current


def deep_set(obj: Any, path: str, value: Any) -> None:
    parts = path.split(".")
    current = obj
    for part in parts[:-1]:
        if isinstance(current, list):
            current = current[int(part)]
        else:
            current = current.setdefault(part, {})
    last = parts[-1]
    if isinstance(current, list):
        current[int(last)] = value
    else:
        current[last] = value


def deep_delete(obj: Any, path: str) -> None:
    parts = path.split(".")
    current = obj
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    last = parts[-1]
    if isinstance(current, list):
        del current[int(last)]
    else:
        del current[last]


def deep_append(obj: Any, path: str, value: Any) -> None:
    target = deep_get(obj, path)
    if not isinstance(target, list):
        raise ValueError(f"Target is not a list: {path}")
    target.append(value)


def deep_extend(obj: Any, path: str, values: List[Any]) -> None:
    target = deep_get(obj, path)
    if not isinstance(target, list):
        raise ValueError(f"Target is not a list: {path}")
    target.extend(values)


# -----------------------------
# Catalog and template loading
# -----------------------------

def find_catalog(path: Optional[str]) -> Path:
    if path:
        p = Path(path)
        if not p.exists():
            print(f"Catalog not found: {p}", file=sys.stderr)
            raise SystemExit(2)
        return p

    script_dir = Path(__file__).resolve().parent
    cwd = Path.cwd()
    for name in DEFAULT_CATALOG_NAMES:
        for p in [cwd / name, script_dir / name]:
            if p.exists():
                return p

    print("Could not find ccnp_encor_lab_catalog.json. Use --catalog.", file=sys.stderr)
    raise SystemExit(2)


def load_catalog(path: Optional[str]) -> Dict[str, Any]:
    p = find_catalog(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Catalog has invalid JSON: {p}", file=sys.stderr)
        print(exc, file=sys.stderr)
        raise SystemExit(2) from exc

    for key in ["templates", "topologies", "scenarios"]:
        if key not in data:
            print(f"Catalog missing required top-level key: {key}", file=sys.stderr)
            raise SystemExit(2)

    data["_catalog_path"] = str(p)
    data["_catalog_dir"] = str(p.parent)
    return data


def resolve_template_dirs(args: argparse.Namespace, catalog: Dict[str, Any]) -> List[Path]:
    dirs: List[Path] = []

    if args.template_dir:
        dirs.append(Path(args.template_dir))

    catalog_dir = Path(catalog["_catalog_dir"])
    script_dir = Path(__file__).resolve().parent

    for entry in catalog.get("config_template_dirs", DEFAULT_TEMPLATE_DIRS):
        ep = Path(entry)
        dirs.append(ep if ep.is_absolute() else catalog_dir / ep)
        dirs.append(ep if ep.is_absolute() else script_dir / ep)

    # Preserve order but dedupe and require existing dirs.
    seen = set()
    final = []
    for d in dirs:
        rd = str(d.resolve()) if d.exists() else str(d)
        if rd in seen:
            continue
        seen.add(rd)
        if d.exists():
            final.append(d)

    if not final:
        print("No config template directory found. Use --template-dir.", file=sys.stderr)
        raise SystemExit(2)

    return final


def make_jinja_env(template_dirs: List[Path]) -> Any:
    if Environment is None:
        print("Jinja2 is required. Install with: /usr/bin/python3 -m pip install Jinja2", file=sys.stderr)
        raise SystemExit(2)

    env = Environment(
        loader=FileSystemLoader([str(p) for p in template_dirs]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    def ip_addr(cidr_or_addr: str) -> str:
        text = str(cidr_or_addr)
        if "/" in text:
            return str(ipaddress.ip_interface(text).ip)
        return text

    def ip_mask(cidr_or_addr: str) -> str:
        return str(ipaddress.ip_interface(str(cidr_or_addr)).network.netmask)

    def wildcard(cidr: str) -> str:
        net = ipaddress.ip_network(str(cidr), strict=False)
        return str(ipaddress.IPv4Address(int(net.hostmask)))

    def network_addr(cidr: str) -> str:
        return str(ipaddress.ip_network(str(cidr), strict=False).network_address)

    env.filters["ip_addr"] = ip_addr
    env.filters["ip_mask"] = ip_mask
    env.filters["wildcard"] = wildcard
    env.filters["network_addr"] = network_addr
    return env


# -----------------------------
# Listing helpers
# -----------------------------

def list_table(rows: List[Tuple[str, ...]], headers: Tuple[str, ...]) -> None:
    if not rows:
        print("No entries matched.")
        return
    widths = [max(len(str(row[i])) for row in rows + [headers]) for i in range(len(headers))]
    print("  ".join(headers[i].ljust(widths[i]) for i in range(len(headers))))
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        print("  ".join(str(row[i]).ljust(widths[i]) for i in range(len(headers))))


def filter_scenarios(catalog: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Dict[str, Any]]:
    result = {}
    exam_filter = getattr(args, "exam", None)
    for sid, s in catalog["scenarios"].items():
        if exam_filter:
            scenario_exams = [str(e).lower() for e in s.get("exam_blueprints", [])]
            if exam_filter.lower() not in scenario_exams:
                continue
        if args.domain and s.get("domain", "").lower() != args.domain.lower():
            continue
        if args.topic and s.get("topic", "").lower() != args.topic.lower():
            continue
        if args.difficulty and s.get("difficulty", "").lower() != args.difficulty.lower():
            continue
        if args.topology and s.get("topology", "").lower() != args.topology.lower():
            continue
        result[sid] = s
    return result


def list_scenarios(catalog: Dict[str, Any], args: argparse.Namespace) -> None:
    rows = []
    for sid, s in sorted(filter_scenarios(catalog, args).items()):
        rows.append((
            sid,
            scenario_concept_id(sid, s),
            "yes" if is_legacy_scenario(sid, s) else "no",
            ",".join(s.get("exam_blueprints", [])),
            s.get("topology", ""),
            s.get("domain", ""),
            s.get("topic", ""),
            s.get("difficulty", ""),
            s.get("title", ""),
        ))
    list_table(rows, ("ID", "Concept", "Legacy", "Exams", "Topology", "Domain", "Topic", "Difficulty", "Title"))


def topologies_for_exam(catalog: Dict[str, Any], exam: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """Return topologies relevant to an exam.

    Exam relevance is scenario-driven: a topology is included when at least one
    scenario using that topology has the requested exam in exam_blueprints.
    If exam is omitted, all topologies are returned.
    """
    if not exam:
        return dict(catalog["topologies"])

    exam_lower = exam.lower()
    matching_topology_ids = {
        scenario.get("topology")
        for scenario in catalog["scenarios"].values()
        if exam_lower in [str(e).lower() for e in scenario.get("exam_blueprints", [])]
    }
    return {
        tid: topo
        for tid, topo in catalog["topologies"].items()
        if tid in matching_topology_ids
    }


def topology_exam_summary(catalog: Dict[str, Any], topology_id: str) -> str:
    exams = sorted({
        exam
        for scenario in catalog["scenarios"].values()
        if scenario.get("topology") == topology_id
        for exam in scenario.get("exam_blueprints", [])
    })
    return ",".join(exams)


def topology_scenario_count(catalog: Dict[str, Any], topology_id: str, exam: Optional[str]) -> int:
    exam_lower = exam.lower() if exam else None
    count = 0
    for scenario in catalog["scenarios"].values():
        if scenario.get("topology") != topology_id:
            continue
        if exam_lower and exam_lower not in [str(e).lower() for e in scenario.get("exam_blueprints", [])]:
            continue
        count += 1
    return count

def is_legacy_scenario(scenario_id: str, scenario: Dict[str, Any]) -> bool:
    return bool(scenario.get("legacy_variant")) or scenario_id.endswith("_iosv")


def scenario_concept_id(scenario_id: str, scenario: Dict[str, Any]) -> str:
    if scenario_id.endswith("_iosv"):
        return scenario_id[:-5]
    return str(scenario.get("concept_id", scenario_id))


def unique_scenario_count(catalog: Dict[str, Any], exam: Optional[str] = None, domain: Optional[str] = None) -> int:
    exam_lower = exam.lower() if exam else None
    domain_lower = domain.lower() if domain else None
    concepts = set()
    for sid, scenario in catalog["scenarios"].items():
        if exam_lower and exam_lower not in [str(e).lower() for e in scenario.get("exam_blueprints", [])]:
            continue
        if domain_lower and str(scenario.get("domain", "")).lower() != domain_lower:
            continue
        concepts.add(scenario_concept_id(sid, scenario))
    return len(concepts)


def list_topologies(catalog: Dict[str, Any], args: argparse.Namespace) -> None:
    rows = []
    topologies = topologies_for_exam(catalog, getattr(args, "exam", None))
    for tid, t in sorted(topologies.items()):
        rows.append((
            tid,
            topology_exam_summary(catalog, tid),
            str(topology_scenario_count(catalog, tid, getattr(args, "exam", None))),
            str(len(t.get("nodes", {}))),
            str(len(t.get("links", []))),
            t.get("description", ""),
        ))
    list_table(rows, ("ID", "Exams", "Scenarios", "Nodes", "Links", "Description"))


def list_templates(catalog: Dict[str, Any]) -> None:
    rows = []
    for tid, t in sorted(catalog["templates"].items()):
        rows.append((tid, t.get("name", ""), t.get("template_type", ""), t.get("template_id", ""), t.get("create_mode", "template")))
    list_table(rows, ("Key", "Name", "Type", "Template ID", "Create Mode"))


def list_config_templates(template_dirs: List[Path]) -> None:
    found = []
    for d in template_dirs:
        for p in sorted(d.glob("*.j2")):
            found.append((p.name, str(p.parent)))
    list_table(found, ("Template", "Directory"))


# -----------------------------
# Scenario/topology materialization
# -----------------------------

def choose_scenario(catalog: Dict[str, Any], args: argparse.Namespace) -> Tuple[str, Dict[str, Any]]:
    filtered = filter_scenarios(catalog, args)

    if args.scenario == "random":
        if not filtered:
            print("No scenarios matched the requested filters.", file=sys.stderr)
            raise SystemExit(2)
        sid = random.choice(list(filtered.keys()))
        return sid, filtered[sid]

    if args.scenario not in catalog["scenarios"]:
        print(f"Unknown scenario: {args.scenario}", file=sys.stderr)
        print("Use --list-scenarios to see valid IDs.", file=sys.stderr)
        raise SystemExit(2)

    if args.domain or args.topic or args.difficulty or args.topology:
        if args.scenario not in filtered:
            print(f"Scenario {args.scenario!r} does not match the requested filters.", file=sys.stderr)
            raise SystemExit(2)

    return args.scenario, catalog["scenarios"][args.scenario]


def apply_data_patches(topology: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
    modified = copy.deepcopy(topology)

    for idx, patch in enumerate(scenario.get("data_patches", []), start=1):
        device = patch.get("device")
        if device not in modified["nodes"]:
            raise SystemExit(f"Data patch {idx}: unknown device {device!r}")

        node = modified["nodes"][device]
        action = patch["action"]
        # Paths are relative to the node object unless they explicitly start with "topology."
        if patch["path"].startswith("topology."):
            target_obj = modified
            path = patch["path"][len("topology."):]
        else:
            target_obj = node
            path = patch["path"]

        try:
            if action == "set":
                deep_set(target_obj, path, patch["value"])
            elif action == "delete":
                deep_delete(target_obj, path)
            elif action == "append":
                deep_append(target_obj, path, patch["value"])
            elif action == "extend":
                deep_extend(target_obj, path, patch["values"])
            else:
                raise ValueError(f"Unsupported data patch action: {action}")
        except Exception as exc:
            raise SystemExit(f"Data patch {idx} failed on {device}: {exc}") from exc

    return modified


def apply_text_patches(configs: Dict[str, str], scenario: Dict[str, Any]) -> Dict[str, str]:
    patched = dict(configs)
    for idx, patch in enumerate(scenario.get("config_patches", []), start=1):
        device = patch["device"]
        if device not in patched:
            raise SystemExit(f"Text patch {idx}: unknown device {device!r}")

        before = patched[device]
        action = patch["action"]
        if action == "replace":
            find, repl = patch["find"], patch["replace"]
            if find not in before:
                raise SystemExit(f"Text patch {idx}: string not found on {device}: {find!r}")
            patched[device] = before.replace(find, repl, patch.get("count", 1))
        elif action == "remove":
            find = patch["find"]
            if find not in before:
                raise SystemExit(f"Text patch {idx}: string not found on {device}: {find!r}")
            patched[device] = before.replace(find, "", patch.get("count", 1))
        elif action == "append":
            patched[device] = before.rstrip() + "\n" + patch["text"].rstrip() + "\n"
        elif action == "append_before_end":
            text = patch["text"].rstrip()
            if "\nend\n" in before:
                patched[device] = before.replace("\nend\n", f"\n{text}\nend\n", 1)
            else:
                patched[device] = before.rstrip() + f"\n{text}\nend\n"
        elif action == "regex_replace":
            patched_text, n = re.subn(patch["pattern"], patch["replace"], before, count=patch.get("count", 1), flags=re.MULTILINE)
            if n == 0:
                raise SystemExit(f"Text patch {idx}: regex matched nothing on {device}: {patch['pattern']!r}")
            patched[device] = patched_text
        else:
            raise SystemExit(f"Text patch {idx}: unsupported action {action!r}")

    return patched


def resolve_node_template_key(node: Dict[str, Any], host_type: str) -> str:
    key = node.get("template")
    if key == "host":
        return host_type
    return key


def is_iou_template(template: Dict[str, Any]) -> bool:
    """Return True for GNS3 IOU/IOL templates.

    The catalog treats link adapter values as a logical interface index. For IOU/IOL,
    GNS3's link API expects an adapter/port pair where Ethernet0/1 is adapter 0,
    port 1 and Ethernet1/0 is adapter 1, port 0. Other templates used by this
    project expose one useful Ethernet port per adapter, so their logical index maps
    directly to adapter N, port 0.
    """
    return str(template.get("template_type") or "").lower() == "iou"


def iou_logical_index_to_adapter_port(index: int) -> tuple[int, int]:
    return index // 4, index % 4


def link_endpoint_for_template(template: Dict[str, Any], logical_index: int) -> tuple[int, int]:
    if is_iou_template(template):
        return iou_logical_index_to_adapter_port(logical_index)
    return logical_index, 0


def iou_interface_name_for_index(index: int) -> str:
    adapter, port = iou_logical_index_to_adapter_port(index)
    return f"Ethernet{adapter}/{port}"


def resolve_config_template(node: Dict[str, Any], host_type: str) -> Optional[str]:
    if "config_template_by_host_type" in node:
        return node["config_template_by_host_type"].get(host_type)
    return node.get("config_template")


def render_configs(env: Any, topology: Dict[str, Any], host_type: str) -> Dict[str, str]:
    configs = {}
    topology_vars = topology.get("vars", {})

    for node_name, node in topology["nodes"].items():
        template_name = resolve_config_template(node, host_type)
        if not template_name:
            continue

        template = env.get_template(template_name)
        node_vars = copy.deepcopy(node.get("vars", {}))
        node_vars.setdefault("hostname", node_name)
        rendered = template.render(
            node=node,
            topology=topology,
            topology_vars=topology_vars,
            host_type=host_type,
            **node_vars,
        )
        configs[node_name] = rendered

    return configs


# -----------------------------
# GNS3 API
# -----------------------------

def gns3_api_session() -> requests.Session:
    """Return a shared requests session so GNS3 API calls reuse HTTP connections."""
    global _API_SESSION
    if _API_SESSION is None:
        _API_SESSION = requests.Session()
        _API_SESSION.headers.update({"Accept": "application/json"})
    return _API_SESSION


def api(method: str, base: str, path: str, **kwargs) -> Any:
    url = f"{base.rstrip('/')}/{path.lstrip('/')}"
    session = kwargs.pop("_session", None) or gns3_api_session()
    try:
        response = session.request(method, url, timeout=30, **kwargs)
    except requests.exceptions.ConnectionError as exc:
        print(f"Could not connect to the GNS3 API at {url}", file=sys.stderr)
        print(f"Test from this machine: curl {GNS3_DEFAULT}/v2/version", file=sys.stderr)
        raise SystemExit(2) from exc
    except requests.exceptions.Timeout as exc:
        print(f"Timed out connecting to the GNS3 API at {url}", file=sys.stderr)
        raise SystemExit(2) from exc

    try:
        response.raise_for_status()
    except requests.HTTPError:
        print(f"API call failed: {method} {url}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        raise
    if response.text:
        return response.json()
    return None


def create_project(base: str, name: str) -> Dict[str, Any]:
    return api("POST", base, "/v2/projects", json={"name": name})


def create_node(base: str, project_id: str, name: str, template: Dict[str, Any], x: int, y: int) -> Dict[str, Any]:
    if template.get("create_mode") == "direct_vpcs":
        payload = {
            "name": name,
            "node_type": "vpcs",
            "compute_id": template.get("compute_id", "local"),
            "x": x,
            "y": y,
            "properties": {},
        }
        return api("POST", base, f"/v2/projects/{project_id}/nodes", json=payload)

    payload = {"name": name, "x": x, "y": y}
    return api("POST", base, f"/v2/projects/{project_id}/templates/{template['template_id']}", json=payload)


def create_link(
    base: str,
    project_id: str,
    a_id: str,
    a_adapter: int,
    b_id: str,
    b_adapter: int,
    a_port: int = 0,
    b_port: int = 0,
) -> Dict[str, Any]:
    payload = {
        "nodes": [
            {"node_id": a_id, "adapter_number": a_adapter, "port_number": a_port},
            {"node_id": b_id, "adapter_number": b_adapter, "port_number": b_port},
        ]
    }
    return api("POST", base, f"/v2/projects/{project_id}/links", json=payload)


def create_catalog_link(
    base: str,
    project_id: str,
    catalog: Dict[str, Any],
    topology: Dict[str, Any],
    host_type: str,
    created_nodes: Dict[str, Any],
    link: Dict[str, Any],
) -> Dict[str, Any]:
    a_name = link["a"]
    b_name = link["b"]
    a_spec = topology["nodes"][a_name]
    b_spec = topology["nodes"][b_name]
    a_template = catalog["templates"][resolve_node_template_key(a_spec, host_type)]
    b_template = catalog["templates"][resolve_node_template_key(b_spec, host_type)]
    a_adapter, a_port = link_endpoint_for_template(a_template, int(link["a_adapter"]))
    b_adapter, b_port = link_endpoint_for_template(b_template, int(link["b_adapter"]))
    return create_link(
        base,
        project_id,
        created_nodes[a_name]["node_id"],
        a_adapter,
        created_nodes[b_name]["node_id"],
        b_adapter,
        a_port,
        b_port,
    )


def start_node(base: str, project_id: str, node_id: str) -> None:
    api("POST", base, f"/v2/projects/{project_id}/nodes/{node_id}/start", json={})


def read_node(base: str, project_id: str, node_id: str) -> Dict[str, Any]:
    return api("GET", base, f"/v2/projects/{project_id}/nodes/{node_id}")


def created_node_has_runtime_metadata(node: Dict[str, Any]) -> bool:
    return bool(node.get("node_id")) and node.get("console") is not None


def refresh_created_nodes(base: str, project_id: str, created_nodes: Dict[str, Any], progress: Optional[ProgressReporter] = None) -> Dict[str, Any]:
    """Fetch node details only when create responses did not include console data."""
    refreshed: Dict[str, Any] = {}
    skipped = 0
    for name, node in created_nodes.items():
        if created_node_has_runtime_metadata(node):
            refreshed[name] = node
            skipped += 1
            continue
        if progress:
            progress.detail(f"Refreshing metadata for {name}")
        refreshed[name] = read_node(base, project_id, node["node_id"])
    if progress and skipped:
        progress.detail(f"Used create responses for {skipped} node(s); skipped redundant node-detail reads")
    return refreshed


# -----------------------------
# telnetlib3 pusher
# -----------------------------

class TelnetPushError(RuntimeError):
    pass


def require_telnetlib3() -> None:
    if telnetlib3 is None:
        print("telnetlib3 is required for --push-config or --verify.", file=sys.stderr)
        print("Install it with: /usr/bin/python3 -m pip install telnetlib3", file=sys.stderr)
        raise SystemExit(2)


def tcp_wait(host: str, port: int, timeout: int = 420) -> None:
    deadline = time.time() + timeout
    last_error: Optional[BaseException] = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=5):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(3)
    raise TelnetPushError(f"Timed out waiting for {host}:{port}: {last_error}")


async def read_some(reader: Any, timeout: float = 1.0) -> str:
    chunks = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            chunk = await asyncio.wait_for(reader.read(4096), timeout=0.2)
            if not chunk:
                break
            chunks.append(chunk)
        except asyncio.TimeoutError:
            break
    return "".join(chunks)


async def write_line(writer: Any, line: str, delay: float = 0.1) -> None:
    writer.write(line + "\r\n")
    await writer.drain()
    await asyncio.sleep(delay)


async def prepare_ios_console(reader: Any, writer: Any, hostname: str, timeout: int = 240) -> str:
    deadline = time.time() + timeout
    buffer = ""
    while time.time() < deadline:
        await write_line(writer, "", 0.3)
        out = await read_some(reader, 1.0)
        buffer += out
        low = buffer.lower()

        if "would you like to enter the initial configuration dialog" in low:
            await write_line(writer, "no", 0.5)
            buffer = ""
            continue
        if "would you like to terminate autoinstall" in low:
            await write_line(writer, "yes", 0.5)
            buffer = ""
            continue
        if "press return to get started" in low:
            await write_line(writer, "", 0.5)
            buffer = ""
            continue
        if "password:" in low:
            await write_line(writer, "admin", 0.5)
            buffer = ""
            continue
        if re.search(r"[\r\n][A-Za-z0-9_.-]+>\s*$", buffer):
            await write_line(writer, "enable", 0.5)
            buffer = ""
            continue
        if re.search(r"[\r\n][A-Za-z0-9_.-]+#\s*$", buffer):
            return buffer

    raise TelnetPushError(f"{hostname}: console did not reach privileged exec prompt")


async def push_ios_config_to_console(host: str, port: int, hostname: str, config_text: str,
                                     chunk_lines: int = 15) -> str:
    require_telnetlib3()
    reader, writer = await telnetlib3.open_connection(host=host, port=port, connect_minwait=0.5, shell=None)
    log = []
    try:
        log.append(await prepare_ios_console(reader, writer, hostname))
        for cmd in ["terminal length 0", "configure terminal"]:
            await write_line(writer, cmd, 0.3)
            log.append(await read_some(reader, 0.8))

        lines = []
        for raw in config_text.splitlines():
            line = raw.rstrip()
            if not line or line.lower() == "end":
                continue
            lines.append(line)

        for i in range(0, len(lines), chunk_lines):
            for line in lines[i:i + chunk_lines]:
                await write_line(writer, line, 0.03)
            log.append(await read_some(reader, 0.8))

        for cmd in ["end", "write memory"]:
            await write_line(writer, cmd, 0.8)
            log.append(await read_some(reader, 3.0))
    finally:
        writer.close()
    return "".join(log)


async def run_ios_commands_on_console(host: str, port: int, hostname: str, commands: List[str]) -> str:
    require_telnetlib3()
    reader, writer = await telnetlib3.open_connection(host=host, port=port, connect_minwait=0.5, shell=None)
    log = []
    try:
        log.append(await prepare_ios_console(reader, writer, hostname))
        await write_line(writer, "terminal length 0", 0.3)
        log.append(await read_some(reader, 0.8))
        for cmd in commands:
            await write_line(writer, cmd, 0.5)
            log.append(f"\n\n===== {hostname}: {cmd} =====\n")
            log.append(await read_some(reader, 3.0))
    finally:
        writer.close()
    return "".join(log)


def should_push_node(node: Dict[str, Any]) -> bool:
    return bool(node.get("push_config", node.get("device_os") == "ios"))


def gns3_server_host(server_url: str) -> str:
    parsed = urlparse(server_url)
    if parsed.hostname:
        return parsed.hostname
    # Accept bare host strings as a convenience.
    return server_url.split("/")[0].split(":")[0]


def resolve_console_host(node: Dict[str, Any], server_url: str) -> str:
    """Return a client-reachable console host.

    GNS3 often reports console_host as 0.0.0.0 when the server listens on all
    interfaces. That address is not a valid remote destination for a client, so
    use the host from --server instead.
    """
    host = str(node.get("console_host") or "").strip()
    if host in ("", "0.0.0.0", "::", "[::]"):
        return gns3_server_host(server_url)
    return host


def push_cisco_configs(project_name: str, topology: Dict[str, Any], node_map: Dict[str, Dict[str, Any]],
                       configs: Dict[str, str], out_dir: Path, timeout: int, server_url: str) -> None:
    require_telnetlib3()
    push_dir = out_dir / project_name / "push_logs"
    push_dir.mkdir(parents=True, exist_ok=True)

    for device in sorted(node_map):
        node_def = topology["nodes"].get(device, {})
        if not should_push_node(node_def) or device not in configs:
            continue

        node = node_map[device]
        host = resolve_console_host(node, server_url)
        port = int(node.get("console") or 0)
        if not port:
            print(f"Skipping {device}: no console port")
            continue

        print(f"Pushing config to {device} at {host}:{port}")
        tcp_wait(host, port, timeout)
        log = asyncio.run(push_ios_config_to_console(host, port, device, configs[device]))
        (push_dir / f"{device}_push.log").write_text(log, encoding="utf-8", errors="ignore")


def endpoint_push_driver(node_def: Dict[str, Any], host_type: str) -> Optional[str]:
    explicit = node_def.get("endpoint_push_driver")
    if explicit:
        return str(explicit)

    template_key = resolve_node_template_key(node_def, host_type)
    if template_key == "vpcs" or host_type == "vpcs":
        return "vpcs"

    if node_def.get("device_os") == "linux" and template_key in {"alpine", "rhel9"}:
        return "linux-shell"

    if node_def.get("device_os") == "linux":
        return "linux-generated-only"

    return None


def default_linux_endpoint_username(host_type: str) -> str:
    if host_type == "rhel9":
        return "root"
    if host_type == "alpine":
        return "root"
    return "root"


def clean_shell_lines(script_text: str) -> List[str]:
    lines: List[str] = []
    for raw in script_text.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        lines.append(line)
    return lines


async def prepare_linux_console(reader: Any, writer: Any, username: str, password: str, timeout: int = 90) -> str:
    deadline = time.time() + timeout
    buffer = ""
    sent_username = False
    sent_password = False

    while time.time() < deadline:
        await write_line(writer, "", 0.3)
        out = await read_some(reader, 1.0)
        buffer += out
        low = buffer.lower()

        if ("login:" in low or low.endswith("login: ")) and not sent_username:
            await write_line(writer, username, 0.5)
            sent_username = True
            buffer = ""
            continue

        if "password:" in low and not sent_password:
            await write_line(writer, password, 0.8)
            sent_password = True
            buffer = ""
            continue

        # Common shell prompts. Keep this broad because Alpine/RHEL images vary.
        if any(prompt in buffer for prompt in ["# ", "$ ", "~# ", "~$ "]):
            return buffer

        # Some appliances boot directly to a shell after pressing enter.
        if sent_username and not password and any(prompt in buffer for prompt in ["> ", "# ", "$ "]):
            return buffer

    return buffer


async def push_linux_shell_config_to_console(host: str, port: int, node_name: str, config_text: str,
                                             username: str, password: str, timeout: int = 90) -> str:
    require_telnetlib3()
    reader, writer = await telnetlib3.open_connection(host=host, port=port, connect_minwait=0.5, shell=None)
    log: List[str] = []
    try:
        log.append(await prepare_linux_console(reader, writer, username, password, timeout=timeout))
        log.append(f"\n\n===== {node_name}: begin linux endpoint setup =====\n")
        for line in clean_shell_lines(config_text):
            await write_line(writer, line, 0.08)
            if line.startswith("cat > ") or line == "EOF":
                # Here-doc payloads benefit from slightly more time.
                await asyncio.sleep(0.08)
        await write_line(writer, "sync", 0.2)
        await write_line(writer, "ip addr show eth0", 0.2)
        await write_line(writer, "ip route", 0.2)
        log.append(await read_some(reader, 8.0))
        log.append(f"\n===== {node_name}: end linux endpoint setup =====\n")
    finally:
        writer.close()
    return "".join(log)


def vpcs_ip_command(node_def: Dict[str, Any]) -> Optional[str]:
    vars_ = node_def.get("vars", {})
    ip = vars_.get("ip")
    gateway = vars_.get("gateway")
    if not ip or not gateway:
        return None
    return f"ip {ip} {gateway}"


async def push_vpcs_config_to_console(host: str, port: int, node_name: str, node_def: Dict[str, Any]) -> str:
    require_telnetlib3()
    reader, writer = await telnetlib3.open_connection(host=host, port=port, connect_minwait=0.5, shell=None)
    log = []
    try:
        await write_line(writer, "", 0.5)
        log.append(await read_some(reader, 1.5))
        ip_cmd = vpcs_ip_command(node_def)
        if ip_cmd:
            for cmd in [ip_cmd, "save", "show ip"]:
                await write_line(writer, cmd, 0.5)
                log.append(f"\n\n===== {node_name}: {cmd} =====\n")
                log.append(await read_some(reader, 2.0))
        else:
            log.append(f"No VPCS IP configuration found for {node_name}\n")
    finally:
        writer.close()
    return "".join(log)


def push_endpoint_configs(project_name: str, topology: Dict[str, Any], node_map: Dict[str, Dict[str, Any]],
                          configs: Dict[str, str], out_dir: Path, timeout: int, server_url: str,
                          host_type: str, linux_username: Optional[str] = None,
                          linux_password: str = "", linux_login_timeout: int = 90) -> None:
    require_telnetlib3()
    push_dir = out_dir / project_name / "endpoint_push_logs"
    push_dir.mkdir(parents=True, exist_ok=True)

    for device in sorted(node_map):
        node_def = topology["nodes"].get(device, {})
        if should_push_node(node_def):
            continue

        driver = endpoint_push_driver(node_def, host_type)
        if driver is None:
            continue

        node = node_map[device]
        host = resolve_console_host(node, server_url)
        port = int(node.get("console") or 0)
        if not port:
            print(f"Skipping endpoint {device}: no console port")
            continue

        if driver == "vpcs":
            print(f"Pushing VPCS endpoint config to {device} at {host}:{port}")
            tcp_wait(host, port, timeout)
            log = asyncio.run(push_vpcs_config_to_console(host, port, device, node_def))
            (push_dir / f"{device}_endpoint_push.log").write_text(log, encoding="utf-8", errors="ignore")
        elif driver == "linux-shell":
            if device not in configs:
                print(f"Skipping Linux endpoint {device}: no generated endpoint setup config")
                continue
            username = linux_username or default_linux_endpoint_username(host_type)
            print(f"Pushing Linux endpoint setup to {device} at {host}:{port} as {username}")
            tcp_wait(host, port, timeout)
            log = asyncio.run(push_linux_shell_config_to_console(
                host, port, device, configs[device], username, linux_password, timeout=linux_login_timeout
            ))
            (push_dir / f"{device}_endpoint_push.log").write_text(log, encoding="utf-8", errors="ignore")
        elif driver == "linux-generated-only":
            msg = (
                f"Endpoint {device} is Linux-based. Setup script/config was generated, "
                "but no automatic console push driver is available for this host type.\n"
            )
            print(msg.strip())
            (push_dir / f"{device}_endpoint_push.log").write_text(msg, encoding="utf-8")


def collect_verification(project_name: str, topology: Dict[str, Any], scenario: Dict[str, Any],
                         node_map: Dict[str, Dict[str, Any]], out_dir: Path, timeout: int, server_url: str) -> None:
    require_telnetlib3()
    verify_dir = out_dir / project_name / "verification_output"
    verify_dir.mkdir(parents=True, exist_ok=True)

    global_cmds = scenario.get("verification", [])
    per_device = scenario.get("verification_by_device", {})

    for device in sorted(node_map):
        node_def = topology["nodes"].get(device, {})
        if not should_push_node(node_def):
            continue
        commands = list(per_device.get(device, global_cmds))
        if not commands:
            continue

        node = node_map[device]
        host = resolve_console_host(node, server_url)
        port = int(node.get("console") or 0)
        if not port:
            continue

        print(f"Collecting verification from {device}")
        tcp_wait(host, port, timeout)
        output = asyncio.run(run_ios_commands_on_console(host, port, device, commands))
        (verify_dir / f"{device}_verification.txt").write_text(output, encoding="utf-8", errors="ignore")


# -----------------------------
# Lab files
# -----------------------------


def md_bullets(items: List[str], fallback: str = "- Not documented.") -> str:
    clean = [str(item).strip() for item in items if str(item).strip()]
    return "\n".join(f"- {item}" for item in clean) if clean else fallback


def md_numbered(items: List[str], fallback: str = "No items documented.") -> str:
    clean = [str(item).strip() for item in items if str(item).strip()]
    return "\n".join(f"{idx}. {item}" for idx, item in enumerate(clean, start=1)) if clean else fallback


def scenario_terms(scenario: Dict[str, Any]) -> Set[str]:
    terms: Set[str] = set()
    for field in ("domain", "topic", "lab_type", "difficulty"):
        value = scenario.get(field)
        if isinstance(value, str):
            terms.add(value.lower())
    for tag in scenario.get("tags", []) or []:
        terms.add(str(tag).lower())
    return terms


def diagnostic_focus_blocks(scenario: Dict[str, Any]) -> str:
    """Build non-answer-giving troubleshooting guidance for the student walkthrough."""
    terms = scenario_terms(scenario)
    blocks: List[str] = []

    def add(title: str, commands: List[str], purpose: str) -> None:
        command_text = "\n".join(f"   - `{cmd}`" for cmd in commands)
        blocks.append(f"""### {title}

Purpose: {purpose}

Suggested commands:

{command_text}
""")

    if {"ospf", "routing"} & terms:
        add(
            "OSPF and routing control-plane checks",
            [
                "show ip ospf neighbor",
                "show ip ospf interface brief",
                "show ip protocols",
                "show ip route ospf",
                "show running-config | section router ospf",
            ],
            "Confirm whether the expected adjacencies form, whether interfaces participate in the intended area, and whether learned routes enter the RIB.",
        )

    if {"eigrp", "routing"} & terms:
        add(
            "EIGRP and routing checks",
            [
                "show ip eigrp neighbors",
                "show ip eigrp interfaces",
                "show ip protocols",
                "show ip route eigrp",
                "show running-config | section router eigrp",
            ],
            "Validate neighbor formation, participating interfaces, autonomous-system settings, and route installation before changing configuration.",
        )

    if {"bgp", "routing"} & terms:
        add(
            "BGP checks",
            [
                "show ip bgp summary",
                "show ip bgp",
                "show ip route bgp",
                "show running-config | section router bgp",
            ],
            "Determine whether sessions establish, prefixes are advertised/received, and policy is affecting route selection.",
        )

    if {"switching", "vlan", "stp", "etherchannel", "infrastructure"} & terms:
        add(
            "Layer 2 and campus switching checks",
            [
                "show interfaces status",
                "show vlan brief",
                "show interfaces trunk",
                "show spanning-tree summary",
                "show etherchannel summary",
            ],
            "Confirm VLAN presence, trunking, spanning-tree state, and bundled-link state before modifying interfaces.",
        )

    if {"first-hop", "hsrp", "vrrp", "glbp", "gateway"} & terms:
        add(
            "First-hop redundancy checks",
            [
                "show standby brief",
                "show vrrp brief",
                "show glbp brief",
                "show ip interface brief",
                "show running-config interface",
            ],
            "Verify active/standby roles, virtual IP addressing, priorities, tracking, and interface state.",
        )

    if {"security", "acl", "access-list", "policy", "qos"} & terms:
        add(
            "Policy, ACL, and QoS checks",
            [
                "show access-lists",
                "show running-config | include access-list|ip access-group|class-map|policy-map|service-policy",
                "show policy-map interface",
                "show ip interface",
            ],
            "Look for policy attachment, direction, match conditions, counters, and unintended denies or classification misses.",
        )

    if {"dhcp", "services"} & terms:
        add(
            "DHCP and infrastructure services checks",
            [
                "show ip dhcp binding",
                "show ip dhcp pool",
                "show ip helper-address",
                "show running-config interface",
                "show ip route",
            ],
            "Determine whether clients can reach the service, whether relays are present, and whether the pool/network information matches the topology.",
        )

    if {"automation", "programmability", "assurance"} & terms:
        add(
            "Automation and management-plane checks",
            [
                "show ip interface brief",
                "show running-config | include username|aaa|line vty|transport input|ip http|netconf|restconf",
                "show users",
                "show logging",
            ],
            "Confirm management reachability, credentials/AAA behavior, enabled services, and whether automation prerequisites exist.",
        )

    if not blocks:
        add(
            "General baseline checks",
            [
                "show ip interface brief",
                "show interfaces status",
                "show running-config",
                "show ip route",
                "show logging",
            ],
            "Build a neutral baseline of device state before deciding whether the problem is physical, Layer 2, Layer 3, management, or policy related.",
        )

    return "\n".join(blocks).strip()


def build_student_walkthrough(scenario: Dict[str, Any]) -> str:
    verification = scenario.get("verification", []) or []
    verify_text = md_bullets([f"`{cmd}`" for cmd in verification], "- Use the commands listed in `verification.md`, then add relevant `show running-config` checks for the affected feature.")

    return f"""This walkthrough is meant to teach the troubleshooting process without giving away the answer.

## 1. Establish the expected behavior

Read the symptom, requirements, expected results, and topology links. Write down what should be true when the lab is fixed: which neighbors should form, which routes or VLANs should exist, which services should work, and which traffic should pass.

## 2. Confirm the failure before changing anything

Run the listed verification commands first and save the output in your notes:

{verify_text}

Do not start by pasting configuration. First prove what is currently broken.

## 3. Scope the problem

Classify the issue as one or more of the following:

- Physical or interface state
- Layer 2/VLAN/trunking
- Layer 3 addressing or routing
- Control-plane adjacency or protocol configuration
- Policy, filtering, security, or QoS
- Management-plane or automation prerequisites

Use the scope to decide which devices and interfaces deserve attention.

## 4. Inspect configuration only after observing state

After the operational commands show where the behavior diverges from the requirement, inspect the relevant running configuration. Prefer focused commands such as `show running-config interface ...`, `show running-config | section ...`, or protocol-specific show commands instead of reading the whole config from top to bottom.

{diagnostic_focus_blocks(scenario)}

## 5. Make the smallest defensible change

Change only the configuration needed to satisfy the requirement. After each change, re-run the same verification command that proved the failure. If the output improves, continue. If it does not, revert or re-check your assumption.

## 6. Prove the fix

A lab is not complete when the command is entered; it is complete when the expected operational state is visible. Confirm the expected results, then optionally compare your finished configuration with `answer_key_configs/`.

## 7. Use the answer key correctly

Open `answer_key.md` only after you have isolated the likely fault or completed the skill check. Use it to compare reasoning, not just to copy commands."""


def explain_fault_impact(scenario: Dict[str, Any], fault_text: str) -> str:
    terms = scenario_terms(scenario)
    combined = " ".join([fault_text, scenario.get("symptom", ""), scenario.get("topic", "")]).lower()

    if "ospf" in combined or "ospf" in terms:
        if "area" in combined:
            return "OSPF requires matching area information on a link for the adjacency and LSDB exchange to behave correctly. A mismatched area prevents the expected neighbor state and keeps the associated routes from being learned through the intended path."
        if "network" in combined or "passive" in combined:
            return "OSPF only forms adjacencies on participating, non-passive interfaces. If the interface is excluded or suppressed, the device may have correct IP reachability but no routing-protocol relationship."
        return "The OSPF control plane is not matching the intended design, so neighbor state, LSDB exchange, or route installation does not converge as expected."

    if "eigrp" in combined or "eigrp" in terms:
        return "EIGRP depends on matching autonomous-system/K-values, reachable neighbors, and participating interfaces. A mismatch prevents the adjacency or blocks route exchange, so the RIB does not contain the expected EIGRP-learned paths."

    if "bgp" in combined or "bgp" in terms:
        return "BGP requires a valid neighbor relationship and correct prefix/policy handling. When the session or policy is wrong, prefixes are not exchanged or selected, even if basic IP reachability exists."

    if "vlan" in combined or "trunk" in combined:
        return "VLAN and trunk inconsistencies break Layer 2 reachability. Hosts or routed SVIs may look correctly configured locally, but frames are not carried across the expected path."

    if "spanning" in combined or "stp" in combined:
        return "Spanning Tree controls which Layer 2 paths forward. A wrong STP setting can block the intended path, elect the wrong root, or leave access connectivity unstable."

    if "etherchannel" in combined or "port-channel" in combined:
        return "EtherChannel requires compatible member settings. A mismatch prevents links from bundling or causes traffic to use an unintended path."

    if "acl" in combined or "access-list" in combined:
        return "ACLs are directional packet filters. A wrong match, order, or interface direction can silently block traffic that the rest of the topology would otherwise route correctly."

    if "dhcp" in combined or "helper" in combined:
        return "DHCP relay depends on the client-facing interface forwarding broadcasts to the correct server. If relay or pool information is wrong, clients cannot obtain valid addressing even when the routed network is otherwise healthy."

    if "hsrp" in combined or "vrrp" in combined or "glbp" in combined:
        return "First-hop redundancy protocols rely on matching virtual gateway settings and healthy participating interfaces. A mismatch causes hosts to use an unavailable or incorrect default gateway."

    if "qos" in combined or "policy" in combined:
        return "QoS and policy features depend on correct classification and attachment. If the policy is attached incorrectly or matches the wrong traffic, the intended treatment is never applied."

    if "automation" in terms or "management" in combined:
        return "Automation depends on management-plane reachability and enabled services. If credentials, transport, API services, or reachability are wrong, tooling fails even when the data plane may be healthy."

    return "The configured state does not match the intended design. That mismatch prevents the observed operational state from satisfying the lab requirements."



def scenario_commands_for_guidance(scenario: Dict[str, Any]) -> List[str]:
    commands: List[str] = []
    commands.extend(str(cmd) for cmd in scenario.get("verification", []) if cmd)
    answer_key = scenario.get("answer_key", {}) if isinstance(scenario.get("answer_key", {}), dict) else {}
    commands.extend(str(cmd) for cmd in answer_key.get("verification", []) if cmd)
    seen: Set[str] = set()
    result: List[str] = []
    for cmd in commands:
        if cmd not in seen:
            seen.add(cmd)
            result.append(cmd)
    return result


def build_scenario_context_notes(scenario_id: str, scenario: Dict[str, Any]) -> str:
    tags = ", ".join(scenario.get("tags", []) or []) or "No detailed tags supplied."
    requirements = md_bullets(scenario.get("requirements", []) or [], "- No explicit requirements were listed; work from the symptom, topology, and expected results.")
    expected = md_bullets(scenario.get("expected_results", []) or [], "- No explicit expected result was listed; use the verification section and answer key after you finish.")
    commands = md_bullets([f"`{cmd}`" for cmd in scenario_commands_for_guidance(scenario)], "- No scenario-specific verification commands were listed.")
    return f"""## Lab Context

This lab is meant to be approached like a real troubleshooting ticket. Start by proving the symptom, then narrow the fault domain before changing configuration. Avoid jumping straight into the answer key: the goal is to build a repeatable diagnostic process you can use on an unfamiliar network.

- Scenario ID: `{scenario_id}`
- Domain: {scenario.get('domain', 'Unknown')}
- Topic: {scenario.get('topic', 'Unknown')}
- Difficulty: {scenario.get('difficulty', 'Unknown')}
- Lab type: {scenario.get('lab_type', 'Unknown')}
- Tags: {tags}

## Requirements or Success Criteria

{requirements}

## Expected End State

{expected}

## Useful Commands to Start With

{commands}
"""




def interface_name_from_node_vars(node: Dict[str, Any], logical_index: int) -> Optional[str]:
    vars_obj = node.get("vars", {}) if isinstance(node.get("vars", {}), dict) else {}
    interfaces = vars_obj.get("interfaces", []) or []
    if 0 <= logical_index < len(interfaces):
        entry = interfaces[logical_index]
        if isinstance(entry, dict) and entry.get("name"):
            return str(entry["name"])
    return None


def interface_name_for_template(template: Dict[str, Any], logical_index: int) -> str:
    if is_iou_template(template):
        return iou_interface_name_for_index(logical_index)
    return f"Ethernet{logical_index}/0"


def interface_name_for_topology_endpoint(node: Dict[str, Any], template: Dict[str, Any], logical_index: int) -> str:
    return interface_name_from_node_vars(node, logical_index) or interface_name_for_template(template, logical_index)


def topology_link_rows(catalog: Dict[str, Any], topology: Dict[str, Any], host_type: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx, link in enumerate(topology.get("links", []), start=1):
        a_name = str(link.get("a", ""))
        b_name = str(link.get("b", ""))
        a_spec = topology.get("nodes", {}).get(a_name, {})
        b_spec = topology.get("nodes", {}).get(b_name, {})
        a_template = catalog.get("templates", {}).get(resolve_node_template_key(a_spec, host_type), {})
        b_template = catalog.get("templates", {}).get(resolve_node_template_key(b_spec, host_type), {})
        a_idx = int(link.get("a_adapter", 0))
        b_idx = int(link.get("b_adapter", 0))
        a_adapter, a_port = link_endpoint_for_template(a_template, a_idx)
        b_adapter, b_port = link_endpoint_for_template(b_template, b_idx)
        rows.append({
            "index": idx,
            "a": a_name,
            "a_logical_index": a_idx,
            "a_interface": interface_name_for_topology_endpoint(a_spec, a_template, a_idx),
            "a_gns3_adapter": a_adapter,
            "a_gns3_port": a_port,
            "b": b_name,
            "b_logical_index": b_idx,
            "b_interface": interface_name_for_topology_endpoint(b_spec, b_template, b_idx),
            "b_gns3_adapter": b_adapter,
            "b_gns3_port": b_port,
            "label": link.get("label", ""),
        })
    return rows


def build_topology_map(project_name: str, topology_id: str, catalog: Dict[str, Any], topology: Dict[str, Any], host_type: str) -> str:
    rows = topology_link_rows(catalog, topology, host_type)
    table = [
        "| # | Device A | Interface A | GNS3 A/P | Device B | Interface B | GNS3 A/P | Purpose / Label |",
        "|---:|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        table.append(
            f"| {row['index']} | `{row['a']}` | `{row['a_interface']}` | `{row['a_gns3_adapter']}/{row['a_gns3_port']}` | "
            f"`{row['b']}` | `{row['b_interface']}` | `{row['b_gns3_adapter']}/{row['b_gns3_port']}` | {row['label'] or '-'} |"
        )
    if len(table) == 2:
        table.append("| - | - | - | - | - | - | - | No links documented. |")
    node_lines = []
    for name, node in topology.get("nodes", {}).items():
        template_key = resolve_node_template_key(node, host_type)
        node_lines.append(f"`{name}`: template `{template_key}`, role `{node.get('role', 'node')}`")
    return f"""# Topology Map - {project_name}

Topology: `{topology_id}`

This map is the reference point for comparing generated GNS3 links against the interfaces used in device configurations. In the GNS3 application, enable interface labels and compare them to the device/interface pairs below.

## Nodes

{md_bullets(node_lines, '- No nodes documented.')}

## Links

{chr(10).join(table)}

## Notes

- For IOL/IOU templates, catalog interface indexes are logical Ethernet indexes. For example, logical index `4` maps to `Ethernet1/0`.
- The GNS3 adapter/port columns show the API endpoint used to create the link.
- Use this file when a lab appears fixed from the CLI but traffic still fails; it helps distinguish a configuration issue from a topology/interface mismatch.
"""


def build_progressive_hints(scenario_id: str, scenario: Dict[str, Any]) -> str:
    supplied = [str(h) for h in scenario.get("hints", []) if h]
    title = scenario.get("title", scenario_id)
    commands = scenario_commands_for_guidance(scenario)[:8]
    command_text = md_bullets([f"`{cmd}`" for cmd in commands], "- Use the verification commands listed for this lab, then inspect the relevant configuration section.")
    if supplied:
        specific = "\n\n".join(f"### Hint {idx}\n\n{hint}" for idx, hint in enumerate(supplied, start=1))
    else:
        specific = "### Hint 1\n\nStart by proving the symptom from the CLI before changing anything. Compare the expected behavior in `expected_results.md` with the current operational state."
    return f"""# Progressive Hints - {title}

Use these hints gradually. The goal is to help you build the habit of proving each step instead of jumping straight to a configuration edit.

## How to Use This File

1. Read one hint.
2. Run the related verification command.
3. Write down what changed or what failed to change.
4. Only reveal the next hint when you are stuck or when your current theory does not explain the evidence.

## Scenario-Specific Hints

{specific}

## Diagnostic Command Nudge

These commands are useful starting points for this scenario. They are diagnostic, not just answer-revealing:

{command_text}

## Final Nudge Before the Answer Key

Before opening `answer_key.md`, make sure you can state three things in your own words: what is broken, why that breaks the expected behavior, and what minimal change should fix it.
"""


def validate_generated_lab_files(lab_dir: Path, topology: Dict[str, Any], faulty_configs: Dict[str, str]) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    def add(status: str, message: str) -> None:
        results.append({"status": status, "message": message})
    for dirname in ["starter_configs", "answer_key_configs"]:
        path = lab_dir / dirname
        add("PASS" if path.exists() else "WARN", f"{dirname}/ {'exists' if path.exists() else 'was not found'}.")
    for name, node in topology.get("nodes", {}).items():
        if should_push_node(node) and faulty_configs and name not in faulty_configs:
            add("WARN", f"Cisco/config-push node {name} does not have a rendered starter config.")
    for link in topology.get("links", []):
        for side in ["a", "b"]:
            node = link.get(side)
            if not node or node not in topology.get("nodes", {}):
                add("FAIL", f"Topology link references missing or unknown endpoint: {node}")
    if not any(r["status"] == "FAIL" for r in results):
        add("PASS", "Topology link endpoints reference known nodes.")
    return results


def validation_markdown(results: List[Dict[str, str]]) -> str:
    return "\n".join(f"- **{r['status']}**: {r['message']}" for r in results) or "- No validation results were produced."

def build_validation_report(project_name: str, scenario_id: str, scenario: Dict[str, Any], topology: Dict[str, Any], lab_dir: Path, faulty_configs: Dict[str, str]) -> str:
    results = validate_generated_lab_files(lab_dir, topology, faulty_configs)
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    warn_count = sum(1 for r in results if r["status"] == "WARN")
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    overall = "PASS" if fail_count == 0 else "FAIL"
    return f"""# Validation Report - {scenario.get('title', scenario_id)}

## Summary

- Overall status: **{overall}**
- Project: `{project_name}`
- Scenario ID: `{scenario_id}`
- Lab folder: `{lab_dir}`
- Pass checks: {pass_count}
- Warnings: {warn_count}
- Failures: {fail_count}

## What This Report Checks

This generated report is a local consistency check. It is intended to catch lab-construction problems before the learner spends time troubleshooting a broken scaffold. It does not prove that the learner has solved the scenario; it proves that the generated files and topology references look internally consistent.

## Details

{validation_markdown(results)}

## Suggested Use

If this report shows a failure, treat the generated lab as suspect and fix the generator/catalog issue before using the lab for study. If it shows warnings only, review them and decide whether they are expected for the topology.
"""


def build_lab_metadata(project_name: str, project: Dict[str, Any], scenario_id: str, scenario: Dict[str, Any], topology_id: str,
                       topology: Dict[str, Any], catalog: Dict[str, Any], host_type: str, node_map: Dict[str, Any], lab_mode: str = "scenario") -> Dict[str, Any]:
    docs = {
        "readme": "README.md",
        "student_brief": "student_brief.md",
        "walkthrough": "first_time_walkthrough.md",
        "hints": "hints.md",
        "topology_map": "topology_map.md",
        "generation_summary": "generation_summary.md",
        "validation": "validation_report.md",
        "answer_key": "answer_key.md",
        "requirements": "requirements.md",
        "expected_results": "expected_results.md",
        "verification": "verification.md",
    }
    if lab_mode == "blank-topology":
        docs = {"readme": "README.md", "topology_map": "topology_map.md", "generation_summary": "generation_summary.md", "validation": "validation_report.md"}
    return {
        "schema_version": "1.0",
        "lab_mode": lab_mode,
        "project_name": project_name,
        "project_id": project.get("project_id"),
        "scenario_id": scenario_id,
        "title": scenario.get("title", scenario_id),
        "domain": scenario.get("domain"),
        "topic": scenario.get("topic"),
        "difficulty": scenario.get("difficulty"),
        "lab_type": scenario.get("lab_type"),
        "topology_id": topology_id,
        "host_type": host_type,
        "documents": docs,
        "config_sets": {"initial": "starter_configs", "answer_key": "answer_key_configs"} if lab_mode != "blank-topology" else {"baseline": "blank_topology_configs"},
        "nodes": [{"name": name, "role": topology.get("nodes", {}).get(name, {}).get("role", "node"), "node_id": node.get("node_id") if isinstance(node, dict) else None, "console": node.get("console") if isinstance(node, dict) else None} for name, node in node_map.items()],
        "links": topology_link_rows(catalog, topology, host_type),
    }

def build_generation_summary(project_name: str, scenario_id: str, scenario: Dict[str, Any], topology_id: str,
                             lab_dir: Path, topology: Dict[str, Any], args: argparse.Namespace) -> str:
    cisco_nodes = [name for name, node in topology.get("nodes", {}).items() if should_push_node(node)]
    endpoint_nodes = [name for name, node in topology.get("nodes", {}).items() if not should_push_node(node)]
    verification = scenario_commands_for_guidance(scenario)
    validation_text = validation_markdown(validate_generated_lab_files(lab_dir, topology, {}))
    is_blank = str(scenario.get("lab_type", "")) == "blank-topology"
    generated_content = """- README: `README.md`
- Topology map: `topology_map.md`
- Generation summary: `generation_summary.md`
- Validation report: `validation_report.md`
- Workspace metadata: `metadata.json`
- Baseline configs: `blank_topology_configs/`""" if is_blank else """- Student brief: `student_brief.md`
- First-time walkthrough: `first_time_walkthrough.md`
- Requirements: `requirements.md`
- Hints: `hints.md`
- Expected results: `expected_results.md`
- Verification commands: `verification.md`
- Answer key: `answer_key.md`
- Starter configs: `starter_configs/`
- Answer configs: `answer_key_configs/`
- Endpoint setup files: `endpoint_setup/`
- Topology map: `topology_map.md`
- Validation report: `validation_report.md`
- Workspace metadata: `metadata.json`"""
    next_actions = """1. Open `topology_map.md` and compare the interface map against GNS3 interface labels.
2. Use `blank_topology_configs/` as baseline examples if you want starter configuration.
3. Customize the topology manually for your own lab design.""" if is_blank else """1. Open `student_brief.md` and read the scenario story and symptom.
2. Use `first_time_walkthrough.md` to guide your first pass without revealing the exact fix.
3. Confirm the failure from the CLI before editing configuration.
4. Make the smallest change that explains the symptom.
5. Use `verification.md` to prove the fix.
6. Open `answer_key.md` only after you can explain the root cause in your own words."""
    return f"""# Generation Summary - {scenario.get('title', scenario_id)}

## What Was Generated

- Project name: `{project_name}`
- Scenario ID: `{scenario_id}`
- Topology: `{topology_id}`
- Local lab folder: `{lab_dir}`
- Device count: {len(topology.get('nodes', {}))}
- Link count: {len(topology.get('links', []))}

## Generated Content

{generated_content}

## Push / Automation Settings Used

- Start nodes: {'yes' if getattr(args, 'start', False) else 'no'}
- Push Cisco configs: {'yes' if getattr(args, 'push_config', False) else 'no'}
- Push supported endpoint configs: {'yes' if getattr(args, 'push_endpoints', False) else 'no'}
- Collect verification output: {'yes' if getattr(args, 'verify', False) else 'no'}
- Host type: `{getattr(args, 'host_type', 'unknown')}`

## Node Groups

Cisco/config-push nodes:
{md_bullets(cisco_nodes, '- None identified.')}

Endpoint/manual or endpoint-push nodes:
{md_bullets(endpoint_nodes, '- None identified.')}

## Generation Validation

{validation_text}

## Suggested Next Actions

{next_actions}

## Primary Verification Commands

{md_bullets([f'`{cmd}`' for cmd in verification], '- No scenario-specific verification commands were listed.')}
"""


def preflight_required_template_keys(topology: Dict[str, Any], host_type: str) -> List[str]:
    keys: List[str] = []
    for node in topology.get("nodes", {}).values():
        key = resolve_node_template_key(node, host_type)
        if key not in keys:
            keys.append(key)
    return keys


def validate_iol_interface_alignment(catalog: Dict[str, Any], topology: Dict[str, Any], host_type: str) -> List[str]:
    """Return catalog/link/config alignment errors for IOL/IOU nodes.

    Link entries use a logical interface index. For IOL/IOU, logical index 0 is
    Ethernet0/0, 1 is Ethernet0/1, 2 is Ethernet0/2, 3 is Ethernet0/3, and 4 is
    Ethernet1/0. This check prevents a generated lab from linking one interface
    while configuring another.
    """
    errors: List[str] = []
    for node_name, node in topology.get("nodes", {}).items():
        template_key = resolve_node_template_key(node, host_type)
        template = catalog.get("templates", {}).get(template_key, {})
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
            legacy_wrong_name = f"Ethernet{logical_index}/0"
            old_qemu_style_name = f"Ethernet0/{logical_index}"
            if legacy_wrong_name in configured or old_qemu_style_name in configured:
                errors.append(
                    f"Node {node_name} uses IOL logical link index {logical_index}, which should configure "
                    f"{expected_name}; found likely-mismatched interface config instead."
                )
    return errors


def run_preflight(args: argparse.Namespace, catalog: Dict[str, Any], scenario_id: str, scenario: Dict[str, Any]) -> int:
    topology_id = scenario.get("topology")
    print("Preflight Readiness Check")
    print("=========================")
    print(f"Scenario: {scenario_id} - {scenario.get('title', '')}")
    print(f"Topology: {topology_id}")
    print(f"GNS3 server: {args.server}")
    print(f"Output directory: {args.out}")
    print(f"Host type: {args.host_type}")
    print()

    failures: List[str] = []
    warnings: List[str] = []
    topology = catalog.get("topologies", {}).get(topology_id)
    if not topology:
        failures.append(f"Scenario references missing topology: {topology_id}")
        topology = {"nodes": {}, "links": []}

    out_path = Path(args.out)
    try:
        out_path.mkdir(parents=True, exist_ok=True)
        test_file = out_path / ".gns3_generator_write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        print(f"[PASS] Output directory is writable: {out_path}")
    except Exception as exc:
        failures.append(f"Output directory is not writable: {out_path} ({exc})")

    required_keys = preflight_required_template_keys(topology, args.host_type)
    print(f"[INFO] Required template keys: {', '.join(required_keys) if required_keys else 'none'}")
    for key in required_keys:
        template = catalog.get("templates", {}).get(key)
        if not template:
            failures.append(f"Missing catalog template mapping for key: {key}")
            continue
        if template.get("create_mode") != "direct_vpcs" and not template.get("template_id"):
            warnings.append(f"Template key {key} has no template_id. It may require local overrides before generation.")

    interface_alignment_errors = validate_iol_interface_alignment(catalog, topology, args.host_type)
    if interface_alignment_errors:
        failures.extend(interface_alignment_errors)
    else:
        print("[PASS] IOL link/interface alignment check passed.")

    try:
        version = api("GET", args.server, "/v2/version")
        print(f"[PASS] GNS3 API reachable: {version.get('version', 'unknown version') if isinstance(version, dict) else version}")
    except SystemExit:
        failures.append("GNS3 API is not reachable. Confirm the server URL and that GNS3 is running.")
    except Exception as exc:
        failures.append(f"GNS3 API check failed: {exc}")

    if not failures:
        try:
            live_templates = fetch_gns3_templates_by_id(args.server)
            missing_live: List[str] = []
            for key in required_keys:
                template = catalog.get("templates", {}).get(key, {})
                if template.get("create_mode") == "direct_vpcs":
                    continue
                template_id = template.get("template_id")
                if template_id and template_id not in live_templates:
                    missing_live.append(f"{key} ({template.get('name', key)} / {template_id})")
            if missing_live:
                failures.append("Required GNS3 templates were not found on the server: " + "; ".join(missing_live))
            else:
                print("[PASS] Required GNS3 templates were found by template_id where applicable.")
        except Exception as exc:
            warnings.append(f"Could not complete live template lookup: {exc}")

    if not failures:
        try:
            validate_topology_ports_against_live_templates(args.server, catalog, topology, args.host_type)
            print("[PASS] Template port/adapters check passed.")
        except SystemExit as exc:
            failures.append(str(exc))
        except Exception as exc:
            warnings.append(f"Template port/adapters check could not be completed: {exc}")

    print()
    if warnings:
        print("Warnings:")
        for item in warnings:
            print(f"- {item}")
        print()
    if failures:
        print("Result: NOT READY")
        print("Fix these items before generating:")
        for item in failures:
            print(f"- {item}")
        return 1
    print("Result: READY")
    print("This scenario appears ready to generate with the current server, template, output, and host settings.")
    return 0

def build_answer_key_details(scenario: Dict[str, Any]) -> str:
    answer_key = scenario.get("answer_key", {}) if isinstance(scenario.get("answer_key", {}), dict) else {}
    faults = scenario.get("faults", []) or []
    verification = answer_key.get("verification") or scenario.get("verification", []) or []
    profile = topic_guidance_profile(scenario)

    root_cause = answer_key.get("root_cause") or "The scenario does not provide a dedicated root-cause summary. Review the documented faults below and connect them to the reported symptom."
    fix_summary = answer_key.get("fix_summary") or "Apply the documented fault remediation below, then verify the expected results."

    fault_sections: List[str] = []
    for idx, fault in enumerate(faults, start=1):
        device = fault.get("device", "unknown")
        fault_desc = fault.get("fault", "Not specified.")
        fix = fault.get("fix", "Not specified.")
        impact = explain_fault_impact(scenario, fault_desc)
        fault_sections.append(spaced_sections(
            f"### Fault {idx}: {device}",
            f"**What is wrong:** {fault_desc}",
            f"**Why it causes the reported symptom:** {impact}",
            f"**How to fix it:** {fix}",
            f"**Why this fix is correct:** The fix restores the intended design element that the fault broke. It should be limited to the affected device, interface, protocol relationship, or policy attachment unless the lab requirements explicitly call for a broader design change.",
        ))

    if not fault_sections:
        fault_sections.append(spaced_sections(
            "### Documented Faults",
            "No explicit per-device faults are documented for this scenario. Use the root-cause and fix summary as the authoritative answer for this lab.",
        ))

    verify_items = [f"`{cmd}` — run this after the corrective action and compare the output against the expected behavior." for cmd in verification]
    verify_text = md_bullets(verify_items, "- No verification commands documented.")
    expected_text = md_bullets(scenario.get("expected_results", []) or [], "- No expected results documented.")
    grading_text = md_bullets(scenario.get("grading_criteria", []) or [], "- No grading criteria documented.")
    wrong_fix_text = md_bullets(profile.get("wrong", []), "- Do not make broad configuration changes unless you can tie them directly to the observed symptom.")
    proof_commands = md_bullets([f"`{cmd}`" for cmd in (profile.get("commands", []) or verification)], "- Use the scenario verification commands and focused show commands for this technology area.")

    return spaced_sections(
        "## Root Cause",
        root_cause,
        "## Why This Caused the Reported Symptoms",
        explain_fault_impact(scenario, root_cause),
        "## How to Prove It",
        "Before applying or accepting the fix, prove where the behavior diverges from the requirement. These commands are useful evidence points:",
        proof_commands,
        "## Corrective Action Summary",
        fix_summary,
        "## Detailed Fault Analysis",
        "".join(fault_sections).strip(),
        "## Common Wrong Fixes",
        wrong_fix_text,
        "## Verification Procedure",
        "After applying the fix, run the verification commands again. The point is not only that the command succeeds; the output should prove that the original user-facing symptom is gone.",
        verify_text,
        "## Expected Successful Outcomes",
        expected_text,
        "## What a Complete Fix Should Demonstrate",
        "A complete solution shows that the original symptom is gone, the relevant control-plane or data-plane state is stable, and the configuration change is limited to the actual fault. Avoid broad rewrites that mask the issue without explaining it.",
        "## Grading Criteria",
        grading_text,
        "## Configuration Reference",
        "The files in `answer_key_configs/` contain the known-good final configurations. Use them after completing the lab to compare your solution against the generated reference state.",
    )




# -----------------------------
# 3.0 structured workspace content
# -----------------------------

def safe_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if value:
        return [str(value)]
    return []

def content_topic_key(scenario: Dict[str, Any]) -> str:
    combined = " ".join(
        [
            str(scenario.get("topic", "")),
            str(scenario.get("domain", "")),
            str(scenario.get("symptom", "")),
            " ".join(str(t) for t in scenario.get("tags", []) or []),
            " ".join(str(f.get("fault", "")) for f in scenario.get("faults", []) or [] if isinstance(f, dict)),
        ]
    ).lower()
    if "bgp" in combined:
        return "bgp"
    if "ospf" in combined:
        return "ospf"
    if "eigrp" in combined:
        return "eigrp"
    if "etherchannel" in combined or "port-channel" in combined or "port channel" in combined:
        return "etherchannel"
    if "stp" in combined or "spanning" in combined:
        return "stp"
    if "hsrp" in combined or "vrrp" in combined or "glbp" in combined:
        return "fhrp"
    if "dhcp" in combined or "helper" in combined:
        return "dhcp"
    if "acl" in combined or "access-list" in combined or "pbr" in combined or "route-map" in combined:
        return "policy"
    if "vlan" in combined or "trunk" in combined:
        return "switching"
    if "qos" in combined or "policy" in combined:
        return "qos"
    if "automation" in combined or "netconf" in combined or "restconf" in combined or "management" in combined:
        return "automation"
    return "general"


def learner_visible_symptom(scenario: Dict[str, Any]) -> str:
    """Return symptom text suitable for student-facing sections.

    Catalog symptom fields sometimes include a useful root-cause clause such as
    "because X is missing on Y". That is appropriate for internal generation
    and answer keys, but it gives away the lab in the Student Brief and
    Observed Symptoms sections. Strip causal/root-cause clauses while keeping
    the user-visible failure description.
    """
    symptom = str(scenario.get("symptom") or "The reported behavior does not match the expected network state.").strip()
    if not symptom:
        return "The reported behavior does not match the expected network state."

    # Remove common trailing causal clauses that expose the answer. Keep this
    # intentionally conservative so ordinary symptom wording remains intact.
    patterns = [
        r"\s*(?:,|;)\s*because\b.*$",
        r"\s+because\b.*$",
        r"\s*(?:,|;)\s*due to\b.*$",
        r"\s+due to\b.*$",
        r"\s*(?:,|;)\s*caused by\b.*$",
        r"\s+caused by\b.*$",
        r"\s*(?:,|;)\s*as a result of\b.*$",
        r"\s+as a result of\b.*$",
    ]
    cleaned = symptom
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    # Remove parenthetical causal notes, for example "(... caused by X)".
    cleaned = re.sub(r"\s*\((?:because|due to|caused by|as a result of)\b[^)]*\)", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = cleaned.rstrip(" ,;:-")
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned or "The reported behavior does not match the expected network state."


def observed_symptom_text(scenario: Dict[str, Any]) -> str:
    symptom = learner_visible_symptom(scenario)
    lower = symptom.lower()
    if lower.startswith(("users report", "operators report", "the help desk reports", "network users report")):
        return symptom
    return f"Users or operators report that {symptom[0].lower() + symptom[1:] if symptom else 'the service is not behaving as expected.'}"


def topic_guidance_profile(scenario: Dict[str, Any]) -> Dict[str, Any]:
    key = content_topic_key(scenario)
    profiles = {
        "bgp": {
            "concept": "BGP troubleshooting starts with the neighbor session. Route policy and prefix selection only matter after the session is established.",
            "flow": ["Confirm IP reachability to the neighbor.", "Check BGP neighbor state.", "Compare neighbor IP, remote AS, source/update-source, and expected AS ownership.", "Only then inspect route policy or prefix advertisement."],
            "commands": ["show ip bgp summary", "show ip route", "show ip interface brief", "show running-config | section router bgp"],
            "wrong": ["Changing the local AS before proving the router itself is in the wrong AS.", "Troubleshooting route maps before the neighbor session is Established.", "Clearing BGP repeatedly without fixing the underlying neighbor parameter or reachability issue."],
        },
        "ospf": {
            "concept": "OSPF failures usually show up as missing neighbors, incorrect neighbor state, missing LSAs, or routes not entering the RIB.",
            "flow": ["Confirm participating interfaces and IP reachability.", "Check OSPF neighbor state.", "Compare area, network type, authentication, passive-interface, and timers where relevant.", "Verify OSPF routes after the adjacency or LSDB issue is corrected."],
            "commands": ["show ip ospf neighbor", "show ip ospf interface brief", "show ip route ospf", "show running-config | section router ospf"],
            "wrong": ["Changing interface addressing before proving reachability is wrong.", "Redistributing or adding static routes to hide an OSPF adjacency problem.", "Changing every OSPF parameter instead of isolating the specific mismatch."],
        },
        "eigrp": {
            "concept": "EIGRP depends on correct neighbor formation, participating interfaces, and compatible process settings before routes can be exchanged.",
            "flow": ["Confirm the expected neighbors exist.", "Check interface participation and autonomous system or named-mode settings.", "Inspect route tables and topology entries.", "Verify EIGRP routes are installed after the fix."],
            "commands": ["show ip eigrp neighbors", "show ip eigrp interfaces", "show ip route eigrp", "show running-config | section router eigrp"],
            "wrong": ["Adding static routes instead of restoring the EIGRP relationship.", "Changing unrelated K-values or timers without evidence.", "Assuming IP reachability means the routing process is participating correctly."],
        },
        "etherchannel": {
            "concept": "EtherChannel requires compatible member settings. The bundle must form cleanly before VLAN or routing behavior through the bundle can be trusted.",
            "flow": ["Check the port-channel summary.", "Compare member interface mode, trunking, allowed VLANs, speed/duplex, and LACP/PAgP mode.", "Fix the mismatch on the intended member interface.", "Verify the bundle is up and forwarding."],
            "commands": ["show etherchannel summary", "show interfaces trunk", "show running-config interface", "show spanning-tree"],
            "wrong": ["Removing the port-channel and rebuilding it from scratch without identifying the mismatch.", "Fixing only one side of a negotiation mismatch.", "Troubleshooting routing before the Layer 2 bundle is up."],
        },
        "stp": {
            "concept": "Spanning Tree determines which Layer 2 links forward. The right question is often whether the intended root and port roles match the design.",
            "flow": ["Identify the root bridge.", "Inspect port roles and blocked ports.", "Compare bridge priority/path cost/guard settings to the expected design.", "Verify forwarding is stable after the fix."],
            "commands": ["show spanning-tree", "show spanning-tree root", "show spanning-tree blockedports", "show running-config | include spanning-tree"],
            "wrong": ["Disabling STP to make a link forward.", "Changing VLAN trunks before checking root placement and port roles.", "Removing guard features without understanding why they triggered."],
        },
        "fhrp": {
            "concept": "First-hop redundancy depends on matching virtual gateway settings and healthy active/standby behavior.",
            "flow": ["Confirm host default-gateway expectations.", "Check FHRP state on participating routers.", "Compare virtual IP, group, priority, preemption, and tracked interfaces.", "Verify hosts use the restored virtual gateway."],
            "commands": ["show standby brief", "show vrrp brief", "show glbp brief", "show ip interface brief"],
            "wrong": ["Changing host addressing before proving the virtual gateway is wrong.", "Making both routers active with inconsistent group settings.", "Ignoring interface tracking or priority behavior."],
        },
        "dhcp": {
            "concept": "DHCP relay problems often appear as endpoint addressing failures even when routing between infrastructure devices is otherwise healthy.",
            "flow": ["Confirm the client is not receiving correct addressing.", "Identify the client-facing gateway/interface.", "Check relay/helper and server/pool reachability.", "Verify the client receives an address and can reach required destinations."],
            "commands": ["show ip interface brief", "show running-config interface", "show ip dhcp binding", "show ip route"],
            "wrong": ["Changing the client VLAN before proving the relay path is wrong.", "Fixing the DHCP server while the relay interface is missing or incorrect.", "Assuming an APIPA/no-address symptom is a Layer 1 issue."],
        },
        "policy": {
            "concept": "ACL, PBR, and route-map problems require attention to match logic, order, direction, and attachment point.",
            "flow": ["Confirm the traffic or route behavior that is failing.", "Identify where policy is applied.", "Check match order and direction.", "Verify the intended traffic is permitted, denied, or redirected as required."],
            "commands": ["show access-lists", "show route-map", "show running-config interface", "show ip policy"],
            "wrong": ["Deleting the whole policy instead of correcting the specific match or direction.", "Changing routing when an attached policy is filtering or redirecting traffic.", "Ignoring ACL order and implicit deny behavior."],
        },
        "switching": {
            "concept": "Switching and VLAN faults often come from an allowed VLAN, access VLAN, native VLAN, or trunking state mismatch.",
            "flow": ["Confirm which VLAN or host path is affected.", "Check access/trunk state.", "Compare allowed VLANs and native/access VLAN settings.", "Verify Layer 2 reachability and any SVI/routed behavior after the fix."],
            "commands": ["show vlan brief", "show interfaces trunk", "show interfaces switchport", "show mac address-table"],
            "wrong": ["Changing IP routing before proving the VLAN is carried correctly.", "Adding all VLANs to a trunk without understanding the requirement.", "Changing native VLANs to hide an access VLAN mismatch."],
        },
        "qos": {
            "concept": "QoS and policy labs depend on the right classification, attachment point, and direction before any treatment can occur.",
            "flow": ["Identify the traffic class or behavior under test.", "Confirm policy attachment and direction.", "Inspect class-map/policy-map matches.", "Verify counters or expected treatment after the fix."],
            "commands": ["show policy-map interface", "show class-map", "show running-config | section policy-map", "show running-config | section class-map"],
            "wrong": ["Changing DSCP/CoS values before proving classification is wrong.", "Attaching a policy in the wrong direction.", "Editing the policy while traffic is not matching the class."],
        },
        "automation": {
            "concept": "Automation and management-plane labs depend on reachability, enabled services, credentials, and API/transport behavior.",
            "flow": ["Confirm the management endpoint is reachable.", "Check whether the required service or API is enabled.", "Validate credentials, source interface, and control-plane policy.", "Verify the tool can complete the intended action."],
            "commands": ["show ip interface brief", "show running-config | include netconf|restconf|username|aaa", "show control-plane", "show logging"],
            "wrong": ["Troubleshooting data-plane routing while the service is disabled.", "Changing credentials without verifying the transport/API state.", "Ignoring ACL or control-plane restrictions on management access."],
        },
    }
    return profiles.get(key, {
        "concept": "The lab should be approached as an evidence-driven troubleshooting exercise: observe, isolate, change minimally, and verify.",
        "flow": ["Confirm the reported symptom.", "Map affected devices and links.", "Inspect relevant operational state.", "Compare intended and actual configuration.", "Apply and verify a minimal fix."],
        "commands": ["show ip interface brief", "show running-config", "show ip route"],
        "wrong": ["Changing multiple unrelated settings at once.", "Opening the answer key before proving the symptom.", "Applying a broad workaround instead of correcting the actual mismatch."],
    })


def spaced_sections(*sections: str) -> str:
    return "\n\n".join(section.strip() for section in sections if str(section).strip()) + "\n"


def build_guided_steps_data(scenario_id: str, scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
    commands = scenario_commands_for_guidance(scenario)
    profile = topic_guidance_profile(scenario)
    profile_commands = profile.get("commands", [])
    combined_commands: List[str] = []
    for cmd in list(profile_commands) + list(commands):
        if cmd and cmd not in combined_commands:
            combined_commands.append(str(cmd))

    return [
        {
            "id": "understand-scenario",
            "title": "Understand the ticket",
            "objective": "Build a plain-language picture of what users are experiencing and what the network is supposed to do.",
            "instructions": "Read the Scenario Brief, Requirements, and Observed Symptoms. Do not treat the symptom as the named root cause. Treat it as the user-facing problem that your troubleshooting must explain.",
            "what_to_look_for": "Identify the affected service, path, users, VLAN, routing relationship, or management function before opening configuration.",
            "suggested_commands": [],
            "related_devices": [],
            "completion_criteria": "You can summarize the user-visible problem and the expected behavior in your own words.",
        },
        {
            "id": "confirm-symptom",
            "title": "Confirm the symptom from device state",
            "objective": "Prove the reported behavior from the CLI before making any change.",
            "instructions": "Use operational commands to observe the broken state. This step is about evidence, not configuration edits.",
            "what_to_look_for": "Look for a neighbor that is not formed, a route that is missing, a VLAN/path that is not forwarding, a policy counter that is not matching, or endpoint behavior that does not meet the requirement.",
            "suggested_commands": combined_commands[:5],
            "related_devices": [],
            "completion_criteria": "You have CLI evidence that matches the reported symptom.",
        },
        {
            "id": "map-topology",
            "title": "Map the affected topology",
            "objective": "Tie the symptom to specific devices, links, interfaces, and protocol relationships.",
            "instructions": "Use the topology view and topology table to identify the path or relationship that must work for the requirement to pass.",
            "what_to_look_for": "Focus on the devices and links that sit between the user-visible symptom and the expected outcome. Ignore unrelated nodes until evidence brings them into scope.",
            "suggested_commands": ["show ip interface brief", "show interfaces description"],
            "related_devices": [],
            "completion_criteria": "You know which devices, interfaces, and relationships are in scope.",
        },
        {
            "id": "inspect-topic-state",
            "title": "Inspect the relevant control/data plane",
            "objective": profile.get("concept", "Narrow the likely fault domain using protocol and interface state."),
            "instructions": "Follow the technology-specific diagnostic flow for this topic before reading configuration line by line.",
            "what_to_look_for": " ".join(profile.get("flow", [])),
            "suggested_commands": combined_commands[:8],
            "related_devices": [],
            "completion_criteria": "You can state whether the failure is most likely reachability, adjacency/control-plane, Layer 2 forwarding, policy, addressing, or service enablement.",
        },
        {
            "id": "compare-intended-actual",
            "title": "Compare intended state to actual configuration",
            "objective": "Find the smallest configuration mismatch that explains the observed symptom.",
            "instructions": "Inspect focused configuration sections only after operational state points you there. Do not rewrite broad sections of config just because they look unfamiliar.",
            "what_to_look_for": "Compare the requirement, topology, interface role, protocol relationship, and policy attachment against the actual running configuration.",
            "suggested_commands": ["show running-config interface", "show running-config | section router", "show running-config | include access-list|route-map|neighbor|network|standby|channel-group"],
            "related_devices": [],
            "completion_criteria": "You have a specific theory for what is wrong and why it explains the symptom.",
        },
        {
            "id": "apply-minimal-fix",
            "title": "Apply the smallest defensible fix",
            "objective": "Correct the root cause while preserving the intended design.",
            "instructions": "Make one targeted change, then stop. Avoid broad cleanups or design changes unless the lab explicitly requires them.",
            "what_to_look_for": "The fix should directly address the mismatch you identified, not merely work around the symptom.",
            "suggested_commands": [],
            "related_devices": [],
            "completion_criteria": "Your change directly addresses the suspected root cause and does not modify unrelated behavior.",
        },
        {
            "id": "verify-result",
            "title": "Verify the result",
            "objective": "Prove that the original user-visible problem is gone.",
            "instructions": "Re-run the commands that proved the failure and compare the new state against the requirements and expected results.",
            "what_to_look_for": "The expected operational state should now be visible: neighbors formed, routes installed, traffic permitted, clients addressed, policies matching, or services reachable as appropriate.",
            "suggested_commands": combined_commands[:8],
            "related_devices": [],
            "completion_criteria": "The expected behavior is visible and the original symptom is no longer present.",
        },
        {
            "id": "review-answer-key",
            "title": "Review the answer key for understanding",
            "objective": "Use the answer key to validate your reasoning, not just to copy a command.",
            "instructions": "After you finish or get stuck, read the answer key as an explanation: what happened, why it caused the symptom, how to prove it, and why the fix is correct.",
            "what_to_look_for": "Compare the answer key reasoning against your own notes. Pay attention to common wrong fixes and any verification step you missed.",
            "suggested_commands": [],
            "related_devices": [],
            "completion_criteria": "You can explain the root cause, symptom chain, fix, and verification procedure without reading the answer key aloud.",
        },
    ]

def build_hints_data(scenario_id: str, scenario: Dict[str, Any], steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    profile = topic_guidance_profile(scenario)
    supplied = safe_list(scenario.get("hints"))
    defaults = [
        "Start by proving the user-visible symptom. Do not assume the named technology is the root cause yet.",
        "Use the topology map to identify the smallest set of devices and interfaces that could explain the report.",
        profile.get("concept", "Separate operational evidence from configuration assumptions."),
        "Compare the expected relationship or forwarding path with the actual state shown by focused show commands.",
        "The fix should be small enough that you can explain exactly why it resolves the reported symptom.",
    ]
    hint_bodies = supplied or defaults
    step_cycle = ["confirm-symptom", "map-topology", "inspect-topic-state", "compare-intended-actual", "apply-minimal-fix"]
    result = []
    for idx, body in enumerate(hint_bodies, 1):
        result.append({
            "id": f"hint-{idx}",
            "step_id": step_cycle[min(idx - 1, len(step_cycle) - 1)],
            "level": idx,
            "title": f"Hint {idx}: " + ["Start with evidence", "Narrow the scope", "Use the topic model", "Compare intended vs actual", "Strong nudge"][min(idx - 1, 4)],
            "body": str(body),
        })
    return result

def topology_json_data(catalog: Dict[str, Any], topology: Dict[str, Any], host_type: str) -> Dict[str, Any]:
    """Return the machine-readable topology used by the 3.0 workspace.

    `topology_link_rows()` returns normalized rows for the markdown map with
    keys such as `a`, `b`, `a_gns3_adapter`, and `a_gns3_port`. Earlier 3.0
    alpha builds accidentally looked for `a_node`, `a_adapter`, etc. and wrote
    `null` endpoint values into `topology.json`, which meant the topology table
    and graphics renderer had no usable endpoints. Keep this mapping explicit.
    """
    links = []
    for r in topology_link_rows(catalog, topology, host_type):
        links.append({
            "a_node": r.get("a"),
            "a_interface": r.get("a_interface"),
            "a_adapter": r.get("a_gns3_adapter"),
            "a_port": r.get("a_gns3_port"),
            "a_logical_index": r.get("a_logical_index"),
            "b_node": r.get("b"),
            "b_interface": r.get("b_interface"),
            "b_adapter": r.get("b_gns3_adapter"),
            "b_port": r.get("b_gns3_port"),
            "b_logical_index": r.get("b_logical_index"),
            "purpose": r.get("label") or "lab link",
        })
    return {
        "schema_version":"4.0",
        "nodes":[{"name":n,"role":d.get("role","node"),"template":d.get("template"),"platform":d.get("platform") or d.get("template")} for n,d in topology.get("nodes",{}).items()],
        "links": links,
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def copy_text_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def write_structured_workspace_content(lab_dir: Path, project_name: str, project: Dict[str, Any], scenario_id: str,
                                       scenario: Dict[str, Any], topology_id: str, topology: Dict[str, Any],
                                       catalog: Dict[str, Any], host_type: str, catalog_path: str,
                                       node_map: Dict[str, Any], requirements_text: str, expected_text: str,
                                       story: str, context_notes: str) -> None:
    content_dir = lab_dir / "content"; exports_dir = lab_dir / "exports"; reports_dir = lab_dir / "reports"
    for d in [content_dir, exports_dir, reports_dir, lab_dir/"configs"/"initial", lab_dir/"configs"/"answer_key"]:
        d.mkdir(parents=True, exist_ok=True)
    for src_dir, dst_dir in [(lab_dir/"starter_configs", lab_dir/"configs"/"initial"), (lab_dir/"answer_key_configs", lab_dir/"configs"/"answer_key")]:
        if src_dir.exists():
            for src in src_dir.iterdir():
                if src.is_file():
                    (dst_dir/src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    steps = build_guided_steps_data(scenario_id, scenario)
    hints = build_hints_data(scenario_id, scenario, steps)
    topo = topology_json_data(catalog, topology, host_type)
    answer_obj = scenario.get("answer_key", {}) if isinstance(scenario.get("answer_key", {}), dict) else {}
    project_info = {"schema_version":"4.0","project_name":project_name,"project_id":project.get("project_id"),"scenario_id":scenario_id,"title":scenario.get("title", scenario_id),"exam":scenario.get("exam"),"domain":scenario.get("domain"),"topic":scenario.get("topic"),"difficulty":scenario.get("difficulty"),"lab_type":scenario.get("lab_type"),"study_paths":scenario.get("study_paths"),"platforms":scenario.get("platforms"),"skills":scenario.get("skills"),"audience":scenario.get("audience"),"exam_alignment":scenario.get("exam_blueprints"),"topology_id":topology_id,"host_type":host_type,"catalog_path":catalog_path}
    write_json(content_dir/"project_info.json", project_info)
    observed_symptom = observed_symptom_text(scenario)
    profile = topic_guidance_profile(scenario)
    write_json(content_dir/"scenario.json", {"title":scenario.get("title", scenario_id),"story":story,"what_you_are_seeing":observed_symptom,"approach":"Confirm the user-visible symptom, narrow the fault domain, apply a minimal fix, and verify."})
    write_json(content_dir/"requirements.json", {"requirements":safe_list(scenario.get("requirements")),"success_criteria":safe_list(scenario.get("expected_results"))})
    write_json(content_dir/"observations.json", {"observed_symptoms":[observed_symptom],"expected_results":safe_list(scenario.get("expected_results")),"note":"Symptoms are written from the learner's point of view. They describe what users or operators observe, not the exact configuration defect."})
    write_json(content_dir/"lab_context.json", {"context_notes_markdown":context_notes,"technology_model":profile.get("concept"),"diagnostic_flow":profile.get("flow",[]),"verification_commands":scenario_commands_for_guidance(scenario)})
    write_json(content_dir/"guided_steps.json", steps)
    write_json(content_dir/"hints.json", hints)
    write_json(content_dir/"answer_key.json", {"root_cause":answer_obj.get("root_cause","Not documented."),"symptom_chain":explain_fault_impact(scenario, answer_obj.get("root_cause", "")),"fix_summary":answer_obj.get("fix_summary","Not documented."),"faults":scenario.get("faults",[]),"verification":safe_list(answer_obj.get("verification") or scenario.get("verification")),"common_wrong_fixes":profile.get("wrong",[])})
    write_json(content_dir/"topology.json", topo); write_json(lab_dir/"topology.json", topo)
    slim_brief = f"""# {scenario.get('title', scenario_id)}

## Scenario Story

{story}


## What Users Are Seeing

{observed_symptom}


## Lab Context

{context_notes}


## Requirements

{requirements_text}


## Expected Outcome

{expected_text}


## How to Approach This Lab

Work like a troubleshooter, not like someone hunting for a magic command. First prove what users are reporting, then identify the affected devices and interfaces, then inspect the smallest configuration area that could explain the observed behavior.

Make one focused change at a time and verify after each change. If you need to use hints, use them to improve your investigation path rather than to skip directly to the solution.
"""
    (lab_dir/"student_brief.md").write_text(slim_brief, encoding="utf-8")
    (lab_dir/"project_info.md").write_text("# Project Info\n\n" + "\n".join(f"- **{k.replace('_',' ').title()}**: `{v}`" for k,v in project_info.items() if v is not None) + "\n", encoding="utf-8")
    guided_md = [f"# Guided Practice - {scenario.get('title', scenario_id)}\n"]
    for idx, step in enumerate(steps, 1):
        cmds = "\n".join(f"- `{cmd}`" for cmd in step.get("suggested_commands", []) if cmd) or "- No specific command required for this step."
        guided_md.append(f"## Step {idx}: {step['title']}\n\n**Objective:** {step['objective']}\n\n{step['instructions']}\n\n### What to Look For\n\n{step.get('what_to_look_for', 'Look for operational evidence that supports or disproves your current theory.')}\n\n### Suggested Commands\n\n{cmds}\n\n### Completion Criteria\n\n{step['completion_criteria']}\n")
    (lab_dir/"guided_practice.md").write_text("\n".join(guided_md), encoding="utf-8")
    (lab_dir/"first_time_walkthrough.md").write_text("\n".join(guided_md), encoding="utf-8")
    (lab_dir/"hints.md").write_text("# Hints\n\n" + "\n".join(f"## {h['title']}\n\n{h['body']}\n" for h in hints), encoding="utf-8")
    for name in ["student_brief.md","project_info.md","guided_practice.md","first_time_walkthrough.md","hints.md","requirements.md","expected_results.md","verification.md","answer_key.md","topology_map.md","validation_report.md","generation_summary.md"]:
        copy_text_if_exists(lab_dir/name, exports_dir/name)
    for name in ["generation_summary.md","validation_report.md"]:
        copy_text_if_exists(lab_dir/name, reports_dir/name)
    manifest = {"schema_version":"4.0","lab_mode":"scenario","project":project_info,"paths":{"content":"content/","exports":"exports/","reports":"reports/","configs_initial":"configs/initial/","configs_answer":"configs/answer_key/"},"sections":{"project_info":"content/project_info.json","scenario":"content/scenario.json","requirements":"content/requirements.json","observations":"content/observations.json","lab_context":"content/lab_context.json","guided_steps":"content/guided_steps.json","hints":"content/hints.json","answer_key":"content/answer_key.json","topology":"content/topology.json"},"documents":{"project_info":"project_info.md","student_brief":"student_brief.md","guided_practice":"guided_practice.md","walkthrough":"first_time_walkthrough.md","hints":"hints.md","requirements":"requirements.md","expected_results":"expected_results.md","verification":"verification.md","topology_map":"topology_map.md","generation_summary":"generation_summary.md","validation":"validation_report.md","answer_key":"answer_key.md","readme":"README.md"},"config_sets":{"initial":"configs/initial","answer_key":"configs/answer_key"},"deployment":{"gns3_project_id":project.get("project_id"),"nodes":{k:{"node_id":v.get("node_id"),"console":v.get("console"),"console_host":v.get("console_host")} for k,v in node_map.items()}}}
    write_json(lab_dir/"lab_manifest.json", manifest); write_json(lab_dir/"metadata.json", manifest)


def write_lab_files(out_dir: Path, project_name: str, scenario_id: str, scenario: Dict[str, Any],
                    topology_id: str, clean_topology: Dict[str, Any], faulty_topology: Dict[str, Any],
                    project: Dict[str, Any], node_map: Dict[str, Any], clean_configs: Dict[str, str],
                    faulty_configs: Dict[str, str], host_type: str, catalog_path: str, catalog: Optional[Dict[str, Any]] = None) -> None:
    lab_dir = out_dir / project_name
    cfg_dir = lab_dir / "configs"
    clean_dir = lab_dir / "clean_configs"
    starter_dir = lab_dir / "starter_configs"
    answer_dir = lab_dir / "answer_key_configs"
    endpoint_dir = lab_dir / "endpoint_setup"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)
    starter_dir.mkdir(parents=True, exist_ok=True)
    answer_dir.mkdir(parents=True, exist_ok=True)
    endpoint_dir.mkdir(parents=True, exist_ok=True)

    for device, cfg in faulty_configs.items():
        (cfg_dir / f"{device}.cfg").write_text(cfg, encoding="utf-8")
        (starter_dir / f"{device}.cfg").write_text(cfg, encoding="utf-8")
    for device, cfg in clean_configs.items():
        (clean_dir / f"{device}.cfg").write_text(cfg, encoding="utf-8")
        (answer_dir / f"{device}.cfg").write_text(cfg, encoding="utf-8")

    for node_name, node_def in faulty_topology.get("nodes", {}).items():
        if should_push_node(node_def):
            continue
        if node_name in faulty_configs:
            driver = endpoint_push_driver(node_def, host_type) or "generated"
            suffix = ".vpcs" if driver == "vpcs" else ".sh"
            (endpoint_dir / f"{node_name}{suffix}").write_text(faulty_configs[node_name], encoding="utf-8")

    links = "\n".join("- " + l.get("label", f"{l['a']}:{l['a_adapter']} <-> {l['b']}:{l['b_adapter']}") for l in clean_topology.get("links", []))
    verify = "\n".join("- `" + cmd + "`" for cmd in scenario.get("verification", [])) or "- No commands listed."
    fault_text = "\n".join(
        f"- Device: `{f.get('device', 'unknown')}`; Fault: {f.get('fault', 'not specified')}; Fix: {f.get('fix', 'not specified')}"
        for f in scenario.get("faults", [])
    ) or "- No faults documented."

    answer_key_obj = scenario.get("answer_key", {})
    answer_key_summary = ""
    if isinstance(answer_key_obj, dict):
        answer_key_summary = f"""## Root Cause

{answer_key_obj.get('root_cause', 'Not documented.')}

## Fix Summary

{answer_key_obj.get('fix_summary', 'Not documented.')}
"""
    grading = scenario.get("grading_criteria", [])
    grading_text = "\n".join(f"- {item}" for item in grading) or "- No grading criteria documented."

    requirements = scenario.get("requirements", [])
    requirements_text = "\n".join(f"{idx}. {item}" for idx, item in enumerate(requirements, start=1)) or "No explicit requirements listed."

    hints = scenario.get("hints", [])
    hints_text = "\n".join(f"{idx}. {item}" for idx, item in enumerate(hints, start=1)) or "No hints are documented for this scenario yet."

    expected = scenario.get("expected_results", [])
    expected_text = "\n".join(f"- {item}" for item in expected) or "Use the verification commands and answer key to confirm success."

    lab_type = scenario.get("lab_type", "lab")
    story_action = "configuration requirements" if lab_type == "skill-check" else "reported symptoms"
    story = (
        f"You have been assigned to investigate a {scenario.get('difficulty', 'practice')} {scenario.get('domain', 'network')} lab. "
        f"The environment has been generated in GNS3 and the initial device state represents the {story_action}. "
        f"Your job is to work from the symptom, requirements, and verification data to produce a stable, supportable network state."
    )

    guided_steps = build_student_walkthrough(scenario)

    context_notes = build_scenario_context_notes(scenario_id, scenario)

    first_time_guide = f"""This walkthrough is intentionally procedural rather than answer-oriented. Think of it as a mentor sitting next to you and asking, “What do you know, how do you know it, and what would you check next?” It should help you build the troubleshooting path without giving away the exact answer.

{context_notes}

## Suggested Order for New Users

1. Read `student_brief.md` once without opening the answer key. You are looking for the symptom, the expected behavior, and the rough technology area.
2. Open `requirements.md` and `expected_results.md`. Translate each expected result into something you can prove from a device CLI.
3. Run the commands in `verification.md` before changing anything. Save or copy the broken-state output if you want to compare it later.
4. Use the guided steps below to narrow the fault domain. Work from broad state, then neighbor/session/interface state, then specific configuration.
5. Make one small, defensible fix at a time. After each change, re-run the relevant verification command instead of changing several things at once.
6. Use `hints.md` only after your first independent pass. Hints are meant to nudge your investigation, not replace it.
7. Open `answer_key.md` only after you can explain what is wrong and why your fix should work.
8. Compare against `answer_key_configs/` as the final reference. Treat those files as a grading reference, not as the starting point."""

    brief = f"""# {scenario.get('title', scenario_id)}

## Scenario ID

`{scenario_id}`

## Project

`{project_name}`

## Scenario Story

{story}

## What You Are Seeing

{observed_symptom_text(scenario)}

## How to Approach This Lab

Treat the symptom as a clue, not as the answer. First prove what is broken, then decide whether the failure is likely control-plane, data-plane, addressing, policy, or endpoint related. The walkthrough gives you a safe path through that process without immediately revealing the fix.

## Metadata

- Topology: `{topology_id}`
- Domain: {scenario.get('domain', 'Unknown')}
- Topic: {scenario.get('topic', 'Unknown')}
- Difficulty: {scenario.get('difficulty', 'Unknown')}
- Lab type: {scenario.get('lab_type', 'Unknown')}
- Catalog: `{catalog_path}`

## Requirements

{requirements_text}

## Guided Troubleshooting Walkthrough

{guided_steps}

## Hints

{hints_text}

## Expected Results

{expected_text}

## Topology Links

{links}

## Suggested Verification

{verify}

## Generated Files

- `starter_configs/`: Starter configs intended for the learner.
- `answer_key_configs/`: Known-good answer configs.
- `endpoint_setup/`: Endpoint setup artifacts.
- `requirements.md`: Requirement summary.
- `hints.md`: Hints if you need a nudge.
- `expected_results.md`: Success indicators.
- `verification.md`: Suggested verification commands.
- `first_time_walkthrough.md`: Procedural troubleshooting walkthrough that does not reveal the answer.
- `grading_criteria.md`: Skill-check grading criteria where applicable.
- `answer_key.md`: Root cause, fix summary, and verification guidance.
- `generation_summary.md`: What was generated, automation settings used, and next steps.

## First-Time or Stuck Walkthrough

{first_time_guide}

## Notes

- Start with the student brief, requirements, and starter configs.
- Do not open the answer key until you have isolated the issue or completed the skill check.
- If endpoint auto-push was not used or did not complete, apply the files in `endpoint_setup/` manually.
"""
    (lab_dir / "student_brief.md").write_text(brief, encoding="utf-8")

    (lab_dir / "first_time_walkthrough.md").write_text(
        f"# First-Time Walkthrough - {scenario.get('title', scenario_id)}\n\n{guided_steps}\n",
        encoding="utf-8",
    )

    answer_details = build_answer_key_details(scenario)

    answer = f"""# Answer Key - {scenario.get('title', scenario_id)}

## Scenario ID

`{scenario_id}`

{answer_details}

## Project Metadata

```json
{json.dumps(project, indent=2)}
```

## Node Metadata

```json
{json.dumps({k: {'node_id': v.get('node_id'), 'console': v.get('console'), 'console_host': v.get('console_host')} for k, v in node_map.items()}, indent=2)}
```
"""
    (lab_dir / "answer_key.md").write_text(answer, encoding="utf-8")

    summary_args = argparse.Namespace(start=False, push_config=False, push_endpoints=False, verify=False, host_type=host_type)
    (lab_dir / "generation_summary.md").write_text(
        build_generation_summary(project_name, scenario_id, scenario, topology_id, lab_dir, faulty_topology, summary_args),
        encoding="utf-8",
    )

    (lab_dir / "requirements.md").write_text(
        f"# Requirements - {scenario.get('title', scenario_id)}\n\n{requirements_text}\n",
        encoding="utf-8",
    )

    (lab_dir / "hints.md").write_text(
        build_progressive_hints(scenario_id, scenario),
        encoding="utf-8",
    )

    (lab_dir / "expected_results.md").write_text(
        f"# Expected Results - {scenario.get('title', scenario_id)}\n\n{expected_text}\n",
        encoding="utf-8",
    )

    verification_md = f"# Verification - {scenario.get('title', scenario_id)}\n\n{verify}\n"
    (lab_dir / "verification.md").write_text(verification_md, encoding="utf-8")

    (lab_dir / "grading_criteria.md").write_text(
        f"# Grading Criteria - {scenario.get('title', scenario_id)}\n\n{grading_text}\n",
        encoding="utf-8",
    )

    active_catalog = catalog or {"templates": {}}
    (lab_dir / "topology_map.md").write_text(
        build_topology_map(project_name, topology_id, active_catalog, faulty_topology, host_type),
        encoding="utf-8",
    )
    (lab_dir / "validation_report.md").write_text(
        build_validation_report(project_name, scenario_id, scenario, faulty_topology, lab_dir, faulty_configs),
        encoding="utf-8",
    )
    (lab_dir / "metadata.json").write_text(
        json.dumps(build_lab_metadata(project_name, project, scenario_id, scenario, topology_id, faulty_topology, active_catalog, host_type, node_map), indent=2),
        encoding="utf-8",
    )

    # 3.0 alpha1 structured workspace model. This runs after the legacy
    # markdown files are generated, then reorganizes and slims workspace content
    # while preserving export copies for users who open the folder directly.
    write_structured_workspace_content(
        lab_dir=lab_dir,
        project_name=project_name,
        project=project,
        scenario_id=scenario_id,
        scenario=scenario,
        topology_id=topology_id,
        topology=faulty_topology,
        catalog=active_catalog,
        host_type=host_type,
        catalog_path=catalog_path,
        node_map=node_map,
        requirements_text=requirements_text,
        expected_text=expected_text,
        story=story,
        context_notes=context_notes,
    )


# -----------------------------
# Project build
# -----------------------------


def fetch_gns3_templates_by_id(base: str) -> Dict[str, Dict[str, Any]]:
    """Return live GNS3 templates keyed by template_id."""
    templates = api("GET", base, "/v2/templates")
    return {t.get("template_id"): t for t in templates if t.get("template_id")}


def max_logical_interface_index_for_node(topology: Dict[str, Any], node_name: str) -> int:
    max_idx = -1
    for link in topology.get("links", []):
        if link.get("a") == node_name:
            max_idx = max(max_idx, int(link["a_adapter"]))
        if link.get("b") == node_name:
            max_idx = max(max_idx, int(link["b_adapter"]))
    return max_idx


def required_ethernet_adapter_count_for_template(logical_max_index: int, catalog_template: Dict[str, Any]) -> int:
    if logical_max_index < 0:
        return 0
    if is_iou_template(catalog_template):
        return logical_max_index // 4 + 1
    return logical_max_index + 1


def template_ethernet_adapter_count(live_template: Dict[str, Any], catalog_template: Dict[str, Any]) -> Optional[int]:
    """Best-effort Ethernet adapter count from the live GNS3 template.

    IOU/IOL templates can expose both ethernet_adapters and serial_adapters.
    Adapter slots beyond ethernet_adapters may be serial interfaces.
    """
    template_type = str(live_template.get("template_type") or catalog_template.get("template_type") or "").lower()

    if template_type == "iou":
        value = live_template.get("ethernet_adapters")
        if value is not None:
            return int(value)

    value = live_template.get("adapters")
    if value is not None:
        return int(value)

    value = live_template.get("ethernet_adapters")
    if value is not None:
        return int(value)

    return None


def validate_topology_ports_against_live_templates(base: str, catalog: Dict[str, Any], topology: Dict[str, Any], host_type: str) -> None:
    """Fail early if selected topology needs Ethernet ports the live templates lack."""
    live_templates = fetch_gns3_templates_by_id(base)
    errors: List[str] = []

    for node_name, spec in topology.get("nodes", {}).items():
        template_key = resolve_node_template_key(spec, host_type)
        catalog_template = catalog["templates"].get(template_key)
        if not catalog_template:
            continue

        template_id = catalog_template.get("template_id")
        live_template = live_templates.get(template_id)
        if not live_template:
            continue

        required_max_index = max_logical_interface_index_for_node(topology, node_name)
        if required_max_index < 0:
            continue

        required_adapter_count = required_ethernet_adapter_count_for_template(required_max_index, catalog_template)
        ethernet_count = template_ethernet_adapter_count(live_template, catalog_template)
        if ethernet_count is None:
            continue

        if required_adapter_count > ethernet_count:
            template_type = str(live_template.get("template_type") or catalog_template.get("template_type") or "")
            serial_count = live_template.get("serial_adapters")
            serial_text = f", serial_adapters={serial_count}" if serial_count is not None else ""
            errors.append(
                f"- Node {node_name} uses template key '{template_key}' ({catalog_template.get('name', template_key)}), "
                f"but the topology requires logical interface index {required_max_index} "
                f"({required_adapter_count} Ethernet adapter module(s) for this template type). Live GNS3 template has "
                f"{ethernet_count} Ethernet adapter(s){serial_text}; template_type={template_type}."
            )

    if errors:
        msg = [
            "Template port preflight failed before project creation.",
            "",
            "At least one selected topology link needs an Ethernet adapter that the live GNS3 template does not expose.",
            "This commonly happens with IOL/IOU router templates that were imported with only 2 Ethernet adapters; "
            "adapter 2 and above may be serial, which causes GNS3 to reject Ethernet links.",
            "",
            "Fix options:",
            "1. Edit the affected GNS3 template and increase Ethernet adapters, usually to 4 or 8.",
            "2. Regenerate using the corresponding _iosv scenario variant.",
            "3. Use a topology that requires fewer router interfaces.",
            "",
            "Details:",
            *errors,
        ]
        raise SystemExit("\n".join(msg))

def build_project(args: argparse.Namespace, catalog: Dict[str, Any], env: Any,
                  scenario_id: str, scenario: Dict[str, Any]) -> None:
    topology_id = scenario["topology"]
    if topology_id not in catalog["topologies"]:
        raise SystemExit(f"Scenario {scenario_id} references unknown topology: {topology_id}")

    clean_topology = copy.deepcopy(catalog["topologies"][topology_id])
    faulty_topology = apply_data_patches(clean_topology, scenario)
    progress = ProgressReporter(
        8
        + int(bool(args.start or args.push_config or args.push_endpoints or args.verify))
        + int(bool(args.push_config))
        + int(bool(args.push_endpoints))
        + int(bool(args.verify))
    )
    progress.step("Preparing lab generation plan")
    progress.detail(f"Scenario: {scenario_id} - {scenario.get('title', '')}")
    progress.detail(f"Topology: {topology_id}")
    progress.detail(f"Nodes: {len(faulty_topology.get('nodes', {}))}; links: {len(faulty_topology.get('links', []))}")

    if not getattr(args, "skip_template_port_check", False):
        progress.step("Checking live GNS3 template port readiness")
        validate_topology_ports_against_live_templates(args.server, catalog, faulty_topology, args.host_type)
    else:
        progress.step("Skipping live GNS3 template port readiness check")

    progress.step("Rendering clean and faulty device configurations")
    clean_configs = render_configs(env, clean_topology, args.host_type)
    faulty_configs = render_configs(env, faulty_topology, args.host_type)
    faulty_configs = apply_text_patches(faulty_configs, scenario)

    project_name = args.name or f"CCNP_{scenario_id}_{random.randint(1000, 9999)}"
    out_dir = Path(args.out)

    progress.step(f"Creating GNS3 project: {project_name}")
    project = create_project(args.server, project_name)
    project_id = project["project_id"]

    progress.step(f"Creating {len(faulty_topology['nodes'])} GNS3 node(s)")
    created_nodes: Dict[str, Any] = {}
    for name, spec in faulty_topology["nodes"].items():
        template_key = resolve_node_template_key(spec, args.host_type)
        if template_key not in catalog["templates"]:
            raise SystemExit(f"Unknown template key {template_key!r} for node {name}")
        template = catalog["templates"][template_key]
        progress.detail(f"Creating node {name} from template {template_key}")
        created_nodes[name] = create_node(args.server, project_id, name, template, int(spec["x"]), int(spec["y"]))

    progress.step(f"Creating {len(faulty_topology.get('links', []))} GNS3 link(s)")
    for link in faulty_topology.get("links", []):
        label = link.get("label", f"{link['a']}:{link['a_adapter']} <-> {link['b']}:{link['b_adapter']}")
        progress.detail(f"Linking {label}")
        create_catalog_link(
            args.server,
            project_id,
            catalog,
            faulty_topology,
            args.host_type,
            created_nodes,
            link,
        )

    progress.step("Refreshing node runtime metadata")
    created_nodes = refresh_created_nodes(args.server, project_id, created_nodes, progress)

    progress.step("Writing generated lab workspace files")
    write_lab_files(
        out_dir=out_dir,
        project_name=project_name,
        scenario_id=scenario_id,
        scenario=scenario,
        topology_id=topology_id,
        clean_topology=clean_topology,
        faulty_topology=faulty_topology,
        project=project,
        node_map=created_nodes,
        clean_configs=clean_configs,
        faulty_configs=faulty_configs,
        host_type=args.host_type,
        catalog_path=catalog["_catalog_path"],
        catalog=catalog,
    )

    (out_dir / project_name / "generation_summary.md").write_text(
        build_generation_summary(project_name, scenario_id, scenario, topology_id, out_dir / project_name, faulty_topology, args),
        encoding="utf-8",
    )

    if args.start or args.push_config or args.push_endpoints or args.verify:
        progress.step(f"Starting {len(created_nodes)} GNS3 node(s)")
        for name, node in created_nodes.items():
            progress.detail(f"Starting {name}")
            try:
                start_node(args.server, project_id, node["node_id"])
            except requests.HTTPError as exc:
                print(f"Warning: failed to start {name}: {exc}", file=sys.stderr)

    if args.push_config:
        progress.step("Waiting for Cisco consoles and pushing faulty configs")
        push_cisco_configs(project_name, faulty_topology, created_nodes, faulty_configs, out_dir, args.console_timeout, args.server)

    if args.push_endpoints:
        progress.step("Waiting for supported endpoint consoles and pushing endpoint configs")
        push_endpoint_configs(
            project_name, faulty_topology, created_nodes, faulty_configs, out_dir,
            args.endpoint_timeout, args.server, args.host_type,
            linux_username=args.linux_endpoint_username,
            linux_password=args.linux_endpoint_password or "",
            linux_login_timeout=args.linux_endpoint_login_timeout,
        )

    if args.verify:
        progress.step("Collecting verification output")
        collect_verification(project_name, faulty_topology, scenario, created_nodes, out_dir, args.console_timeout, args.server)

    print(flush=True)
    print("Done.", flush=True)
    print(f"GNS3 project: {project_name}", flush=True)
    print(f"Project ID: {project_id}", flush=True)
    print(f"Local files: {out_dir / project_name}", flush=True)
    print(f"Generation summary: {out_dir / project_name / 'generation_summary.md'}", flush=True)
    if args.push_config:
        print("Cisco configs were pushed automatically where supported.", flush=True)
    else:
        print("Cisco configs were not pushed because config push was disabled.", flush=True)
    if args.push_endpoints:
        print("Supported endpoint configs were pushed automatically where supported.", flush=True)
    else:
        print("Endpoint setup files were generated; endpoint push was not requested.", flush=True)


def build_blank_topology_project(args: argparse.Namespace, catalog: Dict[str, Any], env: Any) -> None:
    if not args.topology:
        raise SystemExit("--blank-topology requires --topology <topology_id>")
    topology_id = args.topology
    if topology_id not in catalog["topologies"]:
        raise SystemExit(f"Unknown topology: {topology_id}")

    topology = copy.deepcopy(catalog["topologies"][topology_id])
    progress = ProgressReporter(8 + int(bool(args.start)))
    progress.step("Preparing blank topology generation plan")
    progress.detail(f"Topology: {topology_id}")
    progress.detail(f"Nodes: {len(topology.get('nodes', {}))}; links: {len(topology.get('links', []))}")

    if not getattr(args, "skip_template_port_check", False):
        progress.step("Checking live GNS3 template port readiness")
        validate_topology_ports_against_live_templates(args.server, catalog, topology, args.host_type)
    else:
        progress.step("Skipping live GNS3 template port readiness check")

    progress.step("Rendering baseline topology configurations")
    configs = render_configs(env, topology, args.host_type)
    project_name = args.name or f"BLANK_{topology_id}_{random.randint(1000, 9999)}"
    out_dir = Path(args.out)

    progress.step(f"Creating blank GNS3 topology project: {project_name}")
    progress.detail("No scenario faults or answer-key artifacts will be applied")
    project = create_project(args.server, project_name)
    project_id = project["project_id"]

    progress.step(f"Creating {len(topology['nodes'])} GNS3 node(s)")
    created_nodes: Dict[str, Any] = {}
    for name, spec in topology["nodes"].items():
        template_key = resolve_node_template_key(spec, args.host_type)
        if template_key not in catalog["templates"]:
            raise SystemExit(f"Unknown template key {template_key!r} for node {name}")
        template = catalog["templates"][template_key]
        progress.detail(f"Creating node {name} from template {template_key}")
        created_nodes[name] = create_node(args.server, project_id, name, template, int(spec["x"]), int(spec["y"]))

    progress.step(f"Creating {len(topology.get('links', []))} GNS3 link(s)")
    for link in topology.get("links", []):
        label = link.get("label", f"{link['a']}:{link['a_adapter']} <-> {link['b']}:{link['b_adapter']}")
        progress.detail(f"Linking {label}")
        create_catalog_link(
            args.server,
            project_id,
            catalog,
            topology,
            args.host_type,
            created_nodes,
            link,
        )

    progress.step("Refreshing node runtime metadata")
    created_nodes = refresh_created_nodes(args.server, project_id, created_nodes, progress)

    progress.step("Writing blank topology workspace files")
    lab_dir = out_dir / project_name
    cfg_dir = lab_dir / "blank_topology_configs"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    for device, cfg in configs.items():
        (cfg_dir / f"{device}.cfg").write_text(cfg, encoding="utf-8")

    manifest = {
        "project_name": project_name,
        "project_id": project_id,
        "mode": "blank-topology",
        "topology_id": topology_id,
        "host_type": args.host_type,
        "catalog_path": catalog.get("_catalog_path"),
        "nodes": created_nodes,
        "links": topology.get("links", []),
    }
    (lab_dir / "blank_topology_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (lab_dir / "README.md").write_text(
        f"# Blank Topology: {topology_id}\n\n"
        f"Project: `{project_name}`\n\n"
        "This project was generated in blank-topology mode. Nodes and links were created, but no scenario faults were applied.\n\n"
        "Generated baseline configuration files are in `blank_topology_configs/`.\n",
        encoding="utf-8",
    )
    blank_scenario = {"title": f"Blank Topology: {topology_id}", "lab_type": "blank-topology"}
    (lab_dir / "topology_map.md").write_text(
        build_topology_map(project_name, topology_id, catalog, topology, args.host_type),
        encoding="utf-8",
    )
    (lab_dir / "generation_summary.md").write_text(
        build_generation_summary(project_name, "blank-topology", blank_scenario, topology_id, lab_dir, topology, args),
        encoding="utf-8",
    )
    (lab_dir / "validation_report.md").write_text(
        build_validation_report(project_name, "blank-topology", blank_scenario, topology, lab_dir, configs),
        encoding="utf-8",
    )
    (lab_dir / "metadata.json").write_text(
        json.dumps(build_lab_metadata(project_name, {"project_id": project_id}, "blank-topology", blank_scenario, topology_id, topology, catalog, args.host_type, created_nodes, lab_mode="blank-topology"), indent=2),
        encoding="utf-8",
    )

    if args.start:
        progress.step(f"Starting {len(created_nodes)} GNS3 node(s)")
        for name, node in created_nodes.items():
            progress.detail(f"Starting {name}")
            try:
                start_node(args.server, project_id, node["node_id"])
            except requests.HTTPError as exc:
                print(f"Warning: failed to start {name}: {exc}", file=sys.stderr)

    print(flush=True)
    print("Done.", flush=True)
    print(f"GNS3 project: {project_name}", flush=True)
    print(f"Project ID: {project_id}", flush=True)
    print(f"Local files: {lab_dir}", flush=True)


def scenario_lookup_title(catalog: Dict[str, Any], scenario_id: str) -> str:
    scenario = catalog.get("scenarios", {}).get(scenario_id, {})
    return scenario.get("title", scenario_id)


def catalog_unique_concepts(catalog: Dict[str, Any], exam: Optional[str] = None, domain: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    exam_lower = exam.lower() if exam else None
    domain_lower = domain.lower() if domain else None
    concepts: Dict[str, Dict[str, Any]] = {}

    for sid, scenario in catalog["scenarios"].items():
        if exam_lower and exam_lower not in [str(e).lower() for e in scenario.get("exam_blueprints", [])]:
            continue
        if domain_lower and str(scenario.get("domain", "")).lower() != domain_lower:
            continue

        cid = scenario_concept_id(sid, scenario)
        # Prefer non-legacy/non-fallback scenario as the display representative.
        if cid not in concepts or is_legacy_scenario(sid, scenario):
            concepts.setdefault(cid, {"id": sid, "scenario": scenario})
        if cid in concepts and not is_legacy_scenario(sid, scenario):
            concepts[cid] = {"id": sid, "scenario": scenario}

    return concepts


def show_coverage_summary(catalog: Dict[str, Any]) -> None:
    concepts = catalog_unique_concepts(catalog)
    print(f"Templates: {len(catalog['templates'])}")
    print(f"Topologies: {len(catalog['topologies'])}")
    print(f"Scenario entries: {len(catalog['scenarios'])}")
    print(f"Unique lab concepts: {len(concepts)}")
    print()

    domain_counts: Dict[str, int] = {}
    topic_counts: Dict[str, int] = {}
    difficulty_counts: Dict[str, int] = {}
    for item in concepts.values():
        s = item["scenario"]
        domain_counts[s.get("domain", "Unspecified")] = domain_counts.get(s.get("domain", "Unspecified"), 0) + 1
        topic_counts[s.get("topic", "Unspecified")] = topic_counts.get(s.get("topic", "Unspecified"), 0) + 1
        difficulty_counts[s.get("difficulty", "Unspecified")] = difficulty_counts.get(s.get("difficulty", "Unspecified"), 0) + 1

    print("Unique concepts by domain:")
    for key, value in sorted(domain_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {key}: {value}")

    print()
    print("Unique concepts by difficulty:")
    for key, value in sorted(difficulty_counts.items(), key=lambda kv: (kv[0])):
        print(f"  {key}: {value}")

    print()
    print("Top topics by unique concept count:")
    for key, value in sorted(topic_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:20]:
        print(f"  {key}: {value}")

    plans = catalog.get("study_plans", {})
    if plans:
        print()
        print("Study plans:")
        for plan_id, plan in sorted(plans.items()):
            print(f"  {plan_id}: {plan.get('title', plan_id)} ({len(plan.get('steps', []))} steps)")


def list_study_plan(catalog: Dict[str, Any], plan_id: str) -> None:
    plans = catalog.get("study_plans", {})
    if plan_id not in plans:
        print(f"Study plan not found: {plan_id}")
        if plans:
            print("Available study plans:")
            for pid, plan in sorted(plans.items()):
                print(f"  {pid}: {plan.get('title', pid)}")
        raise SystemExit(1)

    plan = plans[plan_id]
    print(f"{plan.get('title', plan_id)}")
    print("=" * len(plan.get('title', plan_id)))
    if plan.get("description"):
        print(plan["description"])
        print()

    for idx, step in enumerate(plan.get("steps", []), start=1):
        print(f"{idx}. {step.get('title', 'Untitled step')}")
        print(f"   Objective: {step.get('objective', '')}")
        if step.get("scenario_ids"):
            print("   Labs:")
            for sid in step["scenario_ids"]:
                marker = ""
                if sid not in catalog.get("scenarios", {}):
                    marker = " [missing]"
                print(f"     - {sid}: {scenario_lookup_title(catalog, sid)}{marker}")
        if step.get("notes"):
            print(f"   Notes: {step['notes']}")
        print()

def validate_catalog_qa(catalog: Dict[str, Any]) -> Dict[str, Any]:
    policy = catalog.get("qa_policy", {})
    required = policy.get("required_fields", [
        "title", "topology", "exam_blueprints", "domain", "topic", "difficulty",
        "lab_type", "symptom", "faults", "verification", "hints",
        "expected_results", "answer_key", "concept_id",
    ])
    skill_required = policy.get("skill_check_required_fields", ["requirements", "grading_criteria"])

    issues: List[Dict[str, str]] = []
    concept_ids: Dict[str, List[str]] = {}
    topology_ids = set(catalog.get("topologies", {}).keys())

    for sid, scenario in catalog.get("scenarios", {}).items():
        cid = scenario_concept_id(sid, scenario)
        concept_ids.setdefault(cid, []).append(sid)

        for field in required:
            value = scenario.get(field)
            if value is None or value == "" or value == [] or value == {}:
                issues.append({"severity": "error", "scenario": sid, "field": field, "message": "Missing or empty required QA field"})

        topology = scenario.get("topology")
        if topology and topology not in topology_ids:
            issues.append({"severity": "error", "scenario": sid, "field": "topology", "message": f"Unknown topology {topology}"})

        if scenario.get("lab_type") == "skill-check":
            for field in skill_required:
                value = scenario.get(field)
                if value is None or value == "" or value == [] or value == {}:
                    issues.append({"severity": "error", "scenario": sid, "field": field, "message": "Missing skill-check QA field"})

        answer_key = scenario.get("answer_key", {})
        if not isinstance(answer_key, dict):
            issues.append({"severity": "error", "scenario": sid, "field": "answer_key", "message": "answer_key must be an object"})
        else:
            for field in ["root_cause", "fix_summary", "verification"]:
                value = answer_key.get(field)
                if value is None or value == "" or value == []:
                    issues.append({"severity": "warning", "scenario": sid, "field": f"answer_key.{field}", "message": "Answer key field is missing or empty"})

    duplicate_concepts = {cid: ids for cid, ids in concept_ids.items() if len(ids) > 1}
    expected_variant_duplicates = 0
    unexpected_duplicate_groups = {}
    for cid, ids in duplicate_concepts.items():
        non_variants = [sid for sid in ids if not is_legacy_scenario(sid, catalog["scenarios"].get(sid, {}))]
        if len(non_variants) <= 1:
            expected_variant_duplicates += 1
        else:
            unexpected_duplicate_groups[cid] = ids
            issues.append({"severity": "warning", "scenario": ",".join(ids), "field": "concept_id", "message": f"Multiple non-variant scenarios share concept_id {cid}"})

    return {
        "scenario_entries": len(catalog.get("scenarios", {})),
        "unique_concepts": len(concept_ids),
        "issue_count": len(issues),
        "error_count": sum(1 for issue in issues if issue["severity"] == "error"),
        "warning_count": sum(1 for issue in issues if issue["severity"] == "warning"),
        "issues": issues,
        "expected_variant_duplicate_groups": expected_variant_duplicates,
        "unexpected_duplicate_groups": unexpected_duplicate_groups,
    }


def print_qa_report(catalog: Dict[str, Any]) -> None:
    report = validate_catalog_qa(catalog)
    print("Catalog QA Report")
    print("=================")
    print(f"Scenario entries: {report['scenario_entries']}")
    print(f"Unique concepts:  {report['unique_concepts']}")
    print(f"Issues:           {report['issue_count']}")
    print(f"Errors:           {report['error_count']}")
    print(f"Warnings:         {report['warning_count']}")
    print(f"Expected variant duplicate groups: {report['expected_variant_duplicate_groups']}")
    print()

    if not report["issues"]:
        print("No QA issues found.")
        return

    print("Issues:")
    for issue in report["issues"][:200]:
        print(f"- [{issue['severity']}] {issue['scenario']} :: {issue['field']} :: {issue['message']}")
    if len(report["issues"]) > 200:
        print(f"... {len(report['issues']) - 200} additional issues omitted.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate fully modular CCNP ENCOR troubleshooting GNS3 labs.")
    parser.add_argument("--version", action="store_true", help="Print application version and exit.")
    parser.add_argument("--server", default=None, help="GNS3 server URL. Can also be set in config/app_config.local.json or GNS3_SERVER.")
    parser.add_argument("--config", default=None, help="Path to app config JSON. Default search: config/app_config.local.json.")
    parser.add_argument("--template-overrides", default=None, help="Path to template override JSON. Default search: config/template_overrides.local.json.")
    parser.add_argument("--catalog", default=None, help="Path to ccnp_encor_lab_catalog.json.")
    parser.add_argument("--template-dir", default=None, help="Path to config_templates directory.")
    parser.add_argument("--scenario", default="random", help="Scenario ID, or 'random'.")
    parser.add_argument("--blank-topology", action="store_true", help="Generate a topology-only project using --topology without applying a scenario.")
    parser.add_argument("--list-scenarios", action="store_true", help="List scenarios and exit.")
    parser.add_argument("--list-topologies", action="store_true", help="List topologies and exit.")
    parser.add_argument("--list-templates", action="store_true", help="List GNS3 template mappings from the catalog and exit.")
    parser.add_argument("--list-config-templates", action="store_true", help="List Jinja config templates and exit.")
    parser.add_argument("--coverage", action="store_true", help="Show ENCOR curriculum coverage summary and exit.")
    parser.add_argument("--preflight", action="store_true", help="Run readiness checks for the selected scenario without creating a project.")
    parser.add_argument("--qa-report", action="store_true", help="Run catalog QA checks for scenario metadata, answer keys, hints, expected results, and references.")
    parser.add_argument("--list-study-plan", default=None, help="List guided study plan steps by name, such as encor-core or encor-complete.")
    parser.add_argument("--stats", action="store_true", help="Show catalog counts, including unique lab concepts excluding legacy duplicates, and exit.")
    parser.add_argument("--exam", default=None, help="Filter by exam blueprint tag, such as CCNA, ENCOR, or ENARSI.")
    parser.add_argument("--domain", default=None, help="Filter by scenario domain.")
    parser.add_argument("--topic", default=None, help="Filter by scenario topic.")
    parser.add_argument("--difficulty", default=None, help="Filter by difficulty.")
    parser.add_argument("--topology", default=None, help="Filter by topology ID.")
    parser.add_argument("--name", default=None, help="Project name. Default uses scenario name.")
    parser.add_argument("--out", default="generated_labs", help="Local output directory.")
    parser.add_argument("--host-type", choices=["rhel9", "alpine", "vpcs"], default="alpine", help="End-host type for nodes whose template is 'host'. Default: alpine.")
    parser.add_argument(
        "--auto-config",
        dest="auto_config",
        action="store_true",
        default=True,
        help="Default. Start nodes and push Cisco IOS configs when a lab is created.",
    )
    parser.add_argument(
        "--no-auto-config",
        dest="auto_config",
        action="store_false",
        help="Create the GNS3 project and local files only; do not start nodes or push configs.",
    )
    parser.add_argument(
        "--start",
        dest="start",
        action="store_true",
        default=None,
        help="Start nodes after creating the project. Overrides --no-auto-config for starting.",
    )
    parser.add_argument(
        "--no-start",
        dest="start",
        action="store_false",
        default=None,
        help="Do not start nodes after creating the project.",
    )
    parser.add_argument(
        "--push-config",
        dest="push_config",
        action="store_true",
        default=None,
        help="Push Cisco IOS configs over Telnet using telnetlib3. Overrides --no-auto-config for config push.",
    )
    parser.add_argument(
        "--no-push-config",
        dest="push_config",
        action="store_false",
        default=None,
        help="Do not push Cisco IOS configs over Telnet.",
    )
    parser.add_argument("--verify", action="store_true", help="Collect verification command output.")
    parser.add_argument(
        "--push-endpoints",
        dest="push_endpoints",
        action="store_true",
        default=None,
        help="Default. Push supported endpoint configs after nodes start. VPCS, Alpine, and RHEL9 are supported.",
    )
    parser.add_argument(
        "--no-push-endpoints",
        "--skip-endpoints",
        dest="skip_endpoints",
        action="store_true",
        help="Do not push endpoint configs; only generate endpoint_setup files.",
    )
    parser.add_argument("--endpoint-timeout", type=int, default=180, help="Endpoint console wait timeout in seconds. Default: 180.")
    parser.add_argument("--linux-endpoint-username", default=None, help="Linux endpoint console username. Default: root for Alpine/RHEL9.")
    parser.add_argument("--linux-endpoint-password", default="", help="Linux endpoint console password. Default: blank.")
    parser.add_argument("--linux-endpoint-login-timeout", type=int, default=90, help="Linux endpoint login/shell wait timeout in seconds. Default: 90.")
    parser.add_argument("--console-timeout", type=int, default=420, help="Seconds to wait for each console.")

    args = parser.parse_args()

    app_config = load_app_config(args.config)
    if args.server is None:
        args.server = app_config.get("gns3_server") or GNS3_DEFAULT or None
    if args.catalog is None and app_config.get("catalog_path"):
        args.catalog = app_config.get("catalog_path")
    if getattr(args, "out", None) == "generated_labs" and app_config.get("output_dir"):
        args.out = app_config.get("output_dir")
    if getattr(args, "host_type", None) == "alpine" and app_config.get("host_type"):
        args.host_type = app_config.get("host_type")
    if args.linux_endpoint_username is None and app_config.get("linux_endpoint_username"):
        args.linux_endpoint_username = app_config.get("linux_endpoint_username")
    if args.linux_endpoint_password == "" and app_config.get("linux_endpoint_password"):
        args.linux_endpoint_password = app_config.get("linux_endpoint_password")
    if args.template_overrides is None and app_config.get("template_overrides_path"):
        args.template_overrides = app_config.get("template_overrides_path")
    if args.push_endpoints is None:
        args.push_endpoints = bool(app_config.get("push_endpoints", True))
    if args.skip_endpoints:
        args.push_endpoints = False

    if args.version:
        print(APP_VERSION)
        return 0

    if args.start is None:
        args.start = args.auto_config
    if args.push_config is None:
        args.push_config = args.auto_config

    if args.push_config and not args.start:
        print("Note: --push-config requires running nodes; enabling start for this run.", file=sys.stderr)
        args.start = True
    if args.push_endpoints and not args.start:
        print("Note: endpoint config push requires running nodes; enabling start for this run.", file=sys.stderr)
        args.start = True

    catalog = load_catalog(args.catalog)
    apply_template_overrides(catalog, args.template_overrides)
    template_dirs = resolve_template_dirs(args, catalog)

    if args.stats:
        total_entries = len(catalog["scenarios"])
        unique_concepts = unique_scenario_count(catalog)
        print(f"Templates: {len(catalog['templates'])}")
        print(f"Topologies: {len(catalog['topologies'])}")
        print(f"Scenario entries: {total_entries}")
        print(f"Unique lab concepts: {unique_concepts}")
        print(f"Legacy duplicate entries: {total_entries - unique_concepts}")
        exams = sorted({e for s in catalog["scenarios"].values() for e in s.get("exam_blueprints", [])})
        for exam in exams:
            entries = sum(1 for s in catalog["scenarios"].values() if exam in s.get("exam_blueprints", []))
            print(f"{exam} scenario entries: {entries}")
            print(f"{exam} unique lab concepts: {unique_scenario_count(catalog, exam=exam)}")
        return 0

    if args.coverage:
        show_coverage_summary(catalog)
        return 0

    if args.qa_report:
        print_qa_report(catalog)
        return 0

    if args.list_study_plan:
        list_study_plan(catalog, args.list_study_plan)
        return 0

    if args.list_templates:
        list_templates(catalog)
        return 0
    if args.list_topologies:
        list_topologies(catalog, args)
        return 0
    if args.list_config_templates:
        list_config_templates(template_dirs)
        return 0
    if args.list_scenarios:
        list_scenarios(catalog, args)
        return 0

    require_server_url(args)
    if args.preflight:
        scenario_id, scenario = choose_scenario(catalog, args)
        return run_preflight(args, catalog, scenario_id, scenario)

    env = make_jinja_env(template_dirs)
    if args.blank_topology:
        build_blank_topology_project(args, catalog, env)
        return 0

    scenario_id, scenario = choose_scenario(catalog, args)
    build_project(args, catalog, env, scenario_id, scenario)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
