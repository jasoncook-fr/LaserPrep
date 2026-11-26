import pytest
from booking_estimator.geometry import Matrix, Point
from booking_estimator.geometry_pipeline import determinant, inverse, transform_segment, transform_vector

def test_vector_excludes_translation():
    assert transform_vector(Matrix(a=2,d=3,e=10,f=4),Point(1,2)) == Point(2,6)

def test_determinant():
    assert determinant(Matrix(a=2,b=1,c=3,d=4)) == 5

def test_inverse_round_trip():
    m=Matrix(a=2,b=1,c=3,d=4,e=10,f=-5); p=Point(4,7); q=inverse(m).apply(m.apply(p))
    assert q.x == pytest.approx(p.x) and q.y == pytest.approx(p.y)

def test_singular_inverse_rejected():
    with pytest.raises(ValueError): inverse(Matrix(a=1,b=2,c=2,d=4))

def test_transform_line():
    s={"type":"line","start":(1,2),"end":(3,4)}
    assert transform_segment(Matrix(a=2,d=3,e=10,f=-4),s)=={"type":"line","start":(12,2),"end":(16,8)}

def test_transform_quadratic():
    s={"type":"quadratic","start":(1,2),"control":(2,3),"end":(3,4)}
    assert transform_segment(Matrix(a=2,d=3,e=10,f=-4),s)=={"type":"quadratic","start":(12,2),"control":(14,5),"end":(16,8)}

def test_arc_wrapper_preserves_original():
    s={"type":"arc","start":(0,0),"rx":5,"ry":3,"rotation":20,"large_arc":0,"sweep":1,"end":(4,2)}
    out=transform_segment(Matrix(a=2,d=3),s)
    assert out["type"]=="transformed_arc" and out["segment"]==s
