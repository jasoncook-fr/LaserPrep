import pytest

from booking_estimator.geometry import BoundingBox, Matrix, Point


def test_matrix_identity():
    assert Matrix().apply(Point(2, 3)) == Point(2, 3)


def test_matrix_translation_and_scale():
    assert Matrix(e=10, f=-4).apply(Point(2, 3)) == Point(12, -1)
    assert Matrix(a=2, d=3).apply(Point(2, 3)) == Point(4, 9)


def test_matrix_composition_applies_other_first():
    composed = Matrix(e=10, f=5).compose(Matrix(a=2, d=2))
    assert composed.apply(Point(3, 4)) == Point(16, 13)


def test_bbox_properties_and_union():
    box = BoundingBox(-1, 2, 4, 7)
    assert (box.width, box.height, box.area) == (5, 5, 25)
    assert box.union(BoundingBox(3, -2, 8, 5)) == BoundingBox(-1, -2, 8, 7)


def test_bbox_rejects_inverted_bounds():
    with pytest.raises(ValueError):
        BoundingBox(4, 0, 1, 2)
