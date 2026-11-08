#!/usr/bin/env python3
"""K005: inspect kickmix text interchange via an unmodified small reference.

Operate ONLY on a private copy of the official invsqrt sample. Try exporting
the reference to .kmx, inspect bounded structural metadata and re-import
for exact operation-statistics/reaction-depth equality. Never assume
a correct circuit or better score merely from round-trip success.

No optimizer transformations, official scoring claim or Kaggle submission.
"""
import argparse,collections,hashlib,inspect,json,re,sys,traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PRIVATE=(ROOT/"../k001/private").resolve()
SAMPLE=PRIVATE/"official/sample_submission/invsqrt.kmb"
OUTPUT_DIR=PRIVATE/"runs/k005"
REPORT=ROOT/"k005_kickmix_interchange_report.json"

def signature(fn):
 try:return str(inspect.signature(fn))
 except Exception:return "<native binding; signature unavailable>"
def stat_summary(circuit):
 stats=circuit.operation_statistics()
 return {"num_instructions":int(stats.num_instructions),
   "num_toffoli_like":int(stats.num_toffoli_like),
   "num_t_like":int(stats.num_t_like),
   "num_qubits":int(circuit.num_qubits),
   "num_bits":int(circuit.num_bits),
   "reaction_depth":int(circuit.reaction_depth())}
def filehash(path):
 with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--report",default=str(REPORT))
 p.add_argument("--no-convert",action="store_true")
 a=p.parse_args()
 out=Path(a.report);out.parent.mkdir(parents=True,exist_ok=True)
 OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
 if not SAMPLE.is_file():p.error("K001 official reference missing")
 import kickmix as km
 d={"experiment":"K005_KICKMIX_SMALL_REFERENCE_INTERCHANGE","status":"IN_PROGRESS",
   "sample_modified":False,"candidate_optimized":False,
   "kaggle_submission_attempted":False,"source_redistributed":False,
   "kickmix_location":str(getattr(km,"__file__",None)),
   "api":{"to_file":signature(km.Circuit.to_file),
     "from_file":signature(km.Circuit.from_file),
     "text_diagram":signature(km.Circuit.text_diagram),
     "register_data":signature(km.Circuit.register_data)}}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  baseline_sha=filehash(SAMPLE)
  c=km.Circuit.from_file(str(SAMPLE))
  d["reference"]={"sha256":baseline_sha,"stats":stat_summary(c)}
  d["api"]["docstrings"]={key:(inspect.getdoc(getattr(km.Circuit,key)) or "")[:1200]
    for key in ("to_file","from_file","text_diagram","register_data")}
  print("K005 REFERENCE",d["reference"],flush=True)
  for key in ("to_file","from_file","text_diagram","register_data"):
   print("K005 API",key,d["api"][key],d["api"]["docstrings"][key][:350],flush=True)
  try:
   registers=c.register_data()
   d["register_data_type"]=type(registers).__name__
   d["register_data_preview"]=str(registers)[:1600]
  except Exception as exc:d["register_data_error"]=f"{type(exc).__name__}: {exc}"
  if not a.no_convert:
   export=OUTPUT_DIR/"reference_roundtrip.kmx"
   try:
    c.to_file(str(export))
    d["kmx_export"]={"bytes":export.stat().st_size,"sha256":filehash(export)}
    # Only display bounded descriptions and record-like operation tokens;
    # don't publish full official serialized source.
    with export.open("rb") as f:head=f.read(16384)
    d["kmx_export"]["first_bytes_hex"]=head[:48].hex()
    d["kmx_export"]["utf8_decodable"]=True
    try:text=head.decode("utf-8")
    except UnicodeDecodeError:
     d["kmx_export"]["utf8_decodable"]=False
     text=head.decode("utf-8",errors="replace")
    d["kmx_export"]["first_lines_truncated"]=[x[:180] for x in text.splitlines()[:24]]
    d["kmx_export"]["nonempty_line_count_in_first16kb"]=sum(bool(x.strip()) for x in text.splitlines())
    roundtrip=km.Circuit.from_file(str(export))
    d["kmx_roundtrip"]={"stats":stat_summary(roundtrip),
      "exact_stat_and_depth_match":stat_summary(roundtrip)==d["reference"]["stats"]}
    d["status"]="PASS_KICKMIX_INTERCHANGE_INSPECTION" if d["kmx_roundtrip"]["exact_stat_and_depth_match"] else "FAIL_KICKMIX_INTERCHANGE_STATS_DIFFER"
    print("K005 KMx",d["kmx_export"]["bytes"],"bytes",
      "text",d["kmx_export"]["utf8_decodable"],flush=True)
    print("K005 HEAD",d["kmx_export"]["first_lines_truncated"][:12],flush=True)
    print("K005 ROUNDTRIP",d["kmx_roundtrip"],flush=True)
   except Exception as exc:
    d["kmx_export_error"]=f"{type(exc).__name__}: {exc}"
    d["status"]="KICKMIX_EXPORT_API_NEEDS_ADAPTATION"
    print("K005 EXPORT ISSUE",d["kmx_export_error"],flush=True)
  else:d["status"]="PASS_KICKMIX_SIGNATURE_INSPECTION_ONLY"
  if filehash(SAMPLE)!=baseline_sha:raise AssertionError("Official sample changed unexpectedly")
  save();print("K005 STATUS",d["status"],"REPORT",out,flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-5000:]
  save();raise
if __name__=="__main__":main()
