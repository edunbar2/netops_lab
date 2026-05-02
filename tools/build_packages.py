#!/usr/bin/env python3
"""Build NetOps Labs release artifacts.

The script is intentionally stdlib-heavy so GitHub Actions can run it on all
three hosted OS families with only PyInstaller added as a build dependency.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
PYINSTALLER_DIST = DIST_DIR / "pyinstaller"
BUILD_DIR = ROOT / "build" / "packaging"
RELEASE_DIR = DIST_DIR / "release"

DATA_ITEMS = [
    "assets",
    "catalogs",
    "config",
    "config_templates",
    "docs",
    "scripts",
    "CHANGELOG.md",
    "README.md",
    "VERSION",
    "requirements.txt",
    "requirements-pyside6.txt",
    "requirements-tk-legacy.txt",
]
RESOURCE_JUNK_DIRS = {"__MACOSX"}
RESOURCE_JUNK_FILES = {".DS_Store"}


def run(cmd: List[str], *, cwd: Path = ROOT) -> None:
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd), check=True)


def read_version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def platform_id() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def arch_id() -> str:
    machine = platform.machine().lower().replace("amd64", "x86_64")
    return machine or "unknown"


def deb_architecture() -> str:
    machine = arch_id()
    if machine == "x86_64":
        return "amd64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    return machine


def rpm_architecture() -> str:
    machine = arch_id()
    if machine in {"aarch64", "arm64"}:
        return "aarch64"
    return machine


def artifact_stem(version: str) -> str:
    return f"NetOpsLabs-{version}-{platform_id()}-{arch_id()}"


def clean_build_dirs() -> None:
    for path in [PYINSTALLER_DIST, BUILD_DIR, RELEASE_DIR]:
        if path.exists():
            shutil.rmtree(path)
    PYINSTALLER_DIST.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)


def is_resource_junk(path: Path) -> bool:
    return (
        any(part in RESOURCE_JUNK_DIRS for part in path.parts)
        or path.name.startswith("._")
        or path.name in RESOURCE_JUNK_FILES
    )


def copy_data_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*"):
        rel = path.relative_to(source)
        if is_resource_junk(rel):
            continue
        target = destination / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file() or path.is_symlink():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def staged_data_source(item: str, source: Path) -> Path:
    if source.is_dir():
        destination = BUILD_DIR / "data-stage" / item
        copy_data_tree(source, destination)
        return destination
    return source


def add_data_args() -> List[str]:
    separator = ";" if sys.platform == "win32" else ":"
    args: List[str] = []
    for item in DATA_ITEMS:
        source = ROOT / item
        if source.exists():
            source = staged_data_source(item, source)
            args.extend(["--add-data", f"{source}{separator}{item}"])
    return args


def pyinstaller_base(
    name: str,
    *,
    windowed: bool,
    include_data: bool = False,
    include_qt_svg: bool = False,
    onefile: bool = False,
) -> List[str]:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
    ]
    if onefile:
        cmd.append("--onefile")
    else:
        cmd.extend(["--onedir", "--contents-directory", "."])
    cmd.extend(
        [
            "--distpath",
            str(PYINSTALLER_DIST),
            "--workpath",
            str(BUILD_DIR / "pyinstaller-work"),
            "--specpath",
            str(BUILD_DIR / "pyinstaller-spec"),
            "--name",
            name,
        ]
    )
    if windowed:
        cmd.append("--windowed")
    else:
        cmd.append("--console")
    if include_qt_svg:
        cmd.extend(["--hidden-import", "PySide6.QtSvg"])
    if include_data:
        cmd.extend(add_data_args())
    return cmd


def gui_app_name() -> str:
    if sys.platform == "linux":
        return "netops-labs"
    return "NetOps Labs"


def generator_name() -> str:
    return "netops-lab-generator"


def macos_codesign_identity() -> str:
    return os.environ.get("MACOS_CODESIGN_IDENTITY", "-").strip() or "-"


def macos_codesign_command(codesign: str, identity: str, target: Path, *, code: bool = True) -> List[str]:
    cmd = [codesign, "--force", "--sign", identity]
    if identity != "-":
        if code:
            cmd.extend(["--options", "runtime"])
        cmd.append("--timestamp")
    cmd.append(str(target))
    return cmd


def is_macho_file(path: Path) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    try:
        magic = path.read_bytes()[:4]
    except OSError:
        return False
    return magic in {
        b"\xfe\xed\xfa\xce",
        b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
        b"\xca\xfe\xba\xbf",
        b"\xbf\xba\xfe\xca",
    }


def macos_macho_files(app_bundle: Path) -> List[Path]:
    files = [path for path in app_bundle.rglob("*") if is_macho_file(path)]
    return sorted(files, key=lambda path: len(path.relative_to(app_bundle).parts), reverse=True)


def sign_macos_app_bundle(app_bundle: Path) -> None:
    """Ad-hoc sign macOS bundles unless a Developer ID identity is supplied.

    PyInstaller creates Mach-O binaries inside the app bundle, and this script
    copies the generator bundle into the GUI bundle after PyInstaller finishes.
    Signing actual Mach-O files after that copy prevents invalid nested
    signatures that macOS can report as a damaged app. Avoid codesign --deep
    for signing because PyInstaller bundles may contain framework support
    directories that codesign tries to treat as invalid nested bundles.
    """
    if sys.platform != "darwin":
        return
    codesign = shutil.which("codesign")
    if not codesign:
        raise SystemExit("codesign was not found; cannot prepare macOS app bundle.")
    identity = macos_codesign_identity()
    for macho in macos_macho_files(app_bundle):
        run(macos_codesign_command(codesign, identity, macho))
    run(macos_codesign_command(codesign, identity, app_bundle))
    run([codesign, "--verify", "--deep", "--strict", "--verbose=2", str(app_bundle)])


def build_pyinstaller_apps() -> Path:
    gui_name = gui_app_name()
    run(
        pyinstaller_base(gui_name, windowed=True, include_data=True, include_qt_svg=True)
        + [str(ROOT / "gns3_ccnp_lab_gui_qt.py")]
    )
    run(
        pyinstaller_base(generator_name(), windowed=False, onefile=sys.platform == "darwin")
        + [str(ROOT / "gns3_ccnp_lab_generator.py")]
    )

    gui_bundle = pyinstaller_gui_bundle(gui_name)
    generator_bundle = PYINSTALLER_DIST / generator_name()
    if not gui_bundle.exists():
        raise SystemExit(f"PyInstaller GUI bundle not found: {gui_bundle}")
    if not generator_bundle.exists():
        raise SystemExit(f"PyInstaller generator bundle not found: {generator_bundle}")

    copy_generator_into_gui_bundle(gui_bundle, generator_bundle)
    sign_macos_app_bundle(gui_bundle)
    return gui_bundle


def pyinstaller_gui_bundle(gui_name: str) -> Path:
    if sys.platform == "darwin":
        app_bundle = PYINSTALLER_DIST / f"{gui_name}.app"
        if app_bundle.exists():
            return app_bundle
    return PYINSTALLER_DIST / gui_name


def gui_payload_dir(gui_bundle: Path) -> Path:
    if sys.platform == "darwin" and gui_bundle.suffix == ".app":
        return gui_bundle / "Contents" / "MacOS"
    return gui_bundle


def copy_tree_contents(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def copy_generator_into_gui_bundle(gui_bundle: Path, generator_bundle: Path) -> None:
    payload_dir = gui_payload_dir(gui_bundle)
    payload_dir.mkdir(parents=True, exist_ok=True)
    if generator_bundle.is_file():
        shutil.copy2(generator_bundle, payload_dir / generator_bundle.name)
        return
    copy_tree_contents(generator_bundle, payload_dir)


def zip_path(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if source.is_file():
            archive.write(source, source.name)
            return
        parent = source.parent
        for path in source.rglob("*"):
            if path.is_file() or path.is_symlink():
                archive.write(path, path.relative_to(parent))


def create_portable_zip(gui_bundle: Path, version: str) -> Path:
    output = RELEASE_DIR / f"{artifact_stem(version)}-portable.zip"
    zip_path(gui_bundle, output)
    return output


def create_source_zip(version: str) -> Path:
    output = RELEASE_DIR / f"NetOpsLabs-{version}-source.zip"
    exclude_dirs = {".git", ".venv", "__pycache__", "build", "dist", "generated_labs"}
    exclude_files = {"config/app_config.local.json", "config/template_overrides.local.json"}
    exclude_suffixes = {".pyc", ".pyo"}
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in ROOT.rglob("*"):
            rel = path.relative_to(ROOT)
            if any(part in exclude_dirs for part in rel.parts):
                continue
            if is_resource_junk(rel):
                continue
            if rel.as_posix() in exclude_files:
                continue
            if path.suffix in exclude_suffixes:
                continue
            if path.is_file():
                archive.write(path, Path(f"netops_labs_{version}") / rel)
    return output


def find_iscc() -> Optional[Path]:
    found = shutil.which("ISCC.exe") or shutil.which("iscc")
    if found:
        return Path(found)
    for root in [os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")]:
        if not root:
            continue
        candidate = Path(root) / "Inno Setup 6" / "ISCC.exe"
        if candidate.exists():
            return candidate
    return None


def create_windows_installer(gui_bundle: Path, version: str) -> Optional[Path]:
    iscc = find_iscc()
    if not iscc:
        print("WARN: Inno Setup was not found; skipping Windows installer.")
        return None

    setup_base = f"NetOpsLabs-{version}-windows-setup"
    iss_path = BUILD_DIR / "netops-labs.iss"
    app_exe = "NetOps Labs.exe"
    iss_path.write_text(
        textwrap.dedent(
            f"""
            [Setup]
            AppId={{{{93B1B1B5-3A7C-4C8A-8D57-6C042AA3A5A6}}}}
            AppName=NetOps Labs
            AppVersion={version}
            AppPublisher=NetOps Labs
            DefaultDirName={{autopf}}\\NetOps Labs
            DefaultGroupName=NetOps Labs
            DisableProgramGroupPage=yes
            OutputDir={RELEASE_DIR}
            OutputBaseFilename={setup_base}
            Compression=lzma2
            SolidCompression=yes
            WizardStyle=modern

            [Tasks]
            Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

            [Files]
            Source: "{gui_bundle}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

            [Icons]
            Name: "{{autoprograms}}\\NetOps Labs"; Filename: "{{app}}\\{app_exe}"
            Name: "{{autodesktop}}\\NetOps Labs"; Filename: "{{app}}\\{app_exe}"; Tasks: desktopicon

            [Run]
            Filename: "{{app}}\\{app_exe}"; Description: "Launch NetOps Labs"; Flags: nowait postinstall skipifsilent
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    run([str(iscc), str(iss_path)])
    output = RELEASE_DIR / f"{setup_base}.exe"
    return output if output.exists() else None


