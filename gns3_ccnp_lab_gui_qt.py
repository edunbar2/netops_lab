#!/usr/bin/env python3
"""PySide6 GUI for NetOps Labs.

This file is the primary GUI target for the 3.0 line. The legacy
Tk/ttkbootstrap GUI remains packaged as a fallback while the Qt interface
continues to evolve into a full practice workspace.
"""

from __future__ import annotations

import difflib
from datetime import datetime
import html
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from PySide6.QtCore import Qt, QThread, Signal, QObject, qInstallMessageHandler
    from PySide6.QtGui import QPalette, QAction, QColor, QBrush, QPen, QFont, QPixmap, QTextOption
    from PySide6.QtWidgets import (
        QApplication,
        QAbstractItemView,
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QGraphicsScene,
        QGraphicsView,
        QFrame,
        QGroupBox,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QPlainTextEdit,
        QProgressBar,
        QSizePolicy,
        QSpinBox,
        QSplitter,
        QStackedWidget,
        QStatusBar,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except Exception as exc:  # pragma: no cover - used only when dependency is absent
    print(
        "PySide6 is required for the Qt GUI.\n"
        "Install it with: python3 -m pip install -r requirements-pyside6.txt\n"
        f"Import error: {exc}",
        file=sys.stderr,
    )
    raise

def is_frozen_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def packaged_app_dir() -> Path:
    """Return the directory that contains bundled app data in source or frozen runs."""
    if is_frozen_app():
        executable_dir = Path(sys.executable).resolve().parent
        candidates = [
            executable_dir,
            Path(getattr(sys, "_MEIPASS", executable_dir)).resolve(),
            executable_dir.parent / "Resources",
            executable_dir.parent.parent / "Resources",
        ]
        for candidate in candidates:
            if (candidate / "catalogs").exists() or (candidate / "config_templates").exists():
                return candidate
        return executable_dir
    return Path(__file__).resolve().parent


def user_data_dir() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return root / "NetOps Labs"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "NetOps Labs"
    root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return root / "netops-labs"


APP_DIR = packaged_app_dir()
USER_APP_DIR = user_data_dir() if is_frozen_app() else APP_DIR
APP_VERSION = "4.0.1"
APP_NAME = "NetOps Labs"
APP_SUBTITLE = "Hands-on infrastructure training for networking, Linux, and security."
LEGACY_APP_NAME = "GNS3 CCNP Labs"

DEFAULT_CATALOG = APP_DIR / "catalogs" / "ccnp_encor_lab_catalog.json"
DEFAULT_GENERATOR = APP_DIR / "gns3_ccnp_lab_generator.py"
LOCAL_SETTINGS = USER_APP_DIR / "config" / "app_config.local.json"
EXAMPLE_SETTINGS = APP_DIR / "config" / "app_config.example.json"
SYMBOLS_DIR = APP_DIR / "assets" / "symbols"
DEFAULT_OUTPUT_DIR = USER_APP_DIR / "generated_labs"
PACKAGED_GENERATOR_NAMES = ["netops-lab-generator.exe", "netops-lab-generator"]

DIFFICULTY_ORDER = {"intro": 1, "easy": 2, "medium": 3, "hard": 4, "capstone": 5}


def qt_message_handler(mode: object, context: object, message: str) -> None:
    """Keep known harmless Qt text-cursor warnings out of the user terminal.

    QTextEdit.setMarkdown() can emit this warning internally when document content
    is replaced rapidly or when Qt restores a cursor position after a shorter
    document is loaded. It is noisy but not actionable for the user. Other Qt
    messages are still printed to stderr.
    """
    text = str(message)
    if text.startswith("QTextCursor::setPosition: Position '1' out of range"):
        return
    print(text, file=sys.stderr)


READABLE_DOCUMENT_CSS = """
h1 { margin-top: 18px; margin-bottom: 14px; }
h2 { margin-top: 24px; margin-bottom: 12px; }
h3 { margin-top: 18px; margin-bottom: 10px; }
h4 { margin-top: 14px; margin-bottom: 8px; }
p { margin-top: 8px; margin-bottom: 14px; line-height: 135%; }
ul, ol { margin-top: 8px; margin-bottom: 16px; }
li { margin-bottom: 6px; }
pre { margin-top: 10px; margin-bottom: 16px; padding: 8px; }
"""


def configure_readable_text_edit(widget: QTextEdit, margin: int = 12) -> QTextEdit:
    """Apply document-level readability spacing to Markdown-backed text panes."""
    widget.setWordWrapMode(QTextOption.WordWrap)
    widget.document().setDocumentMargin(margin)
    try:
        widget.document().setDefaultStyleSheet(READABLE_DOCUMENT_CSS)
    except Exception:
        pass
    return widget


QT_STYLESHEET = """
QMainWindow, QWidget {
    background: #111827;
    color: #e5e7eb;
    font-size: 13px;
}
QFrame#Sidebar {
    background: #0b1220;
    border-right: 1px solid #223047;
}
QPushButton {
    background: #24324a;
    border: 1px solid #3b4b68;
    border-radius: 8px;
    padding: 7px 10px;
    color: #e5e7eb;
}
QPushButton:hover { background: #2f4262; }
QPushButton:pressed { background: #1d2a3f; }
QPushButton#PrimaryButton {
    background: #2563eb;
    border: 1px solid #3b82f6;
    color: white;
}
QPushButton#DangerButton {
    background: #7f1d1d;
    border: 1px solid #991b1b;
    color: #fee2e2;
}
QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QListWidget, QTableWidget {
    background: #172033;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px;
    color: #e5e7eb;
    selection-background-color: #2563eb;
}
QComboBox::drop-down { border: 0; width: 24px; }
QComboBox { min-height: 28px; padding-top: 5px; padding-bottom: 5px; }
QComboBox QAbstractItemView { padding: 4px; }
QHeaderView::section {
    background: #1f2937;
    color: #d1d5db;
    padding: 5px;
    border: 0;
    border-right: 1px solid #374151;
}
QTabWidget::pane { border: 1px solid #334155; border-radius: 8px; }
QTabBar::tab {
    background: #172033;
    color: #d1d5db;
    padding: 8px 12px;
    border: 1px solid #334155;
    border-bottom: 0;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QTabBar::tab:selected { background: #263246; color: white; }
QGroupBox {
    border: 1px solid #334155;
    border-radius: 10px;
    margin-top: 12px;
    padding: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: #93c5fd;
}
QLabel#PageTitle {
    font-size: 20px;
    font-weight: 700;
    color: #f9fafb;
}
QLabel#Muted { color: #9ca3af; }
QProgressBar {
    border: 1px solid #334155;
    border-radius: 7px;
    text-align: center;
    background: #172033;
}
QProgressBar::chunk { background: #2563eb; border-radius: 6px; }
"""

QT_THEME_STYLES = {
    "darkly": QT_STYLESHEET,
    "cyborg": QT_STYLESHEET.replace("#111827", "#06090f").replace("#0b1220", "#05070c").replace("#2563eb", "#00a3cc"),
    "superhero": QT_STYLESHEET.replace("#111827", "#1b2433").replace("#0b1220", "#111827").replace("#2563eb", "#df691a"),
    "solar": QT_STYLESHEET.replace("#111827", "#002b36").replace("#0b1220", "#073642").replace("#172033", "#073642").replace("#2563eb", "#b58900"),
    "vapor": QT_STYLESHEET.replace("#111827", "#190b2f").replace("#0b1220", "#110720").replace("#172033", "#261447").replace("#2563eb", "#7c3aed"),
    "twilight_forest": QT_STYLESHEET.replace("#111827", "#101914").replace("#0b1220", "#0a100d").replace("#172033", "#17261d").replace("#24324a", "#244331").replace("#2563eb", "#4f7942").replace("#93c5fd", "#a7c957"),
    "deep_earth": QT_STYLESHEET.replace("#111827", "#18130f").replace("#0b1220", "#100c09").replace("#172033", "#261c14").replace("#24324a", "#3b2a1d").replace("#2563eb", "#8b5e34").replace("#93c5fd", "#d6b98c"),
    "evergreen": QT_STYLESHEET.replace("#111827", "#0c1a13").replace("#0b1220", "#06100b").replace("#172033", "#10261a").replace("#24324a", "#16402a").replace("#2563eb", "#2f855a").replace("#93c5fd", "#9ae6b4"),
    "minty": QT_STYLESHEET.replace("#111827", "#eef8f3").replace("#0b1220", "#dbeee6").replace("#172033", "#ffffff").replace("#e5e7eb", "#1f2937").replace("#d1d5db", "#374151").replace("#f9fafb", "#111827").replace("#24324a", "#dff3ea").replace("#2563eb", "#20c997").replace("#93c5fd", "#198754"),
    "morph": QT_STYLESHEET.replace("#111827", "#eef1f6").replace("#0b1220", "#dde4ef").replace("#172033", "#ffffff").replace("#e5e7eb", "#1f2937").replace("#d1d5db", "#374151").replace("#f9fafb", "#111827").replace("#24324a", "#e3eaf5").replace("#2563eb", "#5b6ee1").replace("#93c5fd", "#5060c9"),
    "sandstone": QT_STYLESHEET.replace("#111827", "#f3eee7").replace("#0b1220", "#e6dacd").replace("#172033", "#fffaf3").replace("#e5e7eb", "#2f2923").replace("#d1d5db", "#4a4038").replace("#f9fafb", "#1f1a16").replace("#24324a", "#e7d1bb").replace("#2563eb", "#9a6a3a").replace("#93c5fd", "#7b4f26"),
    "mist": QT_STYLESHEET.replace("#111827", "#edf2f4").replace("#0b1220", "#d8e1e8").replace("#172033", "#f8fafc").replace("#e5e7eb", "#1f2937").replace("#d1d5db", "#334155").replace("#f9fafb", "#111827").replace("#24324a", "#dbeafe").replace("#2563eb", "#3b82f6").replace("#93c5fd", "#2563eb"),
    "sage": QT_STYLESHEET.replace("#111827", "#eef2e6").replace("#0b1220", "#dce5d1").replace("#172033", "#fbfdf7").replace("#e5e7eb", "#263127").replace("#d1d5db", "#3f4b3f").replace("#f9fafb", "#182018").replace("#24324a", "#d7e5c7").replace("#2563eb", "#6b8e4e").replace("#93c5fd", "#56733f"),
    "parchment": QT_STYLESHEET.replace("#111827", "#f4ecd8").replace("#0b1220", "#e8dcc2").replace("#172033", "#fff8e8").replace("#e5e7eb", "#2f271c").replace("#d1d5db", "#4f432f").replace("#f9fafb", "#211a12").replace("#24324a", "#ead8ad").replace("#2563eb", "#b7791f").replace("#93c5fd", "#8a5a14"),
    "twilight_parchment": QT_STYLESHEET.replace("#111827", "#14110f").replace("#0b1220", "#0d0b0a").replace("#172033", "#211c18").replace("#24324a", "#3e342c").replace("#2563eb", "#8c6a43").replace("#93c5fd", "#d8c7a0").replace("#e5e7eb", "#e5d9bf").replace("#d1d5db", "#bfae92").replace("#f9fafb", "#f4ead7"),
    "woodland": QT_STYLESHEET.replace("#111827", "#ece7dc").replace("#0b1220", "#d9ceb8").replace("#172033", "#f8f4eb").replace("#e5e7eb", "#2c261f").replace("#d1d5db", "#4a4035").replace("#f9fafb", "#1f1a14").replace("#24324a", "#d9c5a6").replace("#2563eb", "#5f7a3a").replace("#93c5fd", "#4d612f"),
}

QT_THEME_SELECTIONS = {
    "darkly": ("#334155", "#f8fafc"),
    "cyborg": ("#155e75", "#f0fdfa"),
    "superhero": ("#6b4423", "#fff7ed"),
    "solar": ("#765d13", "#fdf6e3"),
    "vapor": ("#5b21b6", "#faf5ff"),
    "twilight_forest": ("#344b37", "#eef4e8"),
    "deep_earth": ("#57412b", "#f5ead8"),
    "evergreen": ("#24543a", "#eef7ec"),
    "minty": ("#c3e8dd", "#12312a"),
    "morph": ("#d4daf0", "#172033"),
    "sandstone": ("#d9bea0", "#2f2923"),
    "mist": ("#d3dde7", "#172033"),
    "sage": ("#d1dec4", "#182018"),
    "parchment": ("#d9c79f", "#211a12"),
    "twilight_parchment": ("#5a4632", "#f4ead7"),
    "woodland": ("#cfc0a5", "#1f1a14"),
}


def theme_selection_styles(theme: str) -> str:
    background, foreground = QT_THEME_SELECTIONS.get(theme, QT_THEME_SELECTIONS["darkly"])
    return f"""
QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QListWidget, QTableWidget {{
    selection-background-color: {background};
    selection-color: {foreground};
}}
QLineEdit::selection, QTextEdit::selection, QPlainTextEdit::selection {{
    background-color: {background};
    color: {foreground};
}}
QAbstractItemView {{
    selection-background-color: {background};
    selection-color: {foreground};
}}
QListWidget::item:selected, QTableWidget::item:selected, QTreeView::item:selected, QTableView::item:selected {{
    background: {background};
    color: {foreground};
}}
QTableWidget::item:selected:!active, QListWidget::item:selected:!active {{
    background: {background};
    color: {foreground};
}}
QComboBox QAbstractItemView::item:selected {{
    background: {background};
    color: {foreground};
}}
QTabBar::tab:selected {{
    border-bottom: 2px solid {background};
}}
QProgressBar::chunk {{ background: {background}; }}
"""



def theme_role_styles(theme: str) -> str:
    roles = {
        "darkly": {"header_bg": "#1f2937", "header_fg": "#d1d5db", "border": "#334155", "title": "#cbd5e1", "tab_bg": "#263246", "field_border": "#334155"},
        "twilight_forest": {"header_bg": "#17261d", "header_fg": "#dce8d6", "border": "#344b37", "title": "#c8d6b3", "tab_bg": "#203129", "field_border": "#344b37"},
        "deep_earth": {"header_bg": "#261c14", "header_fg": "#e3d5c1", "border": "#57412b", "title": "#c9ae84", "tab_bg": "#302419", "field_border": "#57412b"},
        "evergreen": {"header_bg": "#10261a", "header_fg": "#dce8d9", "border": "#24543a", "title": "#a7c8a7", "tab_bg": "#1b3527", "field_border": "#24543a"},
        "twilight_parchment": {"header_bg": "#2b241f", "header_fg": "#e5d9bf", "border": "#4a3b2c", "title": "#d8c7a0", "tab_bg": "#2b241f", "field_border": "#4a3b2c"},
        "minty": {"header_bg": "#d8f1e8", "header_fg": "#12312a", "border": "#b5d8cb", "title": "#198754", "tab_bg": "#e8f7f2", "field_border": "#b5d8cb"},
        "morph": {"header_bg": "#dbe2ee", "header_fg": "#172033", "border": "#c4cad8", "title": "#4b5563", "tab_bg": "#e6ebf5", "field_border": "#c4cad8"},
        "sandstone": {"header_bg": "#e6dacd", "header_fg": "#2f2923", "border": "#cdb79f", "title": "#7b4f26", "tab_bg": "#f2e7dc", "field_border": "#cdb79f"},
        "mist": {"header_bg": "#dde6ee", "header_fg": "#172033", "border": "#c3ced8", "title": "#506070", "tab_bg": "#edf2f6", "field_border": "#c3ced8"},
        "sage": {"header_bg": "#dce5d1", "header_fg": "#182018", "border": "#bdcdae", "title": "#56733f", "tab_bg": "#eef2e6", "field_border": "#bdcdae"},
        "parchment": {"header_bg": "#e8dcc2", "header_fg": "#211a12", "border": "#cdbb95", "title": "#8a5a14", "tab_bg": "#f4ecd8", "field_border": "#cdbb95"},
        "woodland": {"header_bg": "#d9ceb8", "header_fg": "#1f1a14", "border": "#bdae91", "title": "#4d612f", "tab_bg": "#e9e1d2", "field_border": "#bdae91"},
    }
    r = roles.get(theme, roles.get(normalize_qt_theme(theme), roles["darkly"]))
    return f"""
QHeaderView::section {{
    background: {r['header_bg']};
    color: {r['header_fg']};
    border: 0;
    border-right: 1px solid {r['border']};
    border-bottom: 1px solid {r['border']};
}}
QGroupBox, QTabWidget::pane {{ border: 1px solid {r['border']}; }}
QGroupBox::title {{ color: {r['title']}; }}
QTabBar::tab:selected {{ background: {r['tab_bg']}; color: {r['header_fg']}; border-color: {r['border']}; }}
QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QListWidget, QTableWidget {{ border: 1px solid {r['field_border']}; }}
"""

def theme_visual_roles(theme: str) -> Dict[str, str]:
    """Return dedicated topology canvas colors.

    The topology view intentionally uses a neutral fixed palette rather than
    borrowing theme tertiary/accent colors. This keeps the canvas readable
    across light, dark, and parchment-style themes.
    """
    return {
        "topology_bg": "#343434",
        "topology_node": "#4b5563",
        "topology_line": "#f2f2f2",
        "topology_text": "#f8fafc",
        "topology_muted": "#d1d5db",
        "topology_label_bg": "#4b5563",
    }

def theme_selection_colors(theme: str) -> Tuple[str, str]:
    return QT_THEME_SELECTIONS.get(theme, QT_THEME_SELECTIONS["darkly"])

def qt_theme_names() -> List[str]:
    return list(QT_THEME_STYLES.keys())


def normalize_qt_theme(value: Any) -> str:
    token = normalize_token(value).replace("-", "_")
    aliases = {
        "default": "darkly",
        "dark": "darkly",
        "darkly": "darkly",
        "twilight": "twilight_forest",
        "forest": "twilight_forest",
        "earth": "deep_earth",
        "deep-earth": "deep_earth",
        "deep_earth": "deep_earth",
        "evergreen": "evergreen",
        "twilight-parchment": "twilight_parchment",
        "twilight_parchment": "twilight_parchment",
        "dark-academia": "twilight_parchment",
        "dark_academia": "twilight_parchment",
        "light": "mist",
    }
    token = aliases.get(token, token)
    return token if token in QT_THEME_STYLES else "darkly"



SYMBOL_ROLE_DEFAULTS = {
    "router": "classic/router.svg",
    "switch": "classic/ethernet_switch.svg",
    "endpoint": "classic/computer.svg",
    "firewall": "classic/firewall.svg",
    "cloud": "classic/cloud.svg",
    "unknown": "classic/qemu_guest.svg",
}

SYMBOL_ROLE_LABELS = {
    "router": "Router",
    "switch": "Switch",
    "endpoint": "PC / Endpoint",
    "firewall": "Firewall",
    "cloud": "Cloud / ISP",
    "unknown": "Unknown / Fallback",
}


def available_symbol_paths() -> List[str]:
    if not SYMBOLS_DIR.exists():
        return []
    result: List[str] = []
    for path in SYMBOLS_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith(".") or path.name.startswith("._"):
            continue
        if path.suffix.lower() not in {".svg", ".png", ".jpg", ".jpeg"}:
            continue
        result.append(path.relative_to(SYMBOLS_DIR).as_posix())
    return sorted(result, key=lambda item: (0 if item.startswith("classic/") else 1, item.lower()))


def merged_symbol_mappings(settings: Dict[str, Any]) -> Dict[str, str]:
    mappings = dict(SYMBOL_ROLE_DEFAULTS)
    saved = settings.get("topology_symbol_map") or settings.get("symbol_mappings") or {}
    if isinstance(saved, dict):
        for role, rel in saved.items():
            if role in mappings and isinstance(rel, str) and rel.strip():
                mappings[role] = rel.strip().replace("\\", "/")
    return mappings


def read_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def load_settings() -> Dict[str, Any]:
    settings = read_json(EXAMPLE_SETTINGS)
    settings.update(read_json(LOCAL_SETTINGS))
    return settings


def packaged_generator_path() -> Optional[Path]:
    """Return the bundled generator executable when running from a packaged app."""
    if not is_frozen_app():
        return None
    executable_dir = Path(sys.executable).resolve().parent
    candidates: List[Path] = []
    for root in [executable_dir, APP_DIR]:
        candidates.extend(root / name for name in PACKAGED_GENERATOR_NAMES)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def normalize_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")


def titleize(value: Any) -> str:
    text = str(value or "").strip()
    return text.replace("_", " ").replace("-", " ").title() if text else ""


def scenario_topic_values(scenario: Dict[str, Any]) -> List[str]:
    values: List[str] = []
    if scenario.get("topic"):
        values.append(titleize(scenario.get("topic")))
    for tag in scenario.get("tags", []) or []:
        tag_token = normalize_token(tag)
        if tag_token in {
            "routing",
            "switching",
            "infrastructure",
            "automation",
            "security",
            "services",
            "wireless",
            "architecture",
            "assurance",
            "management",
        }:
            values.append(titleize(tag))
    seen: set[str] = set()
    result: List[str] = []
    for item in values:
        token = normalize_token(item)
        if token and token not in seen:
            seen.add(token)
            result.append(item)
    return result


def scenario_exam_values(scenario: Dict[str, Any]) -> List[str]:
    """Return exam labels available for secondary exam-alignment metadata."""
    values: List[str] = []
    primary = scenario.get("primary_exam")
    if primary:
        values.append(str(primary).strip().upper())
    blueprints = scenario.get("exam_blueprints") or []
    if isinstance(blueprints, str):
        blueprints = [blueprints]
    for exam in blueprints:
        if exam:
            values.append(str(exam).strip().upper())
    seen: set[str] = set()
    result: List[str] = []
    for item in values:
        token = normalize_token(item)
        if token and token not in seen:
            seen.add(token)
            result.append(item)
    return result


STUDY_PATH_LABELS = {
    "ccna-foundations": "CCNA Foundations",
    "ccnp-enterprise": "CCNP Enterprise",
    "secure-enclave-networking": "Secure Enclave Networking",
    "rhel9-operations": "RHEL9 Operations",
    "network-troubleshooting": "Network Troubleshooting",
    "automation-netdevops": "Automation / NetDevOps",
}


def normalize_study_path_label(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    token = normalize_token(text)
    return STUDY_PATH_LABELS.get(token, titleize(text))


def scenario_study_path_values(scenario: Dict[str, Any]) -> List[str]:
    """Return user-facing study path labels.

    4.0 makes study paths the primary catalog filter while preserving 3.x
    catalog compatibility. New catalogs can set study_paths directly. Older
    catalogs fall back to exam alignment.
    """
    raw_paths = scenario.get("study_paths") or []
    if isinstance(raw_paths, str):
        raw_paths = [raw_paths]
    values = [normalize_study_path_label(path) for path in raw_paths if path]

    if not values:
        exams = {normalize_token(e) for e in scenario_exam_values(scenario)}
        if "ccna" in exams:
            values.append("CCNA Foundations")
        if exams.intersection({"encor", "enarsi", "ccnp"}):
            values.append("CCNP Enterprise")

    if not values:
        tags = {normalize_token(t) for t in scenario.get("tags", []) or []}
        lab_type = normalize_token(scenario.get("lab_type", ""))
        if "security" in tags:
            values.append("Secure Enclave Networking")
        if lab_type == "troubleshoot":
            values.append("Network Troubleshooting")

    if not values:
        values.append("CCNP Enterprise")

    seen: set[str] = set()
    result: List[str] = []
    for item in values:
        token = normalize_token(item)
        if token and token not in seen:
            seen.add(token)
            result.append(item)
    return result


class CatalogStore:
    def __init__(self, catalog_path: Path = DEFAULT_CATALOG):
        self.catalog_path = catalog_path
        self.catalog: Dict[str, Any] = read_json(catalog_path)
        self.scenarios: Dict[str, Dict[str, Any]] = self.catalog.get("scenarios", {})
        self.topologies: Dict[str, Dict[str, Any]] = self.catalog.get("topologies", {})

    def all_domains(self) -> List[str]:
        return sorted({str(s.get("domain", "")) for s in self.scenarios.values() if s.get("domain")})

    def all_study_paths(self) -> List[str]:
        values: set[str] = set()
        for scenario in self.scenarios.values():
            values.update(scenario_study_path_values(scenario))
        preferred = {
            "CCNA Foundations": 1,
            "CCNP Enterprise": 2,
            "Secure Enclave Networking": 3,
            "RHEL9 Operations": 4,
            "Network Troubleshooting": 5,
            "Automation / NetDevOps": 6,
        }
        return sorted(values, key=lambda item: (preferred.get(item, 99), item))

    def all_exams(self) -> List[str]:
        values: set[str] = set()
        for scenario in self.scenarios.values():
            values.update(scenario_exam_values(scenario))
        preferred = {"ENCOR": 1, "ENARSI": 2, "CCNA": 3}
        return sorted(values, key=lambda item: (preferred.get(item, 99), item))

    def topologies_list(self) -> List[str]:
        return sorted(self.topologies.keys())

    def filtered_scenarios(
        self,
        study_path: str = "All",
        exam: str = "All",
        deployment: str = "Default",
        domain: str = "All",
        topic: str = "All",
        difficulty: str = "All",
        lab_type: str = "All",
        tag: str = "All",
        search: str = "",
    ) -> List[Tuple[str, Dict[str, Any]]]:
        search_l = search.strip().lower()
        rows: List[Tuple[str, Dict[str, Any]]] = []
        for sid, scenario in self.scenarios.items():
            if study_path != "All":
                study_paths = {normalize_token(v) for v in scenario_study_path_values(scenario)}
                if normalize_token(study_path) not in study_paths:
                    continue
            if exam != "All":
                exams = {normalize_token(v) for v in scenario_exam_values(scenario)}
                if normalize_token(exam) not in exams:
                    continue
            is_legacy = bool(scenario.get("legacy_variant"))
            if deployment == "Default" and is_legacy:
                continue
            if deployment == "Legacy" and not is_legacy:
                continue
            if domain != "All" and str(scenario.get("domain")) != domain:
                continue
            if difficulty != "All" and str(scenario.get("difficulty")) != difficulty:
                continue
            if lab_type != "All" and str(scenario.get("lab_type")) != lab_type:
                continue
            if topic != "All":
                topic_tokens = {normalize_token(v) for v in scenario_topic_values(scenario)}
                if normalize_token(topic) not in topic_tokens:
                    continue
            if tag != "All":
                tags = {normalize_token(t) for t in scenario.get("tags", []) or []}
                if normalize_token(tag) not in tags:
                    continue
            if search_l:
                haystack = " ".join(
                    [
                        sid,
                        str(scenario.get("title", "")),
                        str(scenario.get("symptom", "")),
                        str(scenario.get("domain", "")),
                        str(scenario.get("topic", "")),
                        " ".join(scenario_study_path_values(scenario)),
                        " ".join(scenario_exam_values(scenario)),
                        " ".join(map(str, scenario.get("tags", []) or [])),
                        " ".join(map(str, scenario.get("verification", []) or [])),
                    ]
                ).lower()
                if search_l not in haystack:
                    continue
            rows.append((sid, scenario))
        return sorted(rows, key=lambda item: (
            str(item[1].get("domain", "")),
            DIFFICULTY_ORDER.get(str(item[1].get("difficulty", "")).lower(), 99),
            str(item[1].get("topic", "")),
            str(item[1].get("title", item[0])),
        ))

    def option_values(self, field: str, current_filters: Dict[str, str]) -> List[str]:
        # Cascading options based on higher-level filters only.
        kwargs = dict(current_filters)
        if field == "study_path":
            kwargs.update(study_path="All", domain="All", topic="All", difficulty="All", lab_type="All", tag="All", search="")
            values: set[str] = set()
            for _sid, scenario in self.filtered_scenarios(**kwargs):
                values.update(scenario_study_path_values(scenario))
            return sorted(values)
        if field == "domain":
            kwargs.update(domain="All", topic="All", difficulty="All", lab_type="All", tag="All", search="")
            return sorted({str(s.get("domain", "")) for _sid, s in self.filtered_scenarios(**kwargs) if s.get("domain")})
        if field == "topic":
            kwargs.update(topic="All", difficulty="All", lab_type="All", tag="All", search="")
            values: set[str] = set()
            for _sid, scenario in self.filtered_scenarios(**kwargs):
                values.update(scenario_topic_values(scenario))
            return sorted(values)
        if field == "difficulty":
            kwargs.update(difficulty="All", lab_type="All", tag="All", search="")
            return sorted({str(s.get("difficulty")) for _sid, s in self.filtered_scenarios(**kwargs) if s.get("difficulty")}, key=lambda x: DIFFICULTY_ORDER.get(x.lower(), 99))
        if field == "lab_type":
            kwargs.update(lab_type="All", tag="All", search="")
            return sorted({str(s.get("lab_type")) for _sid, s in self.filtered_scenarios(**kwargs) if s.get("lab_type")})
        if field == "tag":
            kwargs.update(tag="All", search="")
            values: set[str] = set()
            for _sid, scenario in self.filtered_scenarios(**kwargs):
                values.update(str(t) for t in scenario.get("tags", []) or [])
            return sorted(values)
        return []


class ConsoleWorker(QThread):
    output = Signal(str, str)
    status = Signal(str, str)

    def __init__(self, device_name: str, host: str, port: int):
        super().__init__()
        self.device_name = device_name
        self.host = host
        self.port = int(port)
        self._running = True
        self._socket: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._pending: List[bytes] = []

    def queue_text(self, text: str) -> None:
        if not text:
            return
        payload = text.encode("utf-8", errors="ignore")
        with self._lock:
            self._pending.append(payload)

    def stop(self) -> None:
        self._running = False
        try:
            if self._socket:
                self._socket.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            if self._socket:
                self._socket.close()
        except Exception:
            pass

    def run(self) -> None:
        try:
            sock = socket.create_connection((self.host, self.port), timeout=8)
            sock.settimeout(0.25)
            self._socket = sock
            self.status.emit(self.device_name, f"Connected to {self.host}:{self.port}")
            while self._running:
                with self._lock:
                    pending = self._pending[:]
                    self._pending.clear()
                for payload in pending:
                    try:
                        sock.sendall(payload)
                    except Exception as exc:
                        self.status.emit(self.device_name, f"Send failed: {exc}")
                        self._running = False
                        break
                if not self._running:
                    break
                try:
                    data = sock.recv(4096)
                    if data:
                        self.output.emit(self.device_name, data.decode("utf-8", errors="ignore"))
                    else:
                        self.status.emit(self.device_name, "Console closed by remote host.")
                        break
                except socket.timeout:
                    continue
                except Exception as exc:
                    self.status.emit(self.device_name, f"Console error: {exc}")
                    break
        except Exception as exc:
            self.status.emit(self.device_name, f"Connection failed: {exc}")
        finally:
            try:
                if self._socket:
                    self._socket.close()
            except Exception:
                pass
            self.status.emit(self.device_name, "Disconnected")


class ProcessWorker(QThread):
    output = Signal(str)
    finished = Signal(int, str)

    def __init__(self, args: List[str], cwd: Path):
        super().__init__()
        self.args = args
        self.cwd = cwd

    def _run_once(self) -> tuple[int, str]:
        output_chunks: List[str] = []
        proc = subprocess.Popen(
            self.args,
            cwd=str(self.cwd),
            text=True,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            bufsize=1,
            close_fds=True,
        )
        if proc.stdout:
            for line in proc.stdout:
                output_chunks.append(line)
                self.output.emit(line)
            proc.stdout.close()
        return_code = proc.wait()
        return return_code, "".join(output_chunks)

    def run(self) -> None:
        try:
            return_code, output_text = self._run_once()
            if return_code != 0 and "Bad file descriptor" in output_text and "init_sys_streams" in output_text:
                self.output.emit("\n[warn] Readiness process hit a stale file-descriptor condition; retrying once with a clean subprocess context...\n")
                return_code, output_text = self._run_once()
            self.finished.emit(return_code, output_text)
        except Exception as exc:
            message = f"Failed to run command: {exc}"
            self.output.emit(message)
            self.finished.emit(1, message)




class LifecycleWorker(QThread):
    finished = Signal(bool, str, dict)

    def __init__(self, action: str, server: str, project_id: str, node_ids: List[str]):
        super().__init__()
        self.action = action
        self.server = server.rstrip("/")
        self.project_id = project_id
        self.node_ids = node_ids

    def api(self, method: str, path: str) -> Dict[str, Any]:
        url = self.server + path
        request = Request(url, method=method)
        request.add_header("Content-Type", "application/json")
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            return json.loads(body) if body.strip() else {}

    def run(self) -> None:
        try:
            details: Dict[str, Any] = {"action": self.action, "project_id": self.project_id, "nodes": {}}
            if not self.server or not self.project_id:
                self.finished.emit(False, "Missing GNS3 server or project ID in the loaded lab metadata/settings.", details)
                return
            if self.action == "status":
                project = self.api("GET", f"/v2/projects/{self.project_id}")
                details["project"] = project
                for node_id in self.node_ids:
                    try:
                        details["nodes"][node_id] = self.api("GET", f"/v2/projects/{self.project_id}/nodes/{node_id}")
                    except Exception as exc:
                        details["nodes"][node_id] = {"error": str(exc)}
                self.finished.emit(True, "Deployment status refreshed.", details)
                return
            if self.action == "delete":
                self.api("DELETE", f"/v2/projects/{self.project_id}")
                self.finished.emit(True, "GNS3 project deleted. Local generated lab files were kept.", details)
                return
            if self.action in {"start", "stop"}:
                endpoint = "start" if self.action == "start" else "stop"
                for node_id in self.node_ids:
                    try:
                        details["nodes"][node_id] = self.api("POST", f"/v2/projects/{self.project_id}/nodes/{node_id}/{endpoint}")
                    except Exception as exc:
                        details["nodes"][node_id] = {"error": str(exc)}
                self.finished.emit(True, f"Requested node {endpoint} for {len(self.node_ids)} node(s).", details)
                return
            if self.action == "reset":
                for node_id in self.node_ids:
                    try:
                        self.api("POST", f"/v2/projects/{self.project_id}/nodes/{node_id}/stop")
                    except Exception:
                        pass
                time.sleep(1.0)
                for node_id in self.node_ids:
                    try:
                        details["nodes"][node_id] = self.api("POST", f"/v2/projects/{self.project_id}/nodes/{node_id}/start")
                    except Exception as exc:
                        details["nodes"][node_id] = {"error": str(exc)}
                self.finished.emit(True, f"Requested reset for {len(self.node_ids)} node(s).", details)
                return
            self.finished.emit(False, f"Unsupported lifecycle action: {self.action}", details)
        except HTTPError as exc:
            self.finished.emit(False, f"GNS3 API returned HTTP {exc.code}: {exc.reason}", {"action": self.action})
        except URLError as exc:
            self.finished.emit(False, f"Could not reach GNS3 server: {exc}", {"action": self.action})
        except Exception as exc:
            self.finished.emit(False, f"Lifecycle action failed: {exc}", {"action": self.action})


class ProjectManagerWorker(QThread):
    finished = Signal(bool, str, dict)

    def __init__(self, action: str, server: str, project_ids: Optional[List[str]] = None):
        super().__init__()
        self.action = action
        self.server = server.rstrip("/")
        self.project_ids = project_ids or []

    def api(self, method: str, path: str) -> Any:
        url = self.server + path
        request = Request(url, method=method)
        request.add_header("Content-Type", "application/json")
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            return json.loads(body) if body.strip() else {}

    def project_nodes(self, project_id: str) -> List[Dict[str, Any]]:
        data = self.api("GET", f"/v2/projects/{project_id}/nodes")
        return data if isinstance(data, list) else []

    def run(self) -> None:
        details: Dict[str, Any] = {"action": self.action, "projects": [], "results": {}}
        try:
            if not self.server:
                self.finished.emit(False, "GNS3 server is not configured.", details)
                return

            if self.action == "list":
                projects = self.api("GET", "/v2/projects")
                if not isinstance(projects, list):
                    projects = []
                enriched: List[Dict[str, Any]] = []
                for project in projects:
                    if not isinstance(project, dict):
                        continue
                    project_id = str(project.get("project_id") or project.get("id") or "").strip()
                    nodes: List[Dict[str, Any]] = []
                    node_error = ""
                    if project_id:
                        try:
                            nodes = self.project_nodes(project_id)
                        except Exception as exc:
                            node_error = str(exc)
                    running = sum(1 for node in nodes if str(node.get("status", "")).lower() == "started")
                    enriched.append({**project, "project_id": project_id, "nodes": nodes, "node_count": len(nodes), "running_node_count": running, "node_error": node_error})
                details["projects"] = enriched
                self.finished.emit(True, f"Loaded {len(enriched)} project(s) from the GNS3 server.", details)
                return

            if self.action in {"start", "stop"}:
                endpoint = "start" if self.action == "start" else "stop"
                for project_id in self.project_ids:
                    result: Dict[str, Any] = {"nodes": {}, "ok": True}
                    try:
                        for node in self.project_nodes(project_id):
                            node_id = str(node.get("node_id") or node.get("id") or "")
                            name = str(node.get("name") or node.get("node_name") or node_id)
                            if not node_id:
                                continue
                            try:
                                result["nodes"][name] = self.api("POST", f"/v2/projects/{project_id}/nodes/{node_id}/{endpoint}")
                            except Exception as exc:
                                result["ok"] = False
                                result["nodes"][name] = {"error": str(exc)}
                    except Exception as exc:
                        result["ok"] = False
                        result["error"] = str(exc)
                    details["results"][project_id] = result
                self.finished.emit(True, f"Requested {endpoint} for {len(self.project_ids)} project(s).", details)
                return

            if self.action == "delete":
                for project_id in self.project_ids:
                    try:
                        details["results"][project_id] = self.api("DELETE", f"/v2/projects/{project_id}")
                    except Exception as exc:
                        details["results"][project_id] = {"error": str(exc)}
                self.finished.emit(True, f"Requested delete for {len(self.project_ids)} project(s).", details)
                return

            self.finished.emit(False, f"Unsupported project-manager action: {self.action}", details)
        except HTTPError as exc:
            self.finished.emit(False, f"GNS3 API returned HTTP {exc.code}: {exc.reason}", details)
        except URLError as exc:
            self.finished.emit(False, f"Could not reach GNS3 server: {exc}", details)
        except Exception as exc:
            self.finished.emit(False, f"Server project action failed: {exc}", details)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.catalog_store = CatalogStore()
        self.last_lab_dir: Optional[Path] = None
        self.workspace_metadata: Dict[str, Any] = {}
        self.worker: Optional[ProcessWorker] = None
        self.learning_mode = "Student"
        self.guided_steps: List[Tuple[str, str]] = []
        self.current_hint_index = 0
        self.current_guided_step_index = 0
        self.completed_guided_step_ids: set[str] = set()
        self.completed_guided_steps = 0
        self.console_workers: Dict[str, ConsoleWorker] = {}
        self.console_tabs: Dict[str, Dict[str, Any]] = {}
        self.lifecycle_worker: Optional[LifecycleWorker] = None
        self.project_worker: Optional[ProjectManagerWorker] = None
        # Keep QThread objects strongly referenced until they have fully stopped.
        # This prevents Qt from aborting if refresh/action/exit paths occur while
        # a worker is still running.
        self._active_threads: List[QThread] = []
        self._retired_console_workers: List[ConsoleWorker] = []
        self._closing = False
        self.server_project_rows: Dict[str, Dict[str, Any]] = {}
        self.practice_state: Dict[str, Any] = {}

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1760, 1120)
        self.setMinimumSize(1400, 900)
        self.apply_qt_theme(normalize_qt_theme(self.settings.get("theme", "darkly")))

        self._build_menus()
        self._build_ui()
        self.apply_dynamic_ui_scale()
        self.statusBar().showMessage("4.0.1 ready. NetOps Labs now organizes practice by study path and lab type.")
        self.refresh_filters()
        self.refresh_scenarios()

    def track_thread(self, worker: QThread, attr_name: Optional[str] = None) -> QThread:
        """Retain a QThread until it has finished and been cleaned up."""
        self._active_threads.append(worker)

        def cleanup() -> None:
            if worker in self._active_threads:
                self._active_threads.remove(worker)
            if attr_name and getattr(self, attr_name, None) is worker:
                setattr(self, attr_name, None)
            worker.deleteLater()

        worker.finished.connect(cleanup)
        if attr_name:
            setattr(self, attr_name, worker)
        return worker

    def stop_thread_safely(self, worker: Optional[QThread], timeout_ms: int = 5000) -> None:
        if not worker:
            return
        if isinstance(worker, ConsoleWorker):
            worker.stop()
        elif worker.isRunning():
            worker.requestInterruption()
        if worker.isRunning() and not worker.wait(timeout_ms):
            if worker not in self._active_threads:
                self._active_threads.append(worker)

    def cleanup_finished_threads(self) -> None:
        for worker in list(self._active_threads):
            if not worker.isRunning():
                self._active_threads.remove(worker)
        self._retired_console_workers = [w for w in self._retired_console_workers if w.isRunning()]

    def closeEvent(self, event) -> None:
        self._closing = True
        self.close_all_consoles()
        for worker in list(self._active_threads):
            self.stop_thread_safely(worker, timeout_ms=35000)
        self.cleanup_finished_threads()
        super().closeEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.apply_dynamic_ui_scale()
        if hasattr(self, "topology_scene") and hasattr(self, "topology_graphics") and not self.topology_scene.itemsBoundingRect().isNull():
            self.topology_graphics.fitInView(self.topology_scene.sceneRect(), Qt.KeepAspectRatio)

    def ui_scale_factor(self) -> float:
        width_factor = self.width() / 1760.0
        dpi_factor = max(0.9, min(1.35, self.logicalDpiX() / 96.0))
        scale = width_factor * (0.85 + 0.15 * dpi_factor)
        return max(0.9, min(1.55, scale))

    def apply_dynamic_ui_scale(self) -> None:
        scale = self.ui_scale_factor()
        base_pt = max(11.0, min(18.0, 13.0 * scale))
        mono_pt = max(11.0, min(17.0, 12.0 * scale))

        regular = QFont()
        regular.setPointSizeF(base_pt)
        monospace = QFont("Courier New")
        monospace.setStyleHint(QFont.Monospace)
        monospace.setPointSizeF(mono_pt)

        for attr in [
            "detail_text", "guided_view", "guided_hint_view", "doc_view", "topology_detail",
            "reports_view", "lifecycle_status", "project_detail", "practice_status", "practice_summary",
            "practice_notes", "output_text", "advanced_output"
        ]:
            widget = getattr(self, attr, None)
            if widget is not None:
                widget.setFont(regular)

        for attr in ["config_view", "compare_left", "compare_right"]:
            widget = getattr(self, attr, None)
            if widget is not None:
                widget.setFont(monospace)

        if hasattr(self, "scenario_table"):
            self.scenario_table.verticalHeader().setDefaultSectionSize(int(max(26, min(46, 30 * scale))))
        if hasattr(self, "topology_table"):
            self.topology_table.verticalHeader().setDefaultSectionSize(int(max(24, min(42, 28 * scale))))

    def _build_menus(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("File")
        open_action = QAction("Open Generated Lab Folder...", self)
        open_action.triggered.connect(self.browse_lab_folder)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        tools_menu = menu.addMenu("Tools")
        gen_action = QAction("Generate Selected Lab", self)
        gen_action.triggered.connect(self.run_generate)
        tools_menu.addAction(gen_action)
        preflight_action = QAction("Check Selected Lab Readiness", self)
        preflight_action.triggered.connect(self.run_preflight)
        tools_menu.addAction(preflight_action)
        tools_menu.addSeparator()
        audit_action = QAction("Run Offline Lab Audit", self)
        audit_action.triggered.connect(self.run_audit)
        tools_menu.addAction(audit_action)

        help_menu = menu.addMenu("Help")
        about = QAction("About", self)
        about.triggered.connect(self.show_about)
        help_menu.addAction(about)

    def _build_ui(self) -> None:
        root = QWidget()
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(190)
        side_layout = QVBoxLayout(sidebar)
        title = QLabel("NetOps\nLabs")
        title.setObjectName("PageTitle")
        subtitle = QLabel("4.0 Study Paths")
        subtitle.setObjectName("Muted")
        side_layout.addWidget(title)
        side_layout.addWidget(subtitle)
        side_layout.addSpacing(20)

        self.nav_buttons: List[QPushButton] = []
        for label, index in [
            ("Generate", 0),
            ("Lab Workspace", 1),
            ("GNS3 Projects", 2),
            ("Advanced Tools", 3),
            ("Settings", 4),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _checked=False, i=index: self.stack.setCurrentIndex(i))
            side_layout.addWidget(btn)
            self.nav_buttons.append(btn)
        side_layout.addStretch(1)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_generate_page())
        self.stack.addWidget(self._build_workspace_page())
        self.stack.addWidget(self._build_projects_page())
        self.stack.addWidget(self._build_advanced_page())
        self.stack.addWidget(self._build_settings_page())

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())

    def page_header(self, title: str, subtitle: str = "") -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 10, 12, 2)
        h = QLabel(title)
        h.setObjectName("PageTitle")
        layout.addWidget(h)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("Muted")
            layout.addWidget(s)
        return box

    def _build_generate_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.page_header("Generate Lab"))

        filters = QGroupBox("Scenario Filters")
        f_layout = QGridLayout(filters)
        f_layout.setHorizontalSpacing(10)
        f_layout.setVerticalSpacing(6)
        self.study_path_combo = QComboBox()
        self.deployment_combo = QComboBox(); self.deployment_combo.addItems(["Default", "Legacy", "All"])
        self.domain_combo = QComboBox(); self.topic_combo = QComboBox(); self.difficulty_combo = QComboBox()
        self.lab_type_combo = QComboBox(); self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search title, symptom, study path, topic, tag, exam alignment, or command...")
        filter_widgets = [
            ("Study Path", self.study_path_combo), ("Deployment", self.deployment_combo), ("Domain", self.domain_combo),
            ("Topic", self.topic_combo), ("Difficulty", self.difficulty_combo), ("Type", self.lab_type_combo),
        ]
        for idx, (label, widget) in enumerate(filter_widgets):
            row = 0 if idx < 4 else 1
            col = idx if idx < 4 else idx - 4
            widget.setMinimumWidth(190 if label == "Study Path" else (150 if label == "Deployment" else 135))
            f_layout.addWidget(QLabel(label), row * 2, col)
            f_layout.addWidget(widget, row * 2 + 1, col)
        self.search_box.setMinimumWidth(280)
        f_layout.addWidget(QLabel("Search"), 2, 2)
        f_layout.addWidget(self.search_box, 3, 2, 1, 2)
        f_layout.setColumnStretch(2, 1)
        f_layout.setColumnStretch(3, 1)
        layout.addWidget(filters)

        for combo in [self.study_path_combo, self.deployment_combo, self.domain_combo, self.topic_combo, self.difficulty_combo, self.lab_type_combo]:
            combo.currentTextChanged.connect(self.on_filter_changed)
        self.search_box.textChanged.connect(self.refresh_scenarios)

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget(); left_layout = QVBoxLayout(left)
        self.scenario_table = QTableWidget(0, 7)
        self.scenario_table.setHorizontalHeaderLabels(["Title", "Study Path", "Domain", "Topic", "Difficulty", "Type", "Backend ID"])
        self.scenario_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.scenario_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.scenario_table.itemSelectionChanged.connect(self.show_selected_scenario)
        left_layout.addWidget(self.scenario_table)
        splitter.addWidget(left)

        right = QWidget(); right.setMinimumWidth(560); right.setMaximumWidth(760)
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(6)
        right_layout.setContentsMargins(6, 0, 6, 0)

        details_box = QGroupBox("Scenario Details")
        details_layout = QVBoxLayout(details_box)
        details_layout.setContentsMargins(8, 8, 8, 8)
        self.detail_text = configure_readable_text_edit(QTextEdit()); self.detail_text.setReadOnly(True)
        self.detail_text.setMinimumHeight(380)
        self.detail_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.detail_text.document().setDocumentMargin(10)
        self.detail_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        details_layout.addWidget(self.detail_text, 1)
        right_layout.addWidget(details_box, 5)

        gen_opts = QGroupBox("Generation Options")
        gen_form = QGridLayout(gen_opts)
        gen_form.setContentsMargins(8, 6, 8, 6)
        gen_form.setHorizontalSpacing(8)
        gen_form.setVerticalSpacing(4)
        self.project_name = QLineEdit(); self.project_name.setPlaceholderText("Optional project name")
        self.project_name.setMinimumHeight(32)
        self.project_name.setMaximumWidth(300)
        self.push_config_check = QCheckBox("Push Cisco configs")
        self.push_config_check.setChecked(bool(self.settings.get("push_config", True)))
        self.push_endpoints_check = QCheckBox("Push endpoints")
        self.push_endpoints_check.setChecked(bool(self.settings.get("push_endpoints", True)))
        self.verify_check = QCheckBox("Collect verification")
        self.verify_check.setChecked(bool(self.settings.get("verify", False)))
        self.start_nodes_check = QCheckBox("Start nodes")
        self.start_nodes_check.setChecked(bool(self.settings.get("start_nodes", True)))
        self.host_type_combo = QComboBox(); self.host_type_combo.addItems(["alpine", "rhel9", "vpcs"]); self.host_type_combo.setCurrentText(str(self.settings.get("host_type", "alpine")))
        self.host_type_combo.setMinimumHeight(32)
        self.host_type_combo.setMinimumWidth(150)
        self.host_type_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        gen_form.addWidget(QLabel("Project"), 0, 0)
        gen_form.addWidget(self.project_name, 0, 1, 1, 2)
        gen_form.addWidget(QLabel("Host Type"), 0, 3)
        gen_form.addWidget(self.host_type_combo, 0, 4)
        gen_form.addWidget(self.start_nodes_check, 1, 0, 1, 2)
        gen_form.addWidget(self.push_config_check, 1, 2, 1, 2)
        gen_form.addWidget(self.push_endpoints_check, 2, 0, 1, 2)
        gen_form.addWidget(self.verify_check, 2, 2, 1, 2)
        gen_form.setColumnStretch(1, 1)
        gen_form.setColumnStretch(2, 1)
        gen_form.setColumnStretch(4, 0)
        gen_opts.setMaximumHeight(125)
        right_layout.addWidget(gen_opts, 0)

        action_grid = QGridLayout()
        action_grid.setHorizontalSpacing(8)
        action_grid.setVerticalSpacing(6)
        self.preflight_button = QPushButton("Check Readiness")
        self.generate_button = QPushButton("Generate Lab")
        self.open_workspace_button = QPushButton("Open Lab Workspace")
        self.open_output_button = QPushButton("Open Output Folder")
        self.clear_output_button = QPushButton("Clear Output")
        for btn in [self.preflight_button, self.generate_button, self.open_workspace_button, self.open_output_button, self.clear_output_button]:
            btn.setMinimumHeight(34)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.generate_button.setObjectName("PrimaryButton")
        self.preflight_button.clicked.connect(self.run_preflight)
        self.generate_button.clicked.connect(self.run_generate)
        self.open_workspace_button.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.open_output_button.clicked.connect(lambda: self.open_path(self.output_dir()))
        action_grid.addWidget(self.preflight_button, 0, 0)
        action_grid.addWidget(self.generate_button, 0, 1)
        action_grid.addWidget(self.open_workspace_button, 1, 0)
        action_grid.addWidget(self.open_output_button, 1, 1)
        action_grid.addWidget(self.clear_output_button, 2, 0, 1, 2)
        right_layout.addLayout(action_grid, 0)

        self.output_text = QPlainTextEdit(); self.output_text.setReadOnly(True)
        self.output_text.setWordWrapMode(QTextOption.NoWrap)
        self.clear_output_button.clicked.connect(self.output_text.clear)
        output_label = QLabel("Command Output")
        right_layout.addWidget(output_label)
        self.output_text.setMinimumHeight(100)
        right_layout.addWidget(self.output_text, 1)

        splitter.addWidget(right)
        splitter.setSizes([1120, 600])
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)
        return page

    def _build_workspace_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.page_header("Lab Workspace"))

        top_row = QHBoxLayout()
        self.workspace_title = QLabel("No generated lab loaded.")
        self.workspace_title.setObjectName("Muted")
        self.workspace_title.setWordWrap(False)
        self.workspace_title.setMinimumHeight(28)
        browse_btn = QPushButton("Browse Lab Folder")
        refresh_btn = QPushButton("Refresh")
        open_btn = QPushButton("Open Folder")
        browse_btn.clicked.connect(self.browse_lab_folder)
        refresh_btn.clicked.connect(self.refresh_workspace)
        open_btn.clicked.connect(self.open_lab_folder)
        top_row.addWidget(self.workspace_title, 1)
        top_row.addWidget(browse_btn)
        top_row.addWidget(refresh_btn)
        top_row.addWidget(open_btn)
        layout.addLayout(top_row)

        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.addTab(self._build_practice_workspace(), "Practice")
        self.workspace_tabs.addTab(self._build_guided_workspace(), "Guided Learning")
        self.workspace_tabs.addTab(self._build_docs_workspace(), "Documents")
        self.workspace_tabs.addTab(self._build_config_workspace(), "Configs")
        self.workspace_tabs.addTab(self._build_config_compare_workspace(), "Config Compare")
        self.workspace_tabs.addTab(self._build_topology_workspace(), "Topology")
        self.workspace_tabs.addTab(self._build_console_workspace(), "Consoles")
        self.workspace_tabs.addTab(self._build_lifecycle_workspace(), "Lifecycle")
        self.workspace_tabs.addTab(self._build_reports_workspace(), "Reports")
        layout.addWidget(self.workspace_tabs, 1)
        return page

    def _build_practice_workspace(self) -> QWidget:
        """Build the practice-session control panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        top = QHBoxLayout()
        self.start_practice_button = QPushButton("Start Practice")
        self.end_practice_button = QPushButton("End Practice")
        self.open_guided_button = QPushButton("Guided Practice")
        self.open_topology_button = QPushButton("Topology")
        self.open_console_button = QPushButton("Consoles")
        self.open_lifecycle_button = QPushButton("Lifecycle")
        self.start_practice_button.clicked.connect(self.start_practice_session)
        self.end_practice_button.clicked.connect(self.end_practice_session)
        self.open_guided_button.clicked.connect(lambda: self.select_workspace_tab("Guided Learning"))
        self.open_topology_button.clicked.connect(lambda: self.select_workspace_tab("Topology"))
        self.open_console_button.clicked.connect(lambda: self.select_workspace_tab("Consoles"))
        self.open_lifecycle_button.clicked.connect(lambda: self.select_workspace_tab("Lifecycle"))
        for button in (self.start_practice_button, self.end_practice_button, self.open_guided_button, self.open_topology_button, self.open_console_button, self.open_lifecycle_button):
            button.setMinimumHeight(34)
            top.addWidget(button)
        top.addStretch(1)
        layout.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.practice_status = configure_readable_text_edit(QTextEdit())
        self.practice_status.setReadOnly(True)
        self.practice_status.setMarkdown("# Practice Session\n\nLoad or generate a lab to start a practice session.")
        left_layout.addWidget(self.practice_status, 1)

        self.practice_summary = configure_readable_text_edit(QTextEdit())
        self.practice_summary.setReadOnly(True)
        self.practice_summary.setMaximumHeight(260)
        self.practice_summary.setMarkdown("# Summary\n\nNo practice summary has been created yet.")
        left_layout.addWidget(self.practice_summary)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        notes_row = QHBoxLayout()
        notes_row.addWidget(QLabel("Student Notes"))
        save_notes_btn = QPushButton("Save Notes")
        save_notes_btn.clicked.connect(self.save_practice_notes)
        notes_row.addStretch(1)
        notes_row.addWidget(save_notes_btn)
        right_layout.addLayout(notes_row)
        self.practice_notes = QPlainTextEdit()
        self.practice_notes.setPlaceholderText("Record observations, commands tried, likely causes, and verification notes here.")
        right_layout.addWidget(self.practice_notes, 1)
        splitter.addWidget(right)
        splitter.setSizes([700, 700])
        layout.addWidget(splitter, 1)
        return widget

    def _build_guided_workspace(self) -> QWidget:
        """Build the guided-practice panel around explicit, visible steps."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        controls = QGridLayout()
        controls.setHorizontalSpacing(8)
        controls.setVerticalSpacing(6)
        self.learning_mode_combo = QComboBox()
        self.learning_mode_combo.addItems(["Student", "Explorer", "Instructor"])
        self.learning_mode_combo.setCurrentText(self.learning_mode)
        self.learning_mode_combo.setMinimumWidth(180)
        self.learning_mode_combo.setMinimumHeight(38)
        self.learning_mode_combo.view().setMinimumWidth(180)
        self.learning_mode_combo.currentTextChanged.connect(self.on_learning_mode_changed)

        self.prev_step_button = QPushButton("Previous Step")
        self.next_step_button = QPushButton("Next Step")
        self.reveal_hint_button = QPushButton("Reveal Hint")
        self.mark_step_button = QPushButton("Mark Step Complete")
        self.copy_commands_button = QPushButton("Copy Suggested Commands")
        self.open_answer_key_button = QPushButton("Open Answer Key")
        self.guided_open_console_button = QPushButton("Open Consoles")
        self.guided_open_topology_button = QPushButton("Open Topology")
        self.prev_step_button.clicked.connect(self.previous_guided_step)
        self.next_step_button.clicked.connect(self.next_guided_step)
        self.reveal_hint_button.clicked.connect(self.reveal_next_hint)
        self.mark_step_button.clicked.connect(self.mark_guided_step_complete)
        self.copy_commands_button.clicked.connect(self.copy_current_step_commands)
        self.open_answer_key_button.clicked.connect(self.open_answer_key_from_guided)
        self.guided_open_console_button.clicked.connect(lambda: self.select_workspace_tab("Consoles"))
        self.guided_open_topology_button.clicked.connect(lambda: self.select_workspace_tab("Topology"))

        controls.addWidget(QLabel("Learning Mode:"), 0, 0)
        controls.addWidget(self.learning_mode_combo, 0, 1)
        buttons = [
            self.prev_step_button,
            self.next_step_button,
            self.reveal_hint_button,
            self.mark_step_button,
            self.copy_commands_button,
            self.guided_open_console_button,
            self.guided_open_topology_button,
            self.open_answer_key_button,
        ]
        for idx, button in enumerate(buttons):
            button.setMinimumHeight(38)
            button.setMinimumWidth(150 if button is not self.copy_commands_button else 210)
            button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
            row = 0 if idx < 4 else 1
            # Keep the second row aligned with the first button column instead
            # of starting under the Learning Mode label/dropdown.
            col = idx + 2 if idx < 4 else idx - 2
            controls.addWidget(button, row, col)
        controls.setColumnStretch(5, 1)
        layout.addLayout(controls)

        splitter = QSplitter(Qt.Horizontal)
        self.guided_step_list = QListWidget()
        self.guided_step_list.setMinimumWidth(280)
        self.guided_step_list.setMaximumWidth(420)
        self.guided_step_list.currentRowChanged.connect(self.on_guided_step_selected)
        splitter.addWidget(self.guided_step_list)

        right = QSplitter(Qt.Vertical)
        self.guided_view = configure_readable_text_edit(QTextEdit())
        self.guided_view.setReadOnly(True)
        self.guided_view.setMarkdown(
            "# Guided Practice\n\n"
            "Generate or load a lab to begin. The guided practice view presents explicit steps, "
            "suggested commands, revealable hints, and visible completion state."
        )
        right.addWidget(self.guided_view)

        self.guided_hint_view = configure_readable_text_edit(QTextEdit())
        self.guided_hint_view.setReadOnly(True)
        self.guided_hint_view.setMaximumHeight(220)
        self.guided_hint_view.setMarkdown("# Hints\n\nHints appear here as you reveal them for the current step.")
        right.addWidget(self.guided_hint_view)
        right.setSizes([620, 180])
        splitter.addWidget(right)
        splitter.setSizes([320, 1000])
        layout.addWidget(splitter, 1)
        return widget

    def _build_docs_workspace(self) -> QWidget:
        widget = QWidget(); layout = QHBoxLayout(widget)
        self.doc_list = QListWidget(); self.doc_list.setMaximumWidth(300)
        self.doc_view = configure_readable_text_edit(QTextEdit()); self.doc_view.setReadOnly(True)
        self.doc_list.currentRowChanged.connect(self.load_selected_document)
        layout.addWidget(self.doc_list)
        layout.addWidget(self.doc_view, 1)
        return widget

    def _build_config_workspace(self) -> QWidget:
        widget = QWidget(); layout = QVBoxLayout(widget)
        controls = QHBoxLayout()
        self.config_set_combo = QComboBox(); self.device_combo = QComboBox()
        controls.addWidget(QLabel("Config Set:")); controls.addWidget(self.config_set_combo)
        controls.addWidget(QLabel("Device:")); controls.addWidget(self.device_combo)
        controls.addStretch(1)
        self.config_set_combo.currentTextChanged.connect(self.populate_devices)
        self.device_combo.currentTextChanged.connect(self.load_selected_config)
        layout.addLayout(controls)
        self.config_view = QPlainTextEdit(); self.config_view.setReadOnly(True)
        font = QFont("Courier New"); font.setStyleHint(QFont.Monospace); self.config_view.setFont(font)
        layout.addWidget(self.config_view, 1)
        return widget

    def _build_config_compare_workspace(self) -> QWidget:
        widget = QWidget(); layout = QVBoxLayout(widget)
        controls = QHBoxLayout()
        self.compare_device_combo = QComboBox()
        refresh_btn = QPushButton("Refresh Devices")
        refresh_btn.clicked.connect(self.populate_compare_devices)
        controls.addWidget(QLabel("Device:")); controls.addWidget(self.compare_device_combo)
        controls.addWidget(refresh_btn); controls.addStretch(1)
        layout.addLayout(controls)
        splitter = QSplitter(Qt.Horizontal)
        self.compare_left = QPlainTextEdit(); self.compare_left.setReadOnly(True)
        self.compare_right = QPlainTextEdit(); self.compare_right.setReadOnly(True)
        self.compare_diff = configure_readable_text_edit(QTextEdit()); self.compare_diff.setReadOnly(True)
        font = QFont("Courier New"); font.setStyleHint(QFont.Monospace)
        self.compare_left.setFont(font); self.compare_right.setFont(font)
        splitter.addWidget(self.compare_left); splitter.addWidget(self.compare_right)
        splitter.setSizes([800,800])
        layout.addWidget(splitter, 1)
        layout.addWidget(QLabel("Highlighted Diff"))
        layout.addWidget(self.compare_diff, 1)
        self.compare_device_combo.currentTextChanged.connect(self.load_compare_device)
        return widget

    def _build_topology_workspace(self) -> QWidget:
        widget = QWidget(); layout = QVBoxLayout(widget)
        splitter = QSplitter(Qt.Vertical)

        self.topology_scene = QGraphicsScene()
        self.topology_graphics = QGraphicsView(self.topology_scene)
        self.topology_graphics.setMinimumHeight(420)
        self.topology_graphics.setBackgroundBrush(QBrush(QColor("#8b949e")))
        splitter.addWidget(self.topology_graphics)

        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        self.topology_table = QTableWidget(0, 6)
        self.topology_table.setHorizontalHeaderLabels(["Device A", "Interface A", "Device B", "Interface B", "GNS3 A", "GNS3 B"])
        self.topology_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.topology_table.currentCellChanged.connect(self.update_topology_detail)
        bottom_layout.addWidget(self.topology_table, 2)

        self.topology_detail = configure_readable_text_edit(QTextEdit())
        self.topology_detail.setReadOnly(True)
        self.topology_detail.setMarkdown("# Topology Details\n\nLoad a generated lab to inspect devices and links.")
        bottom_layout.addWidget(self.topology_detail, 1)

        splitter.addWidget(bottom)
        splitter.setSizes([460, 280])
        layout.addWidget(splitter, 1)
        return widget

    def _build_console_workspace(self) -> QWidget:
        widget = QWidget(); layout = QVBoxLayout(widget)
        controls = QHBoxLayout()
        self.console_device_list = QListWidget()
        self.console_device_list.setMaximumWidth(280)
        self.console_device_list.currentItemChanged.connect(self.console_device_selected)

        left = QVBoxLayout()
        left.addWidget(QLabel("Available Console Endpoints"))
        left.addWidget(self.console_device_list, 1)
        left_btn_row = QHBoxLayout()
        self.console_open_btn = QPushButton("Open Console")
        self.console_reconnect_btn = QPushButton("Reconnect")
        self.console_close_btn = QPushButton("Close Console")
        self.console_open_btn.clicked.connect(self.open_selected_console)
        self.console_reconnect_btn.clicked.connect(self.reconnect_selected_console)
        self.console_close_btn.clicked.connect(self.close_selected_console)
        left_btn_row.addWidget(self.console_open_btn)
        left_btn_row.addWidget(self.console_reconnect_btn)
        left_btn_row.addWidget(self.console_close_btn)
        left.addLayout(left_btn_row)
        left_widget = QWidget(); left_widget.setLayout(left)

        right_split = QSplitter(Qt.Vertical)
        self.console_tab_widget = QTabWidget()
        self.console_tab_widget.setTabsClosable(True)
        self.console_tab_widget.tabCloseRequested.connect(self.close_console_tab_index)
        right_split.addWidget(self.console_tab_widget)

        send_panel = QWidget()
        send_layout = QVBoxLayout(send_panel)
        self.console_status = QLabel("No console connected.")
        self.console_status.setObjectName("Muted")
        send_layout.addWidget(self.console_status)
        input_row = QHBoxLayout()
        self.console_input = QLineEdit()
        self.console_input.setPlaceholderText("Type a command for the active console tab and press Send")
        send_btn = QPushButton("Send")
        send_enter_btn = QPushButton("Send + Enter")
        ctrl_l_btn = QPushButton("Send Ctrl+L")
        send_btn.clicked.connect(lambda: self.send_console_text(add_newline=False))
        send_enter_btn.clicked.connect(lambda: self.send_console_text(add_newline=True))
        ctrl_l_btn.clicked.connect(self.send_console_ctrl_l)
        self.console_input.returnPressed.connect(lambda: self.send_console_text(add_newline=True))
        input_row.addWidget(self.console_input, 1)
        input_row.addWidget(send_btn)
        input_row.addWidget(send_enter_btn)
        input_row.addWidget(ctrl_l_btn)
        send_layout.addLayout(input_row)
        right_split.addWidget(send_panel)
        right_split.setSizes([720, 120])

        controls.addWidget(left_widget, 1)
        controls.addWidget(right_split, 3)
        layout.addLayout(controls, 1)
        return widget

    def _build_lifecycle_workspace(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Manage the deployed GNS3 project for the currently loaded lab. Local lab files are preserved unless you delete them manually."))

        actions = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Deployment Status")
        start_btn = QPushButton("Start Nodes")
        stop_btn = QPushButton("Stop Nodes")
        reset_btn = QPushButton("Reset Nodes")
        delete_btn = QPushButton("Delete GNS3 Project")
        delete_btn.setObjectName("DangerButton")
        refresh_btn.clicked.connect(lambda: self.run_lifecycle_action("status"))
        start_btn.clicked.connect(lambda: self.run_lifecycle_action("start"))
        stop_btn.clicked.connect(lambda: self.run_lifecycle_action("stop"))
        reset_btn.clicked.connect(lambda: self.run_lifecycle_action("reset"))
        delete_btn.clicked.connect(self.confirm_delete_gns3_project)
        for button in (refresh_btn, start_btn, stop_btn, reset_btn, delete_btn):
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.lifecycle_status = configure_readable_text_edit(QTextEdit())
        self.lifecycle_status.setReadOnly(True)
        self.lifecycle_status.setMarkdown("# Deployment Lifecycle\n\nLoad or generate a deployed lab to manage its GNS3 project lifecycle.")
        layout.addWidget(self.lifecycle_status, 1)
        return widget

    def _build_reports_workspace(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        controls = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Reports")
        refresh_btn.clicked.connect(self.populate_reports)
        open_validation_btn = QPushButton("Open Validation Report")
        open_validation_btn.clicked.connect(lambda: self.open_path((self.last_lab_dir / "validation_report.md") if self.last_lab_dir else self.output_dir()))
        controls.addWidget(refresh_btn)
        controls.addWidget(open_validation_btn)
        controls.addStretch(1)
        layout.addLayout(controls)
        self.reports_view = configure_readable_text_edit(QTextEdit())
        self.reports_view.setReadOnly(True)
        self.reports_view.setMarkdown("# Reports\n\nLoad a generated lab to view its generation and validation reports.")
        layout.addWidget(self.reports_view, 1)
        return widget

    def _build_projects_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.page_header("GNS3 Projects", "Discover, connect to, stop, and delete projects already present on the configured GNS3 server."))

        controls = QGridLayout()
        controls.setHorizontalSpacing(8)
        controls.setVerticalSpacing(6)
        self.project_server_box = QLineEdit(str(self.settings.get("gns3_server", "")))
        self.project_server_box.setPlaceholderText("http://gns3-server:3080")
        self.project_filter_combo = QComboBox()
        self.project_filter_combo.addItems(["All server projects", "Generated by this app", "Running projects only", "Stopped projects only"])
        self.project_filter_combo.setMinimumContentsLength(20)
        self.project_filter_combo.setMinimumWidth(225)
        self.project_filter_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.project_filter_combo.currentTextChanged.connect(self.apply_project_filter)
        refresh_btn = QPushButton("Refresh Server Projects")
        connect_btn = QPushButton("Connect/Open Selected")
        start_btn = QPushButton("Start Selected")
        stop_btn = QPushButton("Stop Selected")
        delete_btn = QPushButton("Delete Selected")
        delete_generated_btn = QPushButton("Delete Generated Projects")
        delete_btn.setObjectName("DangerButton")
        delete_generated_btn.setObjectName("DangerButton")
        refresh_btn.clicked.connect(self.refresh_server_projects)
        connect_btn.clicked.connect(self.connect_selected_server_project)
        start_btn.clicked.connect(lambda: self.run_project_manager_action("start"))
        stop_btn.clicked.connect(lambda: self.run_project_manager_action("stop"))
        delete_btn.clicked.connect(self.confirm_delete_selected_projects)
        delete_generated_btn.clicked.connect(self.confirm_delete_generated_projects)
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(6)
        filter_layout.addWidget(QLabel("Show:"))
        filter_layout.addWidget(self.project_filter_combo)
        filter_layout.addStretch(1)

        controls.addWidget(QLabel("GNS3 server:"), 0, 0)
        controls.addWidget(self.project_server_box, 0, 1, 1, 3)
        controls.addWidget(filter_widget, 0, 4, 1, 2)
        controls.addWidget(refresh_btn, 1, 0)
        controls.addWidget(connect_btn, 1, 1)
        controls.addWidget(start_btn, 1, 2)
        controls.addWidget(stop_btn, 1, 3)
        controls.addWidget(delete_btn, 1, 4)
        controls.addWidget(delete_generated_btn, 1, 5)
        controls.setColumnStretch(1, 2)
        controls.setColumnStretch(5, 1)
        layout.addLayout(controls)

        splitter = QSplitter(Qt.Vertical)
        self.projects_table = QTableWidget(0, 7)
        self.projects_table.setHorizontalHeaderLabels(["Project Name", "Status", "Nodes", "Running", "Generated", "Project ID", "Last Updated"])
        self.projects_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.projects_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.projects_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.projects_table.currentCellChanged.connect(self.update_project_detail)
        splitter.addWidget(self.projects_table)

        self.project_detail = configure_readable_text_edit(QTextEdit())
        self.project_detail.setReadOnly(True)
        self.project_detail.setMaximumHeight(280)
        self.project_detail.setMarkdown("# Server Projects\n\nClick **Refresh Server Projects** to load projects from the configured GNS3 server.")
        splitter.addWidget(self.project_detail)
        splitter.setSizes([680, 220])
        layout.addWidget(splitter, 1)
        return page

    def _build_advanced_page(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        layout.addWidget(self.page_header("Advanced Tools", "Power-user workflows that should remain available outside the guided lab path."))

        blank = QGroupBox("Generate Blank Topology")
        form = QFormLayout(blank)
        self.blank_topology_combo = QComboBox(); self.blank_topology_combo.addItems(self.catalog_store.topologies_list())
        self.blank_name = QLineEdit(); self.blank_name.setPlaceholderText("Optional project name")
        self.blank_no_auto = QCheckBox("Generate local/project scaffold only; do not start or push configs")
        self.blank_no_auto.setChecked(True)
        form.addRow("Topology", self.blank_topology_combo)
        form.addRow("Project Name", self.blank_name)
        form.addRow("Mode", self.blank_no_auto)
        blank_button = QPushButton("Generate Blank Topology")
        blank_button.clicked.connect(self.run_blank_topology)
        form.addRow(blank_button)
        layout.addWidget(blank)

        tools = QGroupBox("Validation")
        tv = QVBoxLayout(tools)
        audit_btn = QPushButton("Run Offline Lab Audit")
        audit_btn.clicked.connect(self.run_audit)
        tv.addWidget(audit_btn)
        layout.addWidget(tools)
        self.advanced_output = QPlainTextEdit(); self.advanced_output.setReadOnly(True)
        layout.addWidget(QLabel("Tool Output"))
        layout.addWidget(self.advanced_output, 1)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        layout.addWidget(self.page_header("Settings", "Configure Qt appearance, GNS3 connection defaults, generation behavior, and endpoint credentials."))

        box = QGroupBox("Application Settings")
        form = QFormLayout(box)
        self.settings_theme = QComboBox(); self.settings_theme.addItems(qt_theme_names()); self.settings_theme.setCurrentText(normalize_qt_theme(self.settings.get("theme", "darkly")))
        self.settings_server = QLineEdit(str(self.settings.get("gns3_server", "")))
        default_output = str(DEFAULT_OUTPUT_DIR if is_frozen_app() else "generated_labs")
        self.settings_output = QLineEdit(str(self.settings.get("output_dir", default_output)))
        out_browse = QPushButton("Browse")
        out_browse.clicked.connect(self.browse_output_dir)
        out_row = QWidget(); out_l = QHBoxLayout(out_row); out_l.setContentsMargins(0,0,0,0); out_l.addWidget(self.settings_output, 1); out_l.addWidget(out_browse)
        self.settings_host_type = QComboBox(); self.settings_host_type.addItems(["alpine", "rhel9", "vpcs"]); self.settings_host_type.setCurrentText(str(self.settings.get("host_type", "alpine")))
        self.settings_push_config = QCheckBox("Push Cisco configs by default"); self.settings_push_config.setChecked(bool(self.settings.get("push_config", True)))
        self.settings_push_endpoints = QCheckBox("Push supported endpoint configs by default"); self.settings_push_endpoints.setChecked(bool(self.settings.get("push_endpoints", True)))
        self.settings_verify = QCheckBox("Collect verification output by default"); self.settings_verify.setChecked(bool(self.settings.get("verify", False)))
        self.settings_linux_user = QLineEdit(str(self.settings.get("linux_endpoint_username", "root")))
        self.settings_linux_password = QLineEdit(str(self.settings.get("linux_endpoint_password", "")))
        self.settings_linux_password.setEchoMode(QLineEdit.Password)
        self.settings_endpoint_timeout = QSpinBox(); self.settings_endpoint_timeout.setRange(10, 1800); self.settings_endpoint_timeout.setValue(int(self.settings.get("endpoint_timeout", 180)))
        self.settings_console_timeout = QSpinBox(); self.settings_console_timeout.setRange(30, 3600); self.settings_console_timeout.setValue(int(self.settings.get("console_timeout", 420)))

        form.addRow("Qt Theme", self.settings_theme)
        form.addRow("GNS3 Server", self.settings_server)
        form.addRow("Output Directory", out_row)
        form.addRow("Host Type", self.settings_host_type)
        form.addRow("Cisco Configs", self.settings_push_config)
        form.addRow("Endpoints", self.settings_push_endpoints)
        form.addRow("Verification", self.settings_verify)
        form.addRow("Linux Endpoint User", self.settings_linux_user)
        form.addRow("Linux Endpoint Password", self.settings_linux_password)
        form.addRow("Endpoint Timeout", self.settings_endpoint_timeout)
        form.addRow("Console Timeout", self.settings_console_timeout)
        symbol_button = QPushButton("Choose Topology Symbols…")
        symbol_button.clicked.connect(self.open_symbol_mapping_dialog)
        form.addRow("Topology Icons", symbol_button)
        layout.addWidget(box)

        actions = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        apply_theme_btn = QPushButton("Apply Theme")
        reload_btn = QPushButton("Reload Catalog")
        save_btn.clicked.connect(self.save_settings)
        apply_theme_btn.clicked.connect(lambda: self.apply_qt_theme(self.settings_theme.currentText()))
        reload_btn.clicked.connect(self.reload_catalog)
        actions.addWidget(save_btn); actions.addWidget(apply_theme_btn); actions.addWidget(reload_btn); actions.addStretch(1)
        layout.addLayout(actions)

        notes = configure_readable_text_edit(QTextEdit()); notes.setReadOnly(True); notes.setMarkdown(f"""
# NetOps Labs {APP_VERSION}

Version: `{APP_VERSION}`

NetOps Labs {APP_VERSION} is a stabilization patch for generation visibility, GNS3 API efficiency, and release workflow guardrails.

- The application now presents itself as NetOps Labs.
- Study Path is the primary catalog filter.
- Exam alignment is preserved as secondary metadata.
- Lab Type remains a first-class filter for build, troubleshoot, verify, mixed, hardening, and explore workflows.
- Lab generation output now streams while the generator is running.
- Existing 3.x generated labs and workspace metadata remain compatible.
- The GNS3 Projects page continues to manage existing server projects and stale generated projects.
""")
        layout.addWidget(notes, 1)
        return page

    def current_filters(self) -> Dict[str, str]:
        return {
            "study_path": self.study_path_combo.currentText() or "All",
            "deployment": self.deployment_combo.currentText() or "Default",
            "domain": self.domain_combo.currentText() or "All",
            "topic": self.topic_combo.currentText() or "All",
            "difficulty": self.difficulty_combo.currentText() or "All",
            "lab_type": self.lab_type_combo.currentText() or "All",
            "tag": "All",
            "search": self.search_box.text(),
        }

    def set_combo_values(self, combo: QComboBox, values: List[str], keep: Optional[str] = None) -> None:
        current = keep if keep is not None else combo.currentText()
        combo.blockSignals(True)
        combo.clear(); combo.addItem("All"); combo.addItems(values)
        if current and current in [combo.itemText(i) for i in range(combo.count())]:
            combo.setCurrentText(current)
        else:
            combo.setCurrentText("All")
        combo.blockSignals(False)

    def refresh_filters(self) -> None:
        filters = self.current_filters() if hasattr(self, "domain_combo") else {}
        self.set_combo_values(self.study_path_combo, self.catalog_store.all_study_paths(), filters.get("study_path", "All"))
        filters = self.current_filters()
        self.set_combo_values(self.domain_combo, self.catalog_store.option_values("domain", filters), filters.get("domain", "All"))
        filters = self.current_filters()
        self.set_combo_values(self.topic_combo, self.catalog_store.option_values("topic", filters), filters.get("topic", "All"))
        filters = self.current_filters()
        self.set_combo_values(self.difficulty_combo, self.catalog_store.option_values("difficulty", filters), filters.get("difficulty", "All"))
        filters = self.current_filters()
        self.set_combo_values(self.lab_type_combo, self.catalog_store.option_values("lab_type", filters), filters.get("lab_type", "All"))

    def on_filter_changed(self, _text: str) -> None:
        self.refresh_filters()
        self.refresh_scenarios()

    def refresh_scenarios(self) -> None:
        rows = self.catalog_store.filtered_scenarios(**self.current_filters())
        self.scenario_table.setRowCount(len(rows))
        for row_idx, (sid, scenario) in enumerate(rows):
            values = [
                str(scenario.get("title", "")),
                ", ".join(scenario_study_path_values(scenario)),
                str(scenario.get("domain", "")),
                str(scenario.get("topic", "")),
                str(scenario.get("difficulty", "")),
                str(scenario.get("lab_type", "")),
                sid,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.UserRole, sid)
                self.scenario_table.setItem(row_idx, col, item)
        self.scenario_table.resizeColumnsToContents()
        self.statusBar().showMessage(f"{len(rows)} scenarios shown")
        if rows:
            self.scenario_table.selectRow(0)
        else:
            self.detail_text.clear()

    def selected_scenario_id(self) -> Optional[str]:
        row = self.scenario_table.currentRow()
        if row < 0:
            return None
        item = self.scenario_table.item(row, 0)
        sid = item.data(Qt.UserRole) if item else None
        return str(sid) if sid else None

    def show_selected_scenario(self) -> None:
        sid = self.selected_scenario_id()
        if not sid:
            self.detail_text.clear(); return
        scenario = self.catalog_store.scenarios.get(sid, {})
        faults = scenario.get("faults", []) or []
        fault_lines = "\n".join(f"- {f.get('device', 'device')}: {f.get('fault', '')}" for f in faults) or "- Fault details are not listed."
        verification = "\n".join(f"- `{cmd}`" for cmd in scenario.get("verification", []) or []) or "- No verification commands listed."
        hints = "\n".join(f"- {h}" for h in scenario.get("hints", []) or []) or "- No hints listed."
        self.detail_text.setMarkdown(f"""
# {scenario.get('title', sid)}

**Study Path:** {", ".join(scenario_study_path_values(scenario))}  
**Exam Alignment:** {", ".join(scenario_exam_values(scenario)) or "None"}  
**Domain:** {scenario.get('domain', '')}  
**Topic:** {scenario.get('topic', '')}  
**Difficulty:** {scenario.get('difficulty', '')}  
**Lab Type:** {scenario.get('lab_type', '')}  
**Topology:** `{scenario.get('topology', '')}`  
**Deployment:** {'Legacy' if scenario.get('legacy_variant') else 'Default'}  
**Backend ID:** `{sid}`

## Symptom

{scenario.get('symptom', 'No symptom text available.')}

## Fault Summary

{fault_lines}

## Verification Commands

{verification}

## Initial Hints

{hints}
""")

    def output_dir(self) -> Path:
        value = self.settings.get("output_dir") or DEFAULT_OUTPUT_DIR
        path = Path(str(value)).expanduser()
        base = USER_APP_DIR if is_frozen_app() else APP_DIR
        return path if path.is_absolute() else (base / path).resolve()

    def apply_qt_theme(self, theme: str) -> None:
        theme = normalize_qt_theme(theme)
        self.current_qt_theme = theme
        self.setStyleSheet(QT_THEME_STYLES.get(theme, QT_STYLESHEET) + theme_selection_styles(theme) + theme_role_styles(theme))
        highlight, highlighted_text = theme_selection_colors(theme)
        palette = self.palette()
        palette.setColor(QPalette.Highlight, QColor(highlight))
        palette.setColor(QPalette.HighlightedText, QColor(highlighted_text))
        QApplication.instance().setPalette(palette)
        self.setPalette(palette)
        if hasattr(self, "topology_graphics"):
            roles = theme_visual_roles(theme)
            self.topology_graphics.setStyleSheet(f"background-color: {roles['topology_bg']}; border: 1px solid #555555;")
            self.populate_topology_visualization()

    def browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select output directory", str(self.output_dir()))
        if path:
            self.settings_output.setText(path)

    def open_path(self, path: Path) -> None:
        path = path.expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True) if not path.exists() and path.suffix == "" else None
        if sys.platform.startswith("darwin"):
            subprocess.Popen(["open", str(path)])
        elif os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def open_symbol_mapping_dialog(self) -> None:
        symbols = available_symbol_paths()
        if not symbols:
            QMessageBox.warning(self, "No symbols found", f"No symbol files were found under {SYMBOLS_DIR}.")
            return
        current = merged_symbol_mappings(self.settings)
        dialog = QDialog(self)
        dialog.setWindowTitle("Topology Symbol Mapping")
        layout = QVBoxLayout(dialog)
        intro = QLabel("Select the icon used for each topology device role. Classic GNS3 symbols are the defaults.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        combos: Dict[str, QComboBox] = {}
        for role, label in SYMBOL_ROLE_LABELS.items():
            combo = QComboBox()
            combo.addItems(symbols)
            desired = current.get(role, SYMBOL_ROLE_DEFAULTS.get(role, ""))
            if desired in symbols:
                combo.setCurrentText(desired)
            elif SYMBOL_ROLE_DEFAULTS.get(role) in symbols:
                combo.setCurrentText(SYMBOL_ROLE_DEFAULTS[role])
            combo.setMinimumWidth(360)
            combos[role] = combo
            form.addRow(label, combo)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        def restore_defaults() -> None:
            for role, combo in combos.items():
                default = SYMBOL_ROLE_DEFAULTS.get(role, "")
                if default in symbols:
                    combo.setCurrentText(default)
        buttons.button(QDialogButtonBox.RestoreDefaults).clicked.connect(restore_defaults)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.Accepted:
            self.settings["topology_symbol_map"] = {role: combo.currentText() for role, combo in combos.items()}
            LOCAL_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
            LOCAL_SETTINGS.write_text(json.dumps(self.settings, indent=2) + "\n", encoding="utf-8")
            self.populate_topology_visualization()
            QMessageBox.information(self, "Topology symbols saved", "Topology symbol mappings were saved to local settings.")

    def save_settings(self) -> None:
        self.settings.update({
            "theme": normalize_qt_theme(self.settings_theme.currentText()),
            "gns3_server": self.settings_server.text().strip(),
            "output_dir": self.settings_output.text().strip() or str(DEFAULT_OUTPUT_DIR if is_frozen_app() else "generated_labs"),
            "host_type": self.settings_host_type.currentText(),
            "push_config": self.settings_push_config.isChecked(),
            "push_endpoints": self.settings_push_endpoints.isChecked(),
            "verify": self.settings_verify.isChecked(),
            "linux_endpoint_username": self.settings_linux_user.text().strip() or "root",
            "linux_endpoint_password": self.settings_linux_password.text(),
            "endpoint_timeout": self.settings_endpoint_timeout.value(),
            "console_timeout": self.settings_console_timeout.value(),
        })
        LOCAL_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_SETTINGS.write_text(json.dumps(self.settings, indent=2) + "\n", encoding="utf-8")
        self.apply_qt_theme(self.settings["theme"])
        if hasattr(self, "host_type_combo"):
            self.host_type_combo.setCurrentText(str(self.settings.get("host_type", "alpine")))
            self.push_config_check.setChecked(bool(self.settings.get("push_config", True)))
            self.push_endpoints_check.setChecked(bool(self.settings.get("push_endpoints", True)))
            self.verify_check.setChecked(bool(self.settings.get("verify", False)))
        self.statusBar().showMessage("Settings saved")
        QMessageBox.information(self, "Settings saved", f"Settings saved to {LOCAL_SETTINGS}")

    def reload_catalog(self) -> None:
        self.catalog_store = CatalogStore()
        self.refresh_filters(); self.refresh_scenarios()
        self.blank_topology_combo.clear(); self.blank_topology_combo.addItems(self.catalog_store.topologies_list())
        self.statusBar().showMessage("Catalog reloaded")

    def base_generator_args(self) -> List[str]:
        packaged_generator = packaged_generator_path()
        if packaged_generator:
            args = [str(packaged_generator)]
        else:
            args = [sys.executable, "-u", str(DEFAULT_GENERATOR)]
        if self.settings.get("gns3_server"):
            args += ["--server", str(self.settings["gns3_server"])]
        if LOCAL_SETTINGS.exists():
            args += ["--config", str(LOCAL_SETTINGS)]
        args += ["--out", str(self.output_dir())]
        args += ["--host-type", str(self.settings.get("host_type", "alpine"))]
        if self.settings.get("linux_endpoint_username"):
            args += ["--linux-endpoint-username", str(self.settings.get("linux_endpoint_username"))]
        if self.settings.get("linux_endpoint_password"):
            args += ["--linux-endpoint-password", str(self.settings.get("linux_endpoint_password"))]
        args += ["--endpoint-timeout", str(int(self.settings.get("endpoint_timeout", 180)))]
        args += ["--console-timeout", str(int(self.settings.get("console_timeout", 420)))]
        return args

    def run_command(self, args: List[str], target: QPlainTextEdit, on_done=None) -> None:
        target.setPlainText("Running:\n" + " ".join(args) + "\n\n")
        self.statusBar().showMessage("Running command...")
        worker = ProcessWorker(args, APP_DIR)
        self.track_thread(worker, "worker")
        def output_ready(text: str) -> None:
            target.appendPlainText(text.rstrip("\n"))
        def finished(code: int, output: str) -> None:
            target.appendPlainText(f"\nExit code: {code}")
            self.statusBar().showMessage("Command completed" if code == 0 else f"Command failed with exit code {code}")
            if on_done:
                on_done(code, output)
        worker.output.connect(output_ready)
        worker.finished.connect(finished)
        worker.start()

    def run_preflight(self) -> None:
        sid = self.selected_scenario_id()
        if not sid:
            return
        args = self.base_generator_args() + ["--scenario", sid, "--preflight", "--no-push-config", "--no-push-endpoints"]
        self.run_command(args, self.output_text)

    def run_generate(self) -> None:
        sid = self.selected_scenario_id()
        if not sid:
            return
        args = self.base_generator_args() + ["--scenario", sid]
        name = self.project_name.text().strip() if hasattr(self, "project_name") else ""
        if name:
            args += ["--name", name]
        if hasattr(self, "host_type_combo"):
            args += ["--host-type", self.host_type_combo.currentText()]
        if hasattr(self, "start_nodes_check") and not self.start_nodes_check.isChecked():
            args += ["--no-start"]
        if hasattr(self, "push_config_check"):
            args += ["--push-config" if self.push_config_check.isChecked() else "--no-push-config"]
        if hasattr(self, "push_endpoints_check"):
            args += ["--push-endpoints" if self.push_endpoints_check.isChecked() else "--no-push-endpoints"]
        if hasattr(self, "verify_check") and self.verify_check.isChecked():
            args += ["--verify"]
        def done(code: int, output: str) -> None:
            if code == 0:
                lab_dir = self.extract_lab_dir(output)
                if lab_dir:
                    self.load_workspace(lab_dir)
                    self.stack.setCurrentIndex(1)
        self.run_command(args, self.output_text, done)

    def run_blank_topology(self) -> None:
        topo = self.blank_topology_combo.currentText()
        if not topo:
            return
        args = self.base_generator_args() + ["--blank-topology", "--topology", topo]
        name = self.blank_name.text().strip()
        if name:
            args += ["--name", name]
        if self.blank_no_auto.isChecked():
            args += ["--no-auto-config", "--no-start", "--no-push-config", "--no-push-endpoints"]
        def done(code: int, output: str) -> None:
            if code == 0:
                lab_dir = self.extract_lab_dir(output)
                if lab_dir:
                    self.load_workspace(lab_dir)
                    self.stack.setCurrentIndex(1)
        self.run_command(args, self.advanced_output, done)

    def run_audit(self) -> None:
        audit_script = APP_DIR / "scripts" / "audit_labs.py"
        if audit_script.exists() and not is_frozen_app():
            args = [sys.executable, str(audit_script)]
        else:
            args = self.base_generator_args() + ["--qa-report"]
        self.run_command(args, self.advanced_output)

    def extract_lab_dir(self, output: str) -> Optional[Path]:
        match = re.search(r"Local files:\s*(.+)", output)
        if match:
            path = Path(match.group(1).strip()).expanduser()
            if not path.is_absolute():
                path = (APP_DIR / path).resolve()
            return path
        candidates = sorted(self.output_dir().glob("*"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
        return candidates[0] if candidates else None

    def browse_lab_folder(self) -> None:
        start = str(self.last_lab_dir or self.output_dir())
        path = QFileDialog.getExistingDirectory(self, "Select generated lab folder", start)
        if path:
            self.load_workspace(Path(path))
            self.stack.setCurrentIndex(1)

    def open_lab_folder(self) -> None:
        if not self.last_lab_dir:
            QMessageBox.information(self, "No lab loaded", "Load or generate a lab first.")
            return
        self.open_path(self.last_lab_dir)

    def refresh_workspace(self) -> None:
        if self.last_lab_dir:
            self.load_workspace(self.last_lab_dir)

    def load_workspace(self, lab_dir: Path) -> None:
        self.close_all_consoles()
        self.last_lab_dir = lab_dir.expanduser().resolve()
        metadata_path = self.last_lab_dir / "metadata.json"
        self.workspace_metadata = read_json(metadata_path)
        title = self.workspace_metadata.get("title") or self.last_lab_dir.name
        mode = self.workspace_metadata.get("lab_mode", "generated lab")
        self.workspace_title.setText(f"Lab: {title}  |  Mode: {mode}")
        self.workspace_title.setToolTip(str(self.last_lab_dir))
        self.populate_documents()
        self.populate_config_sets()
        self.parse_guided_steps()
        self.load_guided_progress()
        self.render_guided_learning()
        workspace_warnings: List[str] = []
        for label, callback in [
            ("topology table", self.populate_topology_table),
            ("topology visualization", self.populate_topology_visualization),
            ("console endpoints", self.populate_console_devices),
            ("lifecycle status", self.populate_lifecycle_status),
            ("reports", self.populate_reports),
        ]:
            try:
                callback()
            except Exception as exc:
                workspace_warnings.append(f"{label}: {exc}")
        if workspace_warnings:
            self.statusBar().showMessage("Loaded workspace with warnings: " + "; ".join(workspace_warnings[:2]))
        else:
            self.statusBar().showMessage(f"Loaded workspace: {self.last_lab_dir.name}")

    def select_workspace_tab(self, tab_name: str) -> None:
        if not hasattr(self, "workspace_tabs"):
            return
        for idx in range(self.workspace_tabs.count()):
            if self.workspace_tabs.tabText(idx) == tab_name:
                self.workspace_tabs.setCurrentIndex(idx)
                return

    def practice_state_path(self) -> Optional[Path]:
        if not self.last_lab_dir:
            return None
        return self.last_lab_dir / "practice_state.json"

    def practice_notes_path(self) -> Optional[Path]:
        if not self.last_lab_dir:
            return None
        return self.last_lab_dir / "student_notes.md"

    def practice_summary_path(self) -> Optional[Path]:
        if not self.last_lab_dir:
            return None
        return self.last_lab_dir / "practice_summary.md"

    def load_practice_state(self) -> None:
        path = self.practice_state_path()
        self.practice_state = read_json(path) if path and path.exists() else {"schema_version": "3.0-beta2", "status": "not_started"}
        notes_path = self.practice_notes_path()
        if hasattr(self, "practice_notes"):
            if notes_path and notes_path.exists():
                try:
                    self.practice_notes.setPlainText(notes_path.read_text(encoding="utf-8"))
                except Exception:
                    self.practice_notes.setPlainText("")
            else:
                self.practice_notes.setPlainText("")
        summary_path = self.practice_summary_path()
        if hasattr(self, "practice_summary"):
            if summary_path and summary_path.exists():
                try:
                    self.practice_summary.setMarkdown(summary_path.read_text(encoding="utf-8"))
                except Exception:
                    self.practice_summary.setMarkdown("# Summary\n\nCould not read practice summary.")
            else:
                self.practice_summary.setMarkdown("# Summary\n\nNo practice summary has been created yet.")

    def save_practice_state(self) -> None:
        path = self.practice_state_path()
        if not path:
            return
        try:
            path.write_text(json.dumps(self.practice_state, indent=2), encoding="utf-8")
        except Exception as exc:
            self.statusBar().showMessage(f"Could not save practice state: {exc}")

    def save_practice_notes(self) -> None:
        path = self.practice_notes_path()
        if not path or not hasattr(self, "practice_notes"):
            return
        try:
            path.write_text(self.practice_notes.toPlainText(), encoding="utf-8")
            self.statusBar().showMessage("Practice notes saved.")
        except Exception as exc:
            QMessageBox.warning(self, "Could not save notes", str(exc))

    def start_practice_session(self) -> None:
        if not self.last_lab_dir:
            QMessageBox.information(self, "No lab loaded", "Load or generate a lab before starting practice.")
            return
        now = datetime.now().isoformat(timespec="seconds")
        if not self.practice_state:
            self.practice_state = {"schema_version": "3.0-beta2"}
        self.practice_state.setdefault("started_at", now)
        self.practice_state["last_started_at"] = now
        self.practice_state["status"] = "in_progress"
        self.save_practice_state()
        self.populate_practice_workspace()
        self.select_workspace_tab("Guided Learning")
        self.statusBar().showMessage("Practice session started.")

    def end_practice_session(self) -> None:
        if not self.last_lab_dir:
            QMessageBox.information(self, "No lab loaded", "Load or generate a lab first.")
            return
        self.save_practice_notes()
        now = datetime.now().isoformat(timespec="seconds")
        self.practice_state["ended_at"] = now
        self.practice_state["status"] = "ended"
        self.save_practice_state()
        summary = self.build_practice_summary()
        path = self.practice_summary_path()
        if path:
            try:
                path.write_text(summary, encoding="utf-8")
            except Exception as exc:
                QMessageBox.warning(self, "Could not save summary", str(exc))
        if hasattr(self, "practice_summary"):
            self.practice_summary.setMarkdown(summary)
        self.populate_practice_workspace()
        self.statusBar().showMessage("Practice session ended and summary saved.")

    def build_practice_summary(self) -> str:
        project = self.workspace_metadata.get("project", {}) if self.workspace_metadata else {}
        title = project.get("title") or project.get("scenario_id") or (self.last_lab_dir.name if self.last_lab_dir else "Generated lab")
        total_steps = len(getattr(self, "guided_step_records", [])) or len(getattr(self, "guided_steps", []))
        completed = len(getattr(self, "completed_guided_step_ids", set())) or getattr(self, "completed_guided_steps", 0)
        hints_used = getattr(self, "current_hint_index", 0)
        answer_key = "yes" if self.practice_state.get("answer_key_revealed") else "no"
        return (
            f"# Practice Summary\n\n"
            f"**Lab:** {title}\n\n"
            f"**Status:** {self.practice_state.get('status', 'unknown')}\n\n"
            f"**Started:** `{self.practice_state.get('started_at') or self.practice_state.get('last_started_at') or 'not recorded'}`\n\n"
            f"**Ended:** `{self.practice_state.get('ended_at', 'not ended')}`\n\n"
            f"**Guided steps completed:** {completed}/{total_steps}\n\n"
            f"**Hints revealed in current step:** {hints_used}\n\n"
            f"**Answer key revealed:** {answer_key}\n\n"
            "## Suggested Follow-up\n\n"
            "- Review your notes and compare your final verification against the answer key.\n"
            "- Use the Lifecycle tab to stop, reset, or delete the deployed GNS3 project when you are done.\n"
        )

    def populate_practice_workspace(self) -> None:
        if not hasattr(self, "practice_status"):
            return
        if not self.last_lab_dir:
            self.practice_status.setMarkdown("# Practice Session\n\nLoad or generate a lab to begin.")
            return
        project = self.workspace_metadata.get("project", {}) if self.workspace_metadata else {}
        title = project.get("title") or project.get("scenario_id") or self.last_lab_dir.name
        status = self.practice_state.get("status", "not_started") if self.practice_state else "not_started"
        started = self.practice_state.get("started_at") or self.practice_state.get("last_started_at") or "not started"
        ended = self.practice_state.get("ended_at") or "not ended"
        total_steps = len(getattr(self, "guided_step_records", [])) or len(getattr(self, "guided_steps", []))
        completed = len(getattr(self, "completed_guided_step_ids", set())) or getattr(self, "completed_guided_steps", 0)
        server = self.gns3_server_for_lab()
        project_id = self.gns3_project_id_for_lab()
        self.practice_status.setMarkdown(
            f"# Practice Session\n\n"
            f"**Lab:** {title}\n\n"
            f"**Status:** {status.replace('_', ' ').title()}\n\n"
            f"**Started:** `{started}`  \n**Ended:** `{ended}`\n\n"
            f"**Guided progress:** {completed}/{total_steps} step(s) complete\n\n"
            f"**GNS3 server:** `{server or 'not configured'}`  \n**Project ID:** `{project_id or 'not available'}`\n\n"
            "## Recommended Flow\n\n"
            "1. Start practice.\n"
            "2. Work through Guided Practice.\n"
            "3. Use Topology, Configs, and Consoles as needed.\n"
            "4. End practice to save a summary.\n"
            "5. Use Lifecycle to stop/reset/delete the GNS3 project when finished.\n"
        )

    def guided_progress_path(self) -> Optional[Path]:
        if not self.last_lab_dir:
            return None
        return self.last_lab_dir / ".guided_progress.json"

    def load_guided_progress(self) -> None:
        path = self.guided_progress_path()
        data = read_json(path) if path and path.exists() else {}
        saved_mode = str(data.get("learning_mode", self.learning_mode or "Student"))
        if saved_mode in {"Student", "Explorer", "Instructor"}:
            self.learning_mode = saved_mode
            if hasattr(self, "learning_mode_combo"):
                self.learning_mode_combo.blockSignals(True)
                self.learning_mode_combo.setCurrentText(saved_mode)
                self.learning_mode_combo.blockSignals(False)
        try:
            self.current_hint_index = int(data.get("current_hint_index", self.current_hint_index))
        except Exception:
            self.current_hint_index = 0
        try:
            self.current_guided_step_index = int(data.get("current_step_index", getattr(self, "current_guided_step_index", 0)))
        except Exception:
            self.current_guided_step_index = 0
        completed_ids = data.get("completed_step_ids", [])
        self.completed_guided_step_ids = set(str(item) for item in completed_ids if item) if isinstance(completed_ids, list) else set()
        try:
            self.completed_guided_steps = int(data.get("completed_guided_steps", len(self.completed_guided_step_ids)))
        except Exception:
            self.completed_guided_steps = len(self.completed_guided_step_ids)
        if self.learning_mode != "Student":
            self.current_hint_index = len(getattr(self, "hint_records", [])) or len(getattr(self, "guided_steps", []))
        max_steps = max(0, len(getattr(self, "guided_steps", [])) - 1)
        self.current_guided_step_index = max(0, min(self.current_guided_step_index, max_steps))

    def save_guided_progress(self) -> None:
        path = self.guided_progress_path()
        if not path:
            return
        data = {
            "schema_version": "3.0-beta1",
            "learning_mode": self.learning_mode,
            "current_hint_index": self.current_hint_index,
            "current_step_index": getattr(self, "current_guided_step_index", 0),
            "completed_guided_steps": len(getattr(self, "completed_guided_step_ids", set())),
            "completed_step_ids": sorted(getattr(self, "completed_guided_step_ids", set())),
        }
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            self.statusBar().showMessage(f"Could not save guided progress: {exc}")

    def on_learning_mode_changed(self, mode: str) -> None:
        self.learning_mode = mode or "Student"
        if self.learning_mode != "Student":
            self.current_hint_index = len(getattr(self, "hint_records", [])) or len(getattr(self, "guided_steps", []))
        self.save_guided_progress()
        self.render_guided_learning()

    def read_workspace_file(self, rel: str) -> str:
        if not self.last_lab_dir:
            return ""
        path = self.last_lab_dir / rel
        try:
            return path.read_text(encoding="utf-8") if path.exists() else ""
        except Exception as exc:
            return f"Could not read {path}: {exc}"

    def parse_guided_steps(self) -> None:
        """Load explicit 3.0 guided steps/hints when available, falling back to generated defaults."""
        self.guided_step_records = []
        self.hint_records = []
        if self.last_lab_dir:
            steps_path = self.last_lab_dir / "content" / "guided_steps.json"
            hints_path = self.last_lab_dir / "content" / "hints.json"
            try:
                if steps_path.exists():
                    data = json.loads(steps_path.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        self.guided_step_records = [item for item in data if isinstance(item, dict)]
                if hints_path.exists():
                    data = json.loads(hints_path.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        self.hint_records = [item for item in data if isinstance(item, dict)]
            except Exception as exc:
                self.statusBar().showMessage(f"Could not parse structured guided content: {exc}")

        if not self.guided_step_records:
            fallback = [
                {"id": "understand-scenario", "title": "Understand the scenario", "objective": "Read the scenario brief and identify the intended behavior.", "instructions": "Start by reviewing the scenario, requirements, and topology before changing configuration.", "suggested_commands": [], "completion_criteria": "You can summarize the reported issue and success criteria."},
                {"id": "confirm-symptom", "title": "Confirm the symptom", "objective": "Prove the failure from the device CLI.", "instructions": "Use show and ping commands to confirm what is broken before editing config.", "suggested_commands": ["show ip interface brief", "show ip route", "ping <destination>"], "completion_criteria": "You have confirmed the failure from at least one relevant device."},
                {"id": "inspect-state", "title": "Inspect relevant state", "objective": "Narrow the fault domain.", "instructions": "Use the topology map and configuration viewer to decide which device, link, or protocol relationship deserves attention.", "suggested_commands": ["show running-config", "show protocols"], "completion_criteria": "You can name the likely fault area and explain why."},
                {"id": "fix-and-verify", "title": "Apply and verify the fix", "objective": "Make the smallest defensible change and prove recovery.", "instructions": "Apply a minimal correction, then run verification commands from more than one point of view.", "suggested_commands": ["show ip route", "ping <destination>", "show running-config | section <feature>"], "completion_criteria": "The required reachability or control-plane behavior is restored."},
            ]
            self.guided_step_records = fallback
        # Normalize IDs/titles and legacy tuple list.
        for idx, step in enumerate(self.guided_step_records, start=1):
            step.setdefault("id", f"step-{idx}")
            step.setdefault("title", f"Step {idx}")
            step.setdefault("objective", "")
            step.setdefault("instructions", "")
            step.setdefault("suggested_commands", [])
            step.setdefault("completion_criteria", "")
        self.guided_steps = [(str(s.get("title")), str(s.get("instructions"))) for s in self.guided_step_records]
        self.current_guided_step_index = max(0, min(getattr(self, "current_guided_step_index", 0), max(0, len(self.guided_step_records)-1)))
        if self.learning_mode != "Student":
            self.current_hint_index = len(self.hint_records) or len(self.guided_step_records)
        else:
            self.current_hint_index = max(0, min(getattr(self, "current_hint_index", 0), len(self.hint_records) or len(self.guided_step_records)))
        self.completed_guided_steps = len(getattr(self, "completed_guided_step_ids", set()))

    def current_guided_step(self) -> Dict[str, Any]:
        if not getattr(self, "guided_step_records", None):
            return {}
        idx = max(0, min(getattr(self, "current_guided_step_index", 0), len(self.guided_step_records)-1))
        return self.guided_step_records[idx]

    def hint_matches_step(self, hint: Dict[str, Any], step: Dict[str, Any]) -> bool:
        sid = str(step.get("id", ""))
        return str(hint.get("step_id", "")) in {"", sid} or str(hint.get("step", "")) in {"", sid}

    def populate_guided_step_list(self) -> None:
        if not hasattr(self, "guided_step_list"):
            return
        self.guided_step_list.blockSignals(True)
        self.guided_step_list.clear()
        completed = getattr(self, "completed_guided_step_ids", set())
        for idx, step in enumerate(getattr(self, "guided_step_records", []), start=1):
            sid = str(step.get("id", f"step-{idx}"))
            marker = "✅" if sid in completed else "⬜"
            self.guided_step_list.addItem(f"{marker} {idx}. {step.get('title', f'Step {idx}')}")
        if self.guided_step_records:
            self.guided_step_list.setCurrentRow(getattr(self, "current_guided_step_index", 0))
        self.guided_step_list.blockSignals(False)

    def render_guided_learning(self) -> None:
        if not hasattr(self, "guided_view"):
            return
        self.populate_guided_step_list()
        total = len(getattr(self, "guided_step_records", []))
        completed = len(getattr(self, "completed_guided_step_ids", set()))
        step = self.current_guided_step()
        if not step:
            self.guided_view.setMarkdown("# Guided Practice\n\nLoad or generate a lab to begin.")
            return
        idx = getattr(self, "current_guided_step_index", 0) + 1
        cmds = step.get("suggested_commands") or []
        cmd_text = "\n".join(f"- `{cmd}`" for cmd in cmds if cmd) or "- No specific commands are attached to this step. Use the scenario context and topology to decide what to inspect."
        devices = step.get("devices") or step.get("related_devices") or []
        device_text = ", ".join(str(d) for d in devices) if devices else "Use the topology and configs to choose the relevant device(s)."
        criteria = step.get("completion_criteria") or "You can explain what you checked and why you are ready to move on."
        mode_note = {
            "Student": "Student mode reveals hints progressively and guards full solutions.",
            "Explorer": "Explorer mode keeps the workspace open while still tracking progress.",
            "Instructor": "Instructor mode exposes solution material more directly.",
        }.get(self.learning_mode, "")
        self.guided_view.setMarkdown(f"""# Guided Practice Step {idx} of {total}: {step.get('title', 'Untitled step')}


**Mode:** {self.learning_mode} — {mode_note}

**Progress:** {completed}/{total} step(s) complete.


## Objective

{step.get('objective', '')}


## What to do

{step.get('instructions', '')}


## Suggested commands

{cmd_text}


## Related devices

{device_text}


## Completion criteria

{criteria}


## Helpful workspace actions

- Use the **Topology** tab to confirm device/interface relationships.
- Use the **Configs** tab to inspect starter or answer-key configs.
- Use the **Consoles** tab to connect to deployed devices.
- Use **Copy Suggested Commands** to copy this step's commands to your clipboard.
""")
        self.render_guided_hints()

    def render_guided_hints(self) -> None:
        if not hasattr(self, "guided_hint_view"):
            return
        step = self.current_guided_step()
        hints = [h for h in getattr(self, "hint_records", []) if self.hint_matches_step(h, step)]
        if not hints:
            # Fall back to all hints when step-specific mapping is unavailable.
            hints = list(getattr(self, "hint_records", []))
        visible_count = len(hints) if self.learning_mode != "Student" else min(getattr(self, "current_hint_index", 0), len(hints))
        parts = [f"# Hints for: {step.get('title', 'Current Step')}"]
        if visible_count <= 0:
            parts.append("No hints revealed yet. Use **Reveal Hint** when you want a nudge without opening the answer key.")
        else:
            for hint in hints[:visible_count]:
                parts.append(f"## {hint.get('title', 'Hint')}\n\n{hint.get('body') or hint.get('text') or ''}")
        hidden = max(0, len(hints) - visible_count)
        if hidden and self.learning_mode == "Student":
            parts.append(f"*{hidden} hint(s) still hidden for this step.*")
        self.guided_hint_view.setMarkdown("\n\n".join(parts))

    def on_guided_step_selected(self, row: int) -> None:
        if row < 0 or row >= len(getattr(self, "guided_step_records", [])):
            return
        self.current_guided_step_index = row
        if self.learning_mode == "Student":
            self.current_hint_index = 0
        self.save_guided_progress()
        self.render_guided_learning()

    def previous_guided_step(self) -> None:
        if getattr(self, "current_guided_step_index", 0) > 0:
            self.current_guided_step_index -= 1
            self.save_guided_progress()
            self.render_guided_learning()

    def next_guided_step(self) -> None:
        if getattr(self, "current_guided_step_index", 0) < len(getattr(self, "guided_step_records", [])) - 1:
            self.current_guided_step_index += 1
            self.save_guided_progress()
            self.render_guided_learning()

    def reveal_next_hint(self) -> None:
        step = self.current_guided_step()
        hints = [h for h in getattr(self, "hint_records", []) if self.hint_matches_step(h, step)]
        if not hints:
            hints = list(getattr(self, "hint_records", []))
        if self.current_hint_index < len(hints):
            self.current_hint_index += 1
        self.save_guided_progress()
        self.render_guided_learning()

    def mark_guided_step_complete(self) -> None:
        step = self.current_guided_step()
        if step:
            self.completed_guided_step_ids.add(str(step.get("id", f"step-{getattr(self, 'current_guided_step_index', 0)+1}")))
        self.completed_guided_steps = len(self.completed_guided_step_ids)
        self.statusBar().showMessage("Guided practice step marked complete for this generated lab.")
        if getattr(self, "current_guided_step_index", 0) < len(getattr(self, "guided_step_records", [])) - 1:
            self.current_guided_step_index += 1
            self.current_hint_index = 0
        self.save_guided_progress()
        self.render_guided_learning()
        self.populate_practice_workspace()

    def copy_current_step_commands(self) -> None:
        step = self.current_guided_step()
        cmds = [str(cmd) for cmd in (step.get("suggested_commands") or []) if cmd]
        if not cmds:
            QMessageBox.information(self, "No commands", "This step does not have specific suggested commands.")
            return
        QApplication.clipboard().setText("\n".join(cmds))
        self.statusBar().showMessage("Suggested commands copied to clipboard.")

    def open_answer_key_from_guided(self) -> None:
        if self.learning_mode != "Instructor":
            response = QMessageBox.question(self, "Reveal answer key?", "This opens the full solution. Continue?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if response != QMessageBox.Yes:
                return
            self.practice_state["answer_key_revealed"] = True
            self.save_practice_state()
            self.populate_practice_workspace()
        if not self.last_lab_dir:
            return
        self.practice_state["answer_key_revealed"] = True
        self.save_practice_state()
        self.populate_practice_workspace()
        path = self.last_lab_dir / "answer_key.md"
        try:
            self.doc_view.setMarkdown(path.read_text(encoding="utf-8"))
        except Exception as exc:
            QMessageBox.warning(self, "Answer key unavailable", str(exc))

    def populate_documents(self) -> None:
        self.doc_list.clear()
        self.doc_paths: List[Path] = []
        docs = self.workspace_metadata.get("documents", {}) if self.workspace_metadata else {}
        labels = [
            ("Project Info", docs.get("project_info") or "project_info.md"),
            ("Scenario Brief", docs.get("student_brief") or "student_brief.md"),
            ("Requirements", docs.get("requirements") or "requirements.md"),
            ("Observed Symptoms", docs.get("observations") or "content/observations.json"),
            ("Lab Context", docs.get("lab_context") or "content/lab_context.json"),
            ("Guided Practice", docs.get("guided_practice") or "guided_practice.md"),
            ("Hints", docs.get("hints") or "hints.md"),
            ("Topology Map", docs.get("topology_map") or "topology_map.md"),
            ("Generation Summary", docs.get("generation_summary") or "generation_summary.md"),
            ("README", docs.get("readme") or "README.md"),
            ("Answer Key", docs.get("answer_key") or "answer_key.md"),
            ("Validation", docs.get("validation") or "validation_report.md"),
        ]
        for label, rel in labels:
            if not rel:
                continue
            path = self.last_lab_dir / rel
            if path.exists():
                self.doc_list.addItem(label)
                self.doc_paths.append(path)
        if self.doc_paths:
            self.doc_list.setCurrentRow(0)
        else:
            self.doc_view.setPlainText("No generated documents found in this lab folder.")

    def format_structured_document(self, label: str, data: Any) -> str:
        """Render generated JSON content as learner-readable Markdown with generous spacing.

        The generated Markdown exports already contain whitespace, but the app's
        structured content view is generated from JSON. Keep that view just as
        readable by inserting explicit spacing between sections and list groups.
        """
        title = label or "Document"
        lines: List[str] = [f"# {title}", "", ""]

        def append_blank(count: int = 1) -> None:
            for _ in range(count):
                if lines and lines[-1] == "":
                    continue
                lines.append("")

        def add_paragraph(value: Any) -> None:
            if value is None:
                return
            text = str(value).strip()
            if not text:
                return
            lines.append(text)
            lines.append("")
            lines.append("")

        def add_value(key: str, value: Any, level: int = 2) -> None:
            if value is None or value == "":
                return
            heading = str(key).replace("_", " ").replace("-", " ").title()
            if isinstance(value, dict):
                lines.append(f"{'#' * level} {heading}")
                lines.append("")
                lines.append("")
                for sub_key, sub_value in value.items():
                    add_value(sub_key, sub_value, min(level + 1, 4))
                lines.append("")
            elif isinstance(value, list):
                lines.append(f"{'#' * level} {heading}")
                lines.append("")
                if not value:
                    lines.append("_No entries provided._")
                    lines.append("")
                    lines.append("")
                    return
                for item in value:
                    if isinstance(item, dict):
                        item_title = item.get("title") or item.get("name") or item.get("id")
                        if item_title:
                            lines.append(f"### {item_title}")
                            lines.append("")
                            lines.append("")
                        for sub_key, sub_value in item.items():
                            if sub_key in {"title", "name", "id"} and item_title:
                                continue
                            add_value(sub_key, sub_value, 4)
                        lines.append("")
                    else:
                        text = str(item).strip()
                        if text:
                            lines.append(f"- {text}")
                lines.append("")
                lines.append("")
            else:
                if level <= 2:
                    lines.append(f"## {heading}")
                    lines.append("")
                    add_paragraph(value)
                else:
                    lines.append(f"- **{heading}:** {value}")
                    lines.append("")

        if isinstance(data, dict):
            for key, value in data.items():
                add_value(key, value, 2)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    title_value = item.get("title") or item.get("name") or item.get("id")
                    if title_value:
                        lines.append(f"## {title_value}")
                        lines.append("")
                        lines.append("")
                    for key, value in item.items():
                        if key in {"title", "name", "id"} and title_value:
                            continue
                        add_value(key, value, 3)
                else:
                    lines.append(f"- {item}")
            lines.append("")
        else:
            add_paragraph(data)

        # Collapse excessive blank runs while preserving clear section spacing.
        rendered: List[str] = []
        blank_count = 0
        for line in lines:
            if line == "":
                blank_count += 1
                if blank_count <= 2:
                    rendered.append(line)
            else:
                blank_count = 0
                rendered.append(line)
        return "\n".join(rendered).strip() + "\n"

    def load_selected_document(self, row: int) -> None:
        if row < 0 or row >= len(getattr(self, "doc_paths", [])):
            return
        path = self.doc_paths[row]
        label = self.doc_list.item(row).text()
        if "Answer Key" in label and getattr(self, "learning_mode", "Student") != "Instructor":
            response = QMessageBox.question(
                self,
                "Reveal answer key?",
                "This opens the full solution. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if response != QMessageBox.Yes:
                return
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            text = f"Could not read {path}: {exc}"
        if path.suffix.lower() == ".md":
            self.doc_view.setMarkdown(text)
        elif path.suffix.lower() == ".json":
            try:
                data = json.loads(text)
                self.doc_view.setMarkdown(self.format_structured_document(label, data))
            except Exception:
                self.doc_view.setPlainText(text)
        else:
            self.doc_view.setPlainText(text)

    def populate_config_sets(self) -> None:
        self.config_set_combo.blockSignals(True)
        self.config_set_combo.clear()
        config_sets = self.workspace_metadata.get("config_sets", {}) if self.workspace_metadata else {}
        if not config_sets and self.last_lab_dir:
            for name in ["startup_configs", "starter_configs", "answer_key_configs", "blank_topology_configs"]:
                if (self.last_lab_dir / name).exists():
                    config_sets[name] = name
        for key, rel in config_sets.items():
            if (self.last_lab_dir / rel).exists():
                self.config_set_combo.addItem(key, rel)
        self.config_set_combo.blockSignals(False)
        self.populate_devices()
        if hasattr(self, "compare_device_combo"):
            self.populate_compare_devices()

    def populate_devices(self) -> None:
        # Preserve the selected device filename when switching between Initial
        # and Answer Key config sets. This keeps the learner anchored on the
        # same device while comparing config versions.
        previous_name = self.device_combo.currentText() if hasattr(self, "device_combo") else ""
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        rel = self.config_set_combo.currentData()
        cfg_dir = self.last_lab_dir / rel if self.last_lab_dir and rel else None
        names = []
        if cfg_dir and cfg_dir.exists():
            files = sorted([p for p in cfg_dir.iterdir() if p.is_file() and p.suffix.lower() in {".cfg", ".txt", ".sh"}])
            for path in files:
                names.append(path.name)
                self.device_combo.addItem(path.name, str(path))
        if previous_name and previous_name in names:
            self.device_combo.setCurrentText(previous_name)
        self.device_combo.blockSignals(False)
        self.load_selected_config()

    def load_selected_config(self) -> None:
        path_text = self.device_combo.currentData()
        if not path_text:
            self.config_view.setPlainText("No configs found for this set.")
            return
        path = Path(path_text)
        try:
            self.config_view.setPlainText(path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.config_view.setPlainText(f"Could not read {path}: {exc}")

    def populate_compare_devices(self) -> None:
        if not self.last_lab_dir:
            return
        initial_dirs = [self.last_lab_dir / "startup_configs", self.last_lab_dir / "starter_configs"]
        answer_dir = self.last_lab_dir / "answer_key_configs"
        names = set()
        for d in initial_dirs + [answer_dir]:
            if d.exists():
                names.update(p.name for p in d.iterdir() if p.is_file() and p.suffix.lower() in {".cfg", ".txt", ".sh"})
        self.compare_device_combo.blockSignals(True)
        current = self.compare_device_combo.currentText()
        self.compare_device_combo.clear()
        for name in sorted(names):
            self.compare_device_combo.addItem(name)
        if current in names:
            self.compare_device_combo.setCurrentText(current)
        self.compare_device_combo.blockSignals(False)
        self.load_compare_device()

    def load_compare_device(self) -> None:
        if not self.last_lab_dir:
            return
        name = self.compare_device_combo.currentText()
        if not name:
            self.compare_left.setPlainText("No comparable configs found.")
            self.compare_right.setPlainText("No comparable configs found.")
            return
        left_path = None
        for d in [self.last_lab_dir / "startup_configs", self.last_lab_dir / "starter_configs", self.last_lab_dir / "blank_topology_configs"]:
            if (d / name).exists():
                left_path = d / name; break
        right_path = self.last_lab_dir / "answer_key_configs" / name
        def read_or_note(path: Optional[Path], label: str) -> str:
            if path and path.exists():
                try:
                    return f"# {label}: {path.name}\n" + path.read_text(encoding="utf-8")
                except Exception as exc:
                    return f"Could not read {path}: {exc}"
            return f"No {label} config found for {name}."
        left_text = read_or_note(left_path, "starter")
        right_text = read_or_note(right_path if right_path.exists() else None, "answer-key")
        self.compare_left.setPlainText(left_text)
        self.compare_right.setPlainText(right_text)
        diff = difflib.HtmlDiff(wrapcolumn=120).make_table(
            left_text.splitlines(), right_text.splitlines(), fromdesc="Starter", todesc="Answer Key", context=True, numlines=3
        )
        self.compare_diff.setHtml("<style>table.diff{font-family:monospace;font-size:12px;} .diff_add{background:#14532d;} .diff_chg{background:#854d0e;} .diff_sub{background:#7f1d1d;}</style>" + diff)

    def populate_topology_table(self) -> None:
        topo = self.topology_json()
        links = (topo.get("links", []) if topo else []) or (self.workspace_metadata.get("links", []) if self.workspace_metadata else [])
        self.topology_table.setRowCount(len(links))
        for row, link in enumerate(links):
            values = [
                str(link.get("device_a") or link.get("a") or link.get("a_node") or ""),
                str(link.get("interface_a") or link.get("a_interface") or ""),
                str(link.get("device_b") or link.get("b") or link.get("b_node") or ""),
                str(link.get("interface_b") or link.get("b_interface") or ""),
                str(link.get("gns3_a") or link.get("a_gns3") or f"{link.get('a_gns3_adapter', link.get('a_adapter', ''))}/{link.get('a_gns3_port', link.get('a_port', ''))}"),
                str(link.get("gns3_b") or link.get("b_gns3") or f"{link.get('b_gns3_adapter', link.get('b_adapter', ''))}/{link.get('b_gns3_port', link.get('b_port', ''))}"),
            ]
            for col, value in enumerate(values):
                self.topology_table.setItem(row, col, QTableWidgetItem(value))
        self.topology_table.resizeColumnsToContents()

    def topology_json(self) -> Dict[str, Any]:
        if not self.last_lab_dir:
            return {}
        for rel in ("content/topology.json", "topology.json"):
            path = self.last_lab_dir / rel
            if path.exists():
                return read_json(path)
        return {}

    def normalized_topology_nodes_links(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        topo = self.topology_json()
        raw_links = (topo.get("links", []) if isinstance(topo, dict) else []) or (self.workspace_metadata.get("links", []) if self.workspace_metadata else []) or []
        raw_nodes = (topo.get("nodes", []) if isinstance(topo, dict) else []) or []
        links: List[Dict[str, Any]] = []
        for link in raw_links:
            if not isinstance(link, dict):
                continue
            norm = dict(link)
            norm["a_node"] = str(link.get("a_node") or link.get("device_a") or link.get("a") or link.get("source") or link.get("source_node") or "")
            norm["b_node"] = str(link.get("b_node") or link.get("device_b") or link.get("b") or link.get("target") or link.get("target_node") or "")
            norm["a_interface"] = str(link.get("a_interface") or link.get("interface_a") or link.get("source_interface") or "")
            norm["b_interface"] = str(link.get("b_interface") or link.get("interface_b") or link.get("target_interface") or "")
            if norm["a_node"] and norm["b_node"]:
                links.append(norm)
        nodes: List[Dict[str, Any]] = []
        if isinstance(raw_nodes, dict):
            for name, info in raw_nodes.items():
                nodes.append({"name": str(name), **(info if isinstance(info, dict) else {"role": "device"})})
        elif isinstance(raw_nodes, list):
            for idx, node in enumerate(raw_nodes):
                if isinstance(node, dict):
                    name = node.get("name") or node.get("id") or f"Node{idx+1}"
                    nodes.append({"name": str(name), **node})
                elif node:
                    nodes.append({"name": str(node), "role": "device"})
        seen = {str(n.get("name")) for n in nodes if n.get("name")}
        for link in links:
            for key in ("a_node", "b_node"):
                name = link.get(key)
                if name and str(name) not in seen:
                    seen.add(str(name))
                    nodes.append({"name": str(name), "role": "device"})
        return nodes, links

    def topology_node_kind(self, node: Dict[str, Any]) -> str:
        text = " ".join(str(node.get(key, "")) for key in ("name", "role", "type", "platform", "template", "template_name")).lower()
        if any(token in text for token in ("switch", "sw", "l2")):
            return "switch"
        if any(token in text for token in ("pc", "host", "endpoint", "client", "server", "alpine", "linux", "vpcs", "mgmt")):
            return "endpoint"
        if any(token in text for token in ("firewall", "fw", "asa", "ftd", "fortinet", "pan")):
            return "firewall"
        if any(token in text for token in ("cloud", "internet", "isp")):
            return "cloud"
        return "router"

    def topology_icon_path(self, kind: str) -> Optional[Path]:
        mappings = merged_symbol_mappings(self.settings)
        rel = mappings.get(kind) or mappings.get("unknown") or SYMBOL_ROLE_DEFAULTS.get(kind)
        candidates = []
        if rel:
            candidates.append(rel)
        candidates.extend({
            "router": ["classic/router.svg", "router_red.svg", "vyos.svg", "juniper-vmx.svg"],
            "switch": ["classic/ethernet_switch.svg", "classic/multilayer_switch.svg", "juniper-vqfx.svg"],
            "endpoint": ["classic/computer.svg", "classic/vpcs_guest.svg", "mgmt_station.svg", "linux_guest.svg"],
            "firewall": ["classic/firewall.svg", "classic/asa.svg", "fortinet.svg", "pan-vm-fw.svg"],
            "cloud": ["classic/cloud.svg", "vRIN.svg", "loadbalancer.svg"],
            "unknown": ["classic/qemu_guest.svg", "router_red.svg"],
        }.get(kind, ["classic/qemu_guest.svg", "router_red.svg"]))
        seen: set[str] = set()
        for name in candidates:
            if not name or name in seen:
                continue
            seen.add(name)
            path = SYMBOLS_DIR / name
            if path.exists():
                return path
        return None

    def draw_topology_fallback_node(self, scene: QGraphicsScene, kind: str, x: float, y: float, w: float, h: float, pen: QPen, brush: QBrush) -> None:
        if kind == "router":
            scene.addEllipse(x, y, w, h, pen, brush).setZValue(2)
        elif kind == "switch":
            scene.addRect(x, y + 10, w, h - 20, pen, brush).setZValue(2)
            scene.addLine(x + 12, y + h / 2, x + w - 12, y + h / 2, pen).setZValue(3)
        elif kind == "endpoint":
            scene.addRect(x + 18, y + 6, w - 36, h - 24, pen, brush).setZValue(2)
            scene.addLine(x + w / 2, y + h - 18, x + w / 2, y + h - 6, pen).setZValue(3)
            scene.addLine(x + w / 2 - 22, y + h - 6, x + w / 2 + 22, y + h - 6, pen).setZValue(3)
        elif kind == "cloud":
            scene.addEllipse(x + 5, y + 20, w * .45, h * .45, pen, brush).setZValue(2)
            scene.addEllipse(x + w * .28, y + 8, w * .48, h * .55, pen, brush).setZValue(2)
            scene.addEllipse(x + w * .55, y + 20, w * .40, h * .42, pen, brush).setZValue(2)
        else:
            scene.addRect(x, y, w, h, pen, brush).setZValue(2)

    def short_interface_label(self, value: Any) -> str:
        """Return a compact topology label while preserving full names in tables/details."""
        text = str(value or "").strip()
        if not text:
            return ""
        compact = re.sub(r"\s+", "", text)
        replacements = [
            (r"(?i)^TwentyFiveGigabitEthernet", "twe"),
            (r"(?i)^TwentyFiveGigE", "twe"),
            (r"(?i)^TwentyFiveGig", "twe"),
            (r"(?i)^FortyGigabitEthernet", "fo"),
            (r"(?i)^FortyGigE", "fo"),
            (r"(?i)^TenGigabitEthernet", "te"),
            (r"(?i)^TenGigE", "te"),
            (r"(?i)^GigabitEthernet", "g"),
            (r"(?i)^GigabyteEthernet", "g"),
            (r"(?i)^FastEthernet", "f"),
            (r"(?i)^Ethernet", "e"),
            (r"(?i)^Serial", "s"),
            (r"(?i)^Loopback", "lo"),
            (r"(?i)^Port-channel", "po"),
            (r"(?i)^PortChannel", "po"),
            (r"(?i)^Vlan", "vlan"),
            (r"(?i)^Management", "mgmt"),
            (r"(?i)^Mgmt", "mgmt"),
        ]
        for pattern, prefix in replacements:
            if re.match(pattern, compact):
                return re.sub(pattern, prefix, compact, count=1)
        # Common already-short forms should simply be normalized to lower case.
        if re.match(r"(?i)^(e|g|gi|ge|te|f|fa|s|lo|po|vlan|mgmt)\d", compact):
            return compact.lower().replace("gi", "g", 1).replace("ge", "g", 1).replace("fa", "f", 1)
        return compact

    def edge_point(self, a: Dict[str, Any], b: Dict[str, Any]) -> Tuple[float, float]:
        ax = a["x"] + a["w"] / 2; ay = a["y"] + a["h"] / 2
        bx = b["x"] + b["w"] / 2; by = b["y"] + b["h"] / 2
        dx = bx - ax; dy = by - ay
        if abs(dx) < 0.001 and abs(dy) < 0.001:
            return ax, ay
        # Intersect ray with the node bounding rectangle. This keeps link lines
        # outside device icons instead of running through their centers.
        scale_x = (a["w"] / 2) / abs(dx) if abs(dx) > 0.001 else float("inf")
        scale_y = (a["h"] / 2) / abs(dy) if abs(dy) > 0.001 else float("inf")
        scale = min(scale_x, scale_y)
        return ax + dx * scale, ay + dy * scale

    def populate_topology_visualization(self) -> None:
        if not hasattr(self, "topology_scene"):
            return
        scene = self.topology_scene
        scene.clear()
        nodes, links = self.normalized_topology_nodes_links()
        roles = theme_visual_roles(getattr(self, "current_qt_theme", normalize_qt_theme(self.settings.get("theme", "darkly"))))
        bg = "#343434"
        scene.setBackgroundBrush(QBrush(QColor(bg)))
        if hasattr(self, "topology_graphics"):
            self.topology_graphics.setStyleSheet(f"background-color: {bg}; border: 1px solid #555555;")
        if not nodes:
            self.topology_detail.setMarkdown("# Topology Details\n\nNo topology data is available for this lab yet.")
            text_item = scene.addText("No topology visualization available.")
            text_item.setDefaultTextColor(QColor("#d1d5db"))
            return

        node_map: Dict[str, Dict[str, Any]] = {}
        cols = max(2, min(4, int(len(nodes) ** 0.5) + 1))
        scale = self.ui_scale_factor() if hasattr(self, "ui_scale_factor") else 1.0
        spacing_x = int(320 * scale)
        spacing_y = int(230 * scale)
        origin_x = int(90 * scale)
        origin_y = int(90 * scale)
        width = int(96 * scale)
        height = int(72 * scale)

        line_pen = QPen(QColor("#f2f2f2")); line_pen.setWidth(max(2, int(3 * scale))); line_pen.setCosmetic(True)
        node_pen = QPen(QColor("#eeeeee")); node_pen.setWidth(max(1, int(2 * scale))); node_pen.setCosmetic(True)
        node_brush = QBrush(QColor("#4b5563"))
        label_bg = QBrush(QColor("#343434"))
        link_font = QFont(); link_font.setPointSizeF(max(9.0, min(16.0, 10.5 * scale)))
        node_name_font = QFont(); node_name_font.setPointSizeF(max(10.0, min(18.0, 11.5 * scale))); node_name_font.setBold(True)
        node_kind_font = QFont(); node_kind_font.setPointSizeF(max(9.0, min(15.0, 10.0 * scale)))

        for idx, node in enumerate(nodes):
            name = str(node.get("name", f"Node{idx+1}"))
            row = idx // cols; col = idx % cols
            # Stagger alternate rows to reduce label/link overlap on dense topologies.
            x = origin_x + col * spacing_x + (row % 2) * 70
            y = origin_y + row * spacing_y
            kind = self.topology_node_kind(node)
            node_map[name] = {"x": x, "y": y, "w": width, "h": height, "data": node, "kind": kind}

        drawn_links = 0
        label_offsets: Dict[Tuple[int, int], int] = {}
        for link in links:
            a_name = str(link.get("a_node") or link.get("device_a") or link.get("a") or "")
            b_name = str(link.get("b_node") or link.get("device_b") or link.get("b") or "")
            a = node_map.get(a_name); b = node_map.get(b_name)
            if not a or not b:
                continue
            x1, y1 = self.edge_point(a, b)
            x2, y2 = self.edge_point(b, a)
            line_item = scene.addLine(x1, y1, x2, y2, line_pen)
            line_item.setZValue(1)
            drawn_links += 1
            a_label = self.short_interface_label(link.get('a_interface', link.get('interface_a','')))
            b_label = self.short_interface_label(link.get('b_interface', link.get('interface_b','')))
            label = f"{a_label} ↔ {b_label}"
            if label.strip() != "↔":
                # Offset labels perpendicular to the link. If multiple links share
                # the same node pair, stack their labels rather than overlapping.
                mx = (x1 + x2) / 2; my = (y1 + y2) / 2
                dx = x2 - x1; dy = y2 - y1
                length = max((dx * dx + dy * dy) ** 0.5, 1.0)
                nx = -dy / length; ny = dx / length
                key = tuple(sorted((hash(a_name), hash(b_name))))
                idx = label_offsets.get(key, 0); label_offsets[key] = idx + 1
                offset = 22 + (idx * 18)
                tx = scene.addText(label)
                tx.setFont(link_font)
                tx.setDefaultTextColor(QColor("#ffffff"))
                tx.setZValue(4)
                tx.setPos(mx + nx * offset - (48 * scale), my + ny * offset - (14 * scale))
                rect = tx.boundingRect().adjusted(-5, -2, 5, 2)
                bg_item = scene.addRect(rect.translated(tx.pos()), QPen(QColor("#5f6368")), label_bg)
                bg_item.setZValue(3)

        for name, entry in node_map.items():
            x, y, w, h = entry["x"], entry["y"], entry["w"], entry["h"]
            node = entry.get("data") or {}
            kind = entry.get("kind", "device")
            icon = self.topology_icon_path(kind)
            if icon:
                pix = QPixmap(str(icon))
                if not pix.isNull():
                    pix = pix.scaled(int(w), int(h), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    item = scene.addPixmap(pix)
                    item.setZValue(2)
                    item.setPos(x + (w - pix.width()) / 2, y)
                else:
                    self.draw_topology_fallback_node(scene, kind, x, y, w, h, node_pen, node_brush)
            else:
                self.draw_topology_fallback_node(scene, kind, x, y, w, h, node_pen, node_brush)
            name_item = scene.addText(name)
            name_item.setFont(node_name_font)
            name_item.setDefaultTextColor(QColor("#ffffff"))
            name_item.setZValue(5)
            name_item.setPos(x + w / 2 - min((80 * scale), len(name) * (4.6 * scale)), y + h + (8 * scale))
            kind_item = scene.addText(kind.title())
            kind_item.setFont(node_kind_font)
            kind_item.setDefaultTextColor(QColor("#d1d5db"))
            kind_item.setZValue(5)
            kind_item.setPos(x + w / 2 - (38 * scale), y + h + (30 * scale))

        rect = scene.itemsBoundingRect()
        scene.setSceneRect(rect.adjusted(-110, -90, 110, 110))
        self.topology_graphics.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)
        self.topology_detail.setMarkdown(
            "# Topology Visualization\n\n"
            "The graphical view now uses bundled GNS3 symbols when available, with shape-based fallbacks for unknown device types. "
            "The table below remains the source of truth for exact interface and adapter/port mappings.\n\n"
            f"**Devices:** {len(nodes)}  \n**Links:** {len(links)}  \n**Rendered Links:** {drawn_links}"
        )

    def update_topology_detail(self, current_row: int, _current_col: int, _prev_row: int, _prev_col: int) -> None:
        if current_row < 0:
            return
        topo = self.topology_json() if hasattr(self, "topology_json") else {}
        _nodes, links = self.normalized_topology_nodes_links() if hasattr(self, "normalized_topology_nodes_links") else ([], [])
        if current_row >= len(links):
            return
        link = links[current_row]
        a_node = link.get("device_a") or link.get("a") or link.get("a_node") or ""
        b_node = link.get("device_b") or link.get("b") or link.get("b_node") or ""
        a_if = link.get("interface_a") or link.get("a_interface") or ""
        b_if = link.get("interface_b") or link.get("b_interface") or ""
        purpose = link.get("purpose") or link.get("segment") or "No purpose/segment text provided."
        a_g = link.get("gns3_a") or link.get("a_gns3") or f"adapter {link.get('a_gns3_adapter', link.get('a_adapter', ''))} port {link.get('a_gns3_port', link.get('a_port', ''))}"
        b_g = link.get("gns3_b") or link.get("b_gns3") or f"adapter {link.get('b_gns3_adapter', link.get('b_adapter', ''))} port {link.get('b_gns3_port', link.get('b_port', ''))}"
        self.topology_detail.setMarkdown(
            f"# Link Detail\n\n**Endpoint A:** `{a_node}` — `{a_if}`  \n**Endpoint B:** `{b_node}` — `{b_if}`  \n**Purpose:** {purpose}  \n**GNS3 A:** {a_g}  \n**GNS3 B:** {b_g}"
        )

    def current_project_server(self) -> str:
        value = ""
        if hasattr(self, "project_server_box"):
            value = self.project_server_box.text().strip()
        return value or str(self.settings.get("gns3_server") or "").strip()

    def local_project_index(self) -> Dict[str, Path]:
        index: Dict[str, Path] = {}
        roots = [self.output_dir(), self.output_dir() / "external_gns3_projects"]
        for root in roots:
            if not root.exists():
                continue
            for metadata_path in root.rglob("metadata.json"):
                data = read_json(metadata_path)
                deployment = data.get("deployment", {}) if isinstance(data, dict) else {}
                project_id = str(deployment.get("gns3_project_id") or deployment.get("project_id") or "").strip()
                if project_id:
                    index[project_id] = metadata_path.parent
        return index

    def refresh_server_projects(self) -> None:
        server = self.current_project_server()
        if not server:
            QMessageBox.warning(self, "GNS3 server missing", "Configure a GNS3 server URL in Settings or enter one on this page.")
            return
        if hasattr(self, "project_detail"):
            self.project_detail.setMarkdown(f"# Server Projects\n\nRefreshing projects from `{server}`...")
        worker = ProjectManagerWorker("list", server)
        self.track_thread(worker, "project_worker")
        worker.finished.connect(self.on_project_manager_finished)
        worker.start()

    def on_project_manager_finished(self, ok: bool, message: str, details: Dict[str, Any]) -> None:
        self.statusBar().showMessage(message)
        if details.get("action") == "list" and ok:
            self.server_project_rows = {str(p.get("project_id")): p for p in details.get("projects", []) if p.get("project_id")}
            self.apply_project_filter()
            return
        if hasattr(self, "project_detail"):
            lines = ["# Server Project Action", f"**Last action:** {message}"]
            results = details.get("results") or {}
            for project_id, result in results.items():
                status = "ok"
                if isinstance(result, dict) and (result.get("error") or result.get("ok") is False):
                    status = result.get("error") or "completed with node errors"
                lines.append(f"- `{project_id}`: {status}")
            self.project_detail.setMarkdown("\n".join(lines))
        if not ok:
            QMessageBox.warning(self, "GNS3 project action failed", message)
        else:
            self.refresh_server_projects()

    def apply_project_filter(self) -> None:
        if not hasattr(self, "projects_table"):
            return
        local_index = self.local_project_index()
        filter_text = self.project_filter_combo.currentText() if hasattr(self, "project_filter_combo") else "All server projects"
        projects = list(self.server_project_rows.values())
        filtered: List[Dict[str, Any]] = []
        for project in projects:
            project_id = str(project.get("project_id") or "")
            generated = project_id in local_index or self.project_name_looks_generated(project)
            running = int(project.get("running_node_count") or 0) > 0 or str(project.get("status", "")).lower() in {"opened", "started"}
            if filter_text == "Generated by this app" and not generated:
                continue
            if filter_text == "Running projects only" and not running:
                continue
            if filter_text == "Stopped projects only" and running:
                continue
            filtered.append({**project, "_generated": generated, "_local_dir": str(local_index.get(project_id, ""))})
        self.populate_projects_table(filtered)

    def project_name_looks_generated(self, project: Dict[str, Any]) -> bool:
        name = str(project.get("name") or project.get("project_name") or "").lower()
        return any(token in name for token in ["ccnp", "encor", "gns3 ccnp", "lab_"])

    def populate_projects_table(self, projects: List[Dict[str, Any]]) -> None:
        self.projects_table.setRowCount(0)
        for row, project in enumerate(sorted(projects, key=lambda p: str(p.get("name") or p.get("project_name") or "").lower())):
            self.projects_table.insertRow(row)
            project_id = str(project.get("project_id") or "")
            values = [
                str(project.get("name") or project.get("project_name") or "Unnamed project"),
                str(project.get("status") or "unknown"),
                str(project.get("node_count") or 0),
                str(project.get("running_node_count") or 0),
                "yes" if project.get("_generated") else "no",
                project_id,
                str(project.get("last_updated") or project.get("updated_at") or project.get("created_at") or ""),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, project_id)
                self.projects_table.setItem(row, col, item)
        self.projects_table.resizeColumnsToContents()
        if projects:
            self.projects_table.selectRow(0)
        else:
            self.project_detail.setMarkdown("# Server Projects\n\nNo projects match the current filter.")

    def selected_project_ids(self) -> List[str]:
        if not hasattr(self, "projects_table"):
            return []
        ids: List[str] = []
        for item in self.projects_table.selectedItems():
            project_id = str(item.data(Qt.UserRole) or "").strip()
            if project_id and project_id not in ids:
                ids.append(project_id)
        return ids

    def selected_project(self) -> Optional[Dict[str, Any]]:
        ids = self.selected_project_ids()
        if not ids:
            return None
        return self.server_project_rows.get(ids[0])

    def update_project_detail(self, current_row: int, _current_col: int, _prev_row: int, _prev_col: int) -> None:
        if current_row < 0 or not hasattr(self, "projects_table"):
            return
        item = self.projects_table.item(current_row, 0)
        if not item:
            return
        project_id = str(item.data(Qt.UserRole) or "")
        project = self.server_project_rows.get(project_id, {})
        nodes = project.get("nodes") or []
        lines = ["# Project Detail"]
        lines.append(f"**Name:** `{project.get('name') or project.get('project_name') or 'Unnamed project'}`")
        lines.append(f"**Project ID:** `{project_id}`")
        lines.append(f"**Status:** `{project.get('status', 'unknown')}`")
        lines.append(f"**Nodes:** {project.get('node_count', len(nodes))} total / {project.get('running_node_count', 0)} running")
        if project.get("node_error"):
            lines.append(f"\nNode details could not be loaded: `{project.get('node_error')}`")
        if nodes:
            lines.append("\n## Nodes")
            for node in nodes:
                name = node.get("name") or node.get("node_name") or node.get("node_id")
                console = node.get("console") or node.get("console_port") or ""
                console_host = node.get("console_host") or ""
                console_text = f" — console {console_host}:{console}" if console else ""
                lines.append(f"- `{name}`: {node.get('status', 'unknown')}{console_text}")
        if project_id in self.local_project_index():
            lines.append(f"\nLocal generated-lab metadata found at `{self.local_project_index()[project_id]}`.")
        else:
            lines.append("\nThis project was not generated by NetOps Labs, so guided lab content may be unavailable. Server lifecycle and console tools are still available.")
        self.project_detail.setMarkdown("\n".join(lines))

    def run_project_manager_action(self, action: str) -> None:
        project_ids = self.selected_project_ids()
        if not project_ids:
            QMessageBox.information(self, "No project selected", "Select one or more GNS3 projects first.")
            return
        server = self.current_project_server()
        worker = ProjectManagerWorker(action, server, project_ids)
        self.track_thread(worker, "project_worker")
        worker.finished.connect(self.on_project_manager_finished)
        worker.start()

    def confirm_delete_selected_projects(self) -> None:
        project_ids = self.selected_project_ids()
        if not project_ids:
            QMessageBox.information(self, "No project selected", "Select one or more GNS3 projects first.")
            return
        names = []
        for project_id in project_ids:
            project = self.server_project_rows.get(project_id, {})
            names.append(str(project.get("name") or project.get("project_name") or project_id))
        server = self.current_project_server()
        response = QMessageBox.question(
            self,
            "Delete selected GNS3 projects?",
            "You are about to delete " + str(len(project_ids)) + " GNS3 project(s) from " + server + ".\n\n"
            + "\n".join("- " + name for name in names[:12])
            + ("\n..." if len(names) > 12 else "")
            + "\n\nThis removes the projects from the GNS3 server. Local generated lab folders will not be deleted.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if response == QMessageBox.Yes:
            self.run_project_manager_action("delete")

    def generated_project_ids(self) -> List[str]:
        local_index = self.local_project_index()
        generated_ids: List[str] = []
        for project_id, project in self.server_project_rows.items():
            if project_id in local_index or self.project_name_looks_generated(project):
                generated_ids.append(project_id)
        return generated_ids

    def confirm_delete_generated_projects(self) -> None:
        project_ids = self.generated_project_ids()
        if not project_ids:
            QMessageBox.information(self, "No generated projects found", "No server projects currently match this app's generated-lab filter. Refresh the project list if needed.")
            return
        names = []
        for project_id in project_ids:
            project = self.server_project_rows.get(project_id, {})
            names.append(str(project.get("name") or project.get("project_name") or project_id))
        server = self.current_project_server()
        response = QMessageBox.question(
            self,
            "Delete all generated GNS3 projects?",
            "You are about to delete " + str(len(project_ids)) + " GNS3 project(s) from " + server + " that appear to have been generated by this application.\n\n"
            + "\n".join("- " + name for name in names[:20])
            + ("\n..." if len(names) > 20 else "")
            + "\n\nThis removes the projects from the GNS3 server. Local generated lab folders will not be deleted. External projects that only match the naming convention may be included.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if response == QMessageBox.Yes:
            worker = ProjectManagerWorker("delete", server, project_ids)
            self.track_thread(worker, "project_worker")
            worker.finished.connect(self.on_project_manager_finished)
            worker.start()

    def connect_selected_server_project(self) -> None:
        project = self.selected_project()
        if not project:
            QMessageBox.information(self, "No project selected", "Select a GNS3 project first.")
            return
        project_id = str(project.get("project_id") or "")
        local_dir = self.local_project_index().get(project_id)
        if local_dir:
            self.load_workspace(local_dir)
        else:
            self.load_workspace(self.create_external_project_workspace(project))
        self.stack.setCurrentIndex(1)
        self.select_workspace_tab("Consoles")

    def create_external_project_workspace(self, project: Dict[str, Any]) -> Path:
        server = self.current_project_server()
        project_id = str(project.get("project_id") or "")
        name = str(project.get("name") or project.get("project_name") or project_id or "external_project")
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "external_project"
        lab_dir = self.output_dir() / "external_gns3_projects" / f"{safe_name}_{project_id[:8]}"
        lab_dir.mkdir(parents=True, exist_ok=True)
        nodes: Dict[str, Dict[str, Any]] = {}
        for node in project.get("nodes") or []:
            node_id = str(node.get("node_id") or node.get("id") or "")
            node_name = str(node.get("name") or node.get("node_name") or node_id)
            if not node_id or not node_name:
                continue
            nodes[node_name] = {
                "node_id": node_id,
                "status": node.get("status"),
                "node_type": node.get("node_type"),
                "console": node.get("console") or node.get("console_port"),
                "console_host": node.get("console_host"),
                "console_type": node.get("console_type"),
            }
        metadata = {
            "schema_version": "3.0.0",
            "lab_mode": "external_gns3_project",
            "title": name,
            "project": {"title": name, "scenario_id": "external_gns3_project", "gns3_server": server},
            "deployment": {"gns3_server": server, "gns3_project_id": project_id, "project_id": project_id, "nodes": nodes},
            "documents": {"External Project Notice": "README.md"},
            "config_sets": {},
        }
        (lab_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        (lab_dir / "README.md").write_text(
            "# External GNS3 Project\n\n"
            "This project was not generated by NetOps Labs, so guided lab content, answer keys, and generated configs are unavailable.\n\n"
            "The app can still manage server lifecycle actions and open console endpoints discovered from the GNS3 API.\n",
            encoding="utf-8",
        )
        return lab_dir

    def deployment_metadata(self) -> Dict[str, Any]:
        return self.workspace_metadata.get("deployment", {}) if self.workspace_metadata else {}

    def gns3_server_for_lab(self) -> str:
        deployment = self.deployment_metadata()
        project = self.workspace_metadata.get("project", {}) if self.workspace_metadata else {}
        return str(deployment.get("gns3_server") or project.get("gns3_server") or self.settings.get("gns3_server") or "").strip()

    def gns3_project_id_for_lab(self) -> str:
        deployment = self.deployment_metadata()
        return str(deployment.get("gns3_project_id") or deployment.get("project_id") or "").strip()

    def gns3_node_ids_for_lab(self) -> List[str]:
        deployment = self.deployment_metadata()
        nodes = deployment.get("nodes", {}) if isinstance(deployment, dict) else {}
        result: List[str] = []
        if isinstance(nodes, dict):
            for info in nodes.values():
                if isinstance(info, dict) and info.get("node_id"):
                    result.append(str(info.get("node_id")))
        elif isinstance(nodes, list):
            for info in nodes:
                if isinstance(info, dict) and info.get("node_id"):
                    result.append(str(info.get("node_id")))
        return result

    def populate_lifecycle_status(self, details: Optional[Dict[str, Any]] = None, message: str = "") -> None:
        if not hasattr(self, "lifecycle_status"):
            return
        server = self.gns3_server_for_lab()
        project_id = self.gns3_project_id_for_lab()
        node_ids = self.gns3_node_ids_for_lab()
        lines = ["# Deployment Lifecycle"]
        if message:
            lines.append(f"\n**Last action:** {message}")
        lines.append(f"\n**GNS3 server:** `{server or 'not configured'}`")
        lines.append(f"**Project ID:** `{project_id or 'not available'}`")
        lines.append(f"**Tracked nodes:** {len(node_ids)}")
        if not project_id:
            lines.append("\nThis lab does not currently have a GNS3 project ID in its metadata. Generate/deploy the lab first, then reload the workspace.")
        if details:
            project = details.get("project") or {}
            if project:
                lines.append("\n## Project")
                lines.append(f"- Name: `{project.get('name', project.get('project_name', 'unknown'))}`")
                lines.append(f"- Status: `{project.get('status', 'unknown')}`")
            nodes = details.get("nodes") or {}
            if nodes:
                lines.append("\n## Nodes")
                for node_id, info in nodes.items():
                    if isinstance(info, dict):
                        name = info.get("name") or info.get("node_name") or node_id
                        status = info.get("status") or info.get("error") or "requested"
                        lines.append(f"- `{name}` / `{node_id}`: {status}")
                    else:
                        lines.append(f"- `{node_id}`: {info}")
        self.lifecycle_status.setMarkdown("\n".join(lines))

    def run_lifecycle_action(self, action: str) -> None:
        if not self.last_lab_dir:
            QMessageBox.information(self, "No lab loaded", "Load or generate a deployed lab first.")
            return
        server = self.gns3_server_for_lab()
        project_id = self.gns3_project_id_for_lab()
        node_ids = self.gns3_node_ids_for_lab()
        if not server or not project_id:
            QMessageBox.warning(self, "Deployment metadata missing", "The loaded lab does not include enough GNS3 deployment metadata for lifecycle control.")
            return
        self.lifecycle_status.setMarkdown(f"# Deployment Lifecycle\n\nRunning `{action}` against project `{project_id}`...")
        worker = LifecycleWorker(action, server, project_id, node_ids)
        self.track_thread(worker, "lifecycle_worker")
        worker.finished.connect(self.on_lifecycle_finished)
        worker.start()

    def on_lifecycle_finished(self, ok: bool, message: str, details: Dict[str, Any]) -> None:
        self.populate_lifecycle_status(details, message)
        self.statusBar().showMessage(message)
        if not ok:
            QMessageBox.warning(self, "Lifecycle action failed", message)

    def confirm_delete_gns3_project(self) -> None:
        project_id = self.gns3_project_id_for_lab()
        if not project_id:
            QMessageBox.information(self, "No deployed project", "No GNS3 project ID is available for the loaded lab.")
            return
        response = QMessageBox.question(
            self,
            "Delete GNS3 project?",
            "This deletes the deployed GNS3 project from the configured server. Local generated lab files will be kept. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if response == QMessageBox.Yes:
            self.run_lifecycle_action("delete")

    def console_nodes(self) -> Dict[str, Dict[str, Any]]:
        deployment = self.workspace_metadata.get("deployment", {}) if self.workspace_metadata else {}
        nodes = deployment.get("nodes", {}) if isinstance(deployment, dict) else {}
        server = str(deployment.get("gns3_server") or self.settings.get("gns3_server") or "").strip()
        fallback_host = "127.0.0.1"
        if server:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(server)
                if parsed.hostname and parsed.hostname not in {"0.0.0.0", "::"}:
                    fallback_host = parsed.hostname
            except Exception:
                pass
        result: Dict[str, Dict[str, Any]] = {}
        iterable = nodes.items() if isinstance(nodes, dict) else []
        for name, info in iterable:
            if not isinstance(info, dict):
                continue
            port = info.get("console") or info.get("console_port")
            if port in {None, ""}:
                continue
            host = str(info.get("console_host") or info.get("host") or fallback_host).strip()
            if host in {"0.0.0.0", "::", ""}:
                host = fallback_host
            try:
                result[str(name)] = {"host": host, "port": int(port), **info}
            except Exception:
                continue
        return result

    def populate_console_devices(self) -> None:
        if not hasattr(self, "console_device_list"):
            return
        self.console_device_list.clear()
        for name, info in sorted(self.console_nodes().items()):
            item = QListWidgetItem(f"{name}  ({info['host']}:{info['port']})")
            item.setData(Qt.UserRole, name)
            self.console_device_list.addItem(item)
        if self.console_device_list.count():
            self.console_device_list.setCurrentRow(0)
        else:
            self.console_status.setText("No console endpoints are available in this lab metadata yet. Generate/deploy with node start enabled, then reload the workspace if needed.")

    def console_device_selected(self, current: Optional[QListWidgetItem], _previous: Optional[QListWidgetItem]) -> None:
        if not current:
            return
        name = current.data(Qt.UserRole)
        info = self.console_nodes().get(name, {})
        self.console_status.setText(f"Selected {name} — {info.get('host','?')}:{info.get('port','?')}")

    def active_console_name(self) -> Optional[str]:
        widget = self.console_tab_widget.currentWidget() if hasattr(self, 'console_tab_widget') else None
        if not widget:
            return None
        return widget.property("device_name")

    def open_selected_console(self) -> None:
        item = self.console_device_list.currentItem() if hasattr(self, 'console_device_list') else None
        if not item:
            QMessageBox.information(self, "No device selected", "Select a device with an available console first.")
            return
        self.open_console_for_device(str(item.data(Qt.UserRole)))

    def open_console_for_device(self, device_name: str) -> None:
        info = self.console_nodes().get(device_name)
        if not info:
            QMessageBox.warning(self, "Console unavailable", f"No console metadata found for {device_name}.")
            return
        if device_name in self.console_tabs:
            self.console_tab_widget.setCurrentWidget(self.console_tabs[device_name]["widget"])
            return
        widget = QWidget(); layout = QVBoxLayout(widget)
        header = QLabel(f"{device_name} — {info['host']}:{info['port']}")
        header.setObjectName("Muted")
        output = QPlainTextEdit(); output.setReadOnly(True); output.setWordWrapMode(QTextOption.NoWrap)
        output.setFont(QFont("Courier New"))
        layout.addWidget(header)
        layout.addWidget(output, 1)
        widget.setProperty("device_name", device_name)
        idx = self.console_tab_widget.addTab(widget, device_name)
        self.console_tab_widget.setCurrentIndex(idx)
        self.console_tabs[device_name] = {"widget": widget, "output": output, "header": header, "info": info}
        self.start_console_worker(device_name, info['host'], info['port'])

    def start_console_worker(self, device_name: str, host: str, port: int) -> None:
        if device_name in self.console_workers:
            self.stop_console_worker(device_name, remove_tab=False)
        worker = ConsoleWorker(device_name, host, int(port))
        worker.output.connect(self.on_console_output)
        worker.status.connect(self.on_console_status)
        self.track_thread(worker)
        self.console_workers[device_name] = worker
        worker.start()

    def stop_console_worker(self, device_name: str, remove_tab: bool = True) -> None:
        worker = self.console_workers.pop(device_name, None)
        if worker:
            worker.stop()
            if not worker.wait(3000):
                self._retired_console_workers.append(worker)
        if remove_tab:
            tab = self.console_tabs.pop(device_name, None)
            if tab:
                idx = self.console_tab_widget.indexOf(tab["widget"])
                if idx >= 0:
                    self.console_tab_widget.removeTab(idx)

    def on_console_output(self, device_name: str, text: str) -> None:
        tab = self.console_tabs.get(device_name)
        if not tab:
            return
        tab["output"].appendPlainText(text.rstrip("\n"))

    def on_console_status(self, device_name: str, status: str) -> None:
        if self.active_console_name() == device_name:
            self.console_status.setText(f"{device_name}: {status}")
        tab = self.console_tabs.get(device_name)
        if tab:
            tab["header"].setText(f"{device_name} — {status}")

    def send_console_text(self, add_newline: bool = False) -> None:
        name = self.active_console_name()
        if not name or name not in self.console_workers:
            self.console_status.setText("Open a console tab first.")
            return
        text = self.console_input.text()
        if add_newline:
            text += "\n"
        if not text:
            return
        self.console_workers[name].queue_text(text)
        self.console_input.clear()

    def send_console_ctrl_l(self) -> None:
        name = self.active_console_name()
        if not name or name not in self.console_workers:
            self.console_status.setText("Open a console tab first.")
            return
        self.console_workers[name].queue_text(chr(12))

    def reconnect_selected_console(self) -> None:
        name = self.active_console_name()
        if not name:
            self.open_selected_console()
            return
        info = self.console_nodes().get(name)
        if not info:
            return
        self.start_console_worker(name, info['host'], info['port'])

    def close_selected_console(self) -> None:
        name = self.active_console_name()
        if not name:
            return
        self.close_console_tab(name)

    def close_console_tab_index(self, index: int) -> None:
        widget = self.console_tab_widget.widget(index)
        name = widget.property("device_name") if widget else None
        if name:
            self.close_console_tab(name)

    def close_console_tab(self, device_name: str) -> None:
        self.stop_console_worker(device_name, remove_tab=True)
        if hasattr(self, "console_status"):
            self.console_status.setText(f"Closed console for {device_name}.")

    def close_all_consoles(self) -> None:
        for name in list(self.console_tabs.keys()):
            self.close_console_tab(name)

    def populate_reports(self) -> None:
        if not hasattr(self, "reports_view"):
            return
        if not self.last_lab_dir:
            self.reports_view.setMarkdown("# Reports\n\nNo generated lab is loaded.")
            return
        sections = []
        for title, filename in [
            ("Validation Report", "validation_report.md"),
            ("Generation Summary", "generation_summary.md"),
            ("Metadata", "metadata.json"),
        ]:
            path = self.last_lab_dir / filename
            if not path.exists():
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except Exception as exc:
                content = f"Could not read {filename}: {exc}"
            if filename.endswith(".json"):
                content = "```json\n" + content + "\n```"
            sections.append(f"# {title}\n\n{content}")
        if sections:
            self.reports_view.setMarkdown("\n\n---\n\n".join(sections))
        else:
            self.reports_view.setMarkdown("# Reports\n\nNo validation or generation reports were found in this lab folder.")

    def show_about(self) -> None:
        QMessageBox.information(
            self,
            "About NetOps Labs",
            f"NetOps Labs {APP_VERSION} Qt GUI. "
            "The legacy Tk GUI remains packaged as a fallback.",
        )


def main() -> int:
    qInstallMessageHandler(qt_message_handler)
    app = QApplication(sys.argv)
    app.setApplicationName("NetOps Labs")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
