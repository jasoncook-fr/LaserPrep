"""Combined feature bundle for downstream calibration/modeling."""
from .geometry_profile import build_geometry_profile
from .geometry_complexity import analyze_geometry_complexity
from .spatial_complexity import analyze_spatial_complexity
from .operation_features import extract_operation_features

def build_workload_features(measurement: dict, grid_size: int=4, short_segment_threshold_mm: float=1.0,
                           style_operation_map: dict | None=None) -> dict:
    return {"workload_features_version":1,"profile":build_geometry_profile(measurement,short_segment_threshold_mm),
        "complexity":analyze_geometry_complexity(measurement),"spatial":analyze_spatial_complexity(measurement,grid_size),
        "operations":extract_operation_features(measurement,style_operation_map),
        "coverage_status":measurement.get("coverage_status","unknown"),
        "coverage_complete":bool(measurement.get("coverage_complete",False)),
        "warnings":list(measurement.get("warnings",[]))}
