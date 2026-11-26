import pytest
from booking_estimator.path_parser import parse_path_data

def test_absolute_commands():
    s=parse_path_data("M 1 2 L 4 2 H 7 V 9 Z")
    assert [(x["start"],x["end"]) for x in s]==[((1.,2.),(4.,2.)),((4.,2.),(7.,2.)),((7.,2.),(7.,9.)),((7.,9.),(1.,2.))]
    assert s[-1]["closed"] is True

def test_relative_and_repeated_coordinates():
    s=parse_path_data("m 1 1 2 0 l 0 3 h 2 v -1")
    assert [(x["start"],x["end"]) for x in s]==[((1.,1.),(3.,1.)),((3.,1.),(3.,4.)),((3.,4.),(5.,4.)),((5.,4.),(5.,3.))]

def test_multiple_subpaths():
    s=parse_path_data("M0 0L1 1 M5 5l2 0")
    assert len(s)==2
    assert s[-1]["start"]==(5.,5.)

def test_cubic_absolute():
    s=parse_path_data("M0 0 C10 0 10 10 20 10")
    assert s[0]=={"type":"cubic","start":(0.,0.),"control1":(10.,0.),"control2":(10.,10.),"end":(20.,10.)}

def test_cubic_relative_and_repeated():
    s=parse_path_data("m1 1 c2 0 2 2 4 2 2 0 2 2 4 2")
    assert len(s)==2
    assert s[0]["control1"]==(3.,1.)
    assert s[0]["control2"]==(3.,3.)
    assert s[0]["end"]==(5.,3.)
    assert s[1]["start"]==(5.,3.)
    assert s[1]["end"]==(9.,5.)

def test_smooth_cubic_reflects_previous_control():
    s=parse_path_data("M0 0 C2 0 4 0 6 0 S10 0 12 0")
    assert s[1]["control1"]==(8.,0.)
    assert s[1]["control2"]==(10.,0.)

def test_smooth_cubic_without_prior_cubic():
    s=parse_path_data("M1 1 L2 2 S4 4 6 6")
    assert s[1]["control1"]==(2.,2.)

def test_smooth_cubic_after_cubic_reflection_relative():
    s=parse_path_data("M0 0 c1 0 2 0 3 0 s2 0 3 0")
    assert s[1]["control1"]==(4.,0.)
    assert s[1]["control2"]==(5.,0.)
    assert s[1]["end"]==(6.,0.)

@pytest.mark.parametrize("d",["","M0","X0 0","M0 0 A1 1 0 0 1 2 2"])
def test_invalid_or_deferred_commands(d):
    with pytest.raises(ValueError): parse_path_data(d)


def test_quadratic_absolute():
    s=parse_path_data("M0 0 Q10 5 20 0")
    assert s[0]=={"type":"quadratic","start":(0.,0.),"control":(10.,5.),"end":(20.,0.)}

def test_quadratic_relative_and_repeated():
    s=parse_path_data("m1 1 q2 2 4 0 2 -2 4 0")
    assert len(s)==2
    assert s[0]["control"]==(3.,3.) and s[0]["end"]==(5.,1.)
    assert s[1]["start"]==(5.,1.) and s[1]["control"]==(7.,-1.) and s[1]["end"]==(9.,1.)

def test_smooth_quadratic_reflects_control():
    s=parse_path_data("M0 0 Q2 2 4 0 T8 0")
    assert s[1]["control"]==(6.,-2.)

def test_smooth_quadratic_relative():
    s=parse_path_data("M0 0 q2 2 4 0 t4 0")
    assert s[1]["control"]==(6.,-2.) and s[1]["end"]==(8.,0.)

def test_smooth_quadratic_without_prior_quadratic():
    s=parse_path_data("M1 1 L2 2 T4 4")
    assert s[1]["control"]==(2.,2.)

@pytest.mark.parametrize("d", ["M0 0 Q1 1", "M0 0 T", "M0 0 Q1 1 2 2 A1 1 0 0 1 3 3"])
def test_malformed_or_arc_still_deferred(d):
    with pytest.raises(ValueError): parse_path_data(d)
