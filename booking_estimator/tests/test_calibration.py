import pytest
from booking_estimator.calibration import make_calibration_record,append_record,load_records
def test_roundtrip(tmp_path):
 r=make_calibration_record("m","plywood",3,120,"file-1"); p=tmp_path/"data.jsonl"; append_record(p,r)
 assert load_records(p)[0]["actual_runtime_s"]==120
def test_invalid():
 with pytest.raises(ValueError): make_calibration_record("m","wood",3,0,"f")
