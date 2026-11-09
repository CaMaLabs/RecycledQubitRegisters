#!/usr/bin/env python3
"""K066: verified low-angle ablations in public Helios invsqrt phase ladder.

Scientific probe, NOT an original circuit: source heliosli/qcc-circuits-live
invsqrt.kmb. Remove selected Z_POW operations from the distinct q28 binary
phase ladder near KMX lines 25762..25955. Every accepted result must pass
the official full-domain verifier on TWO seeds. No approximation claims from
bounded tests alone. Does not edit source reference or submit outputs.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"competition/k001/private/official/verifiers"))
Z=re.compile(r"^Z_POW\s+q28\s+([^\s]+)$",re.I)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(path,n,seed,timeout):
 file=ROOT/"competition/k031/k031_full_domain_repair.py"
 spec=importlib.util.spec_from_file_location("k031_k066",file)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 return m.verify(path,n,seed,timeout)
def full_n():
 file=ROOT/"competition/k031/k031_full_domain_repair.py"
 spec=importlib.util.spec_from_file_location("k031_full_k066",file)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 return m.FULL_X
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--source",type=Path,default=ROOT/"competition/k059/results/helios_public.kmx")
 p.add_argument("--out",type=Path,default=ROOT/"competition/k066/results")
 p.add_argument("--timeout",type=int,default=600)
 p.add_argument("--full",action="store_true",help="Verify entire domain on two seeds for each candidate")
 p.add_argument("--max-cumulative",type=int,default=5)
 p.add_argument("--single-count",type=int,default=5)
 args=p.parse_args()
 args.out.mkdir(parents=True,exist_ok=True)
 if not args.source.is_file():raise SystemExit("Missing decoded KMX: "+str(args.source))
 lines=args.source.read_text().splitlines(keepends=True)
 # No dependence on brittle absolute line addresses: match 26-phase q28
 # ladder by contiguous phase events separated by <=24 instructions.
 entries=[]
 for i,s in enumerate(lines):
  m=Z.fullmatch(s.strip())
  if m:
   try:a=float(m.group(1))
   except ValueError:continue
   entries.append((i,a))
 clusters=[];cur=[]
 for item in entries:
  if cur and item[0]-cur[-1][0]>24:
   clusters.append(cur);cur=[]
  cur.append(item)
 if cur:clusters.append(cur)
 matches=[c for c in clusters if len(c)>=20 and
          all(c[i+1][1]>c[i][1] for i in range(len(c)-1)) and
          c[0][1]<1e-9]
 if len(matches)!=1:
  raise SystemExit("Expected precisely one low-angle monotone q28 phase ladder, found "+str(len(matches)))
 ladder=matches[0]
 print("K066_LADDER",json.dumps({"count":len(ladder),
   "range":[ladder[0][0]+1,ladder[-1][0]+1],
   "first_angles":[x[1] for x in ladder[:min(10,len(ladder))]],
   "source_sha256":sha(args.source)}),flush=True)
 import kickmix as km
 baseline_score=95369.00696815242
 candidates=[]
 for k in range(1,min(args.max_cumulative,len(ladder))+1):
  candidates.append(("drop_first_"+str(k),tuple(range(k))))
 for k in range(1,min(args.single_count,len(ladder))):
  candidates.append(("drop_only_"+str(k+1),(k,)))
 full=full_n() if args.full else 64
 outputs=[]
 for name,subset in candidates:
  drop={ladder[i][0] for i in subset}
  txt=args.out/(name+".kmx")
  txt.write_text("".join(s for i,s in enumerate(lines) if i not in drop))
  record={"name":name,"removed_rotations":len(drop),
          "removed_angles":[ladder[i][1] for i in subset]}
  try:
   circ=km.Circuit.from_file(str(txt),format="kmx")
   binary=args.out/(name+".kmb")
   circ.to_file(str(binary),format="kmb")
   record["sha256"]=sha(binary)
   record["num_qubits"]=circ.num_qubits
   checks={}
   checks["prefix"]=verify(binary,64,12345,args.timeout)
   if checks["prefix"].get("status")=="PASS" and checks["prefix"].get("exit_code")==0 and args.full:
    checks["full_seed_12345"]=verify(binary,full,12345,args.timeout)
    if checks["full_seed_12345"].get("status")=="PASS" and checks["full_seed_12345"].get("exit_code")==0:
     checks["full_seed_23456"]=verify(binary,full,23456,args.timeout)
   record["verification"]=checks
   all_good=all(x.get("status")=="PASS" and x.get("exit_code")==0 for x in checks.values())
   full_good=all_good and all(key in checks for key in ("full_seed_12345","full_seed_23456"))
   record["status"]="PASS_FULL" if full_good else "PASS_PREFIX_ONLY" if all_good else "FAIL"
   if full_good:
    record["full_score"]=checks["full_seed_12345"].get("score")
    record["score_change"]=record["full_score"]-baseline_score
  except Exception as e:
   record["status"]="ERROR";record["error"]=repr(e)
  outputs.append(record)
  print("K066_CANDIDATE",json.dumps({"name":name,"removed_rotations":len(drop),
   "status":record["status"],"full_score":record.get("full_score"),
   "score_change":record.get("score_change"),
   "prefix_worst_ratio":record.get("verification",{}).get("prefix",{}).get("worst_error_over_tolerance"),
   "full_worst_ratio":record.get("verification",{}).get("full_seed_12345",{}).get("worst_error_over_tolerance"),
   "error":record.get("error")},sort_keys=True),flush=True)
 (args.out/"ablation.json").write_text(json.dumps({
   "source":str(args.source),"source_sha256":sha(args.source),
   "attribution":"Third-party Helios public circuit; numerical ablation experiment",
   "baseline_full_score_seed_12345":baseline_score,
   "full_domain_checked":bool(args.full),
   "ladder":[{"line":i+1,"angle":x} for i,x in ladder],
   "results":outputs},indent=2))
 print("K066_RESULT",json.dumps({"total":len(outputs),
  "passes_full":sum(x["status"]=="PASS_FULL" for x in outputs),
  "best_pass":min(({"name":x["name"],"score":x["full_score"]}
    for x in outputs if x["status"]=="PASS_FULL"),key=lambda z:z["score"],default=None)},
  sort_keys=True),flush=True)
 print("SAVED",args.out/"ablation.json",flush=True)
if __name__=="__main__":main()
