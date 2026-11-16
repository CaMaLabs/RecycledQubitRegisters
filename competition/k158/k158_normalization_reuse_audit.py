#!/usr/bin/env python3
"""K158 read-only Helios normalization-reuse evidence audit.
No assumed exponent register. It emits candidate neighborhoods, never claims a rewrite.
"""
import argparse,collections,hashlib,json,re
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
Q=re.compile(r"^q(\d+)$")
MEASURE={"HMR","M","MEASURE","R","RESET"}
def qlist(tokens):
 result=[]
 for t in tokens[1:]:
  m=Q.fullmatch(t)
  if m:result.append(int(m[1]))
 return result
def target_indices(op,qs):
 if op in ("X","Z","H","S","T","T_DAG","Z_POW","R","HMR","RESET") and qs:return (qs[0],)
 if op in ("CX","CZ") and len(qs)>=2:return (qs[-1],) if op=="CX" else ()
 if op in ("CCX","CCZ") and len(qs)>=3:return (qs[-1],) if op=="CCX" else ()
 if op=="CSWAP" and len(qs)>=3:return tuple(qs[-2:])
 if op=="SWAP" and len(qs)>=2:return tuple(qs[-2:])
 return ()
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--out",type=Path,default=Path("competition/k158/results/normalization_audit.json"))
 p.add_argument("--window",type=int,default=128)
 p.add_argument("--top",type=int,default=24)
 p.add_argument("--context",type=int,default=16)
 a=p.parse_args()
 if not 32<=a.window<=2048 or not 1<=a.top<=100 or not 2<=a.context<=100:p.error("invalid bounds")
 raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
 lines=raw.decode().splitlines()
 records=[];writes=collections.Counter();reads=collections.Counter()
 for i,line in enumerate(lines):
  t=line.strip().split()
  if not t or t[0].startswith(("#","//")):continue
  op=t[0].upper();qs=qlist(t);targets=target_indices(op,qs)
  guarded=("if" in [w.lower() for w in t]) or op in ("PUSH_CONDITION","POP_CONDITION")
  for q in targets:writes[q]+=1
  for q in qs:reads[q]+=1
  records.append({"line":i+1,"op":op,"qs":qs,"targets":targets,"guarded":guarded,
                  "text":line.strip()})
 # Identify locations where input register and derived values are manipulated.
 # Merely seeing q0..21 is not evidence for normalization; never label the cone as such.
 chunks=[]
 for start in range(0,len(lines),a.window):
  rr=[r for r in records if start<r["line"]<=start+a.window]
  if not rr:continue
  c=collections.Counter(r["op"] for r in rr)
  input_reads=sum(sum(q<22 for q in r["qs"]) for r in rr)
  input_writes=sum(sum(q<22 for q in r["targets"]) for r in rr)
  nonlinear=sum(c[g] for g in ("CCX","CCZ","CSWAP"))
  hmr=c["HMR"]
  if input_reads<4 or nonlinear<2:continue
  chunks.append({"start":start+1,"end":min(len(lines),start+a.window),
       "input_touches":input_reads,"input_writes":input_writes,
       "CCX":c["CCX"],"CCZ":c["CCZ"],"CSWAP":c["CSWAP"],
       "HMR":hmr,"conditionally_scoped":sum(r["guarded"] for r in rr)})
 chunks.sort(key=lambda d:(-d["input_touches"],-d["CCX"],d["start"]))
 top=chunks[:a.top]
 contexts=[]
 for c in top:
  midpoint=(c["start"]+c["end"])//2
  subset=[r["text"] for r in records if midpoint-a.context<=r["line"]<=midpoint+a.context]
  contexts.append({"window":[c["start"],c["end"]],"excerpt_center":midpoint,
                   "lines":subset})
 result={"status":"READ_ONLY_SOURCE_LOCALITY_NOT_NORMALIZATION_PROOF",
    "baseline_sha256":sha,"source_lines":len(lines),
    "top_input_touched_windows":top,
    "excerpts":contexts,
    "input_q0_q21_writes":{str(q):writes[q] for q in range(22)},
    "input_q0_q21_touches":{str(q):reads[q] for q in range(22)},
    "scorable_counts":dict(collections.Counter(r["op"] for r in records if r["op"] in ("CCX","CCZ","CSWAP","Z_POW"))),
    "limitations":["No known exponent register, normalized mantissa or liveness markers in raw KMX source.",
     "Input touches and repeated gates do NOT establish duplicate normalization.",
     "No actual shared exponent computation or scored rewrite found by this structural audit.",
     "Requires manual interpretation of source excerpts and register provenance before hypothesis.",
     "No KMX modification, official verifier, or score win."]}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(result,indent=2)+"\n")
 print("K158_SUMMARY",json.dumps({"windows":len(chunks),"reported":len(top),
         "source_lines":len(lines),"out":str(a.out),
         "status":result["status"]}),flush=True)
 for c in top[:8]:print("K158_REGION",json.dumps(c),flush=True)
 print("K158_NEXT","Share the report or excerpts; we will identify any actual repeated exponent/mantissa computations before writing a rewrite.",flush=True)
if __name__=="__main__":main()
