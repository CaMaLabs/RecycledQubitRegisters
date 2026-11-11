#!/usr/bin/env python3
"""K131 exact domain-restricted identity-gate screen before first HMR."""
import argparse,collections,hashlib,json,re
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
MAX_X=3133452;WIDTH=22;QRE=re.compile(r"^q(\d+)$",re.I)
def input_bit(bit,n,mask):
 run=1<<bit;period=run*2;count=(n+period-1)//period
 repeats=((1<<(period*count))-1)//((1<<period)-1)
 return (((1<<run)-1)*repeats << (run-1)) & mask
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--baseline",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);ap.add_argument("--candidate",type=Path);a=ap.parse_args()
 raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit("baseline SHA mismatch: "+sha)
 n=MAX_X;mask=(1<<n)-1;w=[0]*62
 for bit in range(WIDTH):w[bit]=input_bit(bit,n,mask)
 lines=raw.decode().splitlines();removed=[];processed=0;seen=collections.Counter();first_boundary=None
 def qidx(token):return int(token[1:])
 def target_noop(op,qs):
  x=[w[qidx(q)] for q in qs]
  if op=="R":return x[0]==0
  if op=="CX":return x[0]==0
  if op=="CCX":return (x[0]&x[1])==0
  if op=="CZ":return (x[0]&x[1])==0
  if op=="CCZ":return (x[0]&x[1]&x[2])==0
  if op=="CSWAP":return (x[0]&(x[1]^x[2]))==0
  if op=="SWAP":return x[0]==x[1]
  if op in ("Z","S","S_DAG","T","T_DAG","Z_POW"):return x[0]==0
  return False
 for i,line in enumerate(lines):
  s=line.strip()
  if not s or s.startswith("#") or s.startswith("//"):continue
  t=s.split();op=t[0].upper();seen[op]+=1
  if op in ("HMR","PUSH_CONDITION","POP_CONDITION") or " if " in s.lower():
   first_boundary={"line":i+1,"opcode":op,"reason":"stochastic measurement or classical condition"};break
  if op in ("APPEND_TO_REGISTER","REGISTER","NEG","BIT_STORE0","BIT_STORE1","BIT_INVERT","Z","CZ","CCZ","Z_POW","S","S_DAG","T","T_DAG","I"):
   pass
  qs=[x for x in t[1:] if QRE.fullmatch(x)]
  if op=="R" and len(qs)==1:
   if w[qidx(qs[0])]==0:removed.append(i)
   else:w[qidx(qs[0])]=0
  elif op=="X" and len(qs)==1:w[qidx(qs[0])]^=mask
  elif op in ("CX","CNOT") and len(qs)==2:
   if w[qidx(qs[0])]==0:removed.append(i)
   else:w[qidx(qs[1])]^=w[qidx(qs[0])]
  elif op=="CCX" and len(qs)==3:
   c=w[qidx(qs[0])]&w[qidx(qs[1])]
   if c==0:removed.append(i)
   else:w[qidx(qs[2])]^=c
  elif op=="SWAP" and len(qs)==2:
   if w[qidx(qs[0])]==w[qidx(qs[1])]:removed.append(i)
   else:w[qidx(qs[0])],w[qidx(qs[1])]=w[qidx(qs[1])],w[qidx(qs[0])]
  elif op=="CSWAP" and len(qs)==3:
   c=w[qidx(qs[0])];d=c&(w[qidx(qs[1])]^w[qidx(qs[2])])
   if d==0:removed.append(i)
   else:w[qidx(qs[1])]^=d;w[qidx(qs[2])]^=d
  elif op=="Y" and len(qs)==1:w[qidx(qs[0])]^=mask
  elif op in ("Z","S","S_DAG","T","T_DAG","Z_POW") and len(qs)==1:
   if w[qidx(qs[0])]==0:removed.append(i)
  elif op in ("CZ","CCZ") and len(qs)==(2 if op=="CZ" else 3):
   if target_noop(op,qs):removed.append(i)
  elif op in ("APPEND_TO_REGISTER","REGISTER","NEG","BIT_STORE0","BIT_STORE1","BIT_INVERT","I"):
   pass
  else:
   raise ValueError(f"unsupported prefix opcode line {i+1}: {s}")
  processed+=1
 score_gates=sum(lines[i].strip().split()[0].upper() in ("CCX","CCZ","CSWAP") for i in removed)
 result={"experiment":"K131","status":"IDENTITY_GATES_FOUND" if removed else "NO_DOMAIN_IDENTITY_GATES","baseline_sha256":sha,"domain":{"x_min":1,"x_max":MAX_X,"values_exhaustively_simulated":n,"input_width":WIDTH},"deterministic_prefix_operations":processed,"stopped_before":first_boundary,"identity_gate_count":len(removed),"removed_source_lines":[i+1 for i in removed],"removed_toffoli_class_count":score_gates,"exact_score_reduction_if_candidate_passes":62*score_gates,"candidate_generated":False,"method":"Packed Python-integer truth tables over every valid x; reversible basis-state dataflow is exact before first HMR/condition.","limitations":["This only screens the deterministic prefix before the first measurement or classical condition.","No approximation is used; every valid x is represented exactly.","Official full-domain verifier remains required for any emitted candidate."]}
 if removed and a.candidate:
  remove=set(removed);a.candidate.parent.mkdir(parents=True,exist_ok=True);a.candidate.write_text("\n".join(line for i,line in enumerate(lines) if i not in remove)+"\n");result["candidate_generated"]=True;result["candidate_path"]=str(a.candidate)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n")
 print("K131_RESULT",json.dumps({k:result[k] for k in ("status","baseline_sha256","domain","deterministic_prefix_operations","stopped_before","identity_gate_count","removed_toffoli_class_count","exact_score_reduction_if_candidate_passes","removed_source_lines","candidate_generated")}))
if __name__=="__main__":main()
