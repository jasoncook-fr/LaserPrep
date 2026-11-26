import pytest
from booking_estimator.validation import evaluate_predictions
def test_metrics():
 r=evaluate_predictions([100,200],[110,190]); assert r["mae_s"]==10 and r["sample_count"]==2
def test_bad_inputs():
 with pytest.raises(ValueError): evaluate_predictions([],[])
