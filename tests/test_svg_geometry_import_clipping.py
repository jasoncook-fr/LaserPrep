import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from svg_geometry_import import import_svg_geometry


class SvgGeometryImportClippingTests(unittest.TestCase):

    def test_rejected_path_is_captured_in_page_coordinates(self):
        svg_content = """\
<svg xmlns="http://www.w3.org/2000/svg">
    <path
        d="M 72,72 L 144,72"
        stroke="#000000"
        fill="none"
    />
</svg>
"""

        with tempfile.TemporaryDirectory() as tmp:
            svg_file = Path(tmp) / "test.svg"
            svg_file.write_text(svg_content, encoding="utf-8")

            clipping_removed = []

            # Force the clipping decision to reject this path.
            # This isolates and tests the capture mechanism itself.
            with patch(
                "svg_geometry_import.should_discard_path",
                return_value=True,
            ):
                imported = import_svg_geometry(
                    svg_file,
                    clipping_removed=clipping_removed,
                )

            self.assertEqual(len(imported), 0)
            self.assertEqual(len(clipping_removed), 1)

            removed_path = clipping_removed[0]
            self.assertEqual(removed_path.object_count, 1)

            segment = removed_path.objects[0]

            # 72 SVG points = 25.4 mm; 144 points = 50.8 mm.
            self.assertAlmostEqual(segment.start.x, 25.4)
            self.assertAlmostEqual(segment.start.y, 25.4)
            self.assertAlmostEqual(segment.end.x, 50.8)
            self.assertAlmostEqual(segment.end.y, 25.4)


if __name__ == "__main__":
    unittest.main()
