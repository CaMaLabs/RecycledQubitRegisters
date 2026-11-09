#!/usr/bin/env python3
"""K060: trace classical feed-forward and measurement/uncompute patterns in KMX.
Descriptive analysis only; no claims of semantic equivalence without verification.
Reads K059 decoded circuit files already on the local machine.
"""
from __future__ import annotations
import argparse,collections,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DEFAULT=ROOT/"competition/k059/results"
WATCH=("HMR","R","PUSH_CONDITION","POP_CONDITION",
       "BIT_STORE0","BIT_STORE1","BIT_INVERT","CCX","CCZ","CSWAP","Z_POW")
def opcode(line):
 s=line.strip()
 if not s or s.startswith(("#","//")):return None
 m=re.match(r"([a-zA-Z][a-zA-Z0-9_]*)",s)
 return m.group(1).upper() if m else None
def inspect(path,samples,window,chunk_count):
 lines=path.read_text(errors="replace").splitlines()
 instr=[(i+1,opcode(s),s.rstrip()) for i,s in enumerate(lines)]
 instr=[x for x in instr if x[1]]
 counts=collections.Counter(x[1] for x in instr)
 chunks=[]
 n=len(instr)
 for j in range(chunk_count):
  region=instr[n*j//chunk_count:n*(j+1)//chunk_count]
  c=collections.Counter(x[1] for x in region)
  chunks.append({"chunk":j,"line_start":region[0][0] if region else 0,
   "line_end":region[-1][0] if region else 0,
   "instructions":len(region),"counts":{k:c[k] for k in WATCH}})
 neighborhoods={}
 for kind in WATCH:
  indices=[i for i,x in enumerate(instr) if x[1]==kind]
  if not indices:continue
  chosen=indices[:samples]
  if len(indices)>samples:
   chosen += indices[len(indices)//2:len(indices)//2+min(2,samples)]
   chosen += indices[-min(2,samples):]
  neighborhoods[kind]=[{"at":instr[i][0],"surrounding":[
   {"line":t[0],"op":t[1],"code":t[2][:350]}
   for t in instr[max(0,i-window):min(n,i+window+1)]]}
   for i in dict.fromkeys(chosen)]
 # Pairing and span of explicit conditions, including nesting.
 scopes=[];stack=[]
 for lineno,op,text in instr:
  if op=="PUSH_CONDITION":stack.append((lineno,text,collections.Counter()))
  elif op=="POP_CONDITION":
   if stack:
    start,original,inner=stack.pop()
    scopes.append({"start":start,"end":lineno,"span_lines":lineno-start,
     "push":original[:200],"pop":text[:200],
     "inside_counts":dict(inner)})
  elif stack:
   for x in stack:x[2][op]+=1
 nested=len(stack)
 # Opcode bigrams reveal repeatedly used compute/cleanup phrases.
 adjacent=collections.Counter((a[1],b[1]) for a,b in zip(instr,instr[1:]))
 return {"file":str(path),"total_instructions":n,"counts":dict(counts),
  "chunks":chunks,"neighborhoods":neighborhoods,
  "condition_scopes_total":len(scopes),"condition_unclosed":nested,
  "condition_scope_samples":sorted(scopes,key=lambda x:x["span_lines"],reverse=True)[:8]+scopes[:8],
  "condition_scope_lengths":dict(collections.Counter(
    "0-4" if s["span_lines"]<5 else "5-19" if s["span_lines"]<20
    else "20-99" if s["span_lines"]<100 else "100+" for s in scopes)),
  "top_pairs":[{"first":a,"second":b,"count":c} for (a,b),c in adjacent.most_common(30)]}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--dir",type=Path,default=DEFAULT)
 p.add_argument("--out",type=Path,default=ROOT/"competition/k060/results")
 p.add_argument("--samples",type=int,default=3)
 p.add_argument("--window",type=int,default=4)
 a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=True)
 report={}
 for name in ("helios_public","k040_ours","k056_bounded_ours"):
  f=a.dir/(name+".kmx")
  if not f.is_file():
   report[name]={"status":"MISSING","path":str(f)}
   print("K060_MISSING",name,f,flush=True);continue
  report[name]=inspect(f,a.samples,a.window,16)
  r=report[name]
  print("K060_COUNTS",json.dumps({"name":name,"ops":r["total_instructions"],
   "interesting":{k:r["counts"].get(k,0) for k in WATCH},
   "condition_scope_lengths":r["condition_scope_lengths"]},sort_keys=True),flush=True)
  print("K060_CHUNKS",json.dumps({"name":name,
   "chunks":[{"part":t["chunk"],"CCX":t["counts"]["CCX"],"HMR":t["counts"]["HMR"],
    "PUSH":t["counts"]["PUSH_CONDITION"],"BIT_STORE0":t["counts"]["BIT_STORE0"],
    "BIT_STORE1":t["counts"]["BIT_STORE1"]} for t in r["chunks"]]},
   sort_keys=True),flush=True)
  for op in ("HMR","PUSH_CONDITION","BIT_STORE0","CCZ"):
   for block in r["neighborhoods"].get(op,[])[:2]:
    print("K060_NEIGHBORHOOD",json.dumps({"name":name,"opcode":op,**block}),flush=True)
 (a.out/"trace.json").write_text(json.dumps(report,indent=2))
 print("K060_SAVED",str(a.out/"trace.json"),flush=True)
if __name__=="__main__":main()
