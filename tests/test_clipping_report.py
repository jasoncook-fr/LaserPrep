import tempfile
import unittest
from pathlib import Path

from report import Report


class ClippingReportTests(unittest.TestCase):

    def test_clipping_removal_is_recorded_in_base_report(self):
        report = Report()
        report.begin_file("student.pdf")

        report.clipping(
            3,
            "student_clipping_removed.svg",
        )

        self.assertEqual(
            report.current["clipping_removed_paths"],
            3,
        )
        self.assertEqual(
            report.current["clipping_proof"],
            "student_clipping_removed.svg",
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "base_report.txt"

            report.save(output, "Test Project")

            content = output.read_text(encoding="utf-8")

            self.assertIn("AUTOMATIC REPAIRS", content)
            self.assertIn("SVG clipping removed 3 paths", content)
            self.assertIn("student_clipping_removed.svg", content)

    def test_zero_removed_paths_creates_no_repair_entry(self):
        report = Report()
        report.begin_file("student.pdf")

        report.clipping(0, None)

        self.assertEqual(
            report.current["clipping_removed_paths"],
            0,
        )
        self.assertIsNone(report.current["clipping_proof"])
        self.assertEqual(report.current["repairs"], [])


if __name__ == "__main__":
    unittest.main()
