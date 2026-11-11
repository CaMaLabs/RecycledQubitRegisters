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
  self.n=[];self.i={};self.z=self.mk(("c",0));self.o=self.mk(("c",1))
 def mk(self,x):
  if x in self.i:return self.i[x]
  j=len(self.n);self.n.append(x);self.i[x]=j;return j
 def v(self,s):return self.mk(("v",s))
 def xor(self,*vs):
  parity=0;terms=set()
  def add(v):
   nonlocal parity
   n=self.n[v]
   if n[0]=="c":parity^=n[1]
   elif n[0]=="x":
    parity^=n[1]
    for z in n[2]:
     if z in terms:terms.remove(z)
     else:terms.add(z)
   elif v in terms:terms.remove(v)
   else:terms.add(v)
  for v in vs:add(v)
  terms=tuple(sorted(terms))
  if not terms:return self.o if parity else self.z
  if len(terms)==1 and not parity:return terms[0]
  return self.mk(("x",parity,terms))
 def neg(self,v):return self.xor(v,self.o)
 def and_(self,*vs):
  terms=set()
  for v in vs:
   n=self.n[v]
   if n==("c",0):return self.z
   if n==("c",1):continue
   terms.update(n[1] if n[0]=="a" else (v,))
  if not terms:return self.o
  if any(self.neg(v) in terms for v in tuple(terms)):return self.z
  terms=tuple(sorted(terms))
  return terms[0] if len(terms)==1 else self.mk(("a",terms))
 def sha(self,v):
  memo={}
  def f(i):
   if i not in memo:
    n=self.n[i]
    if n[0]=="c":s="c"+str(n[1])
    elif n[0]=="v":s="v"+n[1]
    elif n[0]=="x":s="x"+str(n[1])+":".join(sorted(f(z) for z in n[2]))
    else:s="a"+":".join(sorted(f(z) for z in n[1]))
    memo[i]=hashlib.sha256(s.encode()).hexdigest()
   return memo[i]
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
 complements=[];seen=set();old_total=sum(cl(x[1])=="rotation" for x in zpow);projected=old_total
 for pred,xs in groups.items():
  other=d.neg(pred)
  if other not in groups or pred in seen or other==pred:continue
  seen.add(pred);seen.add(other);ys=groups[other]
  a_sum=sum((x[1] for x in xs),Fraction())%2
  b_sum=sum((x[1] for x in ys),Fraction())%2
  delta=(a_sum-b_sum)%2
  old=sum(cl(x[1])=="rotation" for x in xs+ys)
  global_supported=b_sum in (Fraction(0),Fraction(1))
  new=int(cl(delta)=="rotation") if global_supported else old
  if global_supported:projected-=old-new
  complements.append({"predicate_sha256":d.sha(pred),"f_sites":[{"line":x[2],"angle_half_turns":str(x[1])} for x in xs],"not_f_sites":[{"line":x[2],"angle_half_turns":str(x[1])} for x in ys],"constant_half_turns_mod_2":str(b_sum),"constant_supported_by_free_NEG":global_supported,"residual_angle_half_turns_mod_2":str(delta),"rotations_before":old,"rotations_after":new if global_supported else None,"rotation_saving":old-new if global_supported else 0,"candidate":bool(global_supported and old>new)})
 out={"experiment":"K128","status":"SAVING_CANDIDATE_FOUND" if any(x["candidate"] for x in complements) else "NO_COMPLEMENT_PHASE_SAVING","baseline_sha256":sha,"source_lines":len(lines),"tracked_opcodes":dict(sorted(ops.items())),"z_pow_sites":len(zpow),"distinct_z_pow_predicates":len(groups),"duplicate_predicate_groups":rows,"complementary_predicate_pairs":complements,"complement_rotation_count_projected":projected,"max_rotation_reduction":old_total-projected,"rotations_before":before,"rotations_after_folding":after,"max_rotation_reduction":before-after,"limitations":["Canonical exact XOR/AND DAG does not expand distributive ANF identities.","Read-only screen; any rewrite requires official verifier validation.","Tracks computational-basis dataflow through reversible Boolean gates and HMR resets; unsupported operations abort."]}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+"\n")
 print("K128_RESULT",json.dumps({k:out[k] for k in ("status","baseline_sha256","z_pow_sites","complementary_predicate_pairs","max_rotation_reduction")}))
if __name__=="__main__":main()
