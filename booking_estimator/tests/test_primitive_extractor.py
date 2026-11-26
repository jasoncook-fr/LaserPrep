import pytest

from booking_estimator.geometry import Point
from booking_estimator.primitive_extractor import extract_basic_shapes


SVG = """<svg xmlns="http://www.w3.org/2000/svg">
  <rect id="r" x="1" y="2" width="30" height="40" />
  <circle cx="5" cy="6" r="3"/>
  <ellipse cx="7" cy="8" rx="2" ry="4"/>
  <line x1="0" y1="1" x2="2" y2="3"/>
  <polyline points="0,0 10,10 20,0"/>
  <polygon points="1 2 3 4 5 6"/>
</svg>"""


def test_extract_supported_shapes_and_payloads():
    records = extract_basic_shapes(SVG)
    assert [r.element_type for r in records] == [
        "rect", "circle", "ellipse", "line", "polyline", "polygon"
    ]
    assert records[0].source_id == "r"
    assert records[0].payload["width"] == 30
    assert records[1].payload["r"] == 3
    assert records[2].payload["rx"] == 2
    assert records[3].payload["x2"] == 2
    assert records[4].payload["points"] == [(0, 0), (10, 10), (20, 0)]


def test_group_transform_and_style_inheritance():
    svg = """<svg xmlns="http://www.w3.org/2000/svg">
      <g transform="translate(10,20)" stroke="red" style="fill:none">
        <g transform="scale(2)">
          <rect id="nested" x="1" y="2" width="3" height="4" stroke-width="1"/>
        </g>
      </g>
    </svg>"""
    record = extract_basic_shapes(svg)[0]
    point = record.transform.apply(Point(1, 2))
    assert point == Point(12, 24)
    assert record.style["stroke"] == "red"
    assert record.style["fill"] == "none"
    assert record.style["stroke-width"] == "1"


def test_inline_style_overrides_presentational_attribute():
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="red" style="fill:blue" width="2" height="2"/></svg>'
    assert extract_basic_shapes(svg)[0].style["fill"] == "blue"


@pytest.mark.parametrize("svg", [
    '<svg xmlns="http://www.w3.org/2000/svg"><rect width="-1" height="2"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><circle r="-2"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><polyline points="1,2,3"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><rect width="nan" height="2"/></svg>',
])
def test_invalid_geometry_rejected(svg):
    with pytest.raises(ValueError):
        extract_basic_shapes(svg)


def test_bad_xml_rejected():
    with pytest.raises(ValueError, match="Malformed SVG/XML"):
        extract_basic_shapes("<svg><rect></svg>")


def test_path_is_not_yet_extracted():
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0L1 1"/><rect width="1" height="1"/></svg>'
    assert [r.element_type for r in extract_basic_shapes(svg)] == ["rect"]
