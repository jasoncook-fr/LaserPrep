"""Tests for SVG dimension normalization."""

import math
import pytest

from booking_estimator.svg_units import SVGUnitError, parse_length_mm, parse_viewbox, resolve_svg_dimensions


@pytest.mark.parametrize("value,expected", [
    ("1000mm", 1000.0), ("100cm", 1000.0), ("39.37007874in", 1000.0),
    ("2834.645669pt", 1000.0), ("166.6666667pc", 1000.0),
    ("3779.527559px", 1000.0), ("3779.527559", 1000.0),
])
def test_absolute_units(value, expected):
    assert parse_length_mm(value) == pytest.approx(expected, abs=1e-5)


def test_viewbox_parse():
    assert parse_viewbox("-10, 20 1000 600") == (-10.0, 20.0, 1000.0, 600.0)


def test_physical_dimensions_with_viewbox():
    result = resolve_svg_dimensions("1000mm", "600mm", "0 0 1000 600")
    assert result.physical_dimensions_known
    assert result.width_mm == 1000
    assert result.height_mm == 600
    assert result.scale_x_mm_per_user_unit == pytest.approx(1)
    assert result.scale_y_mm_per_user_unit == pytest.approx(1)


def test_viewbox_scaled_to_physical_canvas():
    result = resolve_svg_dimensions("100cm", "60cm", "0 0 500 300")
    assert result.scale_x_mm_per_user_unit == pytest.approx(2)
    assert result.scale_y_mm_per_user_unit == pytest.approx(2)


def test_unitless_root_dimensions_use_css_px_reference():
    result = resolve_svg_dimensions("960", "480", None)
    assert result.width_mm == pytest.approx(254)
    assert result.height_mm == pytest.approx(127)
    assert result.scale_x_mm_per_user_unit == pytest.approx(96 / 25.4)


def test_missing_dimensions_are_not_guessed():
    result = resolve_svg_dimensions(None, None, "0 0 1000 600")
    assert not result.physical_dimensions_known
    assert result.width_mm is None
    assert result.scale_x_mm_per_user_unit is None
    assert result.warnings


@pytest.mark.parametrize("value", ["0mm", "-10mm", "10%", "10foo", "bad"])
def test_invalid_lengths(value):
    with pytest.raises(SVGUnitError):
        parse_length_mm(value)


@pytest.mark.parametrize("value", ["0 0 0 10", "1 2 3", "bad 0 10 10"])
def test_invalid_viewbox(value):
    with pytest.raises(SVGUnitError):
        parse_viewbox(value)


def test_aspect_ratio_warning():
    result = resolve_svg_dimensions("1000mm", "600mm", "0 0 1000 500")
    assert result.warnings
