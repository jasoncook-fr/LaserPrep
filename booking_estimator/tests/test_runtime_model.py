from booking_estimator.machine_model import MachineConfig
from booking_estimator.runtime_model import estimate_runtime
def test_estimate_is_unvalidated():
 f={"profile":{"line_length_mm":100,"curve_length_mm":0},"complexity":{"turn_density_per_m":0},"coverage_complete":True,"coverage_status":"complete"}
 r=estimate_runtime(f,MachineConfig("test",60,10,source="measured config"),"plywood",3)
 assert r["estimated_runtime_s"]==10 and r["confidence"]=="unvalidated"
