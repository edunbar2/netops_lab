#!/usr/bin/env python3
"""NetOps Labs legacy Tk GUI.

1.5.0:
- Theme selector and persistence.
- Beginner-friendly filter.
- Active filter summary and clear search.
- Copy CLI command.
- Open output folder.
- Generation confirmation summary.
- Study-plan table polish with estimated minutes.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

APP_VERSION = "4.0.1"

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import BOTH, END, LEFT, RIGHT, X, Y
    from tkinter import filedialog, messagebox
    import tkinter as tk
except Exception:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    BOTH = "both"
    END = "end"
    LEFT = "left"
    RIGHT = "right"
    X = "x"
    Y = "y"


APP_DIR = Path(__file__).resolve().parent
DEFAULT_CATALOG = APP_DIR / "catalogs" / "ccnp_encor_lab_catalog.json"
DEFAULT_GENERATOR = APP_DIR / "gns3_ccnp_lab_generator.py"
SETTINGS_FILE = APP_DIR / "config" / "app_config.local.json"
EXAMPLE_SETTINGS_FILE = APP_DIR / "config" / "app_config.example.json"

THEMES = [
    # Dark themes kept from ttkbootstrap because they are visually distinct.
    "darkly",
    "superhero",
    "cyborg",
    "solar",
    "vapor",
    # Curated existing light themes. Other light Bootswatch variants were too similar.
    "minty",
    "sandstone",
    "morph",
    # Custom light themes with softer surfaces and stronger personality.
    "mist",
    "sage",
    "parchment",
    "twilight_parchment",
    "woodland",
    # Custom dark green/brown themes.
    "twilight_forest",
    "deep_earth",
    "evergreen",
]

THEME_ALIASES = {
    "mist": "morph",
    "sage": "minty",
    "parchment": "sandstone",
    "woodland": "minty",
    "twilight_forest": "darkly",
    "deep_earth": "darkly",
    "evergreen": "darkly",
}

CUSTOM_THEME_OVERRIDES = {
    "mist": {"background": "#e8edf0", "panel": "#d9e1e5", "field": "#f4f7f8", "heading": "#3f5966", "foreground": "#223039", "muted": "#52646c", "accent": "#4f7485", "button_fg": "#ffffff"},
    "sage": {"background": "#e7ece2", "panel": "#d7dfcf", "field": "#f6f8f2", "heading": "#4f694d", "foreground": "#253224", "muted": "#5b6756", "accent": "#6f8a66", "button_fg": "#ffffff"},
    "parchment": {"background": "#eee6d6", "panel": "#dfd1b8", "field": "#fbf6ea", "heading": "#7a5a32", "foreground": "#34291d", "muted": "#6f604e", "accent": "#8a6b3f", "button_fg": "#ffffff"},
    "twilight_parchment": {"background": "#14110f", "panel": "#1d1917", "field": "#26211d", "heading": "#d8c7a2", "foreground": "#eadfca", "muted": "#baa98f", "accent": "#8c6a43", "button_fg": "#fff7eb"},
    "woodland": {"background": "#e3e8dc", "panel": "#cfd9c3", "field": "#f4f7ef", "heading": "#3f5d36", "foreground": "#202b1d", "muted": "#52614d", "accent": "#5d7f4e", "button_fg": "#ffffff"},
    "twilight_forest": {"background": "#111a17", "panel": "#18251f", "field": "#203129", "heading": "#6f8f72", "foreground": "#d7dfd2", "muted": "#9fad97", "accent": "#4f6f52", "button_fg": "#eef4e8"},
    "deep_earth": {"background": "#17120e", "panel": "#241b14", "field": "#302419", "heading": "#a18055", "foreground": "#e3d5c1", "muted": "#b7a48d", "accent": "#7b5c36", "button_fg": "#f4eadc"},
    "evergreen": {"background": "#0f1d16", "panel": "#14271d", "field": "#1b3527", "heading": "#7aa17d", "foreground": "#dce8d9", "muted": "#a5b8a4", "accent": "#3f744d", "button_fg": "#eef7ec"},
}


def get_style(root: tk.Tk):
    if hasattr(root, "style"):
        return root.style  # type: ignore[attr-defined]
    return ttk.Style()


def normalize_theme_name(theme: Any) -> str:
    theme_name = str(theme or "darkly").strip()
    return theme_name if theme_name in THEMES else "darkly"


def custom_theme_settings(theme: str) -> Optional[Dict[str, Dict[str, Dict[str, str]]]]:
    """Build ttk settings for a custom theme without mutating its base theme."""
    spec = CUSTOM_THEME_OVERRIDES.get(theme)
    if not spec:
        return None
    background = spec["background"]
    panel = spec["panel"]
    field = spec["field"]
    heading = spec["heading"]
    foreground = spec["foreground"]
    muted = spec.get("muted", foreground)
    accent = spec.get("accent", heading)
    button_fg = spec.get("button_fg", "#ffffff")
    return {
        ".": {"configure": {"background": background, "foreground": foreground}},
        "TFrame": {"configure": {"background": background}},
        "TNotebook": {"configure": {"background": background}},
        "TNotebook.Tab": {"configure": {"background": panel, "foreground": foreground}},
        "TLabelframe": {"configure": {"background": panel, "foreground": foreground}},
        "TLabelframe.Label": {"configure": {"background": panel, "foreground": foreground}},
        "TLabel": {"configure": {"background": background, "foreground": foreground}},
        "Muted.TLabel": {"configure": {"background": background, "foreground": muted}},
        "TCheckbutton": {"configure": {"background": background, "foreground": foreground}},
        "TRadiobutton": {"configure": {"background": background, "foreground": foreground}},
        "TEntry": {"configure": {"fieldbackground": field, "background": field, "foreground": foreground}},
        "TCombobox": {"configure": {"fieldbackground": field, "background": field, "foreground": foreground}},
        "TButton": {"configure": {"background": accent, "foreground": button_fg, "bordercolor": accent, "focuscolor": accent}},
        "primary.TButton": {"configure": {"background": accent, "foreground": button_fg, "bordercolor": accent, "focuscolor": accent}},
        "Treeview": {"configure": {"background": field, "fieldbackground": field, "foreground": foreground, "bordercolor": panel}},
        "Treeview.Heading": {"configure": {"background": heading, "foreground": button_fg}},
        "TSeparator": {"configure": {"background": muted}},
    }


def apply_theme_overrides(root: tk.Tk, theme: str) -> None:
    """Fallback custom styling for ttk builds that cannot create themes."""
    settings = custom_theme_settings(theme)
    if not settings:
        return
    style = get_style(root)
    try:
        root.configure(bg=CUSTOM_THEME_OVERRIDES[theme]["background"])
    except Exception:
        pass
    for style_name, options in settings.items():
        try:
            style.configure(style_name, **options.get("configure", {}))
        except Exception:
            pass


def ensure_custom_theme(root: tk.Tk, theme: str) -> Optional[str]:
    """Create and return an isolated ttk theme for a custom theme.

    Custom themes are aliases over ttkbootstrap bases, but they must not mutate
    those bases. Otherwise a custom default launched from install.py can make
    the built-in darkly option inherit the custom colors until restart.
    """
    settings = custom_theme_settings(theme)
    if not settings:
        return None
    style = get_style(root)
    if theme not in set(style.theme_names()):
        parent = THEME_ALIASES.get(theme, "darkly")
        try:
            style.theme_create(theme, parent=parent, settings=settings)
        except Exception:
            # Fall back to the base theme; apply_theme() will layer the custom
            # palette on top for this session. Do not mutate the built-in base
            # here, or selecting darkly later can inherit custom colors.
            return parent
    return theme


DIFFICULTY_ORDER = {"intro": 1, "easy": 2, "medium": 3, "hard": 4, "capstone": 5}


def load_settings_file() -> Dict[str, Any]:
    for path in [SETTINGS_FILE, EXAMPLE_SETTINGS_FILE]:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}
    return {}


def title_value(value: Any) -> str:
    value = str(value or "")
    if not value:
        return ""
    return value.replace("-", " ").title()


def normalize_filter_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")


def topical_display(value: Any) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    return value.replace("_", "-").replace("-", " ").title()


def scenario_topic_values(scenario: Dict[str, Any]) -> List[str]:
    """Return practical topic-filter values for a scenario.

    Catalog topics are often specific lesson names such as OSPF or NAT, while
    broad curriculum areas such as routing are represented as tags. The GUI
    topic selector therefore includes the explicit topic plus topical tags so a
    user can select Routing, Automation, or Infrastructure without needing to
    know whether the catalog stored that concept in topic or tags.
    """
    values: List[str] = []
    raw_topic = scenario.get("topic", "")
    if raw_topic:
        values.append(topical_display(raw_topic))
    topical_tags = {
        "architecture",
        "assurance",
        "automation",
        "automation-and-programmability",
        "device-access",
        "fundamentals",
        "infrastructure",
        "ip-connectivity",
        "ip-services",
        "network-access",
        "network-assurance",
        "network-fundamentals",
        "routing",
        "security",
        "security-fundamentals",
        "switching",
        "virtualization",
    }
    for tag in scenario.get("tags", []):
        tag_norm = normalize_filter_token(tag)
        if tag_norm in topical_tags:
            values.append(topical_display(tag_norm))
    deduped: List[str] = []
    seen = set()
    for value in values:
        key = normalize_filter_token(value)
        if value and key not in seen:
            deduped.append(value)
            seen.add(key)
    return deduped

def is_legacy_deployment(scenario_id: str, scenario: Dict[str, Any]) -> bool:
    """Return True for old/fallback deployment variants hidden by default.

    The catalog marks intentional legacy options with legacy_variant. Do not
    infer legacy status from an _iol suffix alone because newer fallback IOL
    variants should only be hidden when the catalog explicitly marks them old.
    """
    return bool(scenario.get("legacy_variant"))


def concept_id(scenario_id: str, scenario: Dict[str, Any]) -> str:
    if scenario.get("concept_id"):
        return str(scenario["concept_id"])
    if scenario_id.endswith("_iosv"):
        return scenario_id[:-5]
    if scenario_id.endswith("_iol"):
        return scenario_id[:-4]
    return scenario_id


def scenario_sort_key(item: Tuple[str, Dict[str, Any]]) -> Tuple[Any, ...]:
    sid, scenario = item
    rank = scenario.get("progression_rank")
    if isinstance(rank, list):
        return tuple(rank)
    difficulty = DIFFICULTY_ORDER.get(str(scenario.get("difficulty", "")).lower(), 99)
    return (
        str(scenario.get("primary_exam", "")),
        str(scenario.get("domain", "")),
        difficulty,
        str(scenario.get("topic", "")),
        str(scenario.get("title", sid)),
        sid,
    )


class LabGeneratorGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"NetOps Labs {APP_VERSION}")
        self.root.geometry("1760x1280")
        self.root.minsize(1400, 1050)

        self.settings = load_settings_file()

        self.theme_name = tk.StringVar(value=normalize_theme_name(self.settings.get("theme", "darkly")))
        self.catalog_path = tk.StringVar(value=self.settings.get("catalog_path", str(DEFAULT_CATALOG)))
        self.generator_path = tk.StringVar(value=self.settings.get("generator_path", str(DEFAULT_GENERATOR)))
        self.output_dir = tk.StringVar(value=self.settings.get("output_dir", str(APP_DIR / "generated_labs")))
        self.server_url = tk.StringVar(value=self.settings.get("gns3_server", self.settings.get("server_url", "")))
        self.host_type = tk.StringVar(value=self.settings.get("host_type", "alpine"))
        self.auto_config = tk.BooleanVar(value=self.settings.get("auto_config", True))
        self.push_config = tk.BooleanVar(value=self.settings.get("push_config", True))
        self.push_endpoints = tk.BooleanVar(value=self.settings.get("push_endpoints", True))
        self.verify = tk.BooleanVar(value=self.settings.get("verify", False))
        self.linux_user = tk.StringVar(value=self.settings.get("linux_endpoint_username", "root"))
        self.linux_password = tk.StringVar(value=self.settings.get("linux_endpoint_password", ""))

        self.search_text = tk.StringVar()
        self.exam_filter = tk.StringVar(value="All")
        self.domain_filter = tk.StringVar(value="All")
        self.topic_filter = tk.StringVar(value="All")
        self.tag_filter = tk.StringVar(value="All")
        self.difficulty_filter = tk.StringVar(value="All")
        self.lab_type_filter = tk.StringVar(value="All")
        self.show_legacy_deployments = tk.BooleanVar(value=self.settings.get("show_legacy_deployments", False))
        self.beginner_only = tk.BooleanVar(value=False)

        self.topology_search_text = tk.StringVar()
        self.topology_exam_filter = tk.StringVar(value="All")

        self.catalog: Dict[str, Any] = {}
        self.scenario_rows: List[Tuple[str, Dict[str, Any]]] = []
        self.filtered_scenarios: List[Tuple[str, Dict[str, Any]]] = []
        self.topology_rows: List[Tuple[str, Dict[str, Any]]] = []
        self.filtered_topologies: List[Tuple[str, Dict[str, Any]]] = []
        self.selected_scenario_id: Optional[str] = None
        self.selected_plan_scenario_id: Optional[str] = None
        self.selected_topology_id: Optional[str] = None
        self.last_generated_lab_dir: Optional[Path] = None
        self.workspace_lab_dir: Optional[Path] = None
        self.workspace_metadata: Dict[str, Any] = {}
        self.workspace_config_set = tk.StringVar(value="initial")
        self.workspace_device = tk.StringVar(value="")
        self.workspace_title = tk.StringVar(value="No generated lab loaded yet.")
        self.output_queue: "queue.Queue[str]" = queue.Queue()
        self.worker: Optional[threading.Thread] = None

        self.filter_summary = tk.StringVar(value="No filters applied.")
        self.build_ui()
        # Apply the persisted theme after widgets exist so custom theme overrides
        # take effect immediately during startup instead of requiring a manual toggle.
        self.apply_theme(save=False, notify=False)
        self.load_catalog()
        self.root.after(120, self.drain_output_queue)

    # ---------- Settings ----------

    def save_settings(self) -> None:
        data = {
            "theme": self.theme_name.get(),
            "catalog_path": self.catalog_path.get(),
            "generator_path": self.generator_path.get(),
            "output_dir": self.output_dir.get(),
            "gns3_server": self.server_url.get(),
            "host_type": self.host_type.get(),
            "auto_config": self.auto_config.get(),
            "push_config": self.push_config.get(),
            "push_endpoints": self.push_endpoints.get(),
            "verify": self.verify.get(),
            "linux_endpoint_username": self.linux_user.get(),
            "linux_endpoint_password": self.linux_password.get(),
            "show_legacy_deployments": self.show_legacy_deployments.get(),
        }
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ---------- UI construction ----------

    def build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill=BOTH, expand=True)

        header = ttk.Frame(outer)
        header.pack(fill=X, pady=(0, 8))

        ttk.Label(header, text=f"NetOps Labs {APP_VERSION}", font=("", 18, "bold")).pack(side=LEFT)
        self.status_text = tk.StringVar(value="Loading catalog...")
        ttk.Label(header, textvariable=self.status_text).pack(side=RIGHT)

        main_pane = ttk.Panedwindow(outer, orient=tk.VERTICAL)
        main_pane.pack(fill=BOTH, expand=True)

        notebook_frame = ttk.Frame(main_pane)
        output_frame = ttk.Labelframe(main_pane, text="Output", padding=8)

        main_pane.add(notebook_frame, weight=5)
        main_pane.add(output_frame, weight=1)

        self.notebook = ttk.Notebook(notebook_frame)
        self.notebook.pack(fill=BOTH, expand=True)

        self.build_labs_tab()
        self.build_study_plans_tab()
        self.build_workspace_tab()
        self.build_topologies_tab()
        self.build_settings_tab()

        output_controls = ttk.Frame(output_frame)
        output_controls.pack(fill=X, pady=(0, 6))
        ttk.Button(output_controls, text="Open Output Folder", command=self.open_output_folder).pack(side=LEFT)
        ttk.Button(output_controls, text="Open Lab Workspace", command=self.open_workspace_tab).pack(side=LEFT, padx=(8, 0))
        ttk.Button(output_controls, text="Clear Output", command=lambda: self.output.delete("1.0", END)).pack(side=LEFT, padx=(8, 0))

        output_text_frame = ttk.Frame(output_frame)
        output_text_frame.pack(fill=BOTH, expand=True)
        self.output = tk.Text(output_text_frame, height=8, wrap="word")
        output_scroll = ttk.Scrollbar(output_text_frame, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=output_scroll.set)
        self.output.pack(side=LEFT, fill=BOTH, expand=True)
        output_scroll.pack(side=RIGHT, fill=Y)

    def build_labs_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Labs")

        left = ttk.Frame(tab)
        left.pack(side=LEFT, fill=Y, padx=(0, 10))

        ttk.Label(left, text="Find a Lab", font=("", 13, "bold")).pack(anchor="w")

        help_box = ttk.Labelframe(left, text="Recommended Workflow", padding=8)
        help_box.pack(fill=X, pady=(8, 6))
        ttk.Label(
            help_box,
            text="1. Select an exam\n2. Search or filter by tag/topic\n3. Select a lab\n4. Review details\n5. Generate",
            justify="left",
        ).pack(anchor="w")

        ttk.Label(left, text="Search").pack(anchor="w", pady=(8, 0))
        search_row = ttk.Frame(left)
        search_row.pack(fill=X)
        search_entry = ttk.Entry(search_row, textvariable=self.search_text, width=24)
        search_entry.pack(side=LEFT, fill=X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self.apply_lab_filters())
        ttk.Button(search_row, text="Clear", command=self.clear_lab_search).pack(side=RIGHT, padx=(6, 0))

        self.filter_controls = {}
        for label, var in [
            ("Exam", self.exam_filter),
            ("Domain", self.domain_filter),
            ("Topic", self.topic_filter),
            ("Tag", self.tag_filter),
            ("Difficulty", self.difficulty_filter),
            ("Lab type", self.lab_type_filter),
        ]:
            ttk.Label(left, text=label).pack(anchor="w", pady=(8, 0))
            box = ttk.Combobox(left, textvariable=var, values=["All"], state="readonly", width=28)
            box.pack(fill=X)
            box.bind("<<ComboboxSelected>>", lambda _e: self.apply_lab_filters())
            self.filter_controls[label] = box

        ttk.Checkbutton(left, text="Beginner friendly only", variable=self.beginner_only, command=self.apply_lab_filters).pack(anchor="w", pady=(12, 0))
        ttk.Checkbutton(left, text="Legacy deployments", variable=self.show_legacy_deployments, command=self.apply_lab_filters).pack(anchor="w", pady=(4, 0))
        ttk.Label(left, text="Toggle between current default labs and old/fallback deployments.", wraplength=235, justify="left").pack(anchor="w", pady=(2, 0))
        ttk.Button(left, text="Reset Filters", command=self.reset_lab_filters).pack(fill=X, pady=(12, 0))

        summary_box = ttk.Labelframe(left, text="Active Filters", padding=6)
        summary_box.pack(fill=X, pady=(8, 0))
        ttk.Label(summary_box, textvariable=self.filter_summary, wraplength=235, justify="left").pack(anchor="w")

        center = ttk.Frame(tab)
        center.pack(side=LEFT, fill=BOTH, expand=True)

        columns = ("title", "exam", "domain", "topic", "difficulty", "type")
        self.lab_tree = ttk.Treeview(center, columns=columns, show="headings", height=24)
        headings = {
            "title": "Lab",
            "exam": "Exam",
            "domain": "Domain",
            "topic": "Topic",
            "difficulty": "Difficulty",
            "type": "Type",
        }
        widths = {"title": 340, "exam": 80, "domain": 150, "topic": 120, "difficulty": 85, "type": 105}
        for col in columns:
            self.lab_tree.heading(col, text=headings[col])
            self.lab_tree.column(col, width=widths[col], anchor="w")
        self.lab_tree.pack(fill=BOTH, expand=True)
        self.lab_tree.bind("<<TreeviewSelect>>", self.on_lab_select)

        details = ttk.Labelframe(tab, text="Lab Details", padding=8)
        details.pack(side=RIGHT, fill=BOTH, expand=False, padx=(10, 0))

        lab_btns = ttk.Frame(details)
        lab_btns.pack(fill=X, pady=(0, 8))
        ttk.Button(lab_btns, text="Check Readiness", command=self.check_selected_lab_readiness).pack(fill=X, pady=(0, 6))
        ttk.Button(lab_btns, text="Generate Selected Lab", command=self.generate_selected_lab).pack(fill=X, pady=(0, 6))
        ttk.Button(lab_btns, text="Copy CLI Command", command=self.copy_selected_cli_command).pack(fill=X, pady=(0, 6))
        ttk.Button(lab_btns, text="Copy Scenario ID", command=self.copy_selected_scenario_id).pack(fill=X, pady=(0, 6))

        detail_text_frame = ttk.Frame(details)
        detail_text_frame.pack(fill=BOTH, expand=True)
        self.lab_details = tk.Text(detail_text_frame, width=44, wrap="word")
        lab_scroll = ttk.Scrollbar(detail_text_frame, orient="vertical", command=self.lab_details.yview)
        self.lab_details.configure(yscrollcommand=lab_scroll.set)
        self.lab_details.pack(side=LEFT, fill=BOTH, expand=True)
        lab_scroll.pack(side=RIGHT, fill=Y)

    def build_study_plans_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Study Plans")

        left = ttk.Frame(tab)
        left.pack(side=LEFT, fill=Y, padx=(0, 10))
        ttk.Label(left, text="Study Plans", font=("", 13, "bold")).pack(anchor="w")
        ttk.Label(left, text="Plans are ordered by domain and prerequisite progression.", wraplength=240, justify="left").pack(anchor="w", pady=(2, 6))
        self.plan_list = tk.Listbox(left, width=32, height=24)
        self.plan_list.pack(fill=Y, expand=True, pady=(8, 0))
        self.plan_list.bind("<<ListboxSelect>>", self.on_plan_select)

        center = ttk.Frame(tab)
        center.pack(side=LEFT, fill=BOTH, expand=True)

        columns = ("step", "lab", "difficulty", "minutes", "topic")
        self.plan_tree = ttk.Treeview(center, columns=columns, show="headings")
        for col, title, width in [
            ("step", "Step", 220),
            ("lab", "Lab", 340),
            ("difficulty", "Difficulty", 90),
            ("minutes", "Minutes", 70),
            ("topic", "Topic", 130),
        ]:
            self.plan_tree.heading(col, text=title)
            self.plan_tree.column(col, width=width, anchor="w")
        self.plan_tree.pack(fill=BOTH, expand=True)
        self.plan_tree.bind("<<TreeviewSelect>>", self.on_plan_lab_select)

        details = ttk.Labelframe(tab, text="Plan Lab Details", padding=8)
        details.pack(side=RIGHT, fill=BOTH, expand=False, padx=(10, 0))

        btns = ttk.Frame(details)
        btns.pack(fill=X, side="top", pady=(0, 8))
        ttk.Button(btns, text="Generate Selected Plan Lab", command=self.generate_selected_plan_lab).pack(fill=X, pady=(0, 6))
        ttk.Button(btns, text="Generate All Labs in Plan", command=self.generate_all_plan_labs).pack(fill=X, pady=(0, 6))
        ttk.Button(btns, text="Copy Selected CLI Command", command=self.copy_plan_cli_command).pack(fill=X)

        plan_text_frame = ttk.Frame(details)
        plan_text_frame.pack(fill=BOTH, expand=True)
        self.plan_details = tk.Text(plan_text_frame, width=40, height=18, wrap="word")
        plan_scroll = ttk.Scrollbar(plan_text_frame, orient="vertical", command=self.plan_details.yview)
        self.plan_details.configure(yscrollcommand=plan_scroll.set)
        self.plan_details.pack(side=LEFT, fill=BOTH, expand=True)
        plan_scroll.pack(side=RIGHT, fill=Y)


    def build_workspace_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Lab Workspace")

        header = ttk.Frame(tab)
        header.pack(fill=X, pady=(0, 8))
        ttk.Label(header, textvariable=self.workspace_title, font=("", 13, "bold")).pack(side=LEFT)
        ttk.Button(header, text="Browse Lab Folder", command=self.browse_workspace_folder).pack(side=RIGHT, padx=(8, 0))
        ttk.Button(header, text="Refresh", command=self.refresh_workspace).pack(side=RIGHT, padx=(8, 0))
        ttk.Button(header, text="Open Lab Folder", command=self.open_last_lab_folder).pack(side=RIGHT)

        pane = ttk.Panedwindow(tab, orient=tk.HORIZONTAL)
        pane.pack(fill=BOTH, expand=True)

        left = ttk.Labelframe(pane, text="Generated Documents", padding=8)
        pane.add(left, weight=1)
        self.workspace_doc_list = tk.Listbox(left, width=32, height=26)
        self.workspace_doc_list.pack(fill=BOTH, expand=True)
        self.workspace_doc_list.bind("<<ListboxSelect>>", self.on_workspace_doc_select)

        middle = ttk.Labelframe(pane, text="Document Viewer", padding=8)
        pane.add(middle, weight=4)
        self.workspace_doc_text = tk.Text(middle, wrap="word")
        doc_scroll = ttk.Scrollbar(middle, orient="vertical", command=self.workspace_doc_text.yview)
        self.workspace_doc_text.configure(yscrollcommand=doc_scroll.set)
        self.workspace_doc_text.pack(side=LEFT, fill=BOTH, expand=True)
        doc_scroll.pack(side=RIGHT, fill=Y)

        right = ttk.Labelframe(pane, text="Config Viewer", padding=8)
        pane.add(right, weight=3)
        ttk.Label(right, text="Config set").pack(anchor="w")
        self.workspace_config_set_box = ttk.Combobox(right, textvariable=self.workspace_config_set, values=[], state="readonly", width=26)
        self.workspace_config_set_box.pack(fill=X, pady=(0, 8))
        self.workspace_config_set_box.bind("<<ComboboxSelected>>", lambda _e: self.populate_workspace_devices())
        ttk.Label(right, text="Device").pack(anchor="w")
        self.workspace_device_box = ttk.Combobox(right, textvariable=self.workspace_device, values=[], state="readonly", width=26)
        self.workspace_device_box.pack(fill=X, pady=(0, 8))
        self.workspace_device_box.bind("<<ComboboxSelected>>", lambda _e: self.load_workspace_config())
        ttk.Button(right, text="Open Config Folder", command=self.open_last_lab_configs).pack(fill=X, pady=(0, 8))
        config_frame = ttk.Frame(right)
        config_frame.pack(fill=BOTH, expand=True)
        self.workspace_config_text = tk.Text(config_frame, wrap="none", width=50)
        cfg_scroll = ttk.Scrollbar(config_frame, orient="vertical", command=self.workspace_config_text.yview)
        self.workspace_config_text.configure(yscrollcommand=cfg_scroll.set)
        self.workspace_config_text.pack(side=LEFT, fill=BOTH, expand=True)
        cfg_scroll.pack(side=RIGHT, fill=Y)

    def open_workspace_tab(self) -> None:
        try:
            for idx, tab_id in enumerate(self.notebook.tabs()):
                if self.notebook.tab(tab_id, "text") == "Lab Workspace":
                    self.notebook.select(tab_id)
                    return
        except Exception:
            pass

    def workspace_doc_entries(self) -> List[Tuple[str, Path]]:
        lab_dir = self.workspace_lab_dir or self.last_generated_lab_dir
        if not lab_dir:
            return []
        metadata = self.workspace_metadata or {}
        docs = metadata.get("documents", {}) if isinstance(metadata, dict) else {}
        preferred = [
            ("Student Brief", docs.get("student_brief", "student_brief.md")),
            ("First-Time Walkthrough", docs.get("walkthrough", "first_time_walkthrough.md")),
            ("Hints", docs.get("hints", "hints.md")),
            ("Topology Map", docs.get("topology_map", "topology_map.md")),
            ("Generation Summary", docs.get("generation_summary", "generation_summary.md")),
            ("README", docs.get("readme", "README.md")),
            ("Answer Key", docs.get("answer_key", "answer_key.md")),
        ]
        entries: List[Tuple[str, Path]] = []
        seen = set()
        for label, rel in preferred:
            if not rel:
                continue
            path = lab_dir / str(rel)
            if path.exists() and path not in seen:
                entries.append((label, path))
                seen.add(path)
        return entries

    def load_workspace_from_dir(self, lab_dir: Path) -> None:
        self.workspace_lab_dir = lab_dir.expanduser()
        self.last_generated_lab_dir = self.workspace_lab_dir
        metadata_path = self.workspace_lab_dir / "metadata.json"
        self.workspace_metadata = {}
        if metadata_path.exists():
            try:
                self.workspace_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except Exception:
                self.workspace_metadata = {}
        title = self.workspace_metadata.get("title") or self.workspace_lab_dir.name
        mode = self.workspace_metadata.get("lab_mode", "generated lab")
        self.workspace_title.set(f"Current Lab: {title} ({mode})")
        self.populate_workspace_docs()
        self.populate_workspace_config_sets()

    def refresh_workspace(self) -> None:
        lab_dir = self.workspace_lab_dir or self.last_generated_lab_dir
        if not lab_dir:
            messagebox.showinfo("No generated lab", "Generate a lab or browse to a generated lab folder first.")
            return
        self.load_workspace_from_dir(lab_dir)

    def browse_workspace_folder(self) -> None:
        path = filedialog.askdirectory(initialdir=self.output_dir.get())
        if path:
            self.load_workspace_from_dir(Path(path))
            self.open_workspace_tab()

    def populate_workspace_docs(self) -> None:
        self.workspace_doc_list.delete(0, END)
        self.workspace_doc_paths: List[Path] = []
        for label, path in self.workspace_doc_entries():
            self.workspace_doc_list.insert(END, label)
            self.workspace_doc_paths.append(path)
        self.workspace_doc_text.delete("1.0", END)
        if self.workspace_doc_paths:
            self.workspace_doc_list.selection_set(0)
            self.load_workspace_document(self.workspace_doc_paths[0], self.workspace_doc_list.get(0))
        else:
            self.workspace_doc_text.insert(END, "No generated documents found for this folder.\n")

    def on_workspace_doc_select(self, _event: Any = None) -> None:
        selection = self.workspace_doc_list.curselection()
        if not selection:
            return
        index = selection[0]
        path = self.workspace_doc_paths[index]
        label = self.workspace_doc_list.get(index)
        if label == "Answer Key":
            if not messagebox.askyesno("Reveal Answer Key", "This opens the complete solution. Continue?"):
                return
        self.load_workspace_document(path, label)

    def load_workspace_document(self, path: Path, label: str) -> None:
        self.workspace_doc_text.delete("1.0", END)
        try:
            self.workspace_doc_text.insert(END, path.read_text(encoding="utf-8"))
            self.status_text.set(f"Loaded {label}: {path.name}")
        except Exception as exc:
            self.workspace_doc_text.insert(END, f"Could not load {path}: {exc}\n")

    def populate_workspace_config_sets(self) -> None:
        lab_dir = self.workspace_lab_dir or self.last_generated_lab_dir
        if not lab_dir:
            return
        metadata = self.workspace_metadata or {}
        config_sets = metadata.get("config_sets", {}) if isinstance(metadata, dict) else {}
        if not config_sets:
            config_sets = {"initial": "starter_configs", "answer_key": "answer_key_configs", "baseline": "blank_topology_configs"}
        available = [name for name, rel in config_sets.items() if (lab_dir / str(rel)).exists()]
        self.workspace_config_set_box["values"] = available
        if available:
            self.workspace_config_set.set(available[0])
        else:
            self.workspace_config_set.set("")
        self.populate_workspace_devices()

    def populate_workspace_devices(self) -> None:
        lab_dir = self.workspace_lab_dir or self.last_generated_lab_dir
        selected = self.workspace_config_set.get()
        metadata = self.workspace_metadata or {}
        config_sets = metadata.get("config_sets", {}) if isinstance(metadata, dict) else {}
        rel = config_sets.get(selected, selected)
        config_dir = lab_dir / str(rel) if lab_dir and rel else None
        files = sorted(config_dir.glob("*.cfg")) if config_dir and config_dir.exists() else []
        values = [f.stem for f in files]
        self.workspace_device_box["values"] = values
        self.workspace_device.set(values[0] if values else "")
        self.load_workspace_config()

    def load_workspace_config(self) -> None:
        self.workspace_config_text.delete("1.0", END)
        lab_dir = self.workspace_lab_dir or self.last_generated_lab_dir
        if not lab_dir:
            return
        selected = self.workspace_config_set.get()
        device = self.workspace_device.get()
        metadata = self.workspace_metadata or {}
        config_sets = metadata.get("config_sets", {}) if isinstance(metadata, dict) else {}
        rel = config_sets.get(selected, selected)
        path = lab_dir / str(rel) / f"{device}.cfg" if rel and device else None
        if path and path.exists():
            self.workspace_config_text.insert(END, path.read_text(encoding="utf-8"))
        else:
            self.workspace_config_text.insert(END, "No config selected or config file not found.\n")

    def build_topologies_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Advanced Tools")

        left = ttk.Frame(tab)
        left.pack(side=LEFT, fill=Y, padx=(0, 10))
        ttk.Label(left, text="Blank Topology Mode", font=("", 13, "bold")).pack(anchor="w")
        ttk.Label(left, text="Use this when you want nodes and links without a lab scenario.", wraplength=250, justify="left").pack(anchor="w", pady=(0, 10))

        ttk.Label(left, text="Search").pack(anchor="w")
        ent = ttk.Entry(left, textvariable=self.topology_search_text, width=30)
        ent.pack(fill=X)
        ent.bind("<KeyRelease>", lambda _e: self.apply_topology_filters())

        ttk.Label(left, text="Exam relevance").pack(anchor="w", pady=(8, 0))
        self.topology_exam_box = ttk.Combobox(left, textvariable=self.topology_exam_filter, values=["All"], state="readonly", width=28)
        self.topology_exam_box.pack(fill=X)
        self.topology_exam_box.bind("<<ComboboxSelected>>", lambda _e: self.apply_topology_filters())

        ttk.Button(left, text="Reset", command=self.reset_topology_filters).pack(fill=X, pady=(12, 0))

        center = ttk.Frame(tab)
        center.pack(side=LEFT, fill=BOTH, expand=True)

        columns = ("topology", "domains", "nodes", "links")
        self.topology_tree = ttk.Treeview(center, columns=columns, show="headings")
        for col, title, width in [
            ("topology", "Topology", 330),
            ("domains", "Domains", 220),
            ("nodes", "Nodes", 70),
            ("links", "Links", 70),
        ]:
            self.topology_tree.heading(col, text=title)
            self.topology_tree.column(col, width=width, anchor="w")
        self.topology_tree.pack(fill=BOTH, expand=True)
        self.topology_tree.bind("<<TreeviewSelect>>", self.on_topology_select)

        details = ttk.Labelframe(tab, text="Topology Details", padding=8)
        details.pack(side=RIGHT, fill=BOTH, expand=False, padx=(10, 0))
        self.topology_details = tk.Text(details, width=44, wrap="word")
        self.topology_details.pack(fill=BOTH, expand=True)
        ttk.Button(details, text="Generate Blank Topology", command=self.generate_blank_topology).pack(fill=X, pady=(8, 0))

    def build_settings_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Settings")

        form = ttk.Labelframe(tab, text="Paths and Server", padding=10)
        form.pack(fill=X)

        self.path_row(form, "GNS3 server", self.server_url, None, 0)
        self.path_row(form, "Catalog", self.catalog_path, self.browse_catalog, 1)
        self.path_row(form, "Generator", self.generator_path, self.browse_generator, 2)
        self.path_row(form, "Output directory", self.output_dir, self.browse_output, 3)

        opts = ttk.Labelframe(tab, text="Generation Options", padding=10)
        opts.pack(fill=X, pady=(10, 0))

        ttk.Label(opts, text="Theme").grid(row=0, column=0, sticky="w")
        theme_box = ttk.Combobox(opts, textvariable=self.theme_name, values=THEMES, state="readonly", width=22)
        theme_box.grid(row=0, column=1, sticky="w", padx=(8, 0))
        theme_box.bind("<<ComboboxSelected>>", lambda _e: self.apply_theme())

        ttk.Label(opts, text="Host type").grid(row=0, column=2, sticky="w", padx=(20, 0))
        ttk.Combobox(opts, textvariable=self.host_type, values=["alpine", "rhel9", "vpcs"], state="readonly", width=20).grid(row=0, column=3, sticky="w", padx=(8, 0))

        ttk.Checkbutton(opts, text="Auto-config", variable=self.auto_config).grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Checkbutton(opts, text="Push Cisco configs", variable=self.push_config).grid(row=1, column=1, sticky="w", pady=(8, 0))
        ttk.Checkbutton(opts, text="Push supported endpoints", variable=self.push_endpoints).grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Checkbutton(opts, text="Collect verification", variable=self.verify).grid(row=1, column=3, sticky="w", pady=(8, 0))

        ttk.Label(opts, text="Linux endpoint user").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(opts, textvariable=self.linux_user, width=22).grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(10, 0))
        ttk.Label(opts, text="Linux endpoint password").grid(row=2, column=2, sticky="w", pady=(10, 0))
        ttk.Entry(opts, textvariable=self.linux_password, show="*", width=22).grid(row=2, column=3, sticky="w", padx=(8, 0), pady=(10, 0))

        actions = ttk.Frame(tab)
        actions.pack(fill=X, pady=(12, 0))
        ttk.Button(actions, text="Reload Catalog", command=self.load_catalog).pack(side=LEFT)
        ttk.Button(actions, text="Save Settings", command=self.save_settings).pack(side=LEFT, padx=(8, 0))
        ttk.Button(actions, text="Run QA Report", command=self.run_qa_report).pack(side=LEFT, padx=(8, 0))
        ttk.Button(actions, text="Validate Catalog", command=self.run_catalog_validator).pack(side=LEFT, padx=(8, 0))
        ttk.Button(actions, text="Audit Labs", command=self.run_lab_auditor).pack(side=LEFT, padx=(8, 0))
        ttk.Button(actions, text="Check Selected Lab Readiness", command=self.check_selected_lab_readiness).pack(side=LEFT, padx=(8, 0))
        ttk.Button(actions, text="Open Output Folder", command=self.open_output_folder).pack(side=LEFT, padx=(8, 0))

    def path_row(self, parent: ttk.Frame, label: str, variable: tk.StringVar, browse_cmd: Optional[Any], row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=variable, width=95).grid(row=row, column=1, sticky="ew", padx=(8, 8), pady=4)
        if browse_cmd:
            ttk.Button(parent, text="Browse", command=browse_cmd).grid(row=row, column=2, sticky="e", pady=4)
        parent.columnconfigure(1, weight=1)

    # ---------- Theme ----------

    def apply_theme(self, save: bool = True, notify: bool = True) -> None:
        theme = normalize_theme_name(self.theme_name.get())
        if theme != self.theme_name.get():
            self.theme_name.set(theme)
        try:
            style = get_style(self.root)
            if theme in CUSTOM_THEME_OVERRIDES:
                real_theme = ensure_custom_theme(self.root, theme) or THEME_ALIASES.get(theme, "darkly")
                style.theme_use(real_theme)
                # Re-apply the custom palette after selecting the isolated theme.
                # Some ttkbootstrap builds accept theme_create() but do not
                # fully materialize all widget colors from the supplied settings.
                # This keeps twilight_forest, deep_earth, evergreen, and the
                # custom light themes visually distinct without remapping darkly.
                apply_theme_overrides(self.root, theme)
            else:
                style.theme_use(theme)
                try:
                    self.root.configure(bg=style.lookup("TFrame", "background") or self.root.cget("bg"))
                except Exception:
                    pass
            if notify:
                self.status_text.set(f"Theme applied: {theme}")
        except Exception as exc:
            if notify:
                messagebox.showinfo("Theme saved", f"Theme saved as {theme}. Restart the GUI if it does not apply immediately.\n\n{exc}")
        if save:
            self.save_settings()
    # ---------- Catalog and filtering ----------

    def load_catalog(self) -> None:
        try:
            if not SETTINGS_FILE.exists():
                self.status_text.set("Using example config. Save Settings to create config/app_config.local.json.")
            path = Path(self.catalog_path.get())
            if not path.exists():
                path = DEFAULT_CATALOG
                self.catalog_path.set(str(path))
            self.catalog = json.loads(path.read_text(encoding="utf-8"))
            self.scenario_rows = sorted(self.catalog.get("scenarios", {}).items(), key=scenario_sort_key)
            self.topology_rows = sorted(self.catalog.get("topologies", {}).items())
            self.populate_filter_values()
            self.populate_plan_list()
            self.apply_lab_filters()
            self.apply_topology_filters()
            self.status_text.set(f"Catalog loaded: {len(self.scenario_rows)} scenarios, {len(self.topology_rows)} topologies")
        except Exception as exc:
            messagebox.showerror("Catalog error", str(exc))
            self.status_text.set("Catalog failed to load")

    def populate_filter_values(self) -> None:
        self.update_lab_filter_options()
        exams = sorted({exam for _sid, sc in self.scenario_rows for exam in sc.get("exam_blueprints", [])})
        self.topology_exam_box["values"] = ["All"] + exams

    def lab_filter_order(self) -> List[Tuple[str, tk.StringVar]]:
        return [
            ("Exam", self.exam_filter),
            ("Domain", self.domain_filter),
            ("Topic", self.topic_filter),
            ("Tag", self.tag_filter),
            ("Difficulty", self.difficulty_filter),
            ("Lab type", self.lab_type_filter),
        ]

    def scenario_values_for_filter(self, label: str, sc: Dict[str, Any]) -> List[str]:
        if label == "Exam":
            return [str(value) for value in sc.get("exam_blueprints", []) if value]
        if label == "Domain":
            return [str(sc.get("domain", ""))] if sc.get("domain") else []
        if label == "Topic":
            return scenario_topic_values(sc)
        if label == "Tag":
            return [str(value) for value in sc.get("tags", []) if value]
        if label == "Difficulty":
            return [str(sc.get("difficulty", ""))] if sc.get("difficulty") else []
        if label == "Lab type":
            return [str(sc.get("lab_type", ""))] if sc.get("lab_type") else []
        return []

    def scenario_matches_single_filter(self, label: str, selected: str, sc: Dict[str, Any]) -> bool:
        if selected == "All":
            return True
        selected_norm = normalize_filter_token(selected)
        return any(normalize_filter_token(value) == selected_norm for value in self.scenario_values_for_filter(label, sc))

    def scenario_matches_common_filter_base(self, sid: str, sc: Dict[str, Any]) -> bool:
        legacy = is_legacy_deployment(sid, sc)
        if self.show_legacy_deployments.get():
            if not legacy:
                return False
        elif legacy:
            return False
        if self.beginner_only.get() and str(sc.get("difficulty", "")).lower() not in {"intro", "easy"}:
            return False
        search = self.search_text.get().strip().lower()
        if search:
            haystack = " ".join([
                sid,
                sc.get("title", ""),
                sc.get("domain", ""),
                sc.get("topic", ""),
                sc.get("difficulty", ""),
                sc.get("lab_type", ""),
                sc.get("symptom", ""),
                " ".join(sc.get("tags", [])),
            ]).lower()
            if search not in haystack:
                return False
        return True

    def scenario_matches_filters_before(self, sid: str, sc: Dict[str, Any], stop_label: str) -> bool:
        if not self.scenario_matches_common_filter_base(sid, sc):
            return False
        for label, var in self.lab_filter_order():
            if label == stop_label:
                break
            if not self.scenario_matches_single_filter(label, var.get(), sc):
                return False
        return True

    def update_lab_filter_options(self) -> None:
        difficulty_order = {"intro": 1, "easy": 2, "medium": 3, "hard": 4, "capstone": 5}
        for label, var in self.lab_filter_order():
            options = set()
            for sid, sc in self.scenario_rows:
                if self.scenario_matches_filters_before(sid, sc, label):
                    options.update(self.scenario_values_for_filter(label, sc))
            if label == "Difficulty":
                vals = sorted(options, key=lambda v: difficulty_order.get(str(v).lower(), 99))
            else:
                vals = sorted(options, key=lambda v: str(v).lower())
            vals = ["All"] + vals
            self.filter_controls[label]["values"] = vals
            if var.get() not in vals:
                var.set("All")

    def scenario_matches_filters(self, sid: str, sc: Dict[str, Any]) -> bool:
        if not self.scenario_matches_common_filter_base(sid, sc):
            return False
        for label, var in self.lab_filter_order():
            if not self.scenario_matches_single_filter(label, var.get(), sc):
                return False
        return True

    def apply_lab_filters(self) -> None:
        self.update_lab_filter_options()
        self.filtered_scenarios = [(sid, sc) for sid, sc in self.scenario_rows if self.scenario_matches_filters(sid, sc)]
        for item in self.lab_tree.get_children():
            self.lab_tree.delete(item)
        for sid, sc in self.filtered_scenarios:
            self.lab_tree.insert(
                "",
                END,
                iid=sid,
                values=(
                    sc.get("title", sid),
                    ",".join(sc.get("exam_blueprints", [])),
                    sc.get("domain", ""),
                    sc.get("topic", ""),
                    title_value(sc.get("difficulty", "")),
                    title_value(sc.get("lab_type", "")),
                ),
            )
        self.update_filter_summary()
        self.status_text.set(f"Showing {len(self.filtered_scenarios)} labs")

    def update_filter_summary(self) -> None:
        filters = []
        if self.search_text.get().strip():
            filters.append(f"search='{self.search_text.get().strip()}'")
        for label, var in [
            ("exam", self.exam_filter),
            ("domain", self.domain_filter),
            ("topic", self.topic_filter),
            ("tag", self.tag_filter),
            ("difficulty", self.difficulty_filter),
            ("type", self.lab_type_filter),
        ]:
            if var.get() != "All":
                filters.append(f"{label}={var.get()}")
        if self.beginner_only.get():
            filters.append("beginner friendly")
        if self.show_legacy_deployments.get():
            filters.append("legacy deployments only")
        else:
            filters.append("default deployments only")

        if filters:
            self.filter_summary.set(f"Showing {len(self.filtered_scenarios)} labs\n" + "\n".join(filters))
        else:
            self.filter_summary.set(f"Showing {len(self.filtered_scenarios)} labs\nNo filters applied.")

    def clear_lab_search(self) -> None:
        self.search_text.set("")
        self.apply_lab_filters()

    def reset_lab_filters(self) -> None:
        self.search_text.set("")
        self.exam_filter.set("All")
        self.domain_filter.set("All")
        self.topic_filter.set("All")
        self.tag_filter.set("All")
        self.difficulty_filter.set("All")
        self.lab_type_filter.set("All")
        self.show_legacy_deployments.set(False)
        self.beginner_only.set(False)
        self.apply_lab_filters()

    def populate_plan_list(self) -> None:
        self.plan_list.delete(0, END)
        for plan_id, plan in sorted(self.catalog.get("study_plans", {}).items()):
            self.plan_list.insert(END, f"{plan_id} — {plan.get('title', plan_id)}")

    def topology_matches_filters(self, tid: str, topo: Dict[str, Any]) -> bool:
        search = self.topology_search_text.get().strip().lower()
        if search:
            haystack = " ".join([
                tid,
                topo.get("description", ""),
                " ".join(topo.get("technology_domains", [])),
                " ".join(topo.get("exam_blueprints", [])),
            ]).lower()
            if search not in haystack:
                return False
        if self.topology_exam_filter.get() != "All" and self.topology_exam_filter.get() not in topo.get("exam_blueprints", []):
            linked = False
            for _sid, sc in self.scenario_rows:
                if sc.get("topology") == tid and self.topology_exam_filter.get() in sc.get("exam_blueprints", []):
                    linked = True
                    break
            if not linked:
                return False
        return True

    def apply_topology_filters(self) -> None:
        self.filtered_topologies = [(tid, t) for tid, t in self.topology_rows if self.topology_matches_filters(tid, t)]
        for item in self.topology_tree.get_children():
            self.topology_tree.delete(item)
        for tid, topo in self.filtered_topologies:
            self.topology_tree.insert(
                "",
                END,
                iid=tid,
                values=(
                    tid,
                    ", ".join(topo.get("technology_domains", [])),
                    len(topo.get("nodes", {})),
                    len(topo.get("links", [])),
                ),
            )

    def reset_topology_filters(self) -> None:
        self.topology_search_text.set("")
        self.topology_exam_filter.set("All")
        self.apply_topology_filters()

    # ---------- Selection/details ----------

    def scenario_details_text(self, sid: str, sc: Dict[str, Any]) -> str:
        reqs = "\n".join(f"- {r}" for r in sc.get("requirements", [])[:8]) or "- No explicit requirements listed."
        tags = ", ".join(sc.get("tags", []))
        return f"""Title
{sc.get('title', sid)}

