#!/usr/bin/env python3
"""Cross-condition, size-held-out model diagnostics for rectangular fill tests.

This evaluates pooled simple models against the 24 fill observations using
leave-one-size-level-out validation (train on two lengths, test on the third).
No production coefficients are produced or written.

Model families:
 A: common affine length model (intercept + length)
 B: condition-specific intercept and slope (8 groups, too flexible for this
    tiny dataset; included as a cautionary reference)
 C: pooled model with intercept and slope effects for machine, speed, and
    orientation, plus length-factor interactions (structured model).

The script uses standard-library least squares and reports pooled validation
metrics and per-size-level results.
"""
from __future__ import annotations
import argparse,csv,re
from pathlib import Path
DATA=Path(__file__).resolve().parent/"controlled_tests_master.csv"

def parse(r):
 m=re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm",r.get("geometry",""),re.I)
 if not m:return None
 a,b=map(float,m.groups());length=max(a,b)
 speed=1 if "50%" in r.get("test_group","") else 0
 orient=1 if "left-to-right" in r.get("optimization","").lower() else 0
 machine=1 if r.get("machine")=="60W" else 0
 return {"length":length,"y":float(r["actual_time_seconds"]),"speed":speed,"orient":orient,"machine":machine,"id":r["record_id"]}

def features(p,model):
 L=p["length"]/100.0; S=p["speed"]; O=p["orient"]; M=p["machine"]
 if model=="common":return [1,L]
 if model=="structured":
  # Baseline and first-order condition effects, plus length interactions.
  # All interactions are explicit; no higher-order interactions.
  return [1,L,S,O,M,S*L,O*L,M*L,S*O,S*M,O*M,S*O*L,S*M*L,O*M*L]
 if model=="group":
  # eight cell intercepts and eight cell slopes, encoded through condition
  # binary basis and all pairwise/high-order interactions.
  cells=[]
  for s in (0,1):
   for o in (0,1):
    for m in (0,1):
     cells.append((s,o,m))
  c=(S,O,M);return [int(c==cell) for cell in cells]+[L*int(c==cell) for cell in cells]
 raise ValueError(model)

def solve(A,b):
 # Normal equations and pivoted Gauss-Jordan; intentionally simple diagnostic.
 n=len(A[0]); ata=[[sum(row[i]*row[j] for row in A) for j in range(n)] for i in range(n)]
 atb=[sum(row[i]*v for row,v in zip(A,b)) for i in range(n)]
 for i in range(n):
  pivot=max(range(i,n),key=lambda r:abs(ata[r][i]))
  if abs(ata[pivot][i])<1e-12:raise ValueError("singular model matrix")
  ata[i],ata[pivot]=ata[pivot],ata[i];atb[i],atb[pivot]=atb[pivot],atb[i]
  d=ata[i][i];ata[i]=[x/d for x in ata[i]];atb[i]/=d
  for r in range(n):
   if r==i:continue
   factor=ata[r][i]
   ata[r]=[x-factor*y for x,y in zip(ata[r],ata[i])]
   atb[r]-=factor*atb[i]
 return atb

def metrics(errors):
 return (sum(abs(e) for e in errors)/len(errors),(sum(e*e for e in errors)/len(errors))**.5)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--data",type=Path,default=DATA);args=ap.parse_args()
 with args.data.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
 ps=[p for r in rows if r.get("measurement_type","").lower().startswith("filled") and (p:=parse(r))]
 sizes=sorted(set(p["length"] for p in ps))
 print(f"Cross-condition diagnostic: {len(ps)} fill observations; held-out sizes={sizes}")
 print("Each validation fold holds out all observations at one length level.")
 for model in ("common","structured","group"):
  errors=[];folds=[]
  for size in sizes:
   train=[p for p in ps if p["length"]!=size];test=[p for p in ps if p["length"]==size]
   A=[features(p,model) for p in train];b=[p["y"] for p in train]
   try:coef=solve(A,b)
   except ValueError as e:print(f"{model}: skipped fold {size}: {e}");continue
   folderr=[sum(x*c for x,c in zip(features(p,model),coef))-p["y"] for p in test]
   errors.extend(folderr);folds.append((size,folderr))
  if errors:
   mae,rmse=metrics(errors)
   print(f"\n{model}: overall MAE={mae:.2f}s RMSE={rmse:.2f}s, n={len(errors)}")
   for size,err in folds:
    ma,rm=metrics(err);print(f"  held-out {size:g}mm: MAE={ma:.2f}s RMSE={rm:.2f}s")
 print("\nCaution: only three size levels; factor coding and model forms are exploratory.")

if __name__=="__main__":main()
