import tempfile
import unittest
from pathlib import Path

from project_processing import cleanup_warning_outputs


class ClippingProofCleanupTests(unittest.TestCase):

    def test_cached_proof_is_preserved_then_stale_proof_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            reports = folder / "reports"
            reports.mkdir()

            proof = reports / "student_clipping_removed.svg"
            proof.write_text("<svg/>", encoding="utf-8")

            cleanup_args = {
                "print_info": lambda message: None,
                "print_warning": lambda message: None,
            }

            # An unchanged cached PDF must retain its proof.
            cleanup_warning_outputs(
                folder,
                preserve_pdf_stems={"student"},
                **cleanup_args,
            )

            self.assertTrue(proof.exists())

            # A PDF being reprocessed must lose its old proof.
            cleanup_warning_outputs(
                folder,
                preserve_pdf_stems=set(),
                **cleanup_args,
            )

            self.assertFalse(proof.exists())


if __name__ == "__main__":
    unittest.main()
