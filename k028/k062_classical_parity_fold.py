#!/usr/bin/env python3
"""K062: exact GF(2) parity folding of adjacent conditional diagonal phase gates.

SCOPE: consecutive unconditional/conditional Z and CZ only; no measurements,
bit writes, non-diagonal gates, condition push/pop, or any other operation
may be crossed. For each identical Pauli-Z/CZ target, conditions combine as
XOR. This is algebraically exact because Z^2=CZ^2=I and all gates commute.
The transformation is *independent* of the public circuit's numerical model.

Third-party public source is used solely as a benchmark; output is explicitly
marked an adaptation. Always confirm with the official full-domain verifier.
"""
from __future__ import annotations
import argparse, collections, hashlib, importlib.util, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"competition/k001/private/official/verifiers"))
PHASE=re.compile(r"^\s*(Z|CZ)\s+(q\d+)(?:\s+(q\d+))?(?:\s+if\s+b(\d+))?\s*$",re.I)
BIT=re.compile(r"\bb(\d+)\b")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def transform(lines):
 maxbit=max([int(v) for line in lines for v in BIT.findall(line)] or [-1])
 nextbit=maxbit+1
 stats=collections.Counter()
 out=[];i=0
 while i<len(lines):
  # Never reorder past any non-(Z/CZ) instruction, classical mutation,
  # control scope, gate of another basis, or tagged metadata.
  j=i;block=[]
  while j<len(lines):
   m=PHASE.fullmatch(lines[j].strip())
   if m is None:break
   typ,q1,q2,bit=m.groups()
   if typ.upper()=="CZ" and q2 is None:break
   if typ.upper()=="Z" and q2 is not None:break
   qs=tuple(sorted([q1,q2])) if q2 is not None else (q1,)
   block.append((typ.upper(),qs,bit,lines[j]))
   j+=1
  if len(block)<2:
   out.append(lines[i]);i+=1;continue
  # All diagonal gates in the block commute. Their parity conditions
  # may be combined without changing the unitary for any classical state.
  groups={};order=[]
  for typ,qs,bit,original in block:
   key=(typ,qs)
   if key not in groups:groups[key]=[];order.append(key)
   groups[key].append(bit)
  rewritten=[]
  for typ,qs in order:
   terms=groups[(typ,qs)]
   uncond=sum(t is None for t in terms)%2
   c=collections.Counter(t for t in terms if t is not None)
   active=sorted((t for t,n in c.items() if n%2),key=int)
   target=f"{typ} {' '.join(qs)}"
   # G is an involution, so a constant 1 contributes a bare G.
   if uncond:rewritten.append(target)
   if len(active)==1:rewritten.append(f"{target} if b{active[0]}")
   elif len(active)>=2:
    dest=nextbit;nextbit+=1
    rewritten.append(f"BIT_STORE0 b{dest}")
    rewritten.extend(f"BIT_INVERT b{dest} if b{b}" for b in active)
    rewritten.append(f"{target} if b{dest}")
    stats["parity_bits"]+=1
   stats["duplicate_conditions_cancelled"]+=sum(n//2*2 for n in c.values())
  # Only adopt a strictly smaller number of quantum phase gates.
  old=sum(1 for _ in block)
  new=sum(1 for s in rewritten if PHASE.fullmatch(s))
  if new<old:
   out.extend(rewritten)
   stats["phase_gates_removed"]+=old-new
   stats["changed_blocks"]+=1
   stats["original_phase_gates"]+=old
   stats["new_phase_gates"]+=new
  else:out.extend(lines[i:j])
  i=j
 return out,dict(stats)

def verify(p,full,timeout):
 ref=ROOT/"competition/k031/k031_full_domain_repair.py"
 spec=importlib.util.spec_from_file_location("k031_k062",ref)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 d={}
 for name,n,seed in [("prefix",64,12345)]+(
     [("full_12345",m.FULL_X,12345),("full_23456",m.FULL_X,23456)] if full else []):
  d[name]=m.verify(p,n,seed,timeout)
  if d[name].get("status")!="PASS" or d[name].get("exit_code")!=0:break
 return d

def main():
 pa=argparse.ArgumentParser()
 pa.add_argument("--input",type=Path,default=ROOT/"competition/k059/results/helios_public.kmx")
 pa.add_argument("--out",type=Path,default=ROOT/"competition/k062/results")
 pa.add_argument("--full",action="store_true")
 pa.add_argument("--timeout",type=int,default=600)
 a=pa.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 if not a.input.is_file():raise SystemExit("Missing K059 decoded KMX: "+str(a.input))
 lines=a.input.read_text().splitlines()
 candidate,stats=transform(lines)
 print("K062_TRANSFORM",json.dumps({
  "source":str(a.input),"source_sha256":sha(a.input),
  "source_lines":len(lines),"candidate_lines":len(candidate),
  **stats},sort_keys=True),flush=True)
 report={"source_sha256":sha(a.input),"stats":stats,"note":
         "Exact algebraic diagonal parity folding; third-party benchmark adaptation, not original invention."}
 if not stats.get("phase_gates_removed",0):
  report["status"]="NO_OPTIMIZATION";print("K062_RESULT",json.dumps(report),flush=True)
 else:
  dest=a.out/"invsqrt_parity_folded.kmx"
  dest.write_text("\n".join(candidate)+"\n")
  report["candidate_kmx_sha256"]=sha(dest)
  try:
   import kickmix as km
   circuit=km.Circuit.from_file(str(dest),format="kmx")
   kmb=a.out/"invsqrt_parity_folded.kmb"
   circuit.to_file(str(kmb),format="kmb")
   report["candidate_kmb_sha256"]=sha(kmb)
   report["qubits"]=circuit.num_qubits
   report["official"]=verify(kmb,a.full,a.timeout)
   good=all(v.get("status")=="PASS" and v.get("exit_code")==0
            for v in report["official"].values())
   report["status"]="PASS" if good else "FAIL"
  except Exception as e:report["status"]="ERROR";report["error"]=repr(e)
  print("K062_RESULT",json.dumps({"status":report["status"],
    "stats":stats,"qubits":report.get("qubits"),
    "official":report.get("official"),"error":report.get("error")},
    sort_keys=True),flush=True)
 (a.out/"result.json").write_text(json.dumps(report,indent=2,default=str))
 print("SAVED",a.out/"result.json",flush=True)
if __name__=="__main__":main()
