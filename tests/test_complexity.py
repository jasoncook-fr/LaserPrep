import unittest
from types import SimpleNamespace

from complexity import Complexity, analyse_complexity
from report import Report
from student_report_pdf import _translate_detail


class FakeDrawing:
    def __init__(self, object_count, filled_paths):
        self.objects = [None] * object_count
        self.paths = (
            [SimpleNamespace(fill_enabled=True) for _ in range(filled_paths)]
            + [SimpleNamespace(fill_enabled=False)]
        )


class ComplexityTests(unittest.TestCase):

    def test_analyse_complexity_counts_filled_paths(self):
        drawing = FakeDrawing(137686, 1247)

        result = analyse_complexity(drawing)

        self.assertEqual(result.object_count, 137686)
        self.assertEqual(result.rating, "HIGH")
        self.assertFalse(result.should_abort)
        self.assertEqual(result.filled_paths, 1247)

    def test_high_complexity_adds_warning_without_rejecting_file(self):
        report = Report()
        report.begin_file("complex.pdf")

        report.complexity(Complexity(
            object_count=137686,
            rating="HIGH",
            should_abort=False,
            filled_paths=1247,
        ))

        self.assertEqual(report.current["status"], "WARNING")
        self.assertEqual(report.current["alerts"], [])
        self.assertEqual(len(report.current["warnings"]), 1)

        warning = report.current["warnings"][0]
        self.assertIn("137,686 vector objects", warning)
        self.assertIn("1,247 filled paths", warning)
        self.assertIn("laser engraving time", warning)

    def test_elevated_complexity_adds_warning(self):
        report = Report()
        report.begin_file("moderate.pdf")

        report.complexity(Complexity(
            object_count=25000,
            rating="WARNING",
            should_abort=False,
        ))

        self.assertEqual(report.current["status"], "WARNING")
        self.assertIn(
            "Elevated geometry complexity",
            report.current["warnings"][0],
        )

    def test_student_report_translates_complexity_warning_to_french(self):
        message = (
            "High geometry complexity: 137,686 vector objects; 1,247 filled paths. "
            "Processing may take longer than usual. Filled areas may significantly "
            "increase laser engraving time. Consider simplifying the artwork where practical."
        )

        translated = _translate_detail(message, "fr")

        self.assertIn("Complexité géométrique élevée", translated)
        self.assertIn("137 686 objets vectoriels", translated)
        self.assertIn("1 247 tracés remplis", translated)
        self.assertIn("temps de gravure laser", translated)

    def test_student_report_keeps_english_complexity_warning(self):
        message = (
            "High geometry complexity: 137,686 vector objects; 1,247 filled paths. "
            "Processing may take longer than usual. Filled areas may significantly "
            "increase laser engraving time. Consider simplifying the artwork where practical."
        )

        self.assertEqual(_translate_detail(message, "en"), message)


if __name__ == "__main__":
    unittest.main()
