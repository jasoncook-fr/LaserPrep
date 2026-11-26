import pytest
from booking_estimator.viewport import viewbox_to_viewport_matrix
from booking_estimator.geometry import Point


def test_default_meet_center_mapping():
    m=viewbox_to_viewport_matrix("0 0 100 100","200mm","100mm")
    assert m.apply(Point(0,0)) == Point(50,0)
    assert m.apply(Point(100,100)) == Point(150,100)


def test_none_nonuniform_scaling():
    m=viewbox_to_viewport_matrix("10 20 100 100","200mm","100mm","none")
    assert m.apply(Point(10,20)) == Point(0,0)
    assert m.apply(Point(110,120)) == Point(200,100)


def test_meet_alignment_top_left():
    m=viewbox_to_viewport_matrix("0 0 100 100","200mm","100mm","xMinYMin meet")
    assert m.apply(Point(0,0)) == Point(0,0)
    assert m.apply(Point(100,100)) == Point(100,100)


def test_slice_center_alignment():
    m=viewbox_to_viewport_matrix("0 0 100 100","200mm","100mm","xMidYMid slice")
    assert m.apply(Point(0,0)) == Point(0,-50)
    assert m.apply(Point(100,100)) == Point(200,150)


def test_defer_token_accepted():
    m=viewbox_to_viewport_matrix("0 0 100 100","100mm","100mm","defer xMaxYMax meet")
    assert m.apply(Point(0,0)) == Point(0,0)


@pytest.mark.parametrize("value",["bad align","xMidYMid stretch","none meet","xMidYMid meet extra"])
def test_bad_preserve_aspect_ratio_rejected(value):
    with pytest.raises(ValueError):
        viewbox_to_viewport_matrix("0 0 100 100","100mm","100mm",value)
