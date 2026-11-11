#!/usr/bin/env python3
"""K141: correct K140's 'target mixed' false positives with exact local ANF.

For each HMR immediately followed by a CZ conditioned on its measurement
bit, find the nearest unconditionally executed CCX that writes the measured
target without crossing an unknown/phase/measurement/control-flow barrier.
From that CCX to HMR, simulate the ENTIRE unconditional X/CX/CCX section as
GF(2) ANF on independent input qubits. Classify whether:
  * the measured target is unchanged since the producing CCX,
  * its apparent changes cancel exactly,
  * it acquires a different Boolean function,
  * the CZ control product retains the CCX's original predicate.
Reading q as a control is NOT a mutation of q. No quantum channel or
phase-correction equivalence is asserted; this is a narrow Boolean audit.

This script does not alter the circuit or estimate official score savings.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,re
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
Q=re.compile(r"^q(\d+)$");B=re.compile(r"^b(\d+)$")
REV={"X":1,"CX":2,"CCX":3}
def parse(s):
 t=s.strip().split()
 if not t or t[0].startswith(("#","//")):return None
 return t[0].upper(),t
def qs(t):return tuple(int(x[1:]) for x in t[1:] if Q.fullmatch(x))
def guard(t):
 low=[x.lower() for x in t]
 if "if" not in low:return None
 j=low.index("if")
 return t[j+1] if j+1<len(t) and B.fullmatch(t[j+1]) else "<invalid>"
def mul(a,b,limit):
 if len(a)*len(b)>limit*32:raise OverflowError("ANF expansion budget")
 z=set()
 for x in a:
  for y in b:
   p=x|y
   if p in z:z.remove(p)
   else:z.add(p)
   if len(z)>limit:raise OverflowError("ANF monomial budget")
 return z
def propagate(gates,measured,producer_ctrl,limit):
 wires=sorted(set([measured,*producer_ctrl]+[w for _,seq in gates for w in seq]))
 indexes={w:i for i,w in enumerate(wires)}
 v={w:{1<<indexes[w]} for w in wires}
 initial_pred=mul(v[producer_ctrl[0]],v[producer_ctrl[1]],limit)
 after_producer=None;writes=[];reads=[]
 for step,(op,seq) in enumerate(gates):
  if op=="X":
   if seq[0]==measured:writes.append(step)
   v[seq[0]]^={0}
  elif op=="CX":
   if seq[1]==measured:writes.append(step)
   if seq[0]==measured:reads.append(step)
   v[seq[1]]^=v[seq[0]]
  elif op=="CCX":
   if seq[2]==measured:writes.append(step)
   if measured in seq[:2]:reads.append(step)
   v[seq[2]]^=mul(v[seq[0]],v[seq[1]],limit)
  if step==0:after_producer=set(v[measured])
  if len(v[measured])>limit:raise OverflowError("ANF state budget")
 assert after_producer is not None
 return {"target_equal_after_producer":v[measured]==after_producer,
    "target_writes_after_producer":sum(x!=0 for x in writes),
    "target_control_reads_after_producer":sum(x!=0 for x in reads),
    "target_restored_after_intervening_writes":bool(any(x!=0 for x in writes) and v[measured]==after_producer),
    "feedback_control_product_unchanged":mul(v[producer_ctrl[0]],v[producer_ctrl[1]],limit)==initial_pred,
    "target_difference_monomials":len(v[measured]^after_producer),
    "used_wires":len(wires)}
def scan(lines,lookback,limit):
 parsed=[parse(s) for s in lines];counts=collections.Counter();items=[]
 for i,item in enumerate(parsed):
  if not item or item[0]!="HMR":continue
  t=item[1];w=qs(t);b=[s for s in t[1:] if B.fullmatch(s)]
  if len(w)!=1 or len(b)!=1:continue
  counts["hmr"]+=1
  j=i+1
  while j<len(parsed) and parsed[j] is None:j+=1
  if j>=len(parsed) or parsed[j][0]!="CZ" or guard(parsed[j][1])!=b[0]:
   counts["no_immediate_cz"]+=1;continue
  feedback=qs(parsed[j][1])
  if len(feedback)!=2:continue
  counts["immediate_cz"]+=1
  target=w[0];producer=None;intermediate=[]
  for k in range(i-1,max(-1,i-1-lookback),-1):
   rec=parsed[k]
   if rec is None or rec[0] not in REV or guard(rec[1]) is not None:
    break
   op,tok=rec;wr=qs(tok)
   if len(wr)!=REV[op]:break
   intermediate.append((op,wr))
   if op=="CCX" and wr[2]==target:
    producer=(k,wr);break
  if producer is None:
   counts["unresolved_producer"]+=1;continue
  k,wr=producer;intermediate.reverse()
  control_match=set(wr[:2])==set(feedback)
  try:
   data=propagate(intermediate,target,wr[:2],limit)
  except OverflowError:
   counts["anf_budget_unresolved"]+=1;continue
  if control_match and data["target_equal_after_producer"] and data["feedback_control_product_unchanged"]:
   category="BOOLEAN_PRODUCER_AND_CONTROLS_PRESERVED"
  elif control_match and data["target_equal_after_producer"]:
   category="TARGET_PRESERVED_CONTROLS_CHANGED"
  elif control_match:
   category="TARGET_CHANGED_AFTER_PRODUCER"
  else:
   category="FEEDBACK_CONTROLS_MISMATCH"
  counts[category]+=1
  data.update({"hmr_line":i+1,"producer_line":k+1,"feedback_line":j+1,
   "measured_qubit":target,"measurement_bit":b[0],
   "producer_controls":list(wr[:2]),"feedback_controls":list(feedback),
   "category":category})
  items.append(data)
 items.sort(key=lambda x:({"TARGET_CHANGED_AFTER_PRODUCER":0,
   "TARGET_PRESERVED_CONTROLS_CHANGED":1,"FEEDBACK_CONTROLS_MISMATCH":2,
   "BOOLEAN_PRODUCER_AND_CONTROLS_PRESERVED":3}.get(x["category"],4),
   -x["target_writes_after_producer"],x["hmr_line"]))
 return dict(counts),items
def selftest():
 a=[("CCX",(0,1,2)),("CX",(2,3))]
 x=propagate(a,2,(0,1),1000)
 assert x["target_equal_after_producer"] and x["target_control_reads_after_producer"]==1
 a=[("CCX",(0,1,2)),("CX",(3,2)),("CX",(3,2))]
 x=propagate(a,2,(0,1),1000)
 assert x["target_restored_after_intervening_writes"]
 a=[("CCX",(0,1,2)),("CX",(3,2))]
 assert not propagate(a,2,(0,1),1000)["target_equal_after_producer"]
 a=[("CCX",(0,1,2)),("CX",(0,1))]
 assert not propagate(a,2,(0,1),1000)["feedback_control_product_unchanged"]
 assert scan(["CCX q0 q1 q2","CX q2 q3","HMR q2 b4","CZ q0 q1 if b4"],20,1000)[0]["BOOLEAN_PRODUCER_AND_CONTROLS_PRESERVED"]==1
 print("K141_SELFTEST PASS fanout, write cancel, write change, changing controls",flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--out",type=Path,default=Path("competition/k141/results/feedback_boolean_provenance.json"))
 p.add_argument("--lookback",type=int,default=64)
 p.add_argument("--max-monomials",type=int,default=20000)
 p.add_argument("--top",type=int,default=30)
 a=p.parse_args()
 if min(a.lookback,a.max_monomials,a.top)<1:p.error("positive bounds required")
 selftest()
 raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit("Pinned baseline mismatch "+sha)
 counts,items=scan(raw.decode().splitlines(),a.lookback,a.max_monomials)
 result={"experiment":"K141","status":"BOOLEAN_PROVENANCE_ONLY",
  "baseline_sha256":sha,"counts":counts,"gadgets":items,
  "limitations":["ANF equality is over independent Boolean input wires; no quantum channel/phase proof.",
  "Only unconditioned X/CX/CCX gates modeled, stopping at barriers.",
  "The measured qubit need not have been initialized to zero; this test does not establish AND-uncompute validity.",
  "K140's 'mixed target' included harmless uses as a control; this report distinguishes reads from writes.",
  "No circuit rewrite, official verifier, or score improvement."]}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(result,indent=2)+"\n")
 print("K141_SUMMARY",json.dumps(counts),flush=True)
 for x in items[:a.top]:print("K141_GADGET",json.dumps(x),flush=True)
 print("K141_RESULT",json.dumps({"status":result["status"],"out":str(a.out),"gadgets":len(items)}),flush=True)
if __name__=="__main__":main()
