#!/usr/bin/env python3
"""K129: condition-XOR fusion screen for identical self-inverse gates."""
import argparse, collections, hashlib, json, re
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
QRE=re.compile(r"\bq\d+\b",re.I); BRE=re.compile(r"^b\d+$",re.I)
OPS={"CCX","CCZ","CSWAP"}
def signature(op,qs):
 if op=="CCX":return op,(tuple(sorted(qs[:2])),qs[2])
 if op=="CCZ":return op,tuple(sorted(qs))
 if op=="CSWAP":return op,(qs[0],tuple(sorted(qs[1:])))
def main():
 p=argparse.ArgumentParser();p.add_argument("--baseline",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--candidate",type=Path)
 a=p.parse_args();raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit("baseline SHA mismatch: "+sha)
 lines=raw.decode().splitlines();events=[];stack=[];counts=collections.Counter()
 for i,line in enumerate(lines):
  t=line.strip().split()
  if not t or t[0].startswith("#"):continue
  op=t[0].upper();counts[op]+=1
  if op=="PUSH_CONDITION":
   stack.append(t[2] if len(t)>2 else "?");continue
  if op=="POP_CONDITION":
   if stack:stack.pop()
   continue
  if op not in OPS or len(stack)>1:continue
  qs=QRE.findall(line)
  if len(qs)!={"CCX":3,"CCZ":3,"CSWAP":3}[op]:continue
  conds=[x for x in t if BRE.fullmatch(x)]
  if "if" not in [x.lower() for x in t] or len(conds)!=1:continue
  events.append({"index":i,"line":i+1,"op":op,"qs":qs,"sig":signature(op,qs),"cond":conds[0],"context":tuple(stack)})
 bysig=collections.defaultdict(list)
 for e in events:bysig[(e["sig"],e["context"])].append(e)
 pairs=[];used=set()
 for sig,items in bysig.items():
  for pos,left in enumerate(items):
   if left["index"] in used:continue
   wires=set(left["qs"]);c1=left["cond"]
   for right in items[pos+1:]:
    if right["index"] in used:continue
    c2=right["cond"]
    if c1==c2:continue
    blocked=False
    for k in range(left["index"]+1,right["index"]):
     s=lines[k].strip()
     if not s or s.startswith("#"):continue
     toks=s.split();op=toks[0].upper()
     qs=QRE.findall(s)
     # Any intervening quantum operation touching G is a conservative barrier.
     if op in ("PUSH_CONDITION","POP_CONDITION"):
      blocked=True;break
     if wires.intersection(qs):
      blocked=True;break
     # The guard values must remain unchanged between uses.
     writes=set()
     if op in ("BIT_INVERT","BIT_STORE0","BIT_STORE1") and len(toks)>1: writes.add(toks[1])
     if op=="HMR":
      writes.update(x for x in toks[1:] if BRE.fullmatch(x))
     if {c1,c2}.intersection(writes):
      blocked=True;break
    if not blocked:
     pairs.append({"first_line":left["line"],"second_line":right["line"],"opcode":left["op"],"qubits":left["qs"],"conditions":[c1,c2],"shared_condition_context":list(left["context"]),"barrier":"all intervening quantum operations are disjoint; guard bits are not written","max_executed_toffolis_saved_per_shot":2})
     used.update((left["index"],right["index"]));break
 result={"experiment":"K129","status":"FUSION_PAIRS_FOUND" if pairs else "NO_ELIGIBLE_CONDITION_XOR_PAIRS","baseline_sha256":sha,"source_lines":len(lines),"toffoli_class_events_with_single_inline_bit_condition":len(events),"distinct_gate_signatures":len(bysig),"candidate_pairs":pairs,"max_toffoli_reduction_per_shot":2*len(pairs),"max_score_reduction":124*len(pairs),"expected_score_reduction_if_each_pair_guards_are_independent_fair_bits":31*len(pairs),"candidate_generated":False,"limitations":["Only exact identical CCX/CCZ/CSWAP gates with one inline classical-bit condition are considered.","Intervening gates must be quantum-disjoint and must not overwrite either guard bit.","The predicted dynamic saving depends on simultaneous guard values; simulator verification is required for any candidate."]}
 if pairs and a.candidate:
  out=lines[:];maxbit=max([int(x) for x in re.findall(r"\bb(\d+)\b",raw.decode())] or [0])+1
  inserts=[];removes=set()
  for n,pair in enumerate(pairs):
   bnew=f"b{maxbit+n}";c1,c2=pair["conditions"];l1=pair["first_line"]-1;l2=pair["second_line"]-1
   out[l1:l1]=[f"BIT_STORE0 {bnew}",f"BIT_INVERT {bnew} if {c1}",f"BIT_INVERT {bnew} if {c2}"]
   out[l1+3]=re.sub(r"\bif\s+b\d+\b",f"if {bnew}",out[l1+3],count=1)
   # Account for insertions already made by tracking original source line locations below.
   inserts.append((pair["first_line"],bnew,c1,c2));removes.add(pair["second_line"])
  # Rebuild from original lines to avoid shifted-index interactions.
  byfirst={x[0]:x[1:] for x in inserts};out=[]
  for n,line in enumerate(lines,1):
   if n in byfirst:
    bn,c1,c2=byfirst[n];out.extend([f"BIT_STORE0 {bn}",f"BIT_INVERT {bn} if {c1}",f"BIT_INVERT {bn} if {c2}"])
    line=re.sub(r"\bif\s+b\d+\b",f"if {bn}",line,count=1)
   if n not in removes:out.append(line)
  a.candidate.parent.mkdir(parents=True,exist_ok=True);a.candidate.write_text("\n".join(out)+"\n")
  result["candidate_generated"]=True;result["candidate_path"]=str(a.candidate)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n")
 print("K129_RESULT",json.dumps({k:result[k] for k in ("status","baseline_sha256","toffoli_class_events_with_single_inline_bit_condition","distinct_gate_signatures","candidate_pairs","max_toffoli_reduction_per_shot","max_score_reduction","candidate_generated")}))
if __name__=="__main__":main()
