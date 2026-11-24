#!/usr/bin/env python3
"""Compare reduced-complexity fill models under leave-one-size-out validation.

Exploratory only: three distinct size levels, 24 observations. Candidate models
are deliberately nested and small. Uses standard-library least squares.
"""
from __future__ import annotations
import csv,re
from pathlib import Path
DATA=Path(__file__).resolve().parent/"controlled_tests_master.csv"

def parse(r):
 m=re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm",r.get("geometry",""),re.I)
 if not m:return None
 a,b=map(float,m.groups())
 return {"L":max(a,b)/100,"y":float(r["actual_time_seconds"]),
 "S":int("50%" in r.get("test_group","")),
 "O":int("left-to-right" in r.get("optimization","").lower()),
 "M":int(r.get("machine")=="60W"),"id":r.get("record_id","")}

def features(p,kind):
 L,S,O,M=p["L"],p["S"],p["O"],p["M"]
 base=[1,L]
 if kind=="base":return base
 if kind=="main":return base+[S,O,M]
 if kind=="main_length":return base+[S,O,M,S*L,O*L,M*L]
 if kind=="main_length_SO":return base+[S,O,M,S*L,O*L,M*L,S*O]
 if kind=="main_length_SM":return base+[S,O,M,S*L,O*L,M*L,S*M]
 if kind=="main_length_OM":return base+[S,O,M,S*L,O*L,M*L,O*M]
 raise ValueError(kind)

def solve(A,b):
 n=len(A[0]);ata=[[sum(row[i]*row[j] for row in A) for j in range(n)] for i in range(n)]
 atb=[sum(row[i]*v for row,v in zip(A,b)) for i in range(n)]
 for i in range(n):
  pivot=max(range(i,n),key=lambda r:abs(ata[r][i]))
  if abs(ata[pivot][i])<1e-10:raise ValueError("singular")
  ata[i],ata[pivot]=ata[pivot],ata[i];atb[i],atb[pivot]=atb[pivot],atb[i]
  d=ata[i][i];ata[i]=[x/d for x in ata[i]];atb[i]/=d
  for r in range(n):
   if r==i:continue
   f=ata[r][i];ata[r]=[x-f*y for x,y in zip(ata[r],ata[i])];atb[r]-=f*atb[i]
 return atb

def summarize(e):
 return (sum(abs(x) for x in e)/len(e),(sum(x*x for x in e)/len(e))**.5,sum(e)/len(e))
def main():
 with DATA.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
 ps=[p for r in rows if r.get("measurement_type","").lower().startswith("filled") and (p:=parse(r))]
 sizes=sorted({p["L"]*100 for p in ps})
 models=["base","main","main_length","main_length_SO","main_length_SM","main_length_OM"]
 print(f"Reduced-complexity model comparison: {len(ps)} observations; size levels={sizes}")
 print("Validation holds out all observations at each size level.")
 for model in models:
  errors=[]; foldstats=[]
  ncoef=len(features(ps[0],model))
  for size in sizes:
   test=[p for p in ps if p["L"]*100==size];train=[p for p in ps if p["L"]*100!=size]
   try:c=solve([features(p,model) for p in train],[p["y"] for p in train])
   except ValueError: print(f"{model}: singular fold");break
   e=[sum(x*v for x,v in zip(features(p,model),c))-p["y"] for p in test]
   errors+=e;foldstats.append((size,e))
  if len(errors)==24:
   mae,rmse,bias=summarize(errors)
   print(f"\n{model} ({ncoef} coefficients): MAE={mae:.3f}s RMSE={rmse:.3f}s bias={bias:+.3f}s")
   for size,e in foldstats:
    a,r,b=summarize(e);print(f"  {size:g}mm: MAE={a:.3f}s RMSE={r:.3f}s bias={b:+.3f}s")
 print("\nInterpretation warning: results are exploratory; size levels are only three.")
if __name__=="__main__":main()
