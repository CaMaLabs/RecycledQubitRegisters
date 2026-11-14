#!/usr/bin/env python3
"""K145: zero-ancilla cubic phase-polynomial optimization for native CX/Z/CZ/CCZ.
Polytof-inspired GF(2) basis search, NOT full Polytof CP decomposition.
Preserves all quantum phases and affine output by exact algebraic reparse.
Never alters pinned source; --candidate only writes proven local rewrites.
"""
import argparse,hashlib,json,re
from collections import Counter
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
OPS={"CX":2,"Z":1,"CZ":2,"CCZ":3}
Q=re.compile(r"^q([0-9]+)$")
def parse(s):
 t=s.strip().split()
 if not t or t[0] not in OPS or len(t)!=OPS[t[0]]+1:return None
 if not all(Q.fullmatch(v) for v in t[1:]):return None
 w=tuple(int(v[1:]) for v in t[1:])
 return (t[0],w) if len(set(w))==len(w) else None
def flip(s,m):
 if m in s:s.remove(m)
 else:s.add(m)
def model(g):
 ws=sorted({v for _,qq in g for v in qq})
 ix={v:i for i,v in enumerate(ws)}
 state={v:1<<ix[v] for v in ws};p=set()
 for op,qq in g:
  if op=="CX":state[qq[1]]^=state[qq[0]]
  else:
   terms={0}
   for w in qq:
    nxt=set()
    for m in terms:
     v=state[w]
     while v:
      bit=v&-v;v^=bit;flip(nxt,m|bit)
    terms=nxt
   p.symmetric_difference_update(terms)
 return ws,p,state
def substitute(p,c,t):
 cb,tb=1<<c,1<<t;out=set(p)
 for m in p:
  if m&tb:flip(out,(m^tb)|cb)
 return out
def cubic(p):return sum(m.bit_count()==3 for m in p)
def improve(p,n,limit):
 cur=set(p);trans=[]
 for _ in range(limit):
  old=cubic(cur);best=None
  for c in range(n):
   for t in range(n):
    if c==t:continue
    q=substitute(cur,c,t);v=(cubic(q),len(q),c,t)
    if v[0]<old and (best is None or v<best[0]):best=(v,q,c,t)
  if best is None:break
  _,cur,c,t=best;trans.append((c,t))
 return cur,trans
def construct(g,ws,p,final,limit):
 new,trans=improve(p,len(ws),limit)
 check=set(new)
 for c,t in reversed(trans):check=substitute(check,c,t)
 assert check==p,"cubic phase mismatch"
 assert (0 in new)==(0 in p),"global phase mismatch"
 out=[]
 for c,t in trans:out.append(f"CX q{ws[c]} q{ws[t]}\n")
 for m in sorted(new,key=lambda z:(z.bit_count(),z)):
  bits=[ws[i] for i in range(len(ws)) if (m>>i)&1]
  if len(bits)==0:continue
  if len(bits)>3:raise ValueError("phase degree >3")
  out.append({1:"Z",2:"CZ",3:"CCZ"}[len(bits)]+" "+" ".join(f"q{x}" for x in bits)+"\n")
 for c,t in reversed(trans):out.append(f"CX q{ws[c]} q{ws[t]}\n")
 for op,qq in g:
  if op=="CX":out.append("CX "+" ".join(f"q{x}" for x in qq)+"\n")
 parsed=[parse(x) for x in out]
 assert all(parsed)
 rws,rp,rfinal=model(parsed)
 assert rws==ws and rp==p and rfinal==final,"reparse operator equivalence failed"
 return out,new,trans
def windows(lines):
 start=None;g=[]
 for i,s in enumerate(lines+["__END__"]):
  v=parse(s)
  if v is None:
   if g:yield start,i,g
   start=None;g=[]
  else:
   if start is None:start=i
   g.append(v)
def selftest():
 for sample in [
  ["CCZ q0 q1 q2","CCZ q0 q1 q3"],
  ["CX q0 q1","CCZ q0 q1 q2","CX q2 q3","CCZ q0 q1 q3"],
  ["CCZ q0 q1 q2","CZ q0 q2","Z q2","CX q0 q2","CCZ q1 q2 q3"]]:
  g=[parse(x) for x in sample];ws,p,state=model(g)
  out,new,t=construct(g,ws,p,state,16)
  assert model([parse(x) for x in out])[1:]==(p,state)
 g=[parse(x) for x in ["CCZ q0 q1 q2","CCZ q0 q1 q3"]]
 ws,p,state=model(g);out,new,t=construct(g,ws,p,state,16)
 assert cubic(p)==2 and cubic(new)==1
 print("K145_SELFTEST PASS cubic operator and affine output")
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
 ap.add_argument("--out",type=Path,default=Path("competition/k145/results/cubic_tensor_report.json"))
 ap.add_argument("--candidate",type=Path)
 ap.add_argument("--max-wires",type=int,default=12)
 ap.add_argument("--max-lines",type=int,default=512)
 ap.add_argument("--min-ccz",type=int,default=2)
 ap.add_argument("--rounds",type=int,default=32)
 a=ap.parse_args();selftest()
 if min(a.max_wires,a.max_lines,a.min_ccz,a.rounds)<1:ap.error("bounds must be positive")
 raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
 lines=raw.decode().splitlines(keepends=True)
 cases=[];repl=[];counts=Counter();eligible=0
 for begin,end,g in windows(lines):
  old=sum(op=="CCZ" for op,_ in g)
  if old==0:continue
  counts["with_ccz"]+=1
  if old<a.min_ccz:counts["few_ccz"]+=1;continue
  ws=sorted({w for _,qq in g for w in qq})
  if len(ws)>a.max_wires or len(g)>a.max_lines:
   counts["bounds_reject"]+=1;continue
  eligible+=1;ws,p,final=model(g)
  newsource,new,t=construct(g,ws,p,final,a.rounds)
  newcost=sum(x.startswith("CCZ ") for x in newsource)
  row={"first_line":begin+1,"end_line":end,"wire_count":len(ws),
       "old_ccz":old,"new_ccz":newcost,"cubic_terms":cubic(p),
       "delta_ccz":newcost-old,"basis_changes":len(t),"exact_local_proof":True}
  cases.append(row)
  if newcost<old:
   repl.append((begin,end,newsource));counts["improving"]+=1
   print("K145_POTENTIAL",json.dumps(row),flush=True)
  else:counts["no_win"]+=1
 report={"experiment":"K145","status":"EXACT_LOCAL_CUBIC_PHASE_SCREEN",
 "baseline_sha256":sha,"eligible_windows":eligible,"counts":dict(counts),
 "improving_windows":len(repl),"results":cases,
 "limitations":["Greedy cubic GF2 basis reduction, not complete Polytof CPD",
 "Only contiguous unconditional CX/Z/CZ/CCZ; no HMR, CCX, resets or guards crossed",
 "Exact local operator proof, not full official verification",
 "Static CCZ saved is not verified score improvement"]}
 if a.candidate and repl:
  output=list(lines)
  for begin,end,part in sorted(repl,reverse=True):output[begin:end]=part
  a.candidate.parent.mkdir(parents=True,exist_ok=True)
  a.candidate.write_text("".join(output))
  report["candidate"]=str(a.candidate)
  report["candidate_sha256"]=hashlib.sha256(a.candidate.read_bytes()).hexdigest()
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2)+"\n")
 print("K145_RESULT",json.dumps({"eligible_windows":eligible,
  "counts":dict(counts),"improving_windows":len(repl),
  "out":str(a.out)}),flush=True)
if __name__=="__main__":main()
