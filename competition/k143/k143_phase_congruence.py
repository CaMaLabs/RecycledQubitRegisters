#!/usr/bin/env python3
"""K143: exact phase-polynomial CNOT-basis rewrite of HMR Z/CZ feedback.
Read-only unless --candidate. Clifford-only: no claimed Kaggle score win.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,re
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
Q=re.compile(r"q([0-9]+)$");B=re.compile(r"b([0-9]+)$")
def tokens(s):
 t=s.strip().split()
 return t if t and not t[0].startswith(('#','//')) else None
def qubits(t):return [int(x[1:]) for x in t[1:] if Q.fullmatch(x)]
def condition(t):
 if "if" not in t:return None
 i=t.index("if");return t[i+1] if i+1<len(t) and B.fullmatch(t[i+1]) else "INVALID"
def flip(s,x):
 if x in s:s.remove(x)
 else:s.add(x)
def collect(lines):
 t=[tokens(s) for s in lines];out=[]
 for i,op in enumerate(t):
  if op is None or op[0].upper()!="HMR":continue
  bits=[x for x in op[1:] if B.fullmatch(x)]
  if len(bits)!=1:continue
  j=i+1;linear=set();pairs=set();count=0
  while j<len(t):
   z=t[j]
   if z is None:j+=1;continue
   if z[0].upper() not in ("Z","CZ") or condition(z)!=bits[0]:break
   w=qubits(z)
   if z[0].upper()=="Z" and len(w)==1:flip(linear,w[0])
   elif z[0].upper()=="CZ" and len(w)==2 and w[0]!=w[1]:flip(pairs,tuple(sorted(w)))
   else:raise ValueError(f"invalid correction line {j+1}")
   count+=1;j+=1
  if count:out.append(dict(hmr=i+1,start=i+1,end=j,bit=bits[0],linear=linear,pairs=pairs,count=count))
 return out
def substitute(lin,pairs,c,t):
 l=set();e=set()
 for x in lin:
  flip(l,x)
  if x==t:flip(l,c)
 for a,b in pairs:
  if t not in (a,b):flip(e,(a,b));continue
  other=b if a==t else a
  flip(e,(a,b))
  if other==c:flip(l,c)
  else:flip(e,tuple(sorted((other,c))))
 return l,e
def optimize(lin,pairs,steps):
 wires=sorted(set(lin)|{v for p in pairs for v in p});l=set(lin);e=set(pairs);changes=[]
 for _ in range(steps):
  best=None
  for c in wires:
   for t in wires:
    if t==c:continue
    ll,ee=substitute(l,e,c,t)
    if len(ee)>=len(e):continue
    key=(len(ee),len(ll),c,t)
    if best is None or key<best[0]:best=(key,ll,ee,c,t)
  if best is None:break
  _,l,e,c,t=best;changes.append((c,t))
 return l,e,changes
def prove(lin,pairs,newl,newe,changes):
 l=set(newl);e=set(newe)
 for c,t in reversed(changes):l,e=substitute(l,e,c,t)
 return l==lin and e==pairs
def rank(pairs,wires):
 ix={x:i for i,x in enumerate(wires)}
 rows=[0]*len(wires)
 for a,b in pairs:
  x,y=ix[a],ix[b];rows[x]^=1<<y;rows[y]^=1<<x
 r=0
 for k in range(len(wires)):
  j=next((p for p in range(r,len(wires)) if (rows[p]>>k)&1),None)
  if j is None:continue
  rows[r],rows[j]=rows[j],rows[r]
  for p in range(len(wires)):
   if p!=r and ((rows[p]>>k)&1):rows[p]^=rows[r]
  r+=1
 return r
def synth(block,l,e,changes):
 result=[f"CX q{c} q{t}\n" for c,t in changes]
 result += [f"Z q{x} if {block['bit']}\n" for x in sorted(l)]
 result += [f"CZ q{a} q{b} if {block['bit']}\n" for a,b in sorted(e)]
 result += [f"CX q{c} q{t}\n" for c,t in reversed(changes)]
 return result
def selftest():
 x={(0,1),(0,2),(1,2)}
 for c in range(4):
  for t in range(4):
   if t==c:continue
   l,e=substitute({0,1},x,c,t)
   assert substitute(l,e,c,t)==({0,1},x)
 l,e,changes=optimize(set(),x,10)
 assert len(e)<len(x) and prove(set(),x,l,e,changes)
 print("K143_SELFTEST PASS substitution involution and exact phase polynomial",flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--out",type=Path,default=Path("competition/k143/results/quadratic_basis_rewrites.json"))
 p.add_argument("--candidate",type=Path)
 p.add_argument("--focus",default="14768,15165,21606,25612")
 p.add_argument("--top",type=int,default=12)
 p.add_argument("--max-transforms",type=int,default=32)
 a=p.parse_args();selftest()
 raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit("Immutable baseline SHA mismatch: "+sha)
 lines=raw.decode().splitlines(keepends=True);blocks=collect(lines)
 selected={int(x) for x in a.focus.split(",") if x.strip()}
 selected.update(x["hmr"] for x in sorted(blocks,key=lambda b:-len(b["pairs"]))[:a.top])
 rows=[];replacements=[]
 for block in blocks:
  if block["hmr"] not in selected:continue
  lin,pairs=block["linear"],block["pairs"]
  nl,ne,changes=optimize(lin,pairs,a.max_transforms)
  assert prove(lin,pairs,nl,ne,changes)
  wires=sorted(set(lin)|{v for p in pairs for v in p})
  before,after=rank(pairs,wires),rank(ne,wires)
  assert before==after
  saved=len(pairs)-len(ne)
  row={"hmr_line":block["hmr"],"original_z":len(lin),"original_cz":len(pairs),
    "candidate_z":len(nl),"candidate_cz":len(ne),"cz_removed":saved,
    "cx_added":2*len(changes),"quadratic_rank":before,
    "phase_polynomial_equivalent":True,
    "source_toffoli_difference":0,"source_arbitrary_rotation_difference":0,
    "basis_changes":changes}
  rows.append(row);print("K143_BLOCK",json.dumps(row),flush=True)
  if saved>0:replacements.append((block["start"],block["end"],synth(block,nl,ne,changes)))
 result={"experiment":"K143","status":"CLIFFORD_ONLY_EXACT_LOCAL_REWRITES",
   "baseline_sha256":sha,"feedback_blocks_total":len(blocks),
   "focused_blocks_tested":len(rows),"results":rows,
   "net_candidate_cz_removed":sum(x["cz_removed"] for x in rows),
   "net_candidate_cx_added":sum(x["cx_added"] for x in rows),
   "scored_win_not_established":True,
   "constraints":["Exact local Z/CZ phase equivalence; no CCX or rotation reductions.",
   "Official scorer not available here; no verified score claim.",
   "Generated candidates are unverified; source baseline SHA pinned."]}
 if a.candidate:
  new=list(lines)
  for start,end,repl in sorted(replacements,reverse=True):new[start:end]=repl
  a.candidate.parent.mkdir(parents=True,exist_ok=True)
  a.candidate.write_text("".join(new))
  result["candidate_path"]=str(a.candidate)
  result["candidate_sha256"]=hashlib.sha256(a.candidate.read_bytes()).hexdigest()
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(result,indent=2)+"\n")
 print("K143_RESULT",json.dumps({"status":result["status"],"tested":len(rows),
   "cz_removed":result["net_candidate_cz_removed"],"cx_added":result["net_candidate_cx_added"],
   "candidate":str(a.candidate) if a.candidate else None,"out":str(a.out),
   "scored_win_not_established":True}),flush=True)
if __name__=="__main__":main()
