#!/usr/bin/env python3
"""K127 exact Boolean-predicate screen for phase factoring; read-only."""
import argparse, collections, hashlib, json, re
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
QR=re.compile(r"^q\d+$",re.I); BR=re.compile(r"^b\d+$",re.I)
class D:
 def __init__(self):
  self.n=[("c",0),("c",1)];self.i={self.n[0]:0,self.n[1]:1};self.z=0;self.o=1
  self.names=[];self.ranks={};self.cache={}
 def mk(self,n):
  if n[2]==n[3]:return n[2]
  if n in self.i:return self.i[n]
  j=len(self.n);self.n.append(n);self.i[n]=j
  if j>10000000:raise MemoryError("BDD node limit exceeded")
  return j
 def v(self,s):
  if s not in self.ranks:self.ranks[s]=len(self.names);self.names.append(s)
  r=self.ranks[s];return self.mk(("n",r,0,1))
 def top(self,u):return self.n[u][1] if self.n[u][0]=="n" else 1<<30
 def cof(self,u,r):
  n=self.n[u]
  return (n[2],n[3]) if n[0]=="n" and n[1]==r else (u,u)
 def apply(self,op,u,v):
  if op in ("a","x") and u>v:u,v=v,u
  if op=="a":
   if u==0 or v==0:return 0
   if u==1:return v
   if v==1 or u==v:return u
  else:
   if u==0:return v
   if u==v:return 0
  key=(op,u,v)
  if key in self.cache:return self.cache[key]
  if self.n[u][0]=="c" and self.n[v][0]=="c":
   val=(self.n[u][1]&self.n[v][1]) if op=="a" else (self.n[u][1]^self.n[v][1])
   return val
  r=min(self.top(u),self.top(v));ul,uh=self.cof(u,r);vl,vh=self.cof(v,r)
  out=self.mk(("n",r,self.apply(op,ul,vl),self.apply(op,uh,vh)))
  self.cache[key]=out;return out
 def xor(self,*vs):
  x=0
  for v in vs:x=self.apply("x",x,v)
  return x
 def neg(self,v):return self.apply("x",v,1)
 def and_(self,*vs):
  x=1
  for v in vs:x=self.apply("a",x,v)
  return x
 def sha(self,v):
  m={}
  def f(i):
   if i not in m:
    n=self.n[i]
    if n[0]=="c":payload="c"+str(n[1])
    else:payload="n"+self.names[n[1]]+":"+f(n[2])+":"+f(n[3])
    m[i]=hashlib.sha256(payload.encode()).hexdigest()
   return m[i]
  return f(v)
def cl(x):
 x%=2
 return "clifford" if x%Fraction(1,2)==0 else "t" if x%Fraction(1,4)==0 else "rotation"
