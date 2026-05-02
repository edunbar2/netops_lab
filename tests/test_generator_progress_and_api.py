import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import gns3_ccnp_lab_generator as generator


class FakeResponse:
    text = '{"ok": true}'

    def raise_for_status(self):
        return None

    def json(self):
        return {"ok": True}


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return FakeResponse()


class GeneratorApiTests(unittest.TestCase):
    def tearDown(self):
        generator._API_SESSION = None

    def test_api_uses_request_session(self):
        session = FakeSession()

        result = generator.api("GET", "http://gns3.example:3080/", "/v2/version", _session=session)

        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(session.calls), 1)
        method, url, kwargs = session.calls[0]
        self.assertEqual(method, "GET")
        self.assertEqual(url, "http://gns3.example:3080/v2/version")
        self.assertEqual(kwargs["timeout"], 30)

    def test_shared_gns3_session_is_reused(self):
        fake_session = FakeSession()

        with patch.object(generator.requests, "Session", return_value=fake_session):
            first = generator.gns3_api_session()
            second = generator.gns3_api_session()

        self.assertIs(first, second)
        self.assertEqual(fake_session.headers["Accept"], "application/json")

    def test_refresh_created_nodes_skips_nodes_with_console_metadata(self):
        created_nodes = {
            "R1": {"node_id": "node-1", "console": 5001},
            "R2": {"node_id": "node-2"},
        }

        with patch.object(generator, "read_node", return_value={"node_id": "node-2", "console": 5002}) as read_node:
            refreshed = generator.refresh_created_nodes("http://gns3", "project-1", created_nodes)

        read_node.assert_called_once_with("http://gns3", "project-1", "node-2")
        self.assertEqual(refreshed["R1"], {"node_id": "node-1", "console": 5001})
        self.assertEqual(refreshed["R2"], {"node_id": "node-2", "console": 5002})


class GeneratorProgressTests(unittest.TestCase):
    def test_build_project_emits_progress_and_avoids_redundant_node_reads(self):
        catalog = {
            "_catalog_path": "unit-catalog.json",
            "templates": {
                "ios": {"template_id": "template-ios"},
            },
            "topologies": {
                "single-router": {
                    "nodes": {
                        "R1": {"template": "ios", "x": 0, "y": 0},
                    },
                    "links": [],
                },
            },
        }
        scenario = {"topology": "single-router", "title": "Single Router Lab"}

        with tempfile.TemporaryDirectory() as tmpdir:
            args = SimpleNamespace(
                server="http://gns3.example:3080",
                host_type="alpine",
                name="UnitTestLab",
                out=tmpdir,
                start=False,
                push_config=False,
                push_endpoints=False,
                verify=False,
                skip_template_port_check=True,
                console_timeout=1,
                endpoint_timeout=1,
                linux_endpoint_username="root",
                linux_endpoint_password="",
                linux_endpoint_login_timeout=1,
            )

            def fake_write_lab_files(**kwargs):
                Path(kwargs["out_dir"], kwargs["project_name"]).mkdir(parents=True, exist_ok=True)

            buffer = io.StringIO()
            with (
                patch.object(generator, "create_project", return_value={"project_id": "project-1"}) as create_project,
                patch.object(generator, "create_node", return_value={"node_id": "node-1", "console": 5001}) as create_node,
                patch.object(generator, "read_node") as read_node,
                patch.object(generator, "write_lab_files", side_effect=fake_write_lab_files),
                redirect_stdout(buffer),
            ):
                generator.build_project(args, catalog, Mock(), "single-router-lab", scenario)

        output = buffer.getvalue()
        self.assertIn("[1/8] Preparing lab generation plan", output)
        self.assertIn("[5/8] Creating 1 GNS3 node(s)", output)
        self.assertIn("Used create responses for 1 node(s); skipped redundant node-detail reads", output)
        create_project.assert_called_once_with("http://gns3.example:3080", "UnitTestLab")
        create_node.assert_called_once()
        read_node.assert_not_called()


if __name__ == "__main__":
    unittest.main()
