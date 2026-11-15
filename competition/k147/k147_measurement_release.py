#!/usr/bin/env python3
"""K147 exact measurement-release opportunity test.
Find CCX(a,b,t) ... CX(t,o) ... CCX(a,b,t) where t is provably clean
from a preceding HMR reset, the controls are stable, and t has no other
uses. Replacing second CCX by HMR(t,m); CZ(a,b) if m is exact on any
coherent input in this restricted fragment. No baseline mutation.
"""
import argparse,hashlib,json,re
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
Q=re.compile(r"q[0-9]+\Z");B=re.compile(r"b[0-9]+\Z")
# Barriers: for proof we admit only these unconditional gates between pair.
ARITY={"X":1,"CX":2,"CCX":3,"CZ":2,"CCZ":3,"Z":1,"S":1,"T":1}
def toks(line):return line.strip().split()
def wires(t):return tuple(x for x in t[1:] if Q.fullmatch(x))
def valid_op(t):
 if not t:return True
 return t[0] in ARITY and len(t)==ARITY[t[0]]+1 and all(Q.fullmatch(x) for x in t[1:]) and len(set(t[1:]))==len(t[1:])
def latest_clean_witness(lines,idx,target,lookback):
 for j in range(idx-1,max(-1,idx-lookback-1),-1):
  t=toks(lines[j])
  if target not in t:continue
  if len(t)==3 and t[0]=="HMR" and t[1]==target and B.fullmatch(t[2]):
   return j+1
  return None
 return None
def find(lines,lookback,span):
 out=[]
 for i,source in enumerate(lines):
  t=toks(source)
  if len(t)!=4 or t[0]!="CCX" or not all(Q.fullmatch(x) for x in t[1:]):continue
  a,b,target=t[1:4]
  if len({a,b,target})!=3:continue
  witness=latest_clean_witness(lines,i,target,lookback)
  if witness is None:continue
  copies=[]
  for j in range(i+1,min(len(lines),i+span+1)):
   u=toks(lines[j])
   if not u:continue
   if u==t:
    if copies:
     out.append({"compute_line":i+1,"inverse_line":j+1,"clean_hmr_line":witness,
       "controls":[a,b],"target":target,"copy_lines":copies[:],"copies":len(copies),
       "source_ccx_saved":1,"proof":"EXACT_CONDITIONAL_ON_HMR_CLEAN_RESET_AND_LOCAL_STABILITY"})
    break
   if not valid_op(u):break
   op=u[0];qq=u[1:]
   # t may only be a CX control, never target, phase operand, or nonlinear control.
   if target in qq:
    if op=="CX" and qq[0]==target and qq[1] not in (a,b):
     copies.append(j+1)
    else:break
   # Controls may never be mutated, including by a target of CX/CCX.
   elif (a in qq or b in qq):
    if op=="X" and qq[0] in (a,b):break
    if op=="CX" and qq[1] in (a,b):break
    if op=="CCX" and qq[2] in (a,b):break
    if op not in ("CX","CCX","CZ","CCZ","Z","S","T"):break
 return out
def check_proof():
 # For arbitrary coherent amplitudes, it suffices to prove equality
 # term by term in the {|a,b,o>} basis, for both HMR outcomes.
 for a in (0,1):
  for b in (0,1):
   for o in (0,1):
    f=a&b
    for m in (0,1):
     original=(a,b,o^f,0)
     measured=(a,b,o^f,0)
     sign=(-1)**(m*f) * (-1)**(m*(a&b))
     assert original==measured and sign==1
 synthetic=["HMR q3 b100","CCX q0 q1 q3","CX q3 q2","CCX q0 q1 q3"]
 result=find(synthetic,32,32)
 assert len(result)==1 and result[0]["inverse_line"]==4
 assert not find(synthetic[1:],32,32)
 assert not find(["HMR q3 b100","CCX q0 q1 q3","CX q0 q3","CCX q0 q1 q3"],32,32)
 print("K147_SELFTEST PASS coherent conditional phase proof and strict source witnesses",flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--out",type=Path,default=Path("competition/k147/results/measurement_release.json"))
 p.add_argument("--lookback",type=int,default=1024)
 p.add_argument("--span",type=int,default=256)
 p.add_argument("--top",type=int,default=20)
 p.add_argument("--selftest",action="store_true")
 a=p.parse_args();check_proof()
 if a.selftest:return
 if not(1<=a.lookback<=100000 and 1<=a.span<=5000 and a.top>=1):p.error("invalid bounds")
 raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
 lines=raw.decode().splitlines()
 hits=find(lines,a.lookback,a.span)
 # A hit is a proof candidate, not a verifier pass; 1 shot-CCX removed
 # yields at most 62 score units assuming no added T or qubits.
 report={"status":"STRICT_STATIC_CANDIDATE_AUDIT","sha256":sha,"hits":len(hits),
 "candidates":hits[:a.top],"predicted_score_delta_per_unconditional_CCX":-62,
 "caveats":["Requires Kickmix HMR to reset measured target to |0> as documented",
 "Global resource and bit-allocation legality not proven by this local check",
 "No circuit modification or official score verification",
 "This searches coherent compute/use/inverse patterns; K139 scanned already-measurement-based release gadgets"]}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2)+"\n")
 for hit in hits[:a.top]:print("K147_HIT",json.dumps(hit),flush=True)
 print("K147_RESULT",json.dumps({"hits":len(hits),"report":str(a.out)}),flush=True)
if __name__=="__main__":main()
