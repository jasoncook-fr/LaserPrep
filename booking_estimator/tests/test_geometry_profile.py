import pytest
from booking_estimator.geometry_profile import build_geometry_profile


def _line(length):
    return {"type": "line", "start": (0, 0), "end": (length, 0)}


def test_profile_summarizes_segments_and_contours():
    measurement = {
        "elements": [
            {"segments": [_line(2), _line(.5)], "length_mm": 2.5, "is_closed": True,
             "width_mm": 2, "height_mm": 1, "area_mm2": 2},
            {"segments": [_line(3)], "length_mm": 3, "is_closed": False,
             "width_mm": 3, "height_mm": 0, "area_mm2": 0},
        ],
        "coverage_status": "complete", "coverage_complete": True,
        "warning_count": 0, "width_mm": 3, "height_mm": 1, "area_mm2": 3,
    }
    profile = build_geometry_profile(measurement)
    assert profile["element_count"] == 2
    assert profile["segment_count"] == 3
    assert profile["total_length_mm"] == pytest.approx(5.5)
    assert profile["line_length_mm"] == pytest.approx(5.5)
    assert profile["closed_element_count"] == 1
    assert profile["open_element_count"] == 1
    assert profile["short_segment_count"] == 1
    assert profile["short_segment_fraction"] == pytest.approx(1/3)
    assert profile["coverage_complete"] is True


def test_empty_profile():
    profile = build_geometry_profile({"elements": []})
    assert profile["segment_count"] == 0
    assert profile["mean_segment_length_mm"] == 0
    assert profile["short_segment_fraction"] == 0


def test_threshold_validation():
    with pytest.raises(ValueError):
        build_geometry_profile({"elements": []}, -1)
