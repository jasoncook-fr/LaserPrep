#!/usr/bin/env python3
"""Diagnostics for the experimental pooled fill-time model.

Writes observation-level full-fit residuals and leave-one-size-level-out
predictions, plus fold coefficient summaries. These are diagnostics only:
no production coefficients are exported or applied.
"""
from __future__ import annotations
import argparse, csv, re
from pathlib import Path

DATA = Path(__file__).resolve().parent / "controlled_tests_master.csv"
FEATURE_NAMES = ["intercept", "length_100mm", "speed50", "orientation_lr", "machine60",
                 "speed50_x_length", "orientation_x_length", "machine_x_length",
                 "speed_x_orientation", "speed_x_machine", "orientation_x_machine",
                 "speed_x_orientation_x_length", "speed_x_machine_x_length",
                 "orientation_x_machine_x_length"]

def parse(row):
    m = re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm", row.get("geometry",""), re.I)
    if not m: return None
    a,b=map(float,m.groups())
    return {"id":row.get("record_id",""), "length":max(a,b),
            "y":float(row["actual_time_seconds"]),
            "speed":int("50%" in row.get("test_group","")),
            "orient":int("left-to-right" in row.get("optimization","").lower()),
            "machine":int(row.get("machine")=="60W"),
            "machine_label":row.get("machine",""), "speed_label":"50%" if "50%" in row.get("test_group","") else "100%",
            "orientation":row.get("optimization","")}

def features(p):
    L=p["length"]/100.0; S=p["speed"]; O=p["orient"]; M=p["machine"]
    return [1,L,S,O,M,S*L,O*L,M*L,S*O,S*M,O*M,S*O*L,S*M*L,O*M*L]

def solve(A,b):
    n=len(A[0]); ata=[[sum(row[i]*row[j] for row in A) for j in range(n)] for i in range(n)]
    atb=[sum(row[i]*v for row,v in zip(A,b)) for i in range(n)]
    for i in range(n):
        pivot=max(range(i,n),key=lambda r:abs(ata[r][i]))
        if abs(ata[pivot][i])<1e-12: raise ValueError("singular model matrix")
        ata[i],ata[pivot]=ata[pivot],ata[i];atb[i],atb[pivot]=atb[pivot],atb[i]
        d=ata[i][i];ata[i]=[x/d for x in ata[i]];atb[i]/=d
        for r in range(n):
            if r==i:continue
            f=ata[r][i];ata[r]=[x-f*y for x,y in zip(ata[r],ata[i])];atb[r]-=f*atb[i]
    return atb

def predict(p,c): return sum(x*v for x,v in zip(features(p),c))
def mae(vals): return sum(abs(x) for x in vals)/len(vals) if vals else float("nan")
def rmse(vals): return (sum(x*x for x in vals)/len(vals))**0.5 if vals else float("nan")

def write_csv(path, rows, fields):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data",type=Path,default=DATA)
    ap.add_argument("--output-dir",type=Path,default=DATA.parent)
    args=ap.parse_args()
    with args.data.open(newline="",encoding="utf-8-sig") as f: raw=list(csv.DictReader(f))
    ps=[p for r in raw if r.get("measurement_type","").lower().startswith("filled") and (p:=parse(r))]
    sizes=sorted(set(p["length"] for p in ps))
    if len(ps)<14: raise SystemExit("Expected the 24-observation fill dataset; found too few observations.")
    args.output_dir.mkdir(parents=True,exist_ok=True)

    full=solve([features(p) for p in ps],[p["y"] for p in ps])
    fullrows=[]
    for p in ps:
        pred=predict(p,full);err=pred-p["y"]
        fullrows.append({**p,"full_fit_prediction_s":round(pred,5),"full_fit_residual_s":round(err,5),
                         "absolute_error_s":round(abs(err),5),"absolute_error_pct":round(abs(err)/p["y"]*100,5)})
    foldrows=[];foldcoef=[]
    for size in sizes:
        train=[p for p in ps if p["length"]!=size];test=[p for p in ps if p["length"]==size]
        c=solve([features(p) for p in train],[p["y"] for p in train])
        for name,val in zip(FEATURE_NAMES,c): foldcoef.append({"held_out_size_mm":size,"coefficient":name,"value":val})
        for p in test:
            pred=predict(p,c);err=pred-p["y"]
            foldrows.append({"id":p["id"],"length_mm":p["length"],"machine":p["machine_label"],
                "speed":p["speed_label"],"orientation":p["orientation"],"actual_s":p["y"],
                "predicted_s":round(pred,5),"error_s":round(err,5),
                "absolute_error_s":round(abs(err),5),"absolute_error_pct":round(abs(err)/p["y"]*100,5),
                "held_out_size_mm":size})
    write_csv(args.output_dir/"fill_model_full_fit_residuals.csv",fullrows,
        ["id","length","machine_label","speed_label","orientation","y","full_fit_prediction_s","full_fit_residual_s","absolute_error_s","absolute_error_pct"])
    write_csv(args.output_dir/"fill_model_held_out_predictions.csv",foldrows,
        ["id","length_mm","machine","speed","orientation","actual_s","predicted_s","error_s","absolute_error_s","absolute_error_pct","held_out_size_mm"])
    write_csv(args.output_dir/"fill_model_fold_coefficients.csv",foldcoef,["held_out_size_mm","coefficient","value"])

    errors=[r["error_s"] for r in foldrows]
    print(f"Structured fill model diagnostic: {len(ps)} observations; size levels={sizes}")
    print(f"Size-held-out predictions: MAE={mae(errors):.3f}s RMSE={rmse(errors):.3f}s")
    print(f"Mean signed error (predicted - actual): {sum(errors)/len(errors):+.3f}s")
    print(f"Mean absolute percentage error: {mae([r['absolute_error_pct'] for r in foldrows]):.3f}%")
    print("\nHeld-out-size summary:")
    for size in sizes:
        subset=[r for r in foldrows if r["held_out_size_mm"]==size]
        es=[r["error_s"] for r in subset]
        print(f"  {size:g}mm: MAE={mae(es):.3f}s RMSE={rmse(es):.3f}s mean bias={sum(es)/len(es):+.3f}s")
    print("\nFull-fit residuals (descriptive, not validation):")
    fr=[r["full_fit_residual_s"] for r in fullrows]
    print(f"  MAE={mae(fr):.3f}s RMSE={rmse(fr):.3f}s")
    print("\nCondition breakdown of size-held-out predictions:")
    keys=sorted(set((r["machine"],r["speed"],r["orientation"]) for r in foldrows))
    for machine,speed,orient in keys:
        sub=[r for r in foldrows if (r["machine"],r["speed"],r["orientation"])==(machine,speed,orient)]
        es=[r["error_s"] for r in sub]
        print(f"  {machine}, {speed}, {orient}: n={len(es)} MAE={mae(es):.3f}s mean bias={sum(es)/len(es):+.3f}s")
    print("\nCSV reports written:")
    for n in ("fill_model_full_fit_residuals.csv","fill_model_held_out_predictions.csv","fill_model_fold_coefficients.csv"):
        print(f"  {args.output_dir/n}")
    print("\nWarning: 3 size levels only; these diagnostics are exploratory and not production validation.")

if __name__=="__main__": main()
