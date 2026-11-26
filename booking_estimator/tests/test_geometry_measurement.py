import math
from booking_estimator.primitive_to_segments import primitive_to_segments
from booking_estimator.geometry_measurement import analyze_svg_geometry
from booking_estimator.lengths import segment_length
from booking_estimator.geometry import Matrix
from booking_estimator.geometry_pipeline import transform_segment


def test_closed_polygon_closes():
    seg=primitive_to_segments("polygon",{"points":[(0,0),(10,0),(10,10)]})
    assert len(seg)==3
    assert seg[-1]["end"]==(0,0)


def test_circle_is_four_arcs():
    seg=primitive_to_segments("circle",{"cx":0,"cy":0,"r":5})
    assert len(seg)==4 and all(s["type"]=="arc" for s in seg)


def test_rect_rounding_radius_clamped():
    seg=primitive_to_segments("rect",{"x":0,"y":0,"width":10,"height":8,"rx":8,"ry":8})
    assert len(seg)==8


def test_measurement_circle_mm():
    result=analyze_svg_geometry('<svg width="10mm" height="10mm" viewBox="0 0 10 10"><circle id="c" cx="5" cy="5" r="2"/></svg>')
    assert len(result["elements"])==1
    assert math.isclose(result["elements"][0]["length_mm"],4*math.pi*2,rel_tol=1e-6)


def test_mixed_shapes_and_transforms():
    svg='<svg width="100mm" height="100mm" viewBox="0 0 100 100"><g transform="translate(10 10)"><rect id="r" width="10" height="5"/><path id="p" d="M0 0 L3 4"/></g></svg>'
    result=analyze_svg_geometry(svg)
    assert len(result["elements"])==2
    assert math.isclose(result["total_length_mm"],30+5,rel_tol=1e-6)
    assert result["warnings"]==[]


def test_affine_transformed_arc_length():
    arc={"type":"arc","start":(1,0),"rx":1,"ry":1,"rotation":0,"large_arc":0,"sweep":1,"end":(0,1)}
    transformed=transform_segment(Matrix(a=2,d=1),arc)
    assert transformed["type"]=="transformed_arc"
    assert math.isclose(segment_length(transformed),2.422112055,rel_tol=1e-5)
