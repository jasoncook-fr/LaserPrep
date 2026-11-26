import pytest
from booking_estimator.geometry_complexity import analyze_geometry_complexity


def line(a,b):
    return {"type":"line","start":a,"end":b}


def test_straight_connected_segments_zero_turn():
    m={"elements":[{"segments":[line((0,0),(10,0)),line((10,0),(20,0))],"length_mm":20}]}
    r=analyze_geometry_complexity(m)
    assert r["transition_count"]==1
    assert r["mean_turn_angle_deg"]==pytest.approx(0)
    assert r["sharp_turn_counts"]["30.0"]==0


def test_right_angle_and_disconnected_segments():
    m={"elements":[{"segments":[line((0,0),(1,0)),line((1,0),(1,1)),line((9,9),(10,9))],"length_mm":2}]}
    r=analyze_geometry_complexity(m)
    assert r["transition_count"]==1
    assert r["maximum_turn_angle_deg"]==pytest.approx(90)
    assert r["sharp_turn_counts"]["90.0"]==1


def test_angle_threshold_validation():
    with pytest.raises(ValueError):
        analyze_geometry_complexity({"elements":[]},(181,))


def test_empty():
    r=analyze_geometry_complexity({"elements":[]})
    assert r["transition_count"]==0
    assert r["turn_density_per_m"]==0
