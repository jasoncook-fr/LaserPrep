#!/usr/bin/env python3
"""Matched-pair and factor-effect diagnostics for controlled fill tests.

No production estimator is changed. This script summarizes effects directly
from matched experimental conditions and writes no coefficients for deployment.
"""
from __future__ import annotations
import argparse, csv, re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"controlled_tests_master.csv"

def parse(row):
    m=re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm",row.get("geometry",""),re.I)
    if not m:return None
    a,b=map(float,m.groups())
    speed="50%" if "50%" in row.get("test_group","") else "100%"
    orient=row.get("optimization","").strip()
    return (row["machine"],speed,orient,max(a,b),min(a,b),float(row["actual_time_seconds"]),row["record_id"])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,default=DATA)
    args=ap.parse_args()
    with args.data.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
    data=[p for r in rows if r.get("measurement_type","").lower().startswith("filled") and (p:=parse(r))]
    print(f"Fill factor diagnostics: {len(data)} parsed measurements")
    print("All comparisons are descriptive, matched comparisons; not deployment coefficients.")
    # matched orientation contrasts
    by=defaultdict(dict)
    for m,s,o,l,w,t,rid in data:by[(m,s,l,w)][o.lower()] = (t,rid)
    orient_diffs=[]
    for key,vals in sorted(by.items()):
        normal=next((v for k,v in vals.items() if k=="normal"),None)
        ltr=next((v for k,v in vals.items() if "left-to-right" in k),None)
        if normal and ltr:
            ratio=ltr[0]/normal[0]
            orient_diffs.append(ratio)
            print(f"ORIENTATION {key[0]} {key[1]} {key[3]:g}x{key[2]:g}: Normal {normal[0]:.0f}s; L→R {ltr[0]:.0f}s; ratio {ratio:.3f}")
    if orient_diffs:print(f"Orientation ratio: mean={sum(orient_diffs)/len(orient_diffs):.3f}, range={min(orient_diffs):.3f}–{max(orient_diffs):.3f}, n={len(orient_diffs)}")
    # speed contrasts
    by=defaultdict(dict)
    for m,s,o,l,w,t,rid in data:by[(m,o,l,w)][s]=(t,rid)
    ratios=[]
    for key,vals in sorted(by.items()):
        if "50%" in vals and "100%" in vals:
            t50,t100=vals["50%"][0],vals["100%"][0]
            ratio=t50/t100
            ratios.append(ratio)
            print(f"SPEED {key[0]} {key[1]} {key[3]:g}x{key[2]:g}: 100% {t100:.0f}s; 50% {t50:.0f}s; ratio {ratio:.3f}")
    if ratios:print(f"Speed ratio 50%/100%: mean={sum(ratios)/len(ratios):.3f}, range={min(ratios):.3f}–{max(ratios):.3f}, n={len(ratios)}")
    # machine contrasts, matched speed/orientation/size
    by=defaultdict(dict)
    for m,s,o,l,w,t,rid in data:by[(s,o,l,w)][m]=(t,rid)
    ratios=[]
    for key,vals in sorted(by.items()):
        if "60W" in vals and "100W" in vals:
            t60,t100=vals["60W"][0],vals["100W"][0]
            ratio=t60/t100
            ratios.append(ratio)
            print(f"MACHINE {key[0]} {key[1]} {key[3]:g}x{key[2]:g}: 60W {t60:.0f}s; 100W {t100:.0f}s; ratio {ratio:.3f}")
    if ratios:print(f"Machine ratio 60W/100W: mean={sum(ratios)/len(ratios):.3f}, range={min(ratios):.3f}–{max(ratios):.3f}, n={len(ratios)}")
    print("\nCaution: tests do not document enough details to assume these contrasts generalize to arbitrary fill geometries.")

if __name__=="__main__":main()
