#!/usr/bin/env python3
"""K010: prove potential controlled-swap network compression opportunities.

Read-only scan of official kickmix KMx. No circuit rewriting, no score claim.
Treat INFO_TAG, phase, measurement, condition and every non-CSWAP as a barrier.
For each maximal contiguous CSWAP run, split on changes of first operand
(control). For fixed-control runs, compute the target permutation and the
mathematical minimum number of transpositions needed to implement it.

Assumption to validate before *any* rewrite: kickmix CSWAP operand order
is control, target A, target B, and all target wires are distinct from control.
The scanner reports but does not rely on that assumption to modify anything.
"""
import collections,json,re
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=(HERE/"../k001/private/runs/k005/reference_roundtrip.kmx").resolve()
OUT=HERE/"k010_cswap_permutation_audit.json"
CSWAP=re.compile(r"^CSWAP\s+(q\d+)\s+(q\d+)\s+(q\d+)\s*$")

def run_info(start,operations):
 control=operations[0][0]
 wires=sorted({w for _,a,b in operations for w in (a,b)},key=lambda q:int(q[1:]))
 pos={w:w for w in wires}
 for c,a,b in operations:
  if c!=control or c in (a,b) or a==b:
   return {"start_line":start+1,"length":len(operations),"control":control,
      "candidate_savings":0,"invalid_target_or_mixed_control":True}
  pos[a],pos[b]=pos[b],pos[a]
 visited=set();cycles=[]
 for x in wires:
  if x in visited:continue
  y=x;cy=[]
  while y not in visited:
   visited.add(y);cy.append(y);y=pos[y]
  if len(cy)>1:cycles.append(cy)
 minimum=sum(len(c)-1 for c in cycles)
 savings=len(operations)-minimum
 if savings<0:raise AssertionError("permutation minimum exceeded source size")
 return {"start_line":start+1,"end_line":start+len(operations),
   "length":len(operations),"control":control,
   "num_targets":len(wires),"nontrivial_cycles":len(cycles),
   "minimum_transpositions":minimum,"candidate_savings":savings,
   "identity_permutation":minimum==0,
   "cycle_lengths":sorted([len(c) for c in cycles],reverse=True)}

def main():
 if not SOURCE.is_file():raise SystemExit("K005 reference KMx not found")
 lines=SOURCE.read_text(encoding="utf-8").splitlines()
 raw=[];begin=None;ops=[]
 def flush():
  nonlocal begin
  if ops:
   raw.append(run_info(begin,ops))
   ops.clear()
  begin=None
 for i,line in enumerate(lines):
  m=CSWAP.fullmatch(line.strip())
  if m and (not ops or m.group(1)==ops[-1][0]):
   if begin is None:begin=i
   ops.append(m.groups())
  else:
   flush()
   if m:
    begin=i;ops.append(m.groups())
 flush()
 total=sum(x["length"] for x in raw)
 c=collections.Counter(x["length"] for x in raw)
 positive=[x for x in raw if x["candidate_savings"]>0]
 data={"status":"K010_READ_ONLY_PERMUTATION_AUDIT_COMPLETE",
  "source_instructions":len(lines),"total_cswap_in_fixed_control_runs":total,
  "number_of_fixed_control_runs":len(raw),
  "run_length_histogram":dict(sorted(c.items())),
  "max_run_length":max(c,default=0),
  "savings_upper_bound_contiguous_fixed_control":sum(x["candidate_savings"] for x in raw),
  "positive_runs":len(positive),
  "top_savings_runs":sorted(positive,key=lambda x:(-x["candidate_savings"],-x["length"]))[:40],
  "top_longest_runs":sorted(raw,key=lambda x:(-x["length"],-x["candidate_savings"]))[:25],
  "assumptions":["CSWAP qControl qA qB operand semantics MUST be validated against kickmix docs before rewriting",
    "Only uninterrupted runs of CSWAP with same control are analyzed",
    "No cross-gate commutation, no phase operations, no measurement, no conditional scopes are crossed",
    "An upper bound is not a validated implementation and may be zero"],
  "candidate_created":False,"official_verifier_passed":False,"kaggle_submitted":False}
 OUT.write_text(json.dumps(data,indent=2)+"\n")
 print("K010 STATUS",data["status"])
 print("K010 CSWAP COUNT",total,"RUNS",len(raw))
 print("K010 RUN LENGTH HISTOGRAM",data["run_length_histogram"])
 print("K010 POTENTIAL SAVINGS",data["savings_upper_bound_contiguous_fixed_control"],
       "POSITIVE RUNS",data["positive_runs"])
 print("K010 TOP LONGEST",data["top_longest_runs"][:12])
 print("K010 TOP SAVINGS",data["top_savings_runs"][:12])
 print("K010 REPORT",OUT)
if __name__=="__main__":main()
