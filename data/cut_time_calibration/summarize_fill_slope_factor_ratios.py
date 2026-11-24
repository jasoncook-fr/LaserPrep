#!/usr/bin/env python3
"""Summarize fill-model slope ratios for speed, orientation, and machine."""
import csv,re
from pathlib import Path
DATA=Path(__file__).resolve().parent/"controlled_tests_master.csv"
def main():
 with DATA.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
 d={}
 for r in rows:
  if not r.get("measurement_type","").lower().startswith("filled"):continue
  m=re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm",r.get("geometry",""),re.I)
  if not m:continue
  a,b=map(float,m.groups());L=max(a,b);y=float(r["actual_time_seconds"])
  d.setdefault((r["machine"],"50%" if "50%" in r.get("test_group","") else "100%",r["optimization"]),[]).append((L,y))
 slopes={}
 for k,v in d.items():
  v=sorted(v);s=(v[-1][1]-v[0][1])/(v[-1][0]-v[0][0]);i=v[0][1]-s*v[0][0];slopes[k]=(s,i)
 print("Endpoint-derived slope and intercept contrasts (descriptive)")
 print("\nOrientation ratios (Left-to-right / Normal):")
 for m in ("60W","100W"):
  for speed in ("100%","50%"):
   n=slopes[(m,speed,"Normal")][0];lr=slopes[(m,speed,"Left-to-right")][0]
   print(f"  {m} {speed}: {lr/n:.4f}x")
 print("\nSpeed ratios (50% / 100%):")
 for m in ("60W","100W"):
  for o in ("Normal","Left-to-right"):
   lo=slopes[(m,"50%",o)][0];hi=slopes[(m,"100%",o)][0]
   print(f"  {m} {o}: {lo/hi:.4f}x")
 print("\nMachine ratios (60W / 100W slope):")
 for speed in ("100%","50%"):
  for o in ("Normal","Left-to-right"):
   lo=slopes[("60W",speed,o)][0];hi=slopes[("100W",speed,o)][0]
   print(f"  {speed} {o}: {lo/hi:.4f}x")
 print("\nEndpoint-line intercepts (time at extrapolated zero length):")
 for k,(s,i) in sorted(slopes.items()):print(f"  {k[0]} | {k[1]} | {k[2]}: {i:.3f}s")
 print("\nThese are extrapolated intercepts and ratio diagnostics, not validated physical constants.")
if __name__=="__main__":main()
