import math
import pytest

from booking_estimator.geometry import Point
from booking_estimator.transforms import parse_transform_list, parse_transform_function


def close_point(actual, expected, tol=1e-9):
    assert actual.x == pytest.approx(expected.x, abs=tol)
    assert actual.y == pytest.approx(expected.y, abs=tol)


def test_translate():
    close_point(parse_transform_list("translate(10,20)").apply(Point(1, 2)), Point(11, 22))
    close_point(parse_transform_list("translate(10)").apply(Point(1, 2)), Point(11, 2))


def test_scale():
    close_point(parse_transform_list("scale(2,3)").apply(Point(1, 2)), Point(2, 6))
    close_point(parse_transform_list("scale(2)").apply(Point(1, 2)), Point(2, 4))


def test_rotate_90_degrees():
    close_point(parse_transform_list("rotate(90)").apply(Point(1, 0)), Point(0, 1))


def test_rotate_about_center():
    close_point(parse_transform_list("rotate(90,10,10)").apply(Point(11, 10)), Point(10, 11))


def test_skew_x_y():
    close_point(parse_transform_list("skewX(45)").apply(Point(0, 1)), Point(1, 1))
    close_point(parse_transform_list("skewY(45)").apply(Point(1, 0)), Point(1, 1))


def test_matrix():
    close_point(parse_transform_list("matrix(2,0,0,3,4,5)").apply(Point(1, 1)), Point(6, 8))


def test_transform_list_order():
    # SVG list: translate then scale; scale is applied first to point, then translate.
    close_point(parse_transform_list("translate(10 0) scale(2)").apply(Point(1, 0)), Point(12, 0))


def test_whitespace_and_exponent():
    close_point(parse_transform_list("translate(1e1 -2.5) scale(2, 3)").apply(Point(1, 1)), Point(12, 0.5))


@pytest.mark.parametrize("bad", [
    "translate()", "translate(1,2,3)", "scale(1,2,3)", "rotate(1,2)",
    "skewX(1,2)", "matrix(1,2,3)", "unknown(1)", "translate(1) junk",
    "translate(foo)", "translate(1,,2)", "translate(1) scale("
])
def test_malformed_transform_rejected(bad):
    with pytest.raises(ValueError):
        parse_transform_list(bad)


def test_function_argument_validation():
    with pytest.raises(ValueError):
        parse_transform_function("rotate", [0, 1])
