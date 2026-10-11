import tempfile
import unittest
from pathlib import Path

from netroute_diagnose.diagnose import run_diagnostics
from netroute_diagnose.report import write_html


ROOT = Path(__file__).resolve().parents[1]


class ReportTests(unittest.TestCase):
    def test_offline_example_report(self):
        report = run_diagnostics(
            ROOT / "examples" / "diagnosis.yaml",
            ROOT / "examples" / "clash-config.yaml",
            offline=True,
        )
        self.assertEqual(len(report.domain_checks), 10)
        self.assertEqual(sum(item.status == "PASS" for item in report.domain_checks), 5)
        self.assertEqual(sum(item.status == "UNCERTAIN" for item in report.domain_checks), 5)
        self.assertFalse(report.dns_results)
        self.assertEqual(report.source_config, "diagnosis.yaml")
        self.assertEqual(report.clash_config, "clash-config.yaml")
        with tempfile.TemporaryDirectory() as directory:
            output = write_html(report, Path(directory) / "report.html")
            text = output.read_text(encoding="utf-8")
            self.assertIn("NetRoute-Diagnose", text)
            self.assertIn("api.openai.com", text)
            self.assertIn("Static rule analysis is not proof", text)
            self.assertNotIn(str(ROOT), text)


if __name__ == "__main__":
    unittest.main()
