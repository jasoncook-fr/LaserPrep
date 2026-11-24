#!/usr/bin/env python3
"""Experimental integrated LaserPrep job-time estimator.

Component estimates are deliberately transparent and provisional. Filled engraving
uses the controlled fill calibration. Cut/vector components use provisional
production-derived or controlled-series rates and are not machine guarantees.
"""
from __future__ import annotations
import argparse, csv, re
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CAL=ROOT/"data"/"cut_time_calibration"/"controlled_tests_master.csv"
PROD=ROOT/"data"/"cut_time_calibration"/"production_jobs_master.csv"

def area_from_geometry(text):
    m=re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm",text,re.I)
    return float(m.group(1))*float(m.group(2)) if m else None

def linear_fit(x,y):
    n=len(x); xm=sum(x)/n; ym=sum(y)/n
    den=sum((v-xm)**2 for v in x)
    if not den: raise ValueError("Calibration requires distinct values.")
    slope=sum((a-xm)*(b-ym) for a,b in zip(x,y))/den
    intercept=ym-slope*xm
    sst=sum((v-ym)**2 for v in y)
    r2=1-sum((b-(slope*a+intercept))**2 for a,b in zip(x,y))/sst if sst else float("nan")
    return slope,intercept,r2

def fill_model(machine,speed,scan):
    rows=[]
    with CAL.open(newline="",encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("measurement_type")!="filled engraving": continue
            if r.get("machine")!=machine or r.get("test_group")!=f"Filled test {speed} speed" or r.get("optimization")!=scan: continue
            area=area_from_geometry(r.get("geometry",""))
            try: sec=float(r["actual_time_seconds"])
            except (KeyError,ValueError): continue
            if area: rows.append((area,sec,r.get("record_id","")))
    if len(rows)<2: return None
    m,b,r2=linear_fit([r[0] for r in rows],[r[1] for r in rows])
    return max(0,m),b,r2,rows

def cut_rate(machine,optim):
    """Seconds per mm based on the controlled 'bad-distance' 100%-series.
    The source distance is explicitly documented as suspect, so this is only a
    rough experimental rate; spline/line composition is not separable robustly.
    """
    target=f"800pt 100% speed / bad-distance series"
    rows=[]
    with CAL.open(newline="",encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("test_group")!=target or r.get("machine")!=machine: continue
            if r.get("optimization")!=optim: continue
            mm=re.search(r"reported distance ([\d.]+) mm",r.get("geometry",""))
            try: dist=float(mm.group(1)); sec=float(r["actual_time_seconds"])
            except (AttributeError,ValueError,KeyError): continue
            if dist: rows.append(sec/dist)
    if not rows:return None
    return sum(rows)/len(rows)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--machine",choices=("60W","100W"),required=True)
    p.add_argument("--speed",choices=("100%","50%"),default="100%",help="Filled engraving calibration speed")
    p.add_argument("--scan",choices=("Normal","Left-to-right"),default="Normal")
    p.add_argument("--fill-area-mm2",type=float,default=0)
    p.add_argument("--cut-length-mm",type=float,default=0,help="Blue cutting path length (mm)")
    p.add_argument("--vector-length-mm",type=float,default=0,help="Green/red vector engraving length combined (mm)")
    p.add_argument("--cut-optimization",choices=("JcT ON","JcT OFF"),default="JcT ON")
    p.add_argument("--overhead-sec",type=float,default=120,help="Explicit adjustable job overhead")
    p.add_argument("--vector-sec-per-m",type=float,default=34,help="Provisional vector engraving rate, seconds/m; adjustable")
    a=p.parse_args()
    if min(a.fill_area_mm2,a.cut_length_mm,a.vector_length_mm,a.overhead_sec)<0: p.error("Lengths, area and overhead must be non-negative.")
    fill=0; fill_meta=None
    if a.fill_area_mm2:
        fm=fill_model(a.machine,a.speed,a.scan)
        if fm:
            slope,b,r2,rows=fm
            fill=max(0,slope*a.fill_area_mm2+b)
            fill_meta=(r2,rows,slope,b)
        else: print("WARNING: no fill calibration for this condition; fill excluded.")
    rate=cut_rate(a.machine,a.cut_optimization)
    cut=a.cut_length_mm*rate if rate is not None else 0
    vector=a.vector_length_mm/1000*a.vector_sec_per_m
    total=cut+fill+vector+a.overhead_sec
    print("\nLASERPREP — EXPERIMENTAL INTEGRATED JOB ESTIMATE")
    print("="*56)
    print(f"Machine: {a.machine} | Cut condition: {a.cut_optimization}")
    print(f"Cut length: {a.cut_length_mm:,.1f} mm")
    if rate is None: print("Cut model: unavailable for selected condition")
    else: print(f"Cut model: {rate:.4f} sec/mm (rough controlled-series rate)")
    print(f"Estimated cutting: {cut:.1f} sec ({cut/60:.2f} min)")
    print(f"Vector engraving: {a.vector_length_mm:,.1f} mm @ {a.vector_sec_per_m:.1f} sec/m = {vector:.1f} sec")
    print(f"Filled area: {a.fill_area_mm2:,.1f} mm²")
    if fill_meta:
        r2,rows,slope,b=fill_meta
        print(f"Fill model: {slope*1000:.3f} sec/1,000 mm² + {b:.2f}; R²={r2:.3f}; n={len(rows)}")
        print(f"Estimated filled engraving: {fill:.1f} sec ({fill/60:.2f} min)")
    print(f"Overhead: {a.overhead_sec:.1f} sec ({a.overhead_sec/60:.2f} min)")
    print("-"*56)
    print(f"ESTIMATED TOTAL: {total:.1f} sec ({total/60:.2f} min; {total/60:.2f} min)")
    print("\nLIMITATIONS: cut rates use a controlled series whose reported distances are")
    print("documented as suspect. Vector rate is an adjustable provisional placeholder.")
    print("Fill model is calibrated to only three observations per condition.")
    print("This is a test harness, not yet integrated into LaserPrep's pipeline.")
if __name__=="__main__":main()
