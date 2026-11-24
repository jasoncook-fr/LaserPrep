#!/usr/bin/env python3
"""Residual-pattern diagnostic using saved size-held-out predictions."""
import csv
from pathlib import Path
DATA=Path(__file__).resolve().parent/"fill_main_length_stability.csv"
def main():
 with DATA.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
 if not rows: print("No prediction records found.");return
 # Join condition metadata from master
 master=Path(__file__).resolve().parent/"controlled_tests_master.csv"
 with master.open(newline="",encoding="utf-8-sig") as f: source=list(csv.DictReader(f))
 lookup={r.get("record_id",""):r for r in source}
 groups={}
 for p in rows:
  r=lookup.get(p["record_id"],{})
  machine=r.get("machine","?")
  speed="50%" if "50%" in r.get("test_group","") else "100%"
  orient=r.get("optimization","?")
  key=(machine,speed,orient)
  groups.setdefault(key,[]).append(p)
 print("Residual patterns by machine / speed / scan orientation")
 print("Residual = predicted - actual; positive means overprediction.")
 for key,ps in sorted(groups.items()):
  ps=sorted(ps,key=lambda x:float(x["held_out_size_mm"]))
  errors=[float(p["error_seconds"]) for p in ps]
  mae=sum(abs(e) for e in errors)/len(errors)
  print(f"\n{key[0]:>4} | {key[1]:>3} | {key[2]}")
  for p in ps: print(f"  {float(p['held_out_size_mm']):>5.0f}mm: actual={float(p['actual_seconds']):>7.2f}s pred={float(p['predicted_seconds']):>7.2f}s residual={float(p['error_seconds']):+7.2f}s")
  print(f"  Condition MAE across sizes: {mae:.2f}s")
 print("\nOverall residual vs size:")
 for size in sorted({float(p["held_out_size_mm"]) for p in rows}):
  es=[float(p["error_seconds"]) for p in rows if float(p["held_out_size_mm"])==size]
  print(f"  {size:>5.0f}mm: mean={sum(es)/len(es):+.3f}s MAE={sum(abs(e) for e in es)/len(es):.3f}s")
 print("\nThese are diagnostics of the same small experiment, not independent validation.")
if __name__=="__main__":main()
