import math

from drawing import Bezier, Drawing, Line, Path, Point
from cut_time_estimator import analyse_drawing, bezier_length


def line(x1, y1, x2, y2, color):
    return Line(Point(x1, y1), Point(x2, y2), color, 0.01)


def test_measures_blue_straight_cut_length():
    path = Path(
        segments=[line(0, 0, 30, 40, (0, 0, 255))],
        stroke_color=(0, 0, 255),
        stroke_enabled=True,
    )
    result = analyse_drawing(Drawing("test", 100, 100, paths=[path]))
    assert math.isclose(result.cut_straight_length_mm, 50.0)
    assert result.blue_paths == 1
    assert result.blue_segments == 1


def test_measures_green_and_red_separately():
    green = Path(
        segments=[line(0, 0, 10, 0, (0, 255, 0))],
        stroke_color=(0, 255, 0),
        stroke_enabled=True,
    )
    red = Path(
        segments=[line(0, 0, 0, 20, (255, 0, 0))],
        stroke_color=(255, 0, 0),
        stroke_enabled=True,
    )
    result = analyse_drawing(Drawing("test", 100, 100, paths=[green, red]))
    assert result.green_engrave_straight_length_mm == 10
    assert result.red_engrave_straight_length_mm == 20


def test_bezier_length_is_between_chord_and_control_polygon():
    curve = Bezier(
        Point(0, 0), Point(0, 10), Point(10, 10), Point(10, 0),
        (0, 0, 255), 0.01,
    )
    length = bezier_length(curve)
    assert 10 < length < 20


def test_measures_black_filled_rectangle_area():
    points = [Point(0, 0), Point(20, 0), Point(20, 10), Point(0, 10), Point(0, 0)]
    segments = [
        Line(a, b, (0, 0, 0), 0.01)
        for a, b in zip(points, points[1:])
    ]
    path = Path(
        segments=segments,
        closed=True,
        fill_color=(0, 0, 0),
        fill_enabled=True,
        stroke_enabled=False,
    )
    result = analyse_drawing(Drawing("test", 100, 100, paths=[path]))
    assert math.isclose(result.black_fill_area_mm2, 200.0)
    assert result.black_fill_paths == 1