Scenario ID
{sid}

Concept ID
{concept_id(sid, sc)}

Scope
Exam: {', '.join(sc.get('exam_blueprints', []))}
Primary exam: {sc.get('primary_exam', '')}
Domain: {sc.get('domain', '')}
Topic: {sc.get('topic', '')}
Difficulty: {title_value(sc.get('difficulty', ''))}
Lab type: {title_value(sc.get('lab_type', ''))}
Estimated minutes: {sc.get('estimated_minutes', '')}
Deployment: {'Legacy' if is_legacy_deployment(sid, sc) else 'Default'}

Topology
{sc.get('topology', '')}

Why topology is shown
The topology is selected automatically for this lab. Most users do not need to choose a topology manually.

Symptom
{sc.get('symptom', '')}

Requirements
{reqs}

Tags
{tags}
"""

    def on_lab_select(self, _event: Any = None) -> None:
        sel = self.lab_tree.selection()
        if not sel:
            return
        sid = sel[0]
        self.selected_scenario_id = sid
        sc = self.catalog["scenarios"][sid]
        self.lab_details.delete("1.0", END)
        self.lab_details.insert(END, self.scenario_details_text(sid, sc))

    def on_plan_select(self, _event: Any = None) -> None:
        sel = self.plan_list.curselection()
        if not sel:
            return
        entry = self.plan_list.get(sel[0])
        plan_id = entry.split(" — ", 1)[0]
        plan = self.catalog.get("study_plans", {}).get(plan_id, {})

        for item in self.plan_tree.get_children():
            self.plan_tree.delete(item)

        for step_idx, step in enumerate(plan.get("steps", []), start=1):
            step_title = step.get("title", f"Step {step_idx}")
            for sid in step.get("scenario_ids", []):
                sc = self.catalog.get("scenarios", {}).get(sid, {})
                self.plan_tree.insert(
                    "",
                    END,
                    iid=f"{plan_id}|{sid}",
                    values=(
                        step_title,
                        sc.get("title", sid),
                        title_value(sc.get("difficulty", "")),
                        sc.get("estimated_minutes", ""),
                        sc.get("topic", ""),
                    ),
                )
        self.status_text.set(f"Study plan loaded: {plan_id}")

    def on_plan_lab_select(self, _event: Any = None) -> None:
        sel = self.plan_tree.selection()
        if not sel:
            return
        _plan_id, sid = sel[0].split("|", 1)
        self.selected_plan_scenario_id = sid
        sc = self.catalog["scenarios"][sid]
        self.plan_details.delete("1.0", END)
        self.plan_details.insert(END, self.scenario_details_text(sid, sc))

    def on_topology_select(self, _event: Any = None) -> None:
        sel = self.topology_tree.selection()
        if not sel:
            return
        tid = sel[0]
        self.selected_topology_id = tid
        topo = self.catalog["topologies"][tid]
        text = f"""Topology ID
{tid}

