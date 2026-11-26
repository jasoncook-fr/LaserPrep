import pytest
from booking_estimator.svg_normalization import normalize_svg_paths


def test_path_geometry_normalized_to_mm_using_viewbox():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="50mm" viewBox="0 0 100 50"><path id="p" d="M0 0L100 50"/></svg>'
    r=normalize_svg_paths(svg)[0]
    assert r["coordinate_unit"] == "mm"
    assert r["segments"][0]["start"] == pytest.approx((0,0))
    assert r["segments"][0]["end"] == pytest.approx((100,50))


def test_nonzero_viewbox_origin_is_removed():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="50mm" viewBox="10 20 100 50"><path d="M10 20L110 70"/></svg>'
    s=normalize_svg_paths(svg)[0]["segments"][0]
    assert s["start"] == pytest.approx((0,0))
    assert s["end"] == pytest.approx((100,50))


def test_nested_transforms_normalized():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm" viewBox="0 0 100 100"><g transform="translate(10,20)"><path d="M0 0L5 5"/></g></svg>'
    s=normalize_svg_paths(svg)[0]["segments"][0]
    assert s["start"] == pytest.approx((10,20))
    assert s["end"] == pytest.approx((15,25))


def test_meet_letterbox_applied():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="200mm" height="100mm" viewBox="0 0 100 100"><path d="M0 0L100 100"/></svg>'
    s=normalize_svg_paths(svg)[0]["segments"][0]
    assert s["start"] == pytest.approx((50,0))
    assert s["end"] == pytest.approx((150,100))


def test_missing_physical_dimensions_rejected():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0L1 1"/></svg>'
    with pytest.raises(ValueError,match="physical width and height"):
        normalize_svg_paths(svg)
