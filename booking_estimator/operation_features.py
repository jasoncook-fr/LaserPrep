"""Conservative operation/workload feature extraction (Stages 13-14).

No automatic color-to-operation mapping is assumed. Caller-provided mappings only.
"""
from collections import Counter

def extract_operation_features(measurement: dict, style_operation_map: dict | None = None) -> dict:
    mapping=style_operation_map or {}; buckets=Counter(); style_counts=Counter(); unclassified=0; rows=[]
    for e in measurement.get("elements",[]):
        style=e.get("style",{}) or {}; key=style.get("stroke","") or style.get("fill","") or "unstyled"
        op=mapping.get(key,"unclassified"); length=float(e.get("length_mm",0) or 0)
        buckets[op]+=length; style_counts[key]+=1; unclassified+=op=="unclassified"
        rows.append({"source_id":e.get("source_id"),"source_element":e.get("source_element"),
                     "style_key":key,"operation":op,"length_mm":length})
    return {"operation_features_version":1,"operation_length_mm":dict(buckets),"style_frequency":dict(style_counts),
        "unclassified_element_count":unclassified,"element_operation_rows":rows,"mapping_used":dict(mapping),
        "classification_is_explicit_mapping_only":True,"coverage_status":measurement.get("coverage_status","unknown"),
        "coverage_complete":bool(measurement.get("coverage_complete",False))}
