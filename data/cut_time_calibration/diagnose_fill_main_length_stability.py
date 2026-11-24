#!/usr/bin/env python3
"""Coefficient stability diagnostic for the 8-term exploratory filled-engraving model."""
from __future__ import annotations
import csv,re
from pathlib import Path
DATA=Path(__file__).resolve().parent/"controlled_tests_master.csv"
OUT=Path(__file__).resolve().parent/"fill_main_length_stability.csv"
NAMES=["intercept","length","speed","orientation","machine","speed_length","orientation_length","machine_length"]
def parse(r):
 m=re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm",r.get("geometry",""),re.I)
 if not m:return None
 a,b=map(float,m.groups())
 return {"L":max(a,b)/100,"y":float(r["actual_time_seconds"]),"S":int("50%" in r.get("test_group","")),"O":int("left-to-right" in r.get("optimization","").lower()),"M":int(r.get("machine")=="60W"),"id":r.get("record_id","")}
def features(p):
 L,S,O,M=p["L"],p["S"],p["O"],p["M"]
 return [1,L,S,O,M,S*L,O*L,M*L]
def solve(A,b):
 n=len(A[0]);ata=[[sum(row[i]*row[j] for row in A) for j in range(n)] for i in range(n)];atb=[sum(row[i]*v for row,v in zip(A,b)) for i in range(n)]
 for i in range(n):
  pivot=max(range(i,n),key=lambda r:abs(ata[r][i])); 
  if abs(ata[pivot][i])<1e-10:raise ValueError("singular")
  ata[i],ata[pivot]=ata[pivot],ata[i];atb[i],atb[pivot]=atb[pivot],atb[i]
  d=ata[i][i];ata[i]=[x/d for x in ata[i]];atb[i]/=d
  for r in range(n):
   if r==i:continue
   f=ata[r][i];ata[r]=[x-f*y for x,y in zip(ata[r],ata[i])];atb[r]-=f*atb[i]
 return atb
def main():
 with DATA.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
 ps=[p for r in rows if r.get("measurement_type","").lower().startswith("filled") and (p:=parse(r))]
 sizes=sorted({round(p["L"]*100,5) for p in ps}); folds=[]; allrows=[]
 print(f"Coefficient stability: {len(ps)} observations; size levels={sizes}")
 for size in sizes:
  tr=[p for p in ps if round(p["L"]*100,5)!=size];te=[p for p in ps if round(p["L"]*100,5)==size]
  c=solve([features(p) for p in tr],[p["y"] for p in tr]);folds.append((size,c))
  err=[]
  for p in te:
   pred=sum(x*v for x,v in zip(features(p),c));e=pred-p["y"];err.append(e)
   allrows.append({"held_out_size_mm":size,"record_id":p["id"],"actual_seconds":p["y"],"predicted_seconds":round(pred,4),"error_seconds":round(e,4)})
  print(f"\nFold excluding {size:g}mm: train sizes={[s for s in sizes if s!=size]}")
  for n,v in zip(NAMES,c):print(f"  {n:20s} {v:+.6f}")
  print(f"  Held-out mean error: {sum(err)/len(err):+.3f}s; MAE: {sum(abs(x) for x in err)/len(err):.3f}s")
 print("\nCoefficient ranges across folds:")
 for i,n in enumerate(NAMES):
  vals=[c[i] for _,c in folds];print(f"  {n:20s} min={min(vals):+.6f} max={max(vals):+.6f} span={max(vals)-min(vals):.6f}")
 full=solve([features(p) for p in ps],[p["y"] for p in ps])
 print("\nFull-data coefficients (descriptive, not validation):")
 for n,v in zip(NAMES,full):print(f"  {n:20s} {v:+.6f}")
 with OUT.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=allrows[0].keys());w.writeheader();w.writerows(allrows)
 print(f"\nPer-observation fold predictions written: {OUT.name}")
 print("Warning: coefficients are highly dependent on scale and only three sizes are available.")
if __name__=="__main__":main()