Description
{topo.get('description', '')}

Exam tags
{', '.join(topo.get('exam_blueprints', []))}

Technology domains
{', '.join(topo.get('technology_domains', []))}

Difficulty band
{topo.get('difficulty_band', '')}

Nodes
{len(topo.get('nodes', {}))}

Links
{len(topo.get('links', []))}

Node names
{', '.join(topo.get('nodes', {}).keys())}
"""
        self.topology_details.delete("1.0", END)
        self.topology_details.insert(END, text)

    # ---------- Browsing ----------

    def browse_catalog(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if path:
            self.catalog_path.set(path)
            self.load_catalog()

    def browse_generator(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Python", "*.py"), ("All files", "*.*")])
        if path:
            self.generator_path.set(path)

    def browse_output(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)

    # ---------- Command execution ----------

    def base_command(self) -> List[str]:
        generator = Path(self.generator_path.get())
        python_exe = sys.executable or "python3"
        cmd = [
            python_exe,
            str(generator),
            "--server", self.server_url.get().strip(),
            "--config", str(SETTINGS_FILE),
            "--catalog", self.catalog_path.get().strip(),
            "--out", self.output_dir.get().strip(),
            "--host-type", self.host_type.get(),
        ]

        cmd.append("--auto-config" if self.auto_config.get() else "--no-auto-config")
        cmd.append("--push-config" if self.push_config.get() else "--no-push-config")

        if self.push_endpoints.get():
            cmd.append("--push-endpoints")
            if self.linux_user.get().strip():
                cmd.extend(["--linux-endpoint-username", self.linux_user.get().strip()])
            if self.linux_password.get():
                cmd.extend(["--linux-endpoint-password", self.linux_password.get()])
        else:
            cmd.append("--skip-endpoints")

        if self.verify.get():
            cmd.append("--verify")

        return cmd

    def command_for_scenario(self, sid: str) -> List[str]:
        return self.base_command() + ["--scenario", sid]

    def preflight_command_for_scenario(self, sid: str) -> List[str]:
        return self.base_command() + ["--scenario", sid, "--preflight", "--no-push-config", "--skip-endpoints"]

    def command_summary(self, sid: Optional[str] = None, topology_id: Optional[str] = None, all_count: Optional[int] = None) -> str:
        target = ""
        if sid:
            sc = self.catalog.get("scenarios", {}).get(sid, {})
            target = f"Scenario: {sc.get('title', sid)}\nScenario ID: {sid}\n"
        elif topology_id:
            target = f"Blank topology: {topology_id}\n"
        elif all_count is not None:
            target = f"Generate all labs in plan: {all_count} labs\n"

        return f"""{target}
