import tempfile
import unittest
from pathlib import Path
from lxml import etree as ET

from drawing import Point, Line, Bezier
from vector_path import VectorPath
from svg_writer import write_clipping_removed_svg


SVG_NS = "http://www.w3.org/2000/svg"


class ClippingRemovedSvgTests(unittest.TestCase):

    def test_exports_rejected_geometry_in_original_page_coordinates(self):
        path = VectorPath()
        path.add(
            Line(
                Point(25.0, 30.0),
                Point(45.0, 30.0),
                (0, 0, 0),
                0.01,
            )
        )
        path.add(
            Bezier(
                Point(45.0, 30.0),
                Point(50.0, 35.0),
                Point(55.0, 35.0),
                Point(60.0, 30.0),
                (0, 0, 0),
                0.01,
            )
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "clipping_removed.svg"

            write_clipping_removed_svg(
                [path],
                output,
                page_width=210.0,
                page_height=297.0,
            )

            self.assertTrue(output.exists())

            root = ET.parse(str(output)).getroot()

            self.assertEqual(root.get("width"), "210.000mm")
            self.assertEqual(root.get("height"), "297.000mm")
            self.assertEqual(root.get("viewBox"), "0 0 210.000000 297.000000")

            paths = root.findall(f".//{{{SVG_NS}}}path")
            self.assertEqual(len(paths), 1)

            exported = paths[0]
            self.assertEqual(exported.get("stroke"), "#FF0000")
            self.assertEqual(exported.get("fill"), "none")

            d = exported.get("d")
            self.assertIn("M 25.000000,30.000000", d)
            self.assertIn("L 45.000000,30.000000", d)
            self.assertIn("C 50.000000,35.000000 55.000000,35.000000 60.000000,30.000000", d)

            self.assertIsNone(
                root.find(f".//{{{SVG_NS}}}clipPath")
            )

    def test_preserves_original_rgb_stroke_colour(self):
        path = VectorPath()
        path.add(
            Line(
                Point(25.0, 30.0),
                Point(45.0, 30.0),
                (255, 128, 0),
                0.01,
            )
        )
        path.stroke_color = (255, 128, 0)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "clipping_removed.svg"

            write_clipping_removed_svg(
                [path],
                output,
                page_width=210.0,
                page_height=297.0,
            )

            root = ET.parse(str(output)).getroot()
            exported = root.find(f".//{{{SVG_NS}}}path")

            self.assertEqual(exported.get("stroke"), "#FF8000")

if __name__ == "__main__":
    unittest.main()