def linux_desktop_entry() -> str:
    return (
        textwrap.dedent(
            """
            [Desktop Entry]
            Type=Application
            Name=NetOps Labs
            Comment=Hands-on infrastructure training for networking, Linux, and security
            Exec=/opt/netops-labs/netops-labs
            Terminal=false
            Categories=Education;Network;Development;
            """
        ).strip()
        + "\n"
    )


def create_linux_deb(gui_bundle: Path, version: str) -> Optional[Path]:
    dpkg_deb = shutil.which("dpkg-deb")
    if not dpkg_deb:
        print("WARN: dpkg-deb was not found; skipping Linux .deb package.")
        return None

    package_root = BUILD_DIR / "deb-root"
    app_root = package_root / "opt" / "netops-labs"
    control_dir = package_root / "DEBIAN"
    desktop_dir = package_root / "usr" / "share" / "applications"
    bin_dir = package_root / "usr" / "local" / "bin"
    shutil.rmtree(package_root, ignore_errors=True)
    app_root.mkdir(parents=True)
    control_dir.mkdir(parents=True)
    desktop_dir.mkdir(parents=True)
    bin_dir.mkdir(parents=True)

    copy_tree_contents(gui_bundle, app_root)
    launcher = app_root / "netops-labs"
    if launcher.exists():
        launcher.chmod(0o755)
    symlink = bin_dir / "netops-labs"
    symlink.symlink_to("/opt/netops-labs/netops-labs")

    control_dir.joinpath("control").write_text(
        textwrap.dedent(
            f"""
            Package: netops-labs
            Version: {version}
            Section: education
            Priority: optional
            Architecture: {deb_architecture()}
            Maintainer: NetOps Labs
            Description: Hands-on infrastructure training for networking, Linux, and security.
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    desktop_dir.joinpath("netops-labs.desktop").write_text(linux_desktop_entry(), encoding="utf-8")
    output = RELEASE_DIR / f"{artifact_stem(version)}.deb"
    run([dpkg_deb, "--build", str(package_root), str(output)])
    return output if output.exists() else None


def create_linux_rpm(gui_bundle: Path, version: str) -> Optional[Path]:
    rpmbuild = shutil.which("rpmbuild")
    if not rpmbuild:
        print("WARN: rpmbuild was not found; skipping Linux .rpm package.")
        return None

    rpm_top = BUILD_DIR / "rpm"
    for subdir in ["BUILD", "BUILDROOT", "RPMS", "SOURCES", "SPECS", "SRPMS"]:
        (rpm_top / subdir).mkdir(parents=True, exist_ok=True)

    payload_root = BUILD_DIR / "rpm-payload"
    app_payload = payload_root / "netops-labs"
    shutil.rmtree(payload_root, ignore_errors=True)
    copy_tree_contents(gui_bundle, app_payload)
    launcher = app_payload / "netops-labs"
    if launcher.exists():
        launcher.chmod(0o755)

    spec_path = rpm_top / "SPECS" / "netops-labs.spec"
    desktop_entry = linux_desktop_entry().rstrip()
    spec_path.write_text(
        f"""Name: netops-labs
Version: {version}
Release: 1
Summary: Hands-on infrastructure training for networking, Linux, and security.
License: Proprietary
AutoReqProv: no

%description
NetOps Labs provides hands-on infrastructure training for networking, Linux, and security.

%prep

%build

%install
rm -rf "%{{buildroot}}"
mkdir -p "%{{buildroot}}/opt/netops-labs"
cp -a "{app_payload}/." "%{{buildroot}}/opt/netops-labs/"
mkdir -p "%{{buildroot}}/usr/local/bin"
ln -s /opt/netops-labs/netops-labs "%{{buildroot}}/usr/local/bin/netops-labs"
mkdir -p "%{{buildroot}}/usr/share/applications"
cat > "%{{buildroot}}/usr/share/applications/netops-labs.desktop" <<'EOF'
{desktop_entry}
EOF

%files
%defattr(-,root,root,-)
/opt/netops-labs
/usr/local/bin/netops-labs
/usr/share/applications/netops-labs.desktop
""",
        encoding="utf-8",
    )

    run([rpmbuild, "-bb", "--define", f"_topdir {rpm_top}", "--target", rpm_architecture(), str(spec_path)])
    built_rpms = sorted((rpm_top / "RPMS").rglob("*.rpm"))
    if not built_rpms:
        return None
    output = RELEASE_DIR / f"{artifact_stem(version)}.rpm"
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built_rpms[-1], output)
    return output


def create_linux_installers(gui_bundle: Path, version: str) -> List[Optional[Path]]:
    return [create_linux_deb(gui_bundle, version), create_linux_rpm(gui_bundle, version)]


def create_native_installers(gui_bundle: Path, version: str) -> List[Optional[Path]]:
    if sys.platform == "win32":
        return [create_windows_installer(gui_bundle, version)]
    if sys.platform == "darwin":
        print("INFO: macOS native installer packaging is disabled; use the source zip on macOS.")
        return []
    return create_linux_installers(gui_bundle, version)


def print_outputs(paths: Iterable[Optional[Path]]) -> None:
    print("\nRelease artifacts:")
    for path in paths:
        if path:
            print(f"- {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build NetOps Labs release packages.")
    parser.add_argument("--source-only", action="store_true", help="Only create the source zip artifact.")
    args = parser.parse_args()

    version = read_version()
    clean_build_dirs()

    outputs: List[Optional[Path]] = []
    if args.source_only:
        outputs.append(create_source_zip(version))
    else:
        gui_bundle = build_pyinstaller_apps()
        outputs.append(create_portable_zip(gui_bundle, version))
        outputs.extend(create_native_installers(gui_bundle, version))

    print_outputs(outputs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
