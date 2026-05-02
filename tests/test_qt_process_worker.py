import sys
import unittest
from pathlib import Path

try:
    import gns3_ccnp_lab_gui_qt as qt_gui
except Exception as exc:  # pragma: no cover - environment-dependent skip
    qt_gui = None
    QT_IMPORT_ERROR = exc
else:
    QT_IMPORT_ERROR = None


@unittest.skipIf(qt_gui is None, f"PySide6 GUI import unavailable: {QT_IMPORT_ERROR}")
class ProcessWorkerTests(unittest.TestCase):
    def test_process_worker_emits_output_and_returns_full_buffer(self):
        worker = qt_gui.ProcessWorker(
            [
                sys.executable,
                "-u",
                "-c",
                "print('first progress line', flush=True); print('second progress line', flush=True)",
            ],
            Path.cwd(),
        )
        streamed = []
        finished = []
        worker.output.connect(streamed.append)
        worker.finished.connect(lambda code, output: finished.append((code, output)))

        worker.run()

        self.assertEqual(streamed, ["first progress line\n", "second progress line\n"])
        self.assertEqual(finished, [(0, "first progress line\nsecond progress line\n")])


if __name__ == "__main__":
    unittest.main()
