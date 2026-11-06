import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from drawing import Point, Line, Bezier
from vector_path import VectorPath
from svg_clipping import should_discard_path, _has_separating_axis, _is_convex_polygon


class SvgClippingTests(unittest.TestCase):
    def _document(self, clip_d, path_d, path_clip="url(#clip)"):
        xml = f'''<svg xmlns="http://www.w3.org/2000/svg">
          <defs><clipPath id="clip"><path d="{clip_d}" /></clipPath></defs>
          <g clip-path="{path_clip}"><path id="art" d="{path_d}" /></g>
        </svg>'''
        root = ET.fromstring(xml)
        node = next(e for e in root.iter() if e.attrib.get("id") == "art")
        return root, node

    def test_simple_polygon_recognized_as_convex(self):
        self.assertTrue(_is_convex_polygon([(0, 0), (10, 0), (10, 10), (0, 10)]))
        self.assertFalse(_is_convex_polygon([(0, 0), (10, 0), (4, 4), (10, 10), (0, 10)]))

    def test_disjoint_geometry_is_rejected(self):
        root, node = self._document("M0 0H10V10H0Z", "M20 20L30 30")
        path = VectorPath(objects=[Line(Point(20, 20), Point(30, 30), (0, 0, 0), 0.01)])
        self.assertTrue(should_discard_path(root, node, path))

    def test_geometry_inside_clip_is_kept(self):
        root, node = self._document("M0 0H10V10H0Z", "M2 2L8 8")
        path = VectorPath(objects=[Line(Point(2, 2), Point(8, 8), (0, 0, 0), 0.01)])
        self.assertFalse(should_discard_path(root, node, path))

    def test_crossing_geometry_is_kept(self):
        root, node = self._document("M0 0H10V10H0Z", "M5 5L15 5")
        path = VectorPath(objects=[Line(Point(5, 5), Point(15, 5), (0, 0, 0), 0.01)])
        self.assertFalse(should_discard_path(root, node, path))

    def test_bezier_control_hull_outside_is_rejected(self):
        root, node = self._document("M0 0H10V10H0Z", "M20 20C21 20 29 30 30 30")
        path = VectorPath(objects=[Bezier(
            Point(20, 20), Point(21, 20), Point(29, 30), Point(30, 30), (0, 0, 0), 0.01
        )])
        self.assertTrue(should_discard_path(root, node, path))

    def test_unsupported_clip_is_kept(self):
        root, node = self._document("M0 0C1 1 2 2 3 3", "M20 20L30 30")
        path = VectorPath(objects=[Line(Point(20, 20), Point(30, 30), (0, 0, 0), 0.01)])
        self.assertFalse(should_discard_path(root, node, path))

    def test_group_transform_disables_clipping_decision(self):
        root, node = self._document("M0 0H10V10H0Z", "M20 20L30 30")
        parent = next(e for e in root.iter() if e.tag.endswith("g"))
        parent.set("transform", "matrix(1,0,0,1,100,100)")
        path = VectorPath(objects=[Line(Point(20, 20), Point(30, 30), (0, 0, 0), 0.01)])
        self.assertFalse(should_discard_path(root, node, path))


if __name__ == "__main__":
    unittest.main()
