"""Simple, versioned calibration dataset management using JSONL."""
from __future__ import annotations
import json, math
from pathlib import Path
from datetime import datetime, timezone
_REQUIRED=("machine_id","material","thickness_mm","actual_runtime_s","file_id")
def make_calibration_record(machine_id,material,thickness_mm,actual_runtime_s,file_id,feature_bundle=None,configuration=None,notes=""):
    if not machine_id or not material or not file_id: raise ValueError("machine_id, material and file_id required")
    if thickness_mm<0 or actual_runtime_s<=0 or not math.isfinite(thickness_mm) or not math.isfinite(actual_runtime_s): raise ValueError("thickness must be finite and non-negative; runtime finite and positive")
    return {"record_version":1,"recorded_at":datetime.now(timezone.utc).isoformat(),"machine_id":str(machine_id),
        "material":str(material),"thickness_mm":float(thickness_mm),"actual_runtime_s":float(actual_runtime_s),
        "file_id":str(file_id),"feature_bundle":feature_bundle,"configuration":configuration or {},"notes":str(notes)}
def append_record(path,record):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("a",encoding="utf-8") as f: f.write(json.dumps(record,ensure_ascii=False,allow_nan=False)+"\n")
def load_records(path):
    records=[]
    with Path(path).open(encoding="utf-8") as f:
        for n,line in enumerate(f,1):
            if not line.strip(): continue
            try: row=json.loads(line)
            except json.JSONDecodeError as exc: raise ValueError(f"Invalid JSONL at line {n}") from exc
            if not all(k in row for k in _REQUIRED): raise ValueError(f"Missing required fields at line {n}")
            records.append(row)
    return records
