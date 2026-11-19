import tempfile
import unittest
from pathlib import Path

from profile_adjustment import adjust_lcf_text, process_directory


SAMPLE = """[Machine-A]
Power=300 400 200 1000 1000 500 500 500
Speed=1000 900 500 250 100 1000 1000 1000
PPI=800 800 800 800 800 500 500 500 500
"""


class ProfileAdjustmentTests(unittest.TestCase):
    def test_speed_adjustment_and_preservation(self):
        adjusted, audit = adjust_lcf_text(SAMPLE, 0.9, "sample.lcf")
        self.assertIn("Speed=900 810 450 225 90 900 900 900", adjusted)
        self.assertIn("Power=300 400 200 1000 1000 500 500 500", adjusted)
        self.assertIn("PPI=800 800 800 800 800 500 500 500 500", adjusted)
        self.assertEqual(len(audit), 8)

    def test_multiple_sections_are_adjusted(self):
        text = SAMPLE + "\n[Second]\nSpeed=100 100 100 100 100 100 100 100\n"
        adjusted, audit = adjust_lcf_text(text, 0.9)
        self.assertEqual(adjusted.count("Speed=90 90 90 90 90 90 90 90"), 1)
        self.assertEqual(len(audit), 16)
        self.assertEqual(audit[-1]["section"], "Second")

    def test_invalid_slot_count_fails(self):
        with self.assertRaises(ValueError):
            adjust_lcf_text("[M]\nSpeed=100 200\n", 0.9)

    def test_no_speed_entry_fails(self):
        with self.assertRaises(ValueError):
            adjust_lcf_text("[M]\nPower=100\n", 0.9)

    def test_directory_output_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "in"
            dest = root / "out"
            source.mkdir()
            (source / "profile.lcf").write_text(SAMPLE, encoding="utf-8")
            audits = process_directory(source, dest, 0.9)
            self.assertEqual(len(audits), 8)
            self.assertTrue((dest / "profile.lcf").exists())
            self.assertTrue((dest / "speed_adjustment_audit.csv").exists())
            self.assertTrue((dest / "adjustment_summary.json").exists())
            self.assertIn("Speed=900 810 450 225 90 900 900 900",
                          (dest / "profile.lcf").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
