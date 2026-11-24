#!/usr/bin/env python3
"""Explore condition-wise fill runtime slopes and curvature across three tested lengths."""
import csv,re
from pathlib import Path
DATA=Path(__file__).resolve().parent/"controlled_tests_master.csv"
def main():
 with DATA.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
 data={}
 for r in rows:
  if not r.get("measurement_type","").lower().startswith("filled"):continue
  m=re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm",r.get("geometry",""),re.I)
  if not m:continue
  a,b=map(float,m.groups());L=max(a,b);y=float(r["actual_time_seconds"])
  key=(r.get("machine","?"),"50%" if "50%" in r.get("test_group","") else "100%",r.get("optimization","?"))
  data.setdefault(key,[]).append((L,y,r.get("record_id","")))
 print("Condition-specific descriptive slopes and three-point curvature")
 print("Slope is estimated from endpoints; curvature compares the middle observation with the endpoint linear interpolation.")
 for key,vals in sorted(data.items()):
  vals=sorted(vals); x1,y1=vals[0][0],vals[0][1];x2,y2=vals[-1][0],vals[-1][1]
  slope=(y2-y1)/(x2-x1);intercept=y1-slope*x1
  xm,ym=vals[1];linear_mid=intercept+slope*xm;curv=ym-linear_mid
  print(f"\n{key[0]:>4} | {key[1]:>3} | {key[2]}")
  for x,y,rid in vals:print(f"  {x:>5.0f}mm: {y:>7.2f}s ({rid})")
  print(f"  endpoint slope: {slope:.5f} seconds/mm; intercept: {intercept:.2f}s")
  print(f"  middle-point deviation from endpoint line: {curv:+.2f}s")
 print("\nCaution: these are descriptive estimates from three points per condition; endpoint slopes are sensitive to measurement error.")
if __name__=="__main__":main()
