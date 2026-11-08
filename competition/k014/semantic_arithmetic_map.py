#!/usr/bin/env python3
"""K014: semantic arithmetic-region discovery for Google's invsqrt reference.

Read-only. Correlates KMx INFO_TAG operations and expensive CCX/CSWAP/HMR/R
with the *official Python reference builder*, to pick functional
subcircuits for QRR/LWE resynthesis. No reference source copied into repo.

Separately counts operand-only reversible windows and measures how much
Toffoli cost they represent: estimates the ceiling of a peephole strategy.
"""
import argparse,ast,collections,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
PRIVATE=(HERE/"../k001/private").resolve()
SOURCE=PRIVATE/"official/verifiers/invsqrt/nr_reference_circuit.py"
KMX=PRIVATE/"runs/k005/reference_roundtrip.kmx"
REPORT=HERE/"k014_semantic_regions.json"
Q=re.compile(r"\bq\d+\b")
EXPENSIVE={"CCX","CCZ","CSWAP"}
FENCES={"HMR","R","PUSH_CONDITION","POP_CONDITION","INFO_TAG","Z_POW","NEG","APPEND_TO_REGISTER","REGISTER"}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--show-tags",type=int,default=15)
 p.add_argument("--show-blocks",type=int,default=14)
 p.add_argument("--report",default=str(REPORT))
 a=p.parse_args()
 if not SOURCE.is_file() or not KMX.is_file():p.error("Official K001/K005 sources missing")
 lines=KMX.read_text(encoding="utf-8").splitlines()
 ops=[s.strip().split()[0] if s.strip() else "" for s in lines]
 expensive_total=sum(x in EXPENSIVE for x in ops)
 # INFO_TAG may be a material marker, but don't assume one tag
 # is a semantic scope or that it safely isolates a rewrite.
 tags=[]
 for i,s in enumerate(lines):
  if ops[i]!="INFO_TAG":continue
  before=ops[max(0,i-32):i];after=ops[i+1:i+33]
  tags.append({"line":i+1,"tag_excerpt":s[:160],
      "before32_cost":sum(t in EXPENSIVE for t in before),
      "after32_cost":sum(t in EXPENSIVE for t in after),
      "before32_hmr":before.count("HMR"),"after32_hmr":after.count("HMR")})
 regions=[];start=0
 for i,op in enumerate(ops+["<EOF>"]):
  if op in FENCES or op=="<EOF>":
   if i>start:
    chunk=ops[start:i]
    n=sum(x in EXPENSIVE for x in chunk)
    if n:
     wire_ids=set()
     for line in lines[start:i]:wire_ids.update(Q.findall(line))
     regions.append({"start":start+1,"end":i,"length":i-start,
       "toffoli_like":n,"ccx":chunk.count("CCX"),
       "cswap":chunk.count("CSWAP"),"cx":chunk.count("CX"),
       "distinct_operands":len(wire_ids),
       "preceding_barrier":ops[start-1] if start else "<START>",
       "next_barrier":op})
   start=i+1
 # Extract function names and call sites, but never copy full proprietary source.
 tree=ast.parse(SOURCE.read_text(encoding="utf-8"),filename=str(SOURCE))
 methods=[]; calls=collections.Counter()
 for node in ast.walk(tree):
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
   methods.append({"name":node.name,"line":node.lineno,
     "end":getattr(node,"end_lineno",None)})
  if isinstance(node,ast.Call):
   f=node.func
   if isinstance(f,ast.Attribute):calls[f.attr]+=1
   elif isinstance(f,ast.Name):calls[f.id]+=1
 # Quantify how little of the Toffoli workload is accessible through
 # small local rewriting windows (without crossing any barriers).
 histogram=collections.Counter()
 for row in regions:histogram[str(row["distinct_operands"]//4*4)+"-"+str(row["distinct_operands"]//4*4+3)]+=row["toffoli_like"]
 budget={str(k):sum(row["toffoli_like"] for row in regions if row["distinct_operands"]<=k)
         for k in (3,4,5,6,8,10,16,32)}
 data={"status":"PASS_SEMANTIC_ARITHMETIC_REGION_MAPPING",
   "source_file":str(SOURCE),"kmx_file":str(KMX),
   "total_instructions":len(lines),"toffoli_like_total":expensive_total,
   "info_tag_count":len(tags),"tags":tags[:75],
   "reference_builder_methods":methods[:100],
   "reference_builder_calls":calls.most_common(100),
   "reversible_regions":len(regions),
   "expensive_cost_accessible_in_small_regions_by_operand_limit":budget,
   "operand_histogram_weighted_by_toffolis":dict(sorted(histogram.items())),
   "most_expensive_regions":sorted(regions,key=lambda x:(-x["toffoli_like"],-x["length"]))[:60],
   "limitations":["Textual function names and INFO_TAGs suggest structure but do not prove subcircuit equivalence",
     "HMR/R/phase/condition boundaries are never crossed in this analysis",
     "Reference-basis circuit may already contain optimized arithmetic, so resynthesis must be measured",
     "No candidate modified; no Kaggle submission"]}
 out=Path(a.report);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(data,indent=2)+"\n")
 print("K014 STATUS",data["status"])
 print("K014 TOTAL COST",expensive_total,"REGIONS",len(regions),"INFO_TAGS",len(tags))
 print("K014 SMALL REGION COST COVERAGE",budget)
 print("K014 SOURCE FUNCTIONS",[(m["name"],m["line"]) for m in methods[:45]])
 print("K014 HIGH-FREQ BUILDER CALLS",calls.most_common(30))
 print("K014 HOT REGIONS",data["most_expensive_regions"][:a.show_blocks])
 print("K014 TAGS")
 for t in tags[:a.show_tags]:print(" ",t)
 print("K014 REPORT",out)
if __name__=="__main__":main()
