import pytest
from booking_estimator.svg_transform_integration import extract_transformed_paths


def test_nested_group_and_element_transforms_are_applied_to_path():
    svg = """<svg xmlns="http://www.w3.org/2000/svg">
      <g transform="translate(10,20)">
        <g transform="scale(2)">
          <path id="p" transform="translate(1,2)" d="M0 0 L3 4"/>
        </g>
      </g>
    </svg>"""
    records = extract_transformed_paths(svg)
    assert len(records) == 1
    seg = records[0]["segments"][0]
    # Element translation, scaling, and outer translation are composed.
    assert seg["start"] == pytest.approx((12, 24))
    assert seg["end"] == pytest.approx((18, 32))
    assert records[0]["source_id"] == "p"


def test_path_style_metadata_retained():
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><path id="x" stroke="red" d="M0 0L1 1"/></svg>'
    r = extract_transformed_paths(svg)[0]
    assert r["style"]["stroke"] == "red"
    assert r["source_id"] == "x"


def test_non_path_shapes_not_returned():
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/><path d="M0 0L1 1"/></svg>'
    assert len(extract_transformed_paths(svg)) == 1
