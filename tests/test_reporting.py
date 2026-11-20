import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PY = sys.executable
sys.path.insert(0, str(SCRIPTS))

import summary_report  # noqa: E402
import utils  # noqa: E402

REPORT = {
    "results": [
        {
            "check_id": "php-danger-eval",
            "path": "C:\\src\\source_code\\demo\\admin\\index.php",
            "start": {"line": 10},
            "extra": {"severity": "ERROR", "message": "eval usage"},
        },
        {
            "check_id": "php-file-upload",
            "path": "C:\\src\\source_code\\demo\\vendor\\lib\\a.php",
            "start": {"line": 3},
            "extra": {"severity": "WARNING", "message": "upload sink"},
        },
    ]
}


def write_reports(tmp: Path):
    (tmp / "demo_php_report.json").write_text(json.dumps(REPORT), encoding="utf-8")


class UtilsTests(unittest.TestCase):
    def test_repo_name(self):
        self.assertEqual(utils.get_repo_name("https://github.com/a/b.git/"), "b")

    def test_project_relative_windows_path(self):
        raw = "C:\\src\\source_code\\demo\\admin\\index.php"
        self.assertEqual(utils.project_relative(raw, "demo"), "admin/index.php")

    def test_normalize_path(self):
        self.assertEqual(utils.normalize_path("a\\b\\c"), "a/b/c")


class SummaryTests(unittest.TestCase):
    def test_summary_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            write_reports(tmp_path)
            original = summary_report.OUTPUT_ROOT
            original_argv = sys.argv
            summary_report.OUTPUT_ROOT = tmp_path
            try:
                sys.argv = ["summary_report.py"]
                code = summary_report.main()
            finally:
                summary_report.OUTPUT_ROOT = original
                sys.argv = original_argv
            self.assertEqual(code, 0)
            text = (tmp_path / "summary.md").read_text(encoding="utf-8")
        self.assertIn("demo", text)
        self.assertIn("php", text)
        self.assertIn("生成时间", text)
        self.assertIn("admin/index.php", text)
        self.assertNotIn("C:\\src", text)


class TriageTests(unittest.TestCase):
    def test_triage_filters_vendor_and_normalizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            write_reports(tmp_path)
            result = subprocess.run(
                [PY, str(SCRIPTS / "triage_report.py"), "--output-dir", str(tmp_path)],
                cwd=ROOT, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((tmp_path / "triage.json").read_text(encoding="utf-8"))
        self.assertEqual(data["summary"]["excluded"], 1)
        self.assertEqual(len(data["findings"]), 1)
        self.assertEqual(data["findings"][0]["rel_path"], "admin/index.php")


if __name__ == "__main__":
    unittest.main()
