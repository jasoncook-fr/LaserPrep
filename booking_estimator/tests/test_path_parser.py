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

@pytest.mark.parametrize("d",["","M0","X0 0","M0 0 C1 1 2 2 3 3","M0 0 A1 1 0 0 1 2 2"])
def test_invalid_or_deferred_commands(d):
    with pytest.raises(ValueError): parse_path_data(d)
