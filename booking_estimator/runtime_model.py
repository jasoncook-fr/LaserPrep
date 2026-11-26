"""Transparent baseline runtime proxy; deliberately uncalibrated."""
def estimate_runtime(workload_features: dict,machine_config,material=None,thickness_mm=None):
    profile=workload_features.get("profile",{}); line=float(profile.get("line_length_mm",0) or 0)
    curves=float(profile.get("curve_length_mm",0) or 0); speed=float(machine_config.travel_speed_mm_s)
    cs=float(machine_config.curve_speed_mm_s or speed); base=line/speed+curves/cs
    density=float(workload_features.get("complexity",{}).get("turn_density_per_m",0) or 0)
    penalty=base*float(machine_config.corner_penalty_factor)*density
    total=base+penalty+float(machine_config.setup_time_s); warnings=[]
    if not workload_features.get("coverage_complete",False): warnings.append("Geometry coverage is partial or unknown.")
    if not material or thickness_mm is None: warnings.append("Material and thickness are not supplied.")
    warnings.append("Effective speeds are assumptions; model is not trained on measured runtimes.")
    if "placeholder" in machine_config.source.lower(): warnings.append("Machine configuration is a placeholder.")
    return {"runtime_model_version":1,"estimated_runtime_s":total,"estimated_runtime_min":total/60,
        "base_geometry_time_s":base,"corner_penalty_s":penalty,"setup_time_s":machine_config.setup_time_s,
        "machine_id":machine_config.machine_id,"material":material,"thickness_mm":thickness_mm,
        "confidence":"unvalidated","warnings":warnings,"input_coverage_status":workload_features.get("coverage_status","unknown")}
