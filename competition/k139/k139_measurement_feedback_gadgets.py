#!/usr/bin/env python3
"""K139 read-only measurement-assisted uncomputation opportunity audit.

Looks for measurement-feedback gadgets (HMR q b followed by conditional
CZ on b), then measures the *upstream* CCX chain producing q and the
*downstream* reversible cleanup cost. This is a bridge search across the
measurement boundary, unlike K135-K138's purely reversible intervals.

Does NOT assume that the cleanups are removable, or that the measurement
implements a phase-correct AND uncompute: that requires channel/phase
equivalence and official verifier tests. No candidate is generated.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, re
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
Q=re.compile(r"^q(\d+)$")
B=re.compile(r"^b(\d+)$")
REV={"X":1,"CX":2,"CCX":3,"SWAP":2,"CSWAP":3}
PHASE={"Z","CZ","CCZ","S","S_DAG","T","T_DAG","Z_POW"}
def parse(line):
 t=line.strip().split()
 return (t[0].upper(),t) if t and not t[0].startswith(("#","//")) else ("",[])
def qs(t):
 return tuple(int(s[1:]) for s in t[1:] if Q.fullmatch(s))
def scoped_conditions(t):
 low=[s.lower() for s in t]
 if 'if' in low:
  i=low.index('if')
  return t[i+1] if i+1<len(t) and B.fullmatch(t[i+1]) else None
 return None
def scan(lines,forward,backward):
 ops=[parse(s) for s in lines];hits=[];stats=collections.Counter()
 for i,(op,t) in enumerate(ops):
  if op!="HMR":continue
  wires=qs(t);measbits=[s for s in t[1:] if B.fullmatch(s)]
  if len(wires)!=1 or len(measbits)!=1:
   stats["bad_hmr_shape"]+=1;continue
  target,b=wires[0],measbits[0];stats["hmr_total"]+=1
  # Feedback expected in a small region, because bits may be overwritten.
  feedback=[]
  for j in range(i+1,min(i+1+forward,len(lines))):
   oj,tj=ops[j]
   if oj=="HMR" and b in tj[1:]:break
   if oj in ("BIT_STORE0","BIT_STORE1","BIT_INVERT") and b in tj[1:]:break
   if oj in PHASE and scoped_conditions(tj)==b:
    feedback.append({"line":j+1,"opcode":oj,"qubits":qs(tj)})
  if not feedback:
   stats["no_nearby_phase_feedback"]+=1;continue
  stats["phase_feedback_hmr"]+=1
  upstream=[];last_barrier=None
  for j in range(i-1,max(-1,i-1-backward),-1):
   oj,tj=ops[j]
   if oj not in REV or scoped_conditions(tj) is not None:
    last_barrier=j+1;break
   v=qs(tj)
   if len(v)!=REV[oj]:last_barrier=j+1;break
   upstream.append((j+1,oj,v))
  upstream.reverse()
  producer=[(ln,op2,v) for ln,op2,v in upstream if op2=="CCX" and v[-1]==target]
  # Track a feed-forward spine ending at measured target. This is a
  # structural dependency heuristic, not a causal/phase proof.
  active={target};spine=[]
  for ln,op2,v in reversed(upstream):
   touched=(v[-1] in active if op2 in ("X","CX","CCX") else bool(active.intersection(v)))
   if touched:
    spine.append((ln,op2,v))
    active.update(v)
  spine.reverse()
  # Count cost downstream until next HMR or conditional barrier. No
  # claim these operations are a coherent uncompute.
  downstream=[]
  for j in range(i+1,min(len(lines),i+1+forward)):
   oj,tj=ops[j]
   if oj=="HMR":break
   if oj in REV and scoped_conditions(tj) is None:
    downstream.append((j+1,oj,qs(tj)))
  candidate={
   "hmr_line":i+1,"measured_qubit":target,"result_bit":b,
   "feedback":feedback[:12],
   "producer_ccx_lines":[x[0] for x in producer],
   "upstream_ccx_count":sum(op2=="CCX" for _,op2,_ in upstream),
   "upstream_spine_ccx_count":sum(op2=="CCX" for _,op2,_ in spine),
   "spine_length":len(spine),
   "spine_input_qubits":sorted(active),
   "downstream_unconditional_ccx_before_next_hmr":sum(op2=="CCX" for _,op2,_ in downstream),
   "downstream_unconditional_cx_before_next_hmr":sum(op2=="CX" for _,op2,_ in downstream),
   "upstream_window_start":upstream[0][0] if upstream else i+1,
   "upstream_barrier_line":last_barrier,
   "status":"STRUCTURAL_GADGET_ONLY_NOT_PROVEN"}
  candidate["priority_proxy"]=(
   5*len(producer)+candidate["upstream_spine_ccx_count"]+
   candidate["downstream_unconditional_ccx_before_next_hmr"])
  hits.append(candidate)
 hits.sort(key=lambda r:(-r["priority_proxy"],-len(r["feedback"]),r["hmr_line"]))
 return hits,dict(stats)
def selftest():
 sample=["CCX q0 q1 q2","CX q0 q1","HMR q2 b5","CZ q0 q1 if b5","CX q0 q1"]
 rows,counts=scan(sample,16,16)
 assert len(rows)==1 and rows[0]["producer_ccx_lines"]==[1]
 assert rows[0]["feedback"][0]["opcode"]=="CZ"
 assert scan(["HMR q2 b1","CZ q0 q1 if b2"],10,10)[0]==[]
 print("K139_SELFTEST PASS feedback and producer recognition",flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--out",type=Path,default=Path("competition/k139/results/measurement_feedback_gadgets.json"))
 p.add_argument("--forward",type=int,default=24)
 p.add_argument("--backward",type=int,default=64)
 p.add_argument("--top",type=int,default=30)
 a=p.parse_args()
 if min(a.forward,a.backward,a.top)<1:p.error("positive bounds required")
 selftest()
 raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit("Pinned baseline digest mismatch: "+sha)
 rows,stats=scan(raw.decode().splitlines(),a.forward,a.backward)
 result={"experiment":"K139","status":"READ_ONLY_MEASUREMENT_FEEDBACK_AUDIT",
  "baseline_sha256":sha,"source_lines":len(raw.decode().splitlines()),
  "counts":stats,"candidate_gadget_count":len(rows),"top_gadgets":rows[:a.top],
  "limitations":[
   "This is a structural scan, not proof that HMR realizes a coherent uncompute.",
   "Bit overwrites, condition scopes, and phase semantics require exact modeling.",
   "The spine and priority proxy are heuristics, not removable CCX counts.",
   "No gate was deleted, no circuit generated, no verifier or score run.",
   "Small local search bounds may miss long-distance feedback."
  ]}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(result,indent=2)+"\n")
 print("K139_SUMMARY",json.dumps({"status":result["status"],"counts":stats,"candidate_gadget_count":len(rows)}),flush=True)
 for x in rows[:a.top]:
  print("K139_GADGET",json.dumps(x),flush=True)
 print("K139_RESULT",json.dumps({"out":str(a.out),"candidate_gadget_count":len(rows)}),flush=True)
if __name__=="__main__":main()
