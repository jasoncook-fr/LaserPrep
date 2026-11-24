#!/usr/bin/env python3
"""Provisional LaserPrep cutting-time estimator (experimental only).

Rounded to whole minutes. This module is intentionally isolated from production
processing. Calibration assumptions are documented and conservative.
"""
from __future__ import annotations
import csv, math
from pathlib import Path

DATA = Path(__file__).resolve().parent / "controlled_tests_master.csv"

# Provisional rates derived from paired production jobs and controlled data.
# Straight-cut rates: paired LaGesse jobs imply roughly 47 mm/s for the
# extracted blue straight geometry after provisional estimate.
STRAIGHT_MM_PER_SECOND = {"60W": 47.3, "100W": 47.5}
# Green vector engraving proxy from the two paired LaGesse production jobs.
# This is job-specific empirical evidence, not a validated universal rate.
VECTOR_ENGRAVE_SECONDS_PER_MM = {"60W": 0.0278, "100W": 0.0243}

def _parse_fill_rows():
    groups={}
    if not DATA.exists(): return groups
    with DATA.open(newline="",encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if not row.get("measurement_type","").lower().startswith("filled engraving"): continue
            import re
            m=re.search(r"(\\d+(?:\\.\\d+)?)\\s*[x×]\\s*(\\d+(?:\\.\\d+)?)\\s*mm",row.get("geometry",""),re.I)
            if not m: continue
            a,b=map(float,m.groups()); length=max(a,b)
            speed="50%" if "50%" in row.get("test_group","") else "100%"
            orient="lr" if "left-to-right" in row.get("optimization","").lower() else "normal"
            machine=row.get("machine")
            key=(machine,speed,orient)
            groups.setdefault(key,[]).append((length,float(row["actual_time_seconds"])))
    return groups

def _fit_affine(points):
    xs=[p[0] for p in points]; ys=[p[1] for p in points]
    xm=sum(xs)/len(xs); ym=sum(ys)/len(ys)
    den=sum((x-xm)**2 for x in xs)
    slope=sum((x-xm)*(y-ym) for x,y in points)/den if den else 0.0
    return ym-slope*xm,slope

def estimate_fill(area_mm2, machine="100W", speed="100%", orientation="normal"):
    """Estimate raster-fill time from fill area using 10mm test-strip equivalent length."""
    if area_mm2<=0: return 0.0
    key=(machine,speed,"lr" if orientation.lower() in ("lr","left-to-right") else "normal")
    groups=_parse_fill_rows()
    pts=groups.get(key)
    if not pts:
        # Fallback: calibrated reference rate scaled for machine and settings.
        base={"100W":0.155,"60W":0.129}.get(machine,0.14) # seconds/mm, normal 100%
        if speed=="50%": base*=2
        if orientation.lower() in ("lr","left-to-right"): base*=2
        return area_mm2/10.0*base
    intercept,slope=_fit_affine(pts)
    equivalent_length=area_mm2/10.0
    return max(0.0,intercept+slope*equivalent_length)

def estimate(*, machine="100W", blue_straight_mm=0.0, blue_curves_mm=0.0,
              green_vector_mm=0.0, red_vector_mm=0.0, black_fill_area_mm2=0.0,
              fill_speed="100%", fill_orientation="normal", optimization=True,
              overhead_seconds=120.0):
    """Return a provisional component breakdown and rounded total estimate.

    Curves are currently included in straight geometry length as a simplification.
    Optimization is a neutral assumption at this stage; user input is accepted
    for API compatibility but no unsupported optimization multiplier is applied.
    """
    if machine not in ("60W","100W"): raise ValueError("machine must be 60W or 100W")
    cut_length=max(0.0,blue_straight_mm)+max(0.0,blue_curves_mm)
    cutting=cut_length/STRAIGHT_MM_PER_SECOND[machine]
    vector=(max(0.0,green_vector_mm)+max(0.0,red_vector_mm))*VECTOR_ENGRAVE_SECONDS_PER_MM[machine]
    fill=estimate_fill(max(0.0,black_fill_area_mm2),machine,fill_speed,fill_orientation)
    overhead=max(0.0,overhead_seconds)
    total=cutting+vector+fill+overhead
    return {"machine":machine,"cutting_seconds":cutting,"vector_engraving_seconds":vector,
            "fill_engraving_seconds":fill,"overhead_seconds":overhead,
            "total_seconds":total,"rounded_minutes":int(math.floor(total/60.0+0.5)),
            "experimental":True}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--machine",choices=("60W","100W"),default="100W")
    p.add_argument("--blue-straight-mm",type=float,default=0)
    p.add_argument("--blue-curves-mm",type=float,default=0)
    p.add_argument("--green-vector-mm",type=float,default=0)
    p.add_argument("--red-vector-mm",type=float,default=0)
    p.add_argument("--black-fill-area-mm2",type=float,default=0)
    p.add_argument("--fill-speed",choices=("50%","100%"),default="100%")
    p.add_argument("--fill-orientation",choices=("normal","lr"),default="normal")
    p.add_argument("--overhead-seconds",type=float,default=120)
    a=p.parse_args()
    r=estimate(machine=a.machine,blue_straight_mm=a.blue_straight_mm,blue_curves_mm=a.blue_curves_mm,
        green_vector_mm=a.green_vector_mm,red_vector_mm=a.red_vector_mm,
        black_fill_area_mm2=a.black_fill_area_mm2,fill_speed=a.fill_speed,
        fill_orientation=a.fill_orientation,overhead_seconds=a.overhead_seconds)
    for k,v in r.items(): print(f"{k}: {v}")
