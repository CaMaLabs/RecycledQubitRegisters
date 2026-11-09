#!/usr/bin/env python3
"""K063: safely cancel pairs of unconditional involutory quantum gates.

Candidates: CCX, CCZ and CSWAP. A pair G...G cancels when all intervening
operations act on disjoint qubits. Strictly restrict to unconditional unitary
gates, with a boundary at every measurement, classical operation, condition
scope, metadata annotation, or unknown opcode. Gate operands and order are
preserved; CZ/CCZ controls may be permuted without affecting semantics, while
CCX and CSWAP are kept in exact original order.

Measures deltas against the original public invsqrt.kmb and verifies both
full-domain seeds if --full is requested. Benchmark only; third-party
source remains third-party work.
"""
from __future__ import annotations
import argparse,collections,hashlib,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"competition/k001/private/official/verifiers"))
QRE=re.compile(r"\bq(\d+)\b")
OPS={"CCX","CCZ","CSWAP"}
SAFE={"X","Y","Z","H","S","S_DAG","T","T_DAG","CX","CZ","SWAP",
      "CCX","CCZ","CSWAP","Z_POW"}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(line):
 text=line.strip()
 if not text or text.startswith(("#","//")):return None
 op=text.split()[0].upper()
 if op not in SAFE or " if " in text:return None
 qs=tuple(int(n) for n in QRE.findall(text))
 if not qs:return None
 # Prevent parsing any unknown operand syntax.
 if op in ("CCX","CCZ","CSWAP") and len(qs)!=3:return None
 if op in ("CX","CZ","SWAP") and len(qs)!=2:return None
 if op in ("X","Y","Z","H","S","S_DAG","T","T_DAG","Z_POW") and len(qs)!=1:return None
 return op,qs
def signature(op,qs):
 if op=="CCZ":return op,tuple(sorted(qs))
 return op,qs
def optimize(lines):
 # Search backward through disjoint quantum gates only. Work to fixed point.
 total=collections.Counter()
 iterations=0
 while True:
  iterations+=1
  parsed=[decode(s) for s in lines]
  removed=set()
  stats=collections.Counter()
  for i in range(len(lines)):
   if i in removed:continue
   item=parsed[i]
   if item is None or item[0] not in OPS:continue
   op,qs=item
   footprint=set(qs)
   sig=signature(op,qs)
   for j in range(i-1,-1,-1):
    if j in removed:continue
    other=parsed[j]
    if other is None:break
    if other[0]==op and signature(*other)==sig:
     removed.add(j);removed.add(i)
     stats[op]+=2
     break
    if footprint.intersection(other[1]):break
  if not removed:break
  total.update(stats)
  lines=[s for idx,s in enumerate(lines) if idx not in removed]
  if iterations>=20:break
 return lines,dict(total),iterations
def verify(p,full,timeout):
 spec=importlib.util.spec_from_file_location("k031_k063",ROOT/"competition/k031/k031_full_domain_repair.py")
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 runs={}
 for label,n,seed in [("prefix",64,12345)]+(
    [("full_12345",m.FULL_X,12345),("full_23456",m.FULL_X,23456)] if full else []):
  runs[label]=m.verify(p,n,seed,timeout)
  if runs[label].get("status")!="PASS" or runs[label].get("exit_code")!=0:break
 return runs
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--source",type=Path,default=ROOT/"competition/k059/results/helios_public.kmx")
 p.add_argument("--out",type=Path,default=ROOT/"competition/k063/results")
 p.add_argument("--full",action="store_true")
 p.add_argument("--timeout",type=int,default=600)
 args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
 original=args.source.read_text().splitlines()
 candidate,counts,iterations=optimize(original)
 report={"source":str(args.source),"source_sha256":sha(args.source),
         "removed":counts,"iterations":iterations,
         "instructions_before":len(original),"instructions_after":len(candidate),
         "attribution":"Third-party Helios public benchmark; not CaMaLabs original circuit"}
 print("K063_SCAN",json.dumps(report,sort_keys=True),flush=True)
 if counts:
  target=args.out/"candidate.kmx"
  target.write_text("\n".join(candidate)+"\n")
  try:
   import kickmix as km
   circ=km.Circuit.from_file(str(target),format="kmx")
   out=args.out/"candidate.kmb"
   circ.to_file(str(out),format="kmb")
   report["candidate_sha256"]=sha(out)
   report["qubits"]=circ.num_qubits
   report["verification"]=verify(out,args.full,args.timeout)
   report["status"]="PASS" if all(
      r.get("status")=="PASS" and r.get("exit_code")==0
      for r in report["verification"].values()) else "FAIL"
  except Exception as ex:
   report["status"]="ERROR";report["error"]=repr(ex)
 else:report["status"]="NO_CANCELLATIONS"
 print("K063_RESULT",json.dumps({"status":report["status"],"removed":counts,
   "qubits":report.get("qubits"),"verification":report.get("verification"),
   "error":report.get("error")},sort_keys=True),flush=True)
 (args.out/"result.json").write_text(json.dumps(report,indent=2,default=str))
 print("SAVED",args.out/"result.json",flush=True)
if __name__=="__main__":main()
