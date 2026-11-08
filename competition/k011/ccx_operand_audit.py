#!/usr/bin/env python3
"""K011 — operand-aware CCX hotspot and measurement-boundary audit.

Read-only analysis of local official KMx. Analyze CCX source/target roles,
nearby R/HMR/CZ/CX operations, measurement-conditioned dependence, and
CCX pairs with shared operands. Does not rewrite the circuit or assert
phase-equivalence. Prints short bounded snippets from the *user's local*
official reference for review; report stores only metadata/counts and
short operand signatures (not the full official circuit).
"""
import argparse, collections, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
KMX=(ROOT/"../k001/private/runs/k005/reference_roundtrip.kmx").resolve()
REPORT=ROOT/"k011_ccx_hotspots.json"
OPS=re.compile(r"^([A-Z_]+)(?:\s|$)")
Q=re.compile(r"(?<!\w)q\d+(?!\w)")
def parse(s):
 parts=s.strip().split()
 return parts[0] if parts else "",tuple(Q.findall(s))
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--context",type=int,default=5)
 ap.add_argument("--examples",type=int,default=8)
 ap.add_argument("--report",default=str(REPORT))
 args=ap.parse_args()
 if args.context<1 or args.context>15 or args.examples<0 or args.examples>30:
  ap.error("context 1..15, examples 0..30")
 if not KMX.is_file():ap.error("K005 KMx missing")
 lines=KMX.read_text(encoding="utf-8").splitlines()
 ins=[parse(s) for s in lines]
 names=[x[0] for x in ins]
 ccx=[i for i,(n,_) in enumerate(ins) if n=="CCX"]
 patterns=collections.Counter(); triples=collections.Counter()
 target_freq=collections.Counter();controls_freq=collections.Counter()
 shared_opp=collections.Counter();measurement_near=collections.Counter()
 run_labels=collections.Counter();sample_by_label={}
 for i in ccx:
  _,qubits=ins[i]
  if len(qubits)!=3:continue
  a,b,t=qubits
  target_freq[t]+=1;controls_freq.update((a,b))
  before=names[i-1] if i else "<START>"
  after=names[i+1] if i+1<len(ins) else "<END>"
  patterns[(before,after)]+=1
  j=i-1
  while j>=0 and names[j]=="R":j-=1
  k=i+1
  while k<len(ins) and names[k]=="CX":k+=1
  if j<i-1 or k>i+1:
   run_labels[(i-1-j,k-i-1)]+=1
  window=ins[max(0,i-args.context):min(len(ins),i+args.context+1)]
  near_m=tuple(sorted(set(n for n,_ in window if n in ("R","HMR","CZ","PUSH_CONDITION","POP_CONDITION"))))
  measurement_near[near_m]+=1
  label=(before,after,near_m)
  if label not in sample_by_label:sample_by_label[label]=i
  for j in range(i+1,min(i+15,len(ins))):
   if names[j] in ("R","HMR","Z_POW","PUSH_CONDITION","POP_CONDITION","INFO_TAG"):
    break
   if names[j]=="CCX" and len(ins[j][1])==3:
    other=ins[j][1]
    if other[2]==t:shared_opp["same_target"]+=1
    if set(other[:2])==set((a,b)):shared_opp["same_controls"]+=1
    if other==qubits:shared_opp["identical"]+=1
    break
 report={"status":"K011_STATIC_CCX_AUDIT_COMPLETE",
  "instruction_count":len(lines),"ccx_count":len(ccx),
  "ccx_operand_counts":{"unique_targets":len(target_freq),
   "unique_controls":len(controls_freq)},
  "frequent_targets":target_freq.most_common(20),
  "frequent_controls":controls_freq.most_common(20),
  "ccx_immediate_neighbors":[{"before":before,"after":after,"count":count}
    for (before,after),count in patterns.most_common(25)],
  "measurement_context":[{"markers":list(markers),"count":count}
    for markers,count in measurement_near.most_common(20)],
  "local_ccx_relationships":dict(shared_opp),
  "adjacent_r_before_cx_after":[{"r_count":r,"cx_count":c,"count":count}
    for (r,c),count in run_labels.most_common(20)],
  "sample_line_numbers":[{"before":label[0],"after":label[1],"measurement_markers":list(label[2]),
                           "line":i+1} for label,i in list(sample_by_label.items())[:30]],
  "sample_source_rewritten":False,"kaggle_submitted":False}
 out=Path(args.report);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(report,indent=2)+"\n")
 print("K011 STATUS",report["status"])
 print("K011 CCX",report["ccx_count"],"UNIQUE TARGETS",len(target_freq))
 print("K011 MOST COMMON",report["ccx_immediate_neighbors"][:15])
 print("K011 MEASUREMENT CONTEXT",report["measurement_context"][:10])
 print("K011 LOCAL RELATIONS",report["local_ccx_relationships"])
 print("K011 FREQUENT TARGETS",report["frequent_targets"][:12])
 print("K011 R/CX RUNS",report["adjacent_r_before_cx_after"][:12])
 # Representative snippets (small and explicitly scoped), for debugging
 # operand and measurement semantics. Never add these to GitHub.
 examples=sorted(sample_by_label.items(),key=lambda kv:-patterns[(kv[0][0],kv[0][1])])[:args.examples]
 for index,(label,i) in enumerate(examples,1):
  print(f"K011 EXAMPLE {index} LINE {i+1} CONTEXT {label}")
  for j in range(max(0,i-args.context),min(len(lines),i+args.context+1)):
   print(f" {j+1:6d} {lines[j][:170]}")
 print("K011 REPORT",out)
if __name__=="__main__":main()
