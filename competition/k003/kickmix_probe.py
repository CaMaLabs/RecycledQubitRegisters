#!/usr/bin/env python3
"""K003: inspect kickmix ABI, the small invsqrt sample, and official CLI help.

This never mutates official samples, executes a verifier test, loads the
large DQI sample, or submits anything. All output is metadata.
"""
import argparse,hashlib,importlib,inspect,json,os,subprocess,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OFFICIAL=(ROOT/"../k001/private/official").resolve()
SAMPLE=OFFICIAL/"sample_submission/invsqrt.kmb"
VERIFIER=OFFICIAL/"verifiers/invsqrt/verify_submission_invsqrt.py"
REPORT=ROOT/"k003_kickmix_probe.json"
def safe(obj):
 try:return str(obj)[:700]
 except Exception:return "<unprintable>"
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--report",default=str(REPORT))
 a=p.parse_args()
 d={"experiment":"K003_KICKMIX_SMALL_SAMPLE_READ_ONLY_ABI_PROBE","status":"IN_PROGRESS",
    "sample_circuit_modified":False,"competition_submission_attempted":False,
    "dqi_886mb_loaded":False,"python":sys.version.split()[0]}
 out=Path(a.report);out.parent.mkdir(parents=True,exist_ok=True)
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  # Installed PyPI package takes precedence. Otherwise official Kaggle
  # extension may not load under host CPython ABI; record that cleanly.
  try:
   import kickmix as km
  except Exception as first:
   d["initial_import_error"]=f"{type(first).__name__}: {first}"
   sys.path.insert(0,str(OFFICIAL/"kickmix"))
   try:km=importlib.import_module("kickmix")
   except Exception as second:
    d["official_extension_import_error"]=f"{type(second).__name__}: {second}"
    d["status"]="NEEDS_COMPATIBLE_KICKMIX_PYTHON_ABI"
    save();print("K003 STATUS",d["status"]);print("K003 IMPORTS",d.get("initial_import_error"),d.get("official_extension_import_error"));return
  d["kickmix_location"]=safe(getattr(km,"__file__",None))
  d["kickmix_public_symbols"]=[s for s in dir(km) if not s.startswith("_")][:160]
  d["circuit_methods"]=[s for s in dir(km.Circuit) if not s.startswith("_")][:160]
  d["builder_methods"]=[s for s in dir(km.CircuitBuilder) if not s.startswith("_")][:200]
  if not SAMPLE.is_file():raise FileNotFoundError(SAMPLE)
  with SAMPLE.open("rb") as f:d["sample_sha256"]=hashlib.file_digest(f,"sha256").hexdigest()
  d["sample_bytes"]=SAMPLE.stat().st_size
  circuit=km.Circuit.from_file(str(SAMPLE))
  d["sample_operation_statistics"]=safe(circuit.operation_statistics())
  d["sample_reaction_depth"]=safe(circuit.reaction_depth())
  d["circuit_public_attributes"]={}
  for attr in ("registers","num_qubits","num_bits","operations","instructions","register_names","register_sizes","text_diagram"):
   if not hasattr(circuit,attr):continue
   item=getattr(circuit,attr)
   if callable(item):
    d["circuit_public_attributes"][attr]={"callable":True}
   else:
    try:
     ln=len(item)
    except Exception:ln=None
    d["circuit_public_attributes"][attr]={"type":type(item).__name__,"length":ln,"preview":safe(item)[:200]}
  d["status"]="PASS_KICKMIX_SMALL_SAMPLE_READ_ONLY_INSPECTION"
  save()
  print("K003 STATUS",d["status"])
  print("K003 KICKMIX",d["kickmix_location"])
  print("K003 STATS",d["sample_operation_statistics"])
  print("K003 REACTION_DEPTH",d["sample_reaction_depth"])
  print("K003 CIRCUIT_METHODS",d["circuit_methods"])
  print("K003 BUILDER_METHODS",d["builder_methods"])
  print("K003 ATTRIBUTES",d["circuit_public_attributes"])
  print("K003 REPORT",out)
 except Exception:
  d["status"]="ERROR";d["error"]=traceback.format_exc()[-5000:]
  save();raise
if __name__=="__main__":main()
