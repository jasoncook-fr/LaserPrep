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

@pytest.mark.parametrize("d",["","M0","X0 0","M0 0 Q1 1 2 2","M0 0 A1 1 0 0 1 2 2"])
def test_invalid_or_deferred_commands(d):
    with pytest.raises(ValueError): parse_path_data(d)
