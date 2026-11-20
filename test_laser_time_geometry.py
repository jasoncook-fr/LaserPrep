import unittest
import math
from laser_time_geometry import extract_svg, color_name, Affine

class GeometryTests(unittest.TestCase):
    def test_color(self):
        self.assertEqual(color_name("#0000ff"),"blue")
        self.assertEqual(color_name("#0f0"),"green")
        self.assertEqual(color_name("rgb(255,0,0)"),"red")
    def test_style_inheritance(self):
        r=extract_svg('<svg><g stroke="blue"><path d="M0 0 L10 0"/></g></svg>')
        self.assertEqual(r.category_lengths()["cut"],10)
    def test_relative_and_close(self):
        r=extract_svg('<svg><path stroke="blue" d="m0 0 l10 0 l0 10 z"/></svg>')
        self.assertAlmostEqual(r.category_lengths()["cut"],10+10+math.sqrt(200),places=3)
    def test_curve(self):
        r=extract_svg('<svg><path stroke="red" d="M0 0 C0 10 10 10 10 0"/></svg>')
        self.assertGreater(r.category_lengths()["vector"],19)
    def test_arc(self):
        r=extract_svg('<svg><path stroke="blue" d="M0 0 A10 10 0 0 1 20 0"/></svg>')
        self.assertGreater(r.category_lengths()["cut"],30)
    def test_transforms(self):
        r=extract_svg('<svg><g transform="translate(5,0) scale(2)"><path stroke="blue" d="M0 0 L10 0"/></g></svg>')
        self.assertAlmostEqual(r.category_lengths()["cut"],20)
    def test_fill_area(self):
        r=extract_svg('<svg><path fill="black" d="M0 0 L10 0 L10 10 L0 10 Z"/></svg>')
        self.assertAlmostEqual(r.fill_area(),100)
    def test_unsupported(self):
        r=extract_svg('<svg><path stroke="blue" d="M0 0 L1 1"/></svg>')
        self.assertEqual(r.path_count,1)
if __name__=="__main__":
    import math
    unittest.main()
