import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from tools import build_packages

try:
    import gns3_ccnp_lab_gui_qt as qt_gui
except Exception as exc:  # pragma: no cover - environment-dependent skip
    qt_gui = None
    QT_IMPORT_ERROR = exc
else:
    QT_IMPORT_ERROR = None


class BuildPackageTests(unittest.TestCase):
    def test_artifact_stem_includes_version_platform_and_arch(self):
        with (
            patch.object(build_packages, "platform_id", return_value="linux"),
            patch.object(build_packages, "arch_id", return_value="x86_64"),
        ):
            self.assertEqual(build_packages.artifact_stem("4.0.1"), "NetOpsLabs-4.0.1-linux-x86_64")

    def test_add_data_args_uses_existing_bundle_inputs(self):
        args = build_packages.add_data_args()

        joined = " ".join(args)
        self.assertIn("catalogs", joined)
        self.assertIn("config_templates", joined)
        self.assertIn("README.md", joined)

    def test_copy_data_tree_excludes_macos_resource_junk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "assets"
            destination = root / "stage" / "assets"
            source.joinpath("symbols", "router.svg").parent.mkdir(parents=True)
            source.joinpath("symbols", "router.svg").write_text("<svg />", encoding="utf-8")
            source.joinpath("__MACOSX").mkdir()
            source.joinpath("__MACOSX", "._symbols").write_bytes(b"appledouble")
            source.joinpath(".DS_Store").write_bytes(b"finder")
            source.joinpath("._router.svg").write_bytes(b"appledouble")

            build_packages.copy_data_tree(source, destination)

            self.assertTrue(destination.joinpath("symbols", "router.svg").exists())
            self.assertFalse(destination.joinpath("__MACOSX").exists())
            self.assertFalse(destination.joinpath(".DS_Store").exists())
            self.assertFalse(destination.joinpath("._router.svg").exists())

    def test_add_data_args_stages_directories_without_resource_junk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_dir = root / "build"
            root.joinpath("assets", "symbols").mkdir(parents=True)
            root.joinpath("assets", "symbols", "router.svg").write_text("<svg />", encoding="utf-8")
            root.joinpath("assets", "__MACOSX").mkdir()
            root.joinpath("assets", "__MACOSX", "._symbols").write_bytes(b"appledouble")

            with (
                patch.object(build_packages, "ROOT", root),
                patch.object(build_packages, "BUILD_DIR", build_dir),
                patch.object(build_packages, "DATA_ITEMS", ["assets"]),
            ):
                args = build_packages.add_data_args()

            staged_assets = build_dir / "data-stage" / "assets"
            self.assertIn(str(staged_assets), " ".join(args))
            self.assertTrue(staged_assets.joinpath("symbols", "router.svg").exists())
            self.assertFalse(staged_assets.joinpath("__MACOSX").exists())

    def test_generator_pyinstaller_args_do_not_bundle_qt_or_data(self):
        args = build_packages.pyinstaller_base("netops-lab-generator", windowed=False)

        self.assertNotIn("--collect-all", args)
        self.assertNotIn("--onefile", args)
        self.assertNotIn("--add-data", args)
        self.assertIn("--console", args)

    def test_onefile_pyinstaller_args_skip_onedir_layout(self):
        args = build_packages.pyinstaller_base("netops-lab-generator", windowed=False, onefile=True)

        self.assertIn("--onefile", args)
        self.assertNotIn("--onedir", args)
        self.assertNotIn("--contents-directory", args)
        self.assertIn("--console", args)

    def test_gui_pyinstaller_args_include_data_without_collecting_all_qt(self):
        args = build_packages.pyinstaller_base("NetOps Labs", windowed=True, include_data=True, include_qt_svg=True)

        self.assertNotIn("--collect-all", args)
        self.assertIn("--add-data", args)
        self.assertIn("--hidden-import", args)
        self.assertIn("PySide6.QtSvg", args)
        self.assertIn("--windowed", args)

    def test_macos_codesign_identity_defaults_to_ad_hoc(self):
        with patch.dict(build_packages.os.environ, {}, clear=True):
            self.assertEqual(build_packages.macos_codesign_identity(), "-")

    def test_macos_codesign_identity_uses_environment_override(self):
        with patch.dict(build_packages.os.environ, {"MACOS_CODESIGN_IDENTITY": "Developer ID Application: Example"}):
            self.assertEqual(build_packages.macos_codesign_identity(), "Developer ID Application: Example")

    def test_developer_id_codesign_uses_hardened_runtime_and_timestamp(self):
        command = build_packages.macos_codesign_command(
            "/usr/bin/codesign",
            "Developer ID Application: Example",
            Path("/tmp/NetOps Labs.app"),
        )

        self.assertIn("--options", command)
        self.assertIn("runtime", command)
        self.assertIn("--timestamp", command)

    def test_sign_macos_app_bundle_runs_sign_and_verify(self):
        app_bundle = Path("/tmp/NetOps Labs.app")
        macho = app_bundle / "Contents" / "MacOS" / "NetOps Labs"

        with (
            patch.object(build_packages.sys, "platform", "darwin"),
            patch.object(build_packages.shutil, "which", return_value="/usr/bin/codesign"),
            patch.object(build_packages, "macos_macho_files", return_value=[macho]),
            patch.object(build_packages, "run") as run,
        ):
            build_packages.sign_macos_app_bundle(app_bundle)

        run.assert_has_calls(
            [
                call(["/usr/bin/codesign", "--force", "--sign", "-", str(macho)]),
                call(["/usr/bin/codesign", "--force", "--sign", "-", str(app_bundle)]),
                call(["/usr/bin/codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app_bundle)]),
            ]
        )

    def test_macos_macho_file_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            macho = root / "binary"
            text = root / "notes.txt"
            macho.write_bytes(b"\xcf\xfa\xed\xfepayload")
            text.write_text("not a binary", encoding="utf-8")

            self.assertTrue(build_packages.is_macho_file(macho))
            self.assertFalse(build_packages.is_macho_file(text))

    def test_macos_macho_files_sort_deepest_first(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            shallow = root / "Contents" / "MacOS" / "app"
            deep = root / "Contents" / "Frameworks" / "Example.framework" / "Versions" / "A" / "Example"
            shallow.parent.mkdir(parents=True)
            deep.parent.mkdir(parents=True)
            shallow.write_bytes(b"\xcf\xfa\xed\xfepayload")
            deep.write_bytes(b"\xcf\xfa\xed\xfepayload")

            self.assertEqual(build_packages.macos_macho_files(root), [deep, shallow])

    def test_copy_generator_into_gui_bundle_accepts_single_file_generator(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            gui_bundle = root / "NetOps Labs.app"
            generator = root / "netops-lab-generator"
            generator.write_text("generator", encoding="utf-8")

            with patch.object(build_packages.sys, "platform", "darwin"):
                build_packages.copy_generator_into_gui_bundle(gui_bundle, generator)

            copied = gui_bundle / "Contents" / "MacOS" / "netops-lab-generator"
            self.assertEqual(copied.read_text(encoding="utf-8"), "generator")

    def test_rpm_architecture_maps_arm64_to_aarch64(self):
        with patch.object(build_packages, "arch_id", return_value="arm64"):
            self.assertEqual(build_packages.rpm_architecture(), "aarch64")

    def test_create_linux_rpm_writes_spec_and_copies_rpm_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_dir = root / "build"
            release_dir = root / "release"
            gui_bundle = root / "gui"
            gui_bundle.mkdir()
            gui_bundle.joinpath("netops-labs").write_text("launcher", encoding="utf-8")

            def fake_run(_cmd):
                rpm_path = build_dir / "rpm" / "RPMS" / "x86_64" / "netops-labs-4.0.1-1.x86_64.rpm"
                rpm_path.parent.mkdir(parents=True)
                rpm_path.write_text("rpm", encoding="utf-8")

            with (
                patch.object(build_packages, "BUILD_DIR", build_dir),
                patch.object(build_packages, "RELEASE_DIR", release_dir),
                patch.object(build_packages.shutil, "which", return_value="/usr/bin/rpmbuild"),
                patch.object(build_packages, "run", side_effect=fake_run),
                patch.object(build_packages, "platform_id", return_value="linux"),
                patch.object(build_packages, "arch_id", return_value="x86_64"),
            ):
                output = build_packages.create_linux_rpm(gui_bundle, "4.0.1")

            spec = build_dir.joinpath("rpm", "SPECS", "netops-labs.spec").read_text(encoding="utf-8")
            self.assertIn("AutoReqProv: no", spec)
            self.assertIn("/opt/netops-labs", spec)
            self.assertEqual(output, release_dir / "NetOpsLabs-4.0.1-linux-x86_64.rpm")
            self.assertEqual(output.read_text(encoding="utf-8"), "rpm")

    def test_create_native_installers_skips_macos_native_package(self):
        with patch.object(build_packages.sys, "platform", "darwin"):
            self.assertEqual(build_packages.create_native_installers(Path("/tmp/app"), "4.0.1"), [])

    def test_create_native_installers_returns_deb_and_rpm_on_linux(self):
        with (
            patch.object(build_packages.sys, "platform", "linux"),
            patch.object(build_packages, "create_linux_deb", return_value=Path("/tmp/app.deb")),
            patch.object(build_packages, "create_linux_rpm", return_value=Path("/tmp/app.rpm")),
        ):
            self.assertEqual(
                build_packages.create_native_installers(Path("/tmp/app"), "4.0.1"),
                [Path("/tmp/app.deb"), Path("/tmp/app.rpm")],
            )


@unittest.skipIf(qt_gui is None, f"PySide6 GUI import unavailable: {QT_IMPORT_ERROR}")
class PackagedGuiPathTests(unittest.TestCase):
    def test_packaged_generator_path_uses_bundled_executable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            executable = root / "NetOps Labs.exe"
            generator = root / "netops-lab-generator.exe"
            executable.write_text("", encoding="utf-8")
            generator.write_text("", encoding="utf-8")

            with (
                patch.object(qt_gui, "is_frozen_app", return_value=True),
                patch.object(qt_gui.sys, "executable", str(executable)),
                patch.object(qt_gui, "APP_DIR", root),
            ):
                self.assertEqual(qt_gui.packaged_generator_path(), generator.resolve())


if __name__ == "__main__":
    unittest.main()
