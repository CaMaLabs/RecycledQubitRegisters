#!/usr/bin/env python3
"""K009: locate high-cost arithmetic motifs in official kickmix invsqrt.

Static analysis only. Read-only, no full reference content copied into report.
Reports CCX/CSWAP neighborhoods, basic structural patterns, and hard barriers
to inform a new algorithmic optimization. Never asserts semantic equivalence.
"""
import collections,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
KMX=(ROOT/"../k001/private/runs/k005/reference_roundtrip.kmx").resolve()
OUT=ROOT/"k009_structural_audit.json"
TOK=re.compile(r"^([A-Z_]+)(?:\s|$)")
QBIT=re.compile(r"\bq\d+\b")
COST={"CCX","CCZ","CSWAP"}
def op(line):
 m=TOK.match(line.strip())
 return m.group(1) if m else "<OTHER>"
def main():
 if not KMX.is_file():raise SystemExit("K005 KMx reference is missing")
 lines=KMX.read_text(encoding="utf-8").splitlines()
 names=[op(s) for s in lines]
 counts=collections.Counter(names)
 costly=[i for i,name in enumerate(names) if name in COST]
 windows=collections.Counter()
 context=collections.Counter()
 for i in costly:
  left=tuple(names[max(0,i-3):i])
  right=tuple(names[i+1:i+4])
  windows[(names[i],left,right)]+=1
  context[(names[i],names[i-1] if i else "<START>",names[i+1] if i+1<len(names) else "<END>")]+=1
 pair_counts=collections.Counter(zip(names,names[1:]))
 triples=collections.Counter(zip(names,names[1:],names[2:]))
 barrier={"R","HMR","PUSH_CONDITION","POP_CONDITION","Z_POW","INFO_TAG","REGISTER","APPEND_TO_REGISTER","NEG"}
 spans=[];start=0;costs=collections.Counter()
 for i,n in enumerate(names+["<EOF>"]):
  if n in barrier or n=="<EOF>":
   if i>start:
    slice_names=names[start:i]
    spans.append({"start":start+1,"end":i,"length":i-start,
                  "toffoli_like":sum(x in COST for x in slice_names),
                  "cx":slice_names.count("CX"),"x":slice_names.count("X"),
                  "cz":slice_names.count("CZ")})
   start=i+1
 top=sorted(spans,key=lambda d:(-d["toffoli_like"],-d["length"]))[:24]
 adjacent_same=collections.Counter()
 for i in range(len(lines)-1):
  if names[i] in COST and lines[i].strip()==lines[i+1].strip():adjacent_same[names[i]]+=1
 # Structural signature only; no official program text is disclosed.
 # Count gate operand fanout to identify high-frequency central controls.
 operand_frequency=collections.Counter()
 controls=collections.Counter()
 targets=collections.Counter()
 for line,name in zip(lines,names):
  if name not in COST:continue
  q=QBIT.findall(line)
  if not q:continue
  operand_frequency.update(q)
  if name in {"CCX","CSWAP"} and len(q)==3:
   controls.update(q[:1] if name=="CSWAP" else q[:2])
   targets.update(q[1:] if name=="CSWAP" else q[-1:])
 data={"status":"PASS_STATIC_STRUCTURAL_AUDIT",
  "reference_bytes":KMX.stat().st_size,"instruction_count":len(lines),
  "counts":dict(counts),
  "toffoli_like_instruction_total":len(costly),
  "adjacent_identical_costly_gates":dict(adjacent_same),
  "most_common_costly_neighbor_types":[{"gate":key[0],"left":key[1],"right":key[2],"count":n} for key,n in windows.most_common(25)],
  "costly_neighbor_pair_types":[{"gate":key[0],"before":key[1],"after":key[2],"count":n} for key,n in context.most_common(30)],
  "common_operation_pairs":[{"ops":pair,"count":n} for pair,n in pair_counts.most_common(30)],
  "common_operation_triples":[{"ops":tri,"count":n} for tri,n in triples.most_common(30)],
  "top_costly_contiguous_regions":top,
  "region_count":len(spans),
  "max_costly_region":max((s["toffoli_like"] for s in spans),default=0),
  "frequent_costly_operands":operand_frequency.most_common(15),
  "frequent_costly_controls":controls.most_common(15),
  "frequent_costly_targets":targets.most_common(15),
  "candidate_optimized":False,"candidate_verified":False,"kaggle_submitted":False,
  "scope":"Static gate-structure reconnaissance only, no unproven rewrites"}
 OUT.write_text(json.dumps(data,indent=2)+"\n")
 print("K009 STATUS",data["status"])
 print("K009 GATES",data["counts"])
 print("K009 COSTLY REGIONS",top[:12])
 print("K009 COSTLY NEIGHBORS",data["costly_neighbor_pair_types"][:12])
 print("K009 COMMON TRIPLES",data["common_operation_triples"][:15])
 print("K009 ADJACENT IDENTICAL",data["adjacent_identical_costly_gates"])
 print("K009 REPORT",OUT)
if __name__=="__main__":main()
