#!/usr/bin/env python3
"""LOO exploratory model comparison for the controlled rectangular-fill data.

Compares simple proportional (time = rate * length) and affine
(time = overhead + rate * length) models, using leave-one-size-out prediction
within each machine/speed/orientation group. This is a diagnostic, not a
production estimator; groups contain only three observed sizes.
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
    return {"machine":row["machine"],"speed":speed,"orientation":row.get("optimization","").strip(),"length":max(a,b),"time":float(row["actual_time_seconds"]),"id":row["record_id"]}

def fit_line(points, through_origin=False):
    xs=[x for x,y in points];ys=[y for x,y in points]
    if through_origin:
        den=sum(x*x for x in xs)
        return 0.0, sum(x*y for x,y in points)/den if den else 0.0
    xm=sum(xs)/len(xs);ym=sum(ys)/len(ys)
    den=sum((x-xm)**2 for x in xs)
    slope=sum((x-xm)*(y-ym) for x,y in points)/den if den else 0.0
    return ym-slope*xm,slope

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--data",type=Path,default=DATA);args=ap.parse_args()
    with args.data.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
    parsed=[p for r in rows if r.get("measurement_type","").lower().startswith("filled") and (p:=parse(r))]
    groups=defaultdict(list)
    for p in parsed:groups[(p["machine"],p["speed"],p["orientation"])].append(p)
    print(f"Fill model diagnostic: {len(parsed)} observations, {len(groups)} groups")
    print("LOO predicts each held-out size using the other two sizes within its group.")
    print("No coefficient pooling, extrapolation or production use is implied.")
    for key,g in sorted(groups.items()):
        g=sorted(g,key=lambda p:p["length"])
        if len(g)<3:continue
        errors_origin=[];errors_affine=[]
        for held in g:
            train=[(p["length"],p["time"]) for p in g if p["id"]!=held["id"]]
            intercept,slope=fit_line(train,False);pred_aff=intercept+slope*held["length"]
            _,rate=fit_line(train,True);pred_origin=rate*held["length"]
            errors_affine.append(pred_aff-held["time"]);errors_origin.append(pred_origin-held["time"])
        def metrics(err):
            return sum(abs(e) for e in err)/len(err), (sum(e*e for e in err)/len(err))**0.5
        mae_o,rmse_o=metrics(errors_origin);mae_a,rmse_a=metrics(errors_affine)
        print(f"{key[0]} | {key[1]} | {key[2]} | sizes={','.join(str(int(p['length'])) for p in g)}")
        print(f"  proportional: MAE={mae_o:.1f}s RMSE={rmse_o:.1f}s; affine: MAE={mae_a:.1f}s RMSE={rmse_a:.1f}s")
        print("  affine held-out errors: "+", ".join(f"{int(p['length'])}mm {e:+.1f}s" for p,e in zip(g,errors_affine)))
    print("\nCaution: only three sizes per condition; LOO is highly unstable and is used solely to compare model shapes.")

if __name__=="__main__":main()
