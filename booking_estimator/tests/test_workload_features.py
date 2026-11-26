from booking_estimator.workload_features import build_workload_features
def test_bundle():
 r=build_workload_features({"elements":[],"coverage_complete":True,"coverage_status":"complete","warnings":[]})
 assert r["workload_features_version"]==1 and r["coverage_complete"]
