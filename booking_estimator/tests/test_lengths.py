import math
import pytest

from booking_estimator.lengths import segment_length, path_length


def line(a, b):
    return {"type": "line", "start": a, "end": b}


def test_line_length():
    assert segment_length(line((0, 0), (3, 4))) == 5


def test_zero_length_line():
    assert segment_length(line((1, 2), (1, 2))) == 0


def test_quadratic_linear_case():
    seg = {"type": "quadratic", "start": (0, 0), "control": (1, 0), "end": (2, 0)}
    assert segment_length(seg) == pytest.approx(2.0)


def test_quadratic_curve():
    seg = {"type": "quadratic", "start": (0, 0), "control": (1, 2), "end": (2, 0)}
    assert segment_length(seg) == pytest.approx(2.957885715, rel=1e-7)


def test_cubic_linear_case():
    seg = {"type": "cubic", "start": (0, 0), "control1": (1, 0), "control2": (2, 0), "end": (3, 0)}
    assert segment_length(seg) == pytest.approx(3.0)


def test_cubic_curve():
    seg = {"type": "cubic", "start": (0, 0), "control1": (0, 10), "control2": (10, 10), "end": (10, 0)}
    assert segment_length(seg) == pytest.approx(20.0, rel=1e-7)


def test_degenerate_cubic():
    seg = {"type": "cubic", "start": (2, 2), "control1": (2, 2), "control2": (2, 2), "end": (2, 2)}
    assert segment_length(seg) == 0


def test_path_length_sum():
    segments = [line((0, 0), (3, 4)), line((3, 4), (6, 8))]
    assert path_length(segments) == 10


def test_arc_deferred():
    seg = {"type": "arc", "start": (0, 0), "rx": 1, "ry": 1, "rotation": 0, "large_arc": 0, "sweep": 1, "end": (1, 1)}
    with pytest.raises(NotImplementedError):
        segment_length(seg)


def test_unknown_segment():
    with pytest.raises(ValueError):
        segment_length({"type": "unknown"})
