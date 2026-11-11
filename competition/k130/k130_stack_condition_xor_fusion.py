#!/usr/bin/env python3
"""K130: fuse identical Toffoli-class gates across separate one-bit condition scopes."""
import argparse,collections,hashlib,json,re
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
QRE=re.compile(r"\bq\d+\b",re.I);BRE=re.compile(r"^b\d+$",re.I);OPS={"CCX","CCZ","CSWAP"}
def sig(op,qs):
 if op=="CCX":return op,(tuple(sorted(qs[:2])),qs[2])
 if op=="CCZ":return op,tuple(sorted(qs))
 return op,(qs[0],tuple(sorted(qs[1:])))
def writes(t):
 op=t[0].upper();out=set()
 if op in ("BIT_INVERT","BIT_STORE0","BIT_STORE1") and len(t)>1:out.add(t[1])
 if op=="HMR":out.update(x for x in t[1:] if BRE.fullmatch(x))
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--baseline",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);ap.add_argument("--candidate",type=Path);a=ap.parse_args()
 raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit("baseline SHA mismatch: "+sha)
 lines=raw.decode().splitlines();stack=[];events=[];ops=collections.Counter()
 for i,line in enumerate(lines):
  t=line.strip().split()
  if not t or t[0].startswith("#"):continue
  op=t[0].upper();ops[op]+=1
  if op=="PUSH_CONDITION":
   stack.append((t[2] if len(t)>2 else "?",i));continue
  if op=="POP_CONDITION":
   if stack:stack.pop()
   continue
  if op not in OPS or len(stack)!=1:continue
  qs=QRE.findall(line);conds=[x for x in t if BRE.fullmatch(x)]
  if len(qs)!=3 or "if" in [x.lower() for x in t]:continue
  c,push=stack[0]
  if not BRE.fullmatch(c):continue
  events.append({"index":i,"line":i+1,"push":push,"cond":c,"op":op,"qs":qs,"sig":sig(op,qs)})
 bysig=collections.defaultdict(list)
 for e in events:bysig[e["sig"]].append(e)
 pairs=[];used=set()
 for signature,items in bysig.items():
  for pos,left in enumerate(items):
   if left["index"] in used:continue
   wires=set(left["qs"]);c1=left["cond"]
   # Guard values must be unchanged since their computation is inserted before the scope.
   bad=False
   for k in range(left["push"]+1,left["index"]):
    t=lines[k].strip().split()
    if t and c1 in writes(t):bad=True;break
   if bad:continue
   for right in items[pos+1:]:
    if right["index"] in used or right["cond"]==c1:continue
    c2=right["cond"];blocked=False
    for k in range(left["index"]+1,right["index"]):
     t=lines[k].strip().split()
     if not t or t[0].startswith("#"):continue
     if wires.intersection(QRE.findall(lines[k])) or {c1,c2}.intersection(writes(t)):
      blocked=True;break
    if blocked:continue
    for k in range(right["push"]+1,right["index"]):
     t=lines[k].strip().split()
     if t and c2 in writes(t):blocked=True;break
    if blocked:continue
    pairs.append({"first_line":left["line"],"first_push_line":left["push"]+1,"second_line":right["line"],"second_push_line":right["push"]+1,"opcode":left["op"],"qubits":left["qs"],"conditions":[c1,c2],"max_saved_executed_gates_per_shot":2})
    used.update((left["index"],right["index"]));break
 result={"experiment":"K130","status":"FUSION_PAIRS_FOUND" if pairs else "NO_ELIGIBLE_STACK_CONDITION_PAIRS","baseline_sha256":sha,"source_lines":len(lines),"eligible_gate_events":len(events),"distinct_gate_signatures":len(bysig),"candidate_pairs":pairs,"max_toffoli_reduction_per_shot":2*len(pairs),"max_score_reduction":124*len(pairs),"expected_score_reduction_if_guards_independent_fair_bits":31*len(pairs),"candidate_generated":False,"limitations":["Only exact CCX/CCZ/CSWAP involutions in a single one-bit PUSH_CONDITION scope are considered.","Intervening quantum gates must be disjoint and guard bits unchanged.","No eligible pair means this specific score mechanism offers no source-level candidate."]}
 if pairs and a.candidate:
  maxbit=max([int(x) for x in re.findall(r"\bb(\d+)\b",raw.decode())] or [0])+1
  before=collections.defaultdict(list);replacement={};remove=set()
  for n,pair in enumerate(pairs):
   bn=f"b{maxbit+n}";c1,c2=pair["conditions"];push=pair["first_push_line"]-1;gate=pair["first_line"]-1
   before[push].extend([f"BIT_STORE0 {bn}",f"BIT_INVERT {bn} if {c1}",f"BIT_INVERT {bn} if {c2}"])
   replacement[gate]=["POP_CONDITION",f"PUSH_CONDITION if {bn}",lines[gate],"POP_CONDITION",f"PUSH_CONDITION if {c1}"]
   remove.add(pair["second_line"]-1)
  out=[]
  for i,line in enumerate(lines):
   out.extend(before.get(i,[]))
   if i in remove:continue
   out.extend(replacement.get(i,[line]))
  a.candidate.parent.mkdir(parents=True,exist_ok=True);a.candidate.write_text("\n".join(out)+"\n");result["candidate_generated"]=True
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n")
 print("K130_RESULT",json.dumps({k:result[k] for k in ("status","baseline_sha256","eligible_gate_events","distinct_gate_signatures","candidate_pairs","max_toffoli_reduction_per_shot","max_score_reduction","candidate_generated")}))
if __name__=="__main__":main()
