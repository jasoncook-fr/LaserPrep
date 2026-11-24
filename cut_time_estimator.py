#!/usr/bin/env python3
"""Experimental filled-engraving time estimator from LaserPrep controlled data.

This estimates BLACK FILLED ENGRAVING only. It does not estimate vector cutting,
vector engraving, setup/handling time, or a whole-job runtime.

Example:
  python3 cut_time_estimator.py --machine 60W --speed 100% --scan Normal --area-mm2 4500
"""
from __future__ import annotations
import argparse, csv, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "cut_time_calibration" / "controlled_tests_master.csv"

def area_from_geometry(text: str):
    m = re.search(r"(\\d+(?:\\.\\d+)?)\\s*[x×]\\s*(\\d+(?:\\.\\d+)?)\\s*mm", text, re.I)
    return float(m.group(1))*float(m.group(2)) if m else None

def fit(x, y):
    n=len(x); xm=sum(x)/n; ym=sum(y)/n
    ssx=sum((a-xm)**2 for a in x)
    if ssx == 0: raise ValueError("Need at least two distinct calibration areas.")
    slope=sum((a-xm)*(b-ym) for a,b in zip(x,y))/ssx
    intercept=ym-slope*xm
    sst=sum((b-ym)**2 for b in y)
    sse=sum((b-(slope*a+intercept))**2 for a,b in zip(x,y))
    return slope,intercept,(1-sse/sst) if sst else float("nan")

def calibration(machine,speed,scan):
    rows=[]
    with DATA.open(newline="",encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("measurement_type")!="filled engraving": continue
            if row.get("machine")!=machine or row.get("test_group")!=f"Filled test {speed} speed" or row.get("optimization")!=scan: continue
            area=area_from_geometry(row.get("geometry",""))
            try: seconds=float(row["actual_time_seconds"])
            except (KeyError,ValueError): continue
            if area is not None: rows.append((area,seconds,row.get("record_id","")))
    if len(rows)<2: raise ValueError(f"No usable calibration series for {machine}, {speed}, {scan}.")
    slope,intercept,r2=fit([r[0] for r in rows],[r[1] for r in rows])
    return rows,slope,intercept,r2

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--machine",choices=("60W","100W"),required=True)
    p.add_argument("--speed",choices=("100%","50%"),required=True)
    p.add_argument("--scan",choices=("Normal","Left-to-right"),required=True)
    p.add_argument("--area-mm2",type=float,required=True)
    a=p.parse_args()
    rows,slope,intercept,r2=calibration(a.machine,a.speed,a.scan)
    estimate=max(0.0,slope*a.area_mm2+intercept)
    print("\\nLASERPREP — EXPERIMENTAL FILLED ENGRAVING ESTIMATE")
    print("="*54)
    print(f"Machine:       {a.machine}")
    print(f"Speed:         {a.speed}")
    print(f"Scan:          {a.scan}")
    print(f"Area:          {a.area_mm2:,.1f} mm²")
    print(f"Calibration:   {len(rows)} measurements ({', '.join(r[2] for r in rows)})")
    print(f"Model:         {slope*1000:.3f} sec / 1,000 mm² + {intercept:.2f} sec")
    print(f"R²:            {r2:.3f}")
    print("-"*54)
    print(f"ESTIMATED FILL TIME: {estimate:.1f} sec ({estimate/60:.2f} min)")
    print("\\nScope: filled engraving only. No cutting, vector engraving or overhead.")
    print("Experimental: only three measured areas underpin each selected condition.")
if __name__=="__main__": main()