def main():
 p=argparse.ArgumentParser();p.add_argument("--baseline",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit("baseline SHA mismatch: "+sha)
 lines=raw.decode().splitlines();d=D();q={f"q{i}":(d.v(f"q{i}") if i<22 else d.z) for i in reversed(range(22))};q.update({f"q{i}":d.z for i in range(22,62)});b={};stack=[];terms=[];ops=collections.Counter()
 def Q(s):return q.setdefault(s,d.v(s))
 def B(s):return b.setdefault(s,d.z)
 def ph(pr,x,ln,target):terms.append((pr,x if isinstance(x,Fraction) else Fraction(Decimal(x)),ln,target))
 for ln,s0 in enumerate(lines,1):
  s=s0.strip()
  if not s or s.startswith("#") or s.startswith("//"):continue
  t=s.split();op=t[0].upper();ops[op]+=1
  if op in ("APPEND_TO_REGISTER","REGISTER"):continue
  if op=="PUSH_CONDITION":
   if len(t)<3 or t[1].lower()!="if" or not BR.fullmatch(t[2]):raise ValueError(f"condition {ln}: {s}")
   stack.append(B(t[2]));continue
  if op=="POP_CONDITION":
   if not stack:raise ValueError(f"condition underflow {ln}")
   stack.pop();continue
  cond=d.o;low=[x.lower() for x in t]
  if op=="NEG":
   if "if" in low:
    j=low.index("if")
    if j+1==len(t) or not BR.fullmatch(t[j+1]):raise ValueError(f"NEG condition {ln}")
    cond=B(t[j+1])
   for x in stack:cond=d.and_(cond,x)
   ph(cond,Fraction(1),ln,"global")
   continue
  if "if" in low:
   j=low.index("if")
   if j+1==len(t) or not BR.fullmatch(t[j+1]):raise ValueError(f"inline condition {ln}")
   cond=B(t[j+1])
  for x in stack:cond=d.and_(cond,x)
  if op in ("BIT_INVERT","BIT_STORE0","BIT_STORE1"):
   name=t[1]
   if op=="BIT_INVERT":b[name]=d.xor(B(name),cond)
   else:
    value=d.o if op=="BIT_STORE1" else d.z
    b[name]=value if cond==d.o else d.xor(d.and_(cond,value),d.and_(d.neg(cond),B(name)))
   continue
  args=[x for x in t[1:] if x.lower()!="if" and not BR.fullmatch(x)]
  qs=[x for x in args if QR.fullmatch(x)];vs=[Q(x) for x in qs]
  def need(n):
   if len(qs)!=n:raise ValueError(f"operands {ln}: {s}")
  if op=="R":
   need(1)
   if cond!=d.o:raise ValueError(f"conditional reset {ln}")
   q[qs[0]]=d.z
  elif op in ("X","Y"):
   need(1);q[qs[0]]=d.xor(vs[0],cond)
  elif op in ("CX","CNOT"):
   need(2);q[qs[1]]=d.xor(vs[1],d.and_(cond,vs[0]))
  elif op=="CCX":
   need(3);q[qs[2]]=d.xor(vs[2],d.and_(cond,vs[0],vs[1]))
  elif op=="SWAP":
   need(2);e=d.and_(cond,d.xor(*vs));q[qs[0]]=d.xor(vs[0],e);q[qs[1]]=d.xor(vs[1],e)
  elif op=="CSWAP":
   need(3);e=d.and_(cond,vs[0],d.xor(vs[1],vs[2]));q[qs[1]]=d.xor(vs[1],e);q[qs[2]]=d.xor(vs[2],e)
  elif op in ("Z","S","S_DAG","T","T_DAG"):
   need(1);u={"Z":Fraction(1),"S":Fraction(1,2),"S_DAG":Fraction(-1,2),"T":Fraction(1,4),"T_DAG":Fraction(-1,4)}[op];ph(d.and_(cond,vs[0]),u,ln,qs[0])
  elif op=="Z_POW":
   need(1);u=next((x for x in args if not QR.fullmatch(x)),None)
   if u is None:raise ValueError(f"missing phase angle {ln}")
   ph(d.and_(cond,vs[0]),u,ln,qs[0])
  elif op=="CZ":
   need(2);ph(d.and_(cond,*vs),Fraction(1),ln,",".join(qs))
  elif op=="CCZ":
   need(3);ph(d.and_(cond,*vs),Fraction(1),ln,",".join(qs))
  elif op=="HMR":
   need(1)
   out=next((x for x in t[1:] if BR.fullmatch(x)),None)
   if out is None:raise ValueError(f"HMR output {ln}")
   m=d.v("measurement:"+out+":"+str(ln));oldb=B(out)
   ph(d.and_(cond,vs[0],m),Fraction(1),ln,qs[0])
   b[out]=d.xor(d.and_(cond,m),d.and_(d.neg(cond),oldb))
   q[qs[0]]=d.and_(d.neg(cond),vs[0])
  elif op=="I":pass
  else:raise ValueError(f"unsupported opcode {op} line {ln}")
 zpow=[x for x in terms if lines[x[2]-1].strip().upper().startswith("Z_POW ")]
 groups=collections.defaultdict(list)
 for x in zpow:groups[x[0]].append(x)
 rows=[];before=sum(cl(x[1])=="rotation" for x in zpow);after=0
 for pred,xs in groups.items():
  total=sum((x[1] for x in xs),Fraction())%2;after+=cl(total)=="rotation"
  if len(xs)>1:rows.append({"predicate_sha256":d.sha(pred),"sites":[{"line":x[2],"target":x[3],"angle_half_turns":str(x[1])} for x in xs],"sum_half_turns_mod_2":str(total),"combined_class":cl(total),"rotation_count_before":sum(cl(x[1])=="rotation" for x in xs),"rotation_count_after":int(cl(total)=="rotation")})
 out={"experiment":"K127","status":"DUPLICATES_FOUND" if rows else "NO_EXACT_PHASE_FACTORS","baseline_sha256":sha,"source_lines":len(lines),"tracked_opcodes":dict(sorted(ops.items())),"z_pow_sites":len(zpow),"distinct_z_pow_predicates":len(groups),"duplicate_predicate_groups":rows,"rotations_before":before,"rotations_after_folding":after,"max_rotation_reduction":before-after,"bdd_nodes":len(d.n),"symbolic_variables":len(d.names),"limitations":["Canonical exact XOR/AND DAG does not expand distributive ANF identities.","Read-only screen; any rewrite requires official verifier validation.","Tracks computational-basis dataflow through reversible Boolean gates and HMR resets; unsupported operations abort."]}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+"\n")
 print("K127_RESULT",json.dumps({k:out[k] for k in ("status","baseline_sha256","source_lines","z_pow_sites","distinct_z_pow_predicates","duplicate_predicate_groups","rotations_before","rotations_after_folding","max_rotation_reduction")}))
if __name__=="__main__":main()
