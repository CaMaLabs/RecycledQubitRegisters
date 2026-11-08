#!/usr/bin/env python3
"""K019: probe the official deterministic inverse-square-root precision model.

Read-only. Exercise the official reference's fixed_point_model and
relative_error with small numpy batches for K016 candidates 7,10,13,21
and baseline. The model is a screening aid, not the official circuit
verifier; a model result cannot certify measurement or phase semantics.
"""
import dataclasses,importlib,inspect,json,sys,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent
PRIVATE=(HERE/"../k001/private").resolve()
VERIFIERS=PRIVATE/"official/verifiers"
K016=HERE.parent/"k016/k016_precision_search.json"
OUT=HERE/"k019_model_probe.json"
def summarize(value):
 try:
  import numpy as np
  a=np.asarray(value)
  if a.dtype.kind in "biufc" and a.size:
   return {"type":type(value).__name__,"shape":list(a.shape),
           "dtype":str(a.dtype),
           "sample":a.flat[:min(a.size,12)].tolist(),
           "min":float(np.min(a)) if a.dtype.kind in "biuf" else None,
           "max":float(np.max(a)) if a.dtype.kind in "biuf" else None}
 except Exception:pass
 if isinstance(value,dict):return {"type":"dict","keys":list(map(str,value.keys()))[:30],
   "items_preview":str(value)[:800]}
 if isinstance(value,(tuple,list)):
  return {"type":type(value).__name__,"length":len(value),
    "elements":[summarize(x) for x in value[:5]]}
 return {"type":type(value).__name__,"repr":repr(value)[:1100]}
def main():
 import numpy as np
 if str(VERIFIERS) not in sys.path:sys.path.insert(0,str(VERIFIERS))
 module=importlib.import_module("invsqrt.nr_reference_circuit")
 baseline=module.Precision()
 if not K016.is_file():raise SystemExit("K016 report not found")
 trials={x["case"]:x for x in json.loads(K016.read_text())["trials"]}
 cases=[("baseline",{}),*[(str(n),trials[n]["changes"]) for n in (7,10,13,21)]]
 xs=np.array([1,2,3,4,8,16,32,64,128,256,512,1024,2048,4096,8192],dtype=np.int64)
 d={"status":"K019_DETERMINISTIC_MODEL_PROBE_COMPLETE",
   "sample_inputs":xs.tolist(),
   "functions":{},
   "cases":{},
   "submitted":False,"full_domain_certified":False,
   "limitations":["A deterministic fixed-point model is not a quantum circuit simulator",
                  "Official verifier acceptance uses additional phase/measurement and rotation-synthesis checks",
                  "No full-domain candidate acceptance is asserted"]}
 for function in ("fixed_point_model","relative_error"):
  f=getattr(module,function)
  d["functions"][function]={"signature":str(inspect.signature(f)),
       "docstring_excerpt":(inspect.getdoc(f) or "")[:650]}
 for name,changes in cases:
  prec=dataclasses.replace(baseline,**changes)
  row={"changes":changes,"probes":{}}
  for function in ("fixed_point_model","relative_error"):
   try:
    val=getattr(module,function)(10,prec,xs)
    row["probes"][function]={"ok":True,"summary":summarize(val)}
   except Exception as exc:
    row["probes"][function]={"ok":False,
      "error":f"{type(exc).__name__}: {exc}",
      "trace_tail":traceback.format_exc()[-800:]}
  d["cases"][name]=row
  print("K019 CASE",name,"PRECISION",changes,flush=True)
  for function, result in row["probes"].items():
   print("K019",function,"OK",result["ok"],
     "RESULT",result.get("summary",result.get("error")),flush=True)
 OUT.write_text(json.dumps(d,indent=2)+"\n")
 print("K019 STATUS",d["status"])
 print("K019 REPORT",OUT)
if __name__=="__main__":main()
