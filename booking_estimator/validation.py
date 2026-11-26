"""Validation metrics for predictions compared to actual runtime observations."""
import math
def evaluate_predictions(actual_seconds,predicted_seconds):
    if len(actual_seconds)!=len(predicted_seconds) or not actual_seconds: raise ValueError("equal, non-empty sequences required")
    pairs=list(zip(actual_seconds,predicted_seconds))
    if any(not math.isfinite(float(a)) or not math.isfinite(float(p)) or float(a)<=0 or float(p)<0 for a,p in pairs): raise ValueError("actual values must be positive and predictions non-negative and finite")
    errors=[float(p)-float(a) for a,p in pairs]; ae=[abs(x) for x in errors]; pct=[e/float(a)*100 for e,(a,p) in zip(errors,pairs)]
    actual=[float(a) for a,p in pairs]; mean=sum(actual)/len(actual); ss_tot=sum((a-mean)**2 for a in actual); ss_res=sum(e*e for e in errors)
    return {"validation_version":1,"sample_count":len(pairs),"mae_s":sum(ae)/len(ae),"mae_min":sum(ae)/len(ae)/60,
        "rmse_s":math.sqrt(ss_res/len(pairs)),"mean_error_s":sum(errors)/len(errors),
        "mean_absolute_percentage_error":sum(abs(x) for x in pct)/len(pct),
        "median_absolute_error_s":sorted(ae)[(len(ae)-1)//2],"r_squared":1-ss_res/ss_tot if ss_tot else None,
        "bias_direction":"overestimate" if sum(errors)>0 else "underestimate" if sum(errors)<0 else "neutral"}