Server: {self.server_url.get()}
Host type: {self.host_type.get()}
Output directory: {self.output_dir.get()}

Auto-config: {'yes' if self.auto_config.get() else 'no'}
Push Cisco configs: {'yes' if self.push_config.get() else 'no'}
Push supported endpoints: {'yes' if self.push_endpoints.get() else 'no'}
Collect verification: {'yes' if self.verify.get() else 'no'}
"""

    def confirm_generation(self, sid: Optional[str] = None, topology_id: Optional[str] = None, all_count: Optional[int] = None) -> bool:
        if not self.server_url.get().strip():
            messagebox.showerror("GNS3 Server Required", "Set your GNS3 server URL in Settings before generating labs.")
            return False
        return messagebox.askyesno("Confirm Generation", self.command_summary(sid=sid, topology_id=topology_id, all_count=all_count))

    def run_command(self, cmd: List[str]) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("Busy", "A command is already running.")
            return
        self.save_settings()
        self.output.insert(END, "\n$ " + " ".join(cmd) + "\n")
        self.output.see(END)

        def worker() -> None:
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(APP_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                assert proc.stdout is not None
                for line in proc.stdout:
                    self.output_queue.put(line)
                rc = proc.wait()
                self.output_queue.put(f"\n[process exited with code {rc}]\n")
            except Exception as exc:
                self.output_queue.put(f"\n[error] {exc}\n")

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()

    def drain_output_queue(self) -> None:
        try:
            while True:
                text = self.output_queue.get_nowait()
                self.output.insert(END, text)
                self.track_generated_lab_path(text)
                self.output.see(END)
        except queue.Empty:
            pass
        self.root.after(120, self.drain_output_queue)

    def check_selected_lab_readiness(self) -> None:
        if not self.selected_scenario_id:
            messagebox.showinfo("Select a lab", "Select a lab from the table first.")
            return
        if not self.server_url.get().strip():
            messagebox.showerror("GNS3 Server Required", "Set your GNS3 server URL in Settings before checking readiness.")
            return
        self.run_command(self.preflight_command_for_scenario(self.selected_scenario_id))

    def generate_scenario(self, sid: str) -> None:
        if not self.confirm_generation(sid=sid):
            return
        self.run_command(self.command_for_scenario(sid))

    def generate_selected_lab(self) -> None:
        if not self.selected_scenario_id:
            messagebox.showinfo("Select a lab", "Select a lab from the table first.")
            return
        self.generate_scenario(self.selected_scenario_id)

    def generate_selected_plan_lab(self) -> None:
        if not self.selected_plan_scenario_id:
            messagebox.showinfo("Select a plan lab", "Select a lab from the study-plan table first.")
            return
        self.generate_scenario(self.selected_plan_scenario_id)

    def generate_all_plan_labs(self) -> None:
        sel = self.plan_list.curselection()
        if not sel:
            messagebox.showinfo("Select a plan", "Select a study plan first.")
            return
        entry = self.plan_list.get(sel[0])
        plan_id = entry.split(" — ", 1)[0]
        plan = self.catalog.get("study_plans", {}).get(plan_id, {})
        scenario_ids: List[str] = []
        for step in plan.get("steps", []):
            scenario_ids.extend(step.get("scenario_ids", []))
        if not scenario_ids:
            return
        if not self.confirm_generation(all_count=len(scenario_ids)):
            return

        script = "import subprocess,sys\n"
        for sid in scenario_ids:
            cmd = self.command_for_scenario(sid)
            script += f"print('=== Generating {sid} ===')\nsubprocess.call({cmd!r})\n"
        self.run_command([sys.executable, "-c", script])

    def generate_blank_topology(self) -> None:
        if not self.selected_topology_id:
            messagebox.showinfo("Select a topology", "Select a topology first.")
            return
        if not self.confirm_generation(topology_id=self.selected_topology_id):
            return
        cmd = self.base_command() + ["--blank-topology", "--topology", self.selected_topology_id, "--no-push-config", "--skip-endpoints"]
        self.run_command(cmd)

    def run_qa_report(self) -> None:
        cmd = [
            sys.executable,
            self.generator_path.get().strip(),
            "--catalog", self.catalog_path.get().strip(),
            "--qa-report",
        ]
        self.run_command(cmd)

    def run_catalog_validator(self) -> None:
        validator = APP_DIR / "scripts" / "validate_catalog.py"
        if not validator.exists():
            messagebox.showinfo("Validate Catalog", f"Catalog validator not found:\n{validator}")
            return
        cmd = [
            sys.executable,
            str(validator),
            "--catalog", self.catalog_path.get().strip(),
        ]
        self.run_command(cmd)


    def run_lab_auditor(self) -> None:
        auditor = APP_DIR / "scripts" / "audit_labs.py"
        if not auditor.exists():
            messagebox.showinfo("Audit Labs", f"Lab auditor not found:\n{auditor}")
            return
        cmd = [
            sys.executable,
            str(auditor),
            "--catalog", self.catalog_path.get().strip(),
            "--host-type", self.host_type.get(),
        ]
        self.run_command(cmd)

    # ---------- Convenience ----------

    def copy_text(self, text: str, status: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_text.set(status)

    def copy_selected_scenario_id(self) -> None:
        if self.selected_scenario_id:
            self.copy_text(self.selected_scenario_id, f"Copied scenario ID: {self.selected_scenario_id}")

    def copy_selected_cli_command(self) -> None:
        if not self.selected_scenario_id:
            messagebox.showinfo("Select a lab", "Select a lab first.")
            return
        self.copy_text(" ".join(self.command_for_scenario(self.selected_scenario_id)), "Copied CLI command.")

    def copy_plan_cli_command(self) -> None:
        if not self.selected_plan_scenario_id:
            messagebox.showinfo("Select a plan lab", "Select a lab from the study-plan table first.")
            return
        self.copy_text(" ".join(self.command_for_scenario(self.selected_plan_scenario_id)), "Copied plan lab CLI command.")

    def track_generated_lab_path(self, text: str) -> None:
        # Generator prints "Local files: <path>" on success. Capture it so users
        # do not have to dig through the output directory to find lab artifacts.
        marker = "Local files:"
        if marker not in text:
            return
        path_text = text.split(marker, 1)[1].strip()
        if not path_text:
            return
        self.last_generated_lab_dir = Path(path_text).expanduser()
        self.status_text.set(f"Last lab folder: {self.last_generated_lab_dir}")
        if self.last_generated_lab_dir.exists():
            self.load_workspace_from_dir(self.last_generated_lab_dir)

    def open_path(self, path: Path, create_dir: bool = False) -> None:
        path = path.expanduser()
        if create_dir:
            path.mkdir(parents=True, exist_ok=True)
        elif not path.exists():
            messagebox.showinfo("Open Folder", f"Path does not exist yet:\n{path}")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror("Open Folder", str(exc))

    def require_last_lab_dir(self) -> Optional[Path]:
        if not self.last_generated_lab_dir:
            messagebox.showinfo(
                "No generated lab yet",
                "Generate a lab first. The GUI will capture the generated lab folder when the command completes.",
            )
            return None
        if not self.last_generated_lab_dir.exists():
            messagebox.showinfo("Generated lab folder missing", f"The last generated lab folder no longer exists:\n{self.last_generated_lab_dir}")
            return None
        return self.last_generated_lab_dir

    def open_last_lab_folder(self) -> None:
        lab_dir = self.require_last_lab_dir()
        if lab_dir:
            self.open_path(lab_dir)

    def open_last_lab_readme(self) -> None:
        lab_dir = self.require_last_lab_dir()
        if not lab_dir:
            return
        for candidate in [lab_dir / "student_brief.md", lab_dir / "README.md", lab_dir / "requirements.md"]:
            if candidate.exists():
                self.open_path(candidate)
                return
        messagebox.showinfo("README not found", f"No student_brief.md, README.md, or requirements.md found in:\n{lab_dir}")

    def open_last_lab_configs(self) -> None:
        lab_dir = self.require_last_lab_dir()
        if not lab_dir:
            return
        for candidate in [lab_dir / "starter_configs", lab_dir / "configs", lab_dir / "blank_topology_configs"]:
            if candidate.exists():
                self.open_path(candidate)
                return
        messagebox.showinfo("Configs not found", f"No generated config directory found in:\n{lab_dir}")

    def open_output_folder(self) -> None:
        self.open_path(Path(self.output_dir.get()).expanduser(), create_dir=True)

def main() -> None:
    settings = load_settings_file()
    theme = normalize_theme_name(settings.get("theme", "darkly"))
    base_theme = THEME_ALIASES.get(theme, theme)
    try:
        root = ttk.Window(themename=base_theme)  # type: ignore[attr-defined]
    except Exception:
        root = tk.Tk()
    _app = LabGeneratorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
