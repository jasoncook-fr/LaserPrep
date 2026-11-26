from booking_estimator.operation_features import extract_operation_features
def test_explicit_mapping():
 m={"elements":[{"length_mm":10,"style":{"stroke":"red"}},{"length_mm":5,"style":{}}]}
 r=extract_operation_features(m,{"red":"cut"}); assert r["operation_length_mm"]["cut"]==10 and r["unclassified_element_count"]==1
