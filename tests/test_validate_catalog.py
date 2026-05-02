import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tools.validate_catalog import CatalogValidator, main


class ValidateCatalogTests(unittest.TestCase):
    def write_catalog(self, data):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(data, tmp)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return tmp.name

    def minimal_catalog(self):
        return {
            "templates": {
                "iol2": {"name": "IOL L2"},
                "rhel9": {"name": "RHEL9"},
            },
            "topologies": {
                "simple": {
                    "nodes": {
                        "SW1": {"template": "iol2"},
                    }
                }
            },
            "study_paths": {
                "ccna-foundations": {"name": "CCNA Foundations"},
            },
            "scenarios": {
                "good": {
                    "title": "Basic Switching Check",
                    "topology": "simple",
                    "domain": "Switching",
                    "study_paths": ["ccna-foundations"],
                    "lab_type": "troubleshooting",
                    "difficulty": "easy",
                    "platforms": ["gns3", "cisco-iol"],
                    "estimated_minutes": 15,
                    "exam_alignment": ["CCNA"],
                }
            },
        }

    def validate(self, data):
        path = self.write_catalog(data)
        validator = CatalogValidator(path)
        validator.load()
        return validator.run()

    def test_valid_legacy_catalog_has_no_errors(self):
        report = self.validate(self.minimal_catalog())
        self.assertEqual(report.errors, [])
        self.assertEqual(report.stats["legacy_domain_fallbacks"], 1)
        self.assertEqual(report.stats["legacy_lab_type_values"], 1)
        self.assertEqual(report.stats["legacy_difficulty_values"], 1)

    def test_missing_top_level_key_is_error(self):
        data = self.minimal_catalog()
        del data["study_paths"]
        report = self.validate(data)
        self.assertTrue(any(issue.path == "study_paths" for issue in report.errors))

    def test_unknown_study_path_is_error(self):
        data = self.minimal_catalog()
        data["scenarios"]["good"]["study_paths"] = ["missing-path"]
        report = self.validate(data)
        self.assertTrue(any("Unknown study path" in issue.message for issue in report.errors))

    def test_missing_topology_reference_is_error(self):
        data = self.minimal_catalog()
        data["scenarios"]["good"]["topology"] = "does-not-exist"
        report = self.validate(data)
        self.assertTrue(any("does not exist" in issue.message for issue in report.errors))

    def test_missing_template_reference_is_error(self):
        data = self.minimal_catalog()
        data["topologies"]["simple"]["nodes"]["SW1"]["template"] = "missing-template"
        report = self.validate(data)
        self.assertTrue(any("unknown template" in issue.message.lower() for issue in report.errors))

    def test_missing_estimated_minutes_is_warning_not_error(self):
        data = self.minimal_catalog()
        del data["scenarios"]["good"]["estimated_minutes"]
        report = self.validate(data)
        self.assertEqual(report.errors, [])
        self.assertTrue(any("estimated_minutes" in issue.path for issue in report.warnings))

    def test_platforms_can_be_derived_from_topology_templates(self):
        data = self.minimal_catalog()
        del data["scenarios"]["good"]["platforms"]
        report = self.validate(data)
        self.assertEqual(report.errors, [])
        self.assertEqual(report.stats["derived_platform_values"], 1)
        self.assertFalse(any("platforms" in issue.path for issue in report.warnings))

    def test_leakage_pattern_is_warning(self):
        data = self.minimal_catalog()
        data["scenarios"]["good"]["symptom"] = "Root cause: switchport mode is wrong."
        report = self.validate(data)
        self.assertEqual(report.errors, [])
        self.assertTrue(any("Potential answer leakage" in issue.message for issue in report.warnings))

    def test_unused_defined_study_path_is_warning(self):
        data = self.minimal_catalog()
        data["study_paths"]["unused-path"] = {"name": "Unused Path"}
        report = self.validate(data)
        self.assertEqual(report.errors, [])
        self.assertTrue(any(issue.path == "study_paths.unused-path" for issue in report.warnings))
        self.assertEqual(report.stats["study_path_usage"]["unused-path"], 0)

    def run_cli_quietly(self, argv):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(argv)

    def test_cli_exit_codes(self):
        good_path = self.write_catalog(self.minimal_catalog())
        self.assertEqual(self.run_cli_quietly(["--catalog", good_path, "--quiet"]), 0)

        warning_data = self.minimal_catalog()
        del warning_data["scenarios"]["good"]["estimated_minutes"]
        warning_path = self.write_catalog(warning_data)
        self.assertEqual(self.run_cli_quietly(["--catalog", warning_path, "--quiet"]), 0)
        self.assertEqual(self.run_cli_quietly(["--catalog", warning_path, "--quiet", "--strict"]), 1)

        bad_data = self.minimal_catalog()
        bad_data["scenarios"]["good"]["topology"] = "missing"
        bad_path = self.write_catalog(bad_data)
        self.assertEqual(self.run_cli_quietly(["--catalog", bad_path, "--quiet"]), 1)

    def test_current_catalog_has_no_validation_errors(self):
        path = Path("catalogs/ccnp_encor_lab_catalog.json")
        self.assertTrue(path.exists())
        validator = CatalogValidator(path)
        validator.load()
        report = validator.run()
        self.assertEqual(report.errors, [])
        self.assertGreater(report.stats["scenario_count"], 0)


if __name__ == "__main__":
    unittest.main()
