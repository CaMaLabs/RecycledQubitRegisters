#!/usr/bin/env python3
"""K140: producer-to-measurement phase-feedback provenance audit.

K139 detects HMR/CZ adjacency but falsely suggests nearby downstream CCX
could be cleanup. K140 instead checks, for each HMR followed immediately by
a conditional CZ, whether the CZ control pair exactly matches the nearest
unconditional CCX whose TARGET is the measured qubit, and audits every
intervening operation that touches that qubit.

This does not prove channel equivalence; it distinguishes familiar
measurement-assisted AND cleanup patterns from complex mixed-target gadgets
that might warrant a fully phase-aware proof. It makes no circuit edits.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, re
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
Q=re.compile(r"^q(\d+)$")
B=re.compile(r"^b(\d+)$")
def parse(line):
 t=line.strip().split()
 if not t or t[0].startswith(('#','//')):return None
 return t[0].upper(),t
def wires(t):return tuple(int(z[1:]) for z in t[1:] if Q.fullmatch(z))
def guard(t):
 low=[z.lower() for z in t]
 if 'if' not in low:return None
 i=low.index('if')
 return t[i+1] if i+1<len(t) and B.fullmatch(t[i+1]) else "<invalid>"
def classify(lines,lookback,top):
 parsed=[parse(s) for s in lines]
 counts=collections.Counter();results=[]
 for i,rec in enumerate(parsed):
  if not rec or rec[0]!="HMR":continue
  counts["total_hmr"]+=1
  op,t=rec;target=wires(t)
  bits=[z for z in t[1:] if B.fullmatch(z)]
  if len(target)!=1 or len(bits)!=1:
   counts["unrecognized_hmr"]+=1;continue
  q=target[0];b=bits[0]
  j=i+1
  while j<len(lines) and parsed[j] is None:j+=1
  if j>=len(lines) or parsed[j][0]!="CZ" or guard(parsed[j][1])!=b:
   counts["without_immediate_cz_feedback"]+=1;continue
  controls=tuple(wires(parsed[j][1]))
  if len(controls)!=2:
   counts["malformed_feedback"]+=1;continue
  counts["immediate_cz_feedback"]+=1
  producer=None;barriers=[];touch=[]
  # The producer search is bounded and DOES NOT cross conditional,
  # measurement, phase, or unknown operations. Only unconditional
  # reversible classical gates are admitted.
  reversible={"X","CX","CCX","SWAP","CSWAP"}
  for k in range(i-1,max(-1,i-1-lookback),-1):
   prev=parsed[k]
   if not prev or prev[0] not in reversible or guard(prev[1]) is not None:
    barriers.append(k+1);break
   prevop,prevt=prev;pw=wires(prevt)
   if q in pw:
    touch.append({"line":k+1,"op":prevop,"wires":pw})
   if prevop=="CCX" and len(pw)==3 and pw[2]==q:
    producer={"line":k+1,"controls":pw[:2],"target":q};break
  if producer is None:
   counts["no_bounded_unconditional_ccx_producer"]+=1
   category="NO_SAFE_PRODUCER"
  else:
   matched=set(producer["controls"])==set(controls)
   intervening=touch[:-1]
   mixed=bool(intervening)
   if matched and not mixed:
    category="DIRECT_AND_PHASE_FEEDBACK"
   elif matched:
    category="MATCHED_PAIR_BUT_TARGET_MIXED"
   else:
    category="DIFFERENT_FEEDBACK_PAIR"
   counts[category]+=1
  row={"hmr_line":i+1,"measured_qubit":q,"result_bit":b,
       "immediate_cz_line":j+1,"feedback_controls":controls,
       "producer":producer,
       "operations_touching_target_backward":touch[:20],
       "barrier_line":barriers[0] if barriers else None,
       "category":category}
  results.append(row)
 results.sort(key=lambda r:(
  {"MATCHED_PAIR_BUT_TARGET_MIXED":0,"DIFFERENT_FEEDBACK_PAIR":1,
   "NO_SAFE_PRODUCER":2,"DIRECT_AND_PHASE_FEEDBACK":3}.get(r["category"],4),
  r["hmr_line"]))
 return counts,results

def selftest():
 d=["CCX q1 q2 q3","HMR q3 b4","CZ q1 q2 if b4"]
 s,r=classify(d,16,10)
 assert s["DIRECT_AND_PHASE_FEEDBACK"]==1
 d=["CCX q1 q2 q3","CX q0 q3","HMR q3 b4","CZ q1 q2 if b4"]
 s,r=classify(d,16,10)
 assert s["MATCHED_PAIR_BUT_TARGET_MIXED"]==1
 d=["CCX q1 q2 q3","HMR q3 b4","CZ q0 q2 if b4"]
 s,r=classify(d,16,10)
 assert s["DIFFERENT_FEEDBACK_PAIR"]==1
 print("K140_SELFTEST PASS direct/mixed/mismatched feedback attribution",flush=True)

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--out",type=Path,default=Path("competition/k140/results/feedback_provenance.json"))
 p.add_argument("--lookback",type=int,default=64)
 p.add_argument("--top",type=int,default=30)
 a=p.parse_args()
 if a.lookback<1 or a.top<1:p.error("positive bounds required")
 selftest()
 raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit("Pinned baseline SHA mismatch: "+sha)
 counts,rows=classify(raw.decode().splitlines(),a.lookback,a.top)
 report={"experiment":"K140","status":"STRUCTURAL_FEEDBACK_PROVENANCE",
  "baseline_sha256":sha,"counts":dict(counts),"all_gadgets":rows,
  "warnings":["A matched producer/feedback pair is NOT proof of correct phase cancellation.",
   "Intervening operations may be required for later calculations.",
   "Only immediate CZ corrections are examined, not Z or stack-dependent corrections.",
   "Unconditional classical producer search stops at the first barrier.",
   "No candidate generated; no official verifier or score improvement."]}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2)+"\n")
 print("K140_SUMMARY",json.dumps({"status":report["status"],"counts":dict(counts)}),flush=True)
 for row in rows[:a.top]:
  print("K140_GADGET",json.dumps(row),flush=True)
 print("K140_RESULT",json.dumps({"out":str(a.out),"gadgets":len(rows)}),flush=True)
if __name__=="__main__":main()
