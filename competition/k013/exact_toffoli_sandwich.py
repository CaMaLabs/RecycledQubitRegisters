#!/usr/bin/env python3
"""K013: exact arithmetic identity rewrite plus matched official verification.

Recognize only contiguous, unconditional X/CX/CCX triple windows inside
official kickmix KMx. For CCX(a,b,t) ; G ; CCX(a,b,t), with G toggling
one CCX control using the other, or G=X on a control, replace BOTH
Toffolis with a single CX onto t while retaining G.

These are full-unitary permutation identities, not truth-table shortcuts
for one input. Verify each rule exhaustively across all basis states
BEFORE scanning the official circuit. No changes across phase, HMR/R,
metadata, conditional scopes, registration or any unknown operation.

After a nonzero rewrite, independently verify the candidate using Google's
official invsqrt verifier in a bounded matched-seed smoke A/B.
Do not claim full contest validation or submit.
"""
import argparse,collections,hashlib,json,subprocess,sys,time,traceback,re
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIVATE=(HERE/"../k001/private").resolve()
KMX=PRIVATE/"runs/k005/reference_roundtrip.kmx"
REF=PRIVATE/"official/sample_submission/invsqrt.kmb"
VERIFY=PRIVATE/"official/verifiers/invsqrt/verify_submission_invsqrt.py"
RUN=PRIVATE/"runs/k013"
REPORT=HERE/"k013_exact_arithmetic_rewrite.json"
GATE=re.compile(r"^(X|CX|CCX)\s+(q\d+)(?:\s+(q\d+))?(?:\s+(q\d+))?\s*$")
ARITY={"X":1,"CX":2,"CCX":3}
def parse(line):
 if line!=line.lstrip():return None
 m=GATE.fullmatch(line.strip())
 if not m:return None
 g=m.group(1);q=tuple(x for x in m.groups()[1:] if x)
 return (g,q) if len(q)==ARITY[g] and len(set(q))==len(q) else None
def apply(g,bits):
 op,qs=g; a=[bits[q] for q in qs]
 if op=="X":bits[qs[0]]^=1
 elif op=="CX":bits[qs[1]]^=a[0]
 elif op=="CCX":bits[qs[2]]^=a[0]&a[1]
 else:raise ValueError(op)
def same_unitary(original,replacement):
 wires=sorted({q for _,qs in original+replacement for q in qs})
 assert len(wires)<=4
 for mask in range(1<<len(wires)):
  state={q:(mask>>i)&1 for i,q in enumerate(wires)}
  aa=state.copy();bb=state.copy()
  for g in original:apply(g,aa)
  for g in replacement:apply(g,bb)
  if aa!=bb:return False
 return True
def replacement(triple):
 a,g,c=triple
 if a[0]!="CCX" or c[0]!="CCX" or a!=c:return None
 A,B,T=a[1]
 if g==("X",(A,)):return [g,("CX",(B,T))]
 if g==("X",(B,)):return [g,("CX",(A,T))]
 if g==("CX",(A,B)):return [g,("CX",(A,T))]
 if g==("CX",(B,A)):return [g,("CX",(B,T))]
 return None
def prove_rules():
 cases=0
 for a,b,t in [("q0","q1","q2"),("q2","q0","q1"),("q4","q8","q15")]:
  ccx=("CCX",(a,b,t))
  for mid in [("X",(a,)),("X",(b,)),("CX",(a,b)),("CX",(b,a))]:
   triple=[ccx,mid,ccx]
   repl=replacement(triple)
   assert repl is not None and same_unitary(triple,repl),(triple,repl)
   cases+=1
 return cases
def digest(path):
 with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def stats(c):
 o=c.operation_statistics()
 return {"instructions":int(o.num_instructions),"toffoli_like":int(o.num_toffoli_like),
   "t_like":int(o.num_t_like),"qubits":int(c.num_qubits),
   "bits":int(c.num_bits),"reaction_depth":int(c.reaction_depth())}
def run_verifier(path,shots,max_x,batch,seed,timeout):
 cmd=[sys.executable,str(VERIFY),str(path),"--format","kmb","--shots-per-x",str(shots),
      "--max-x",str(max_x),"--batch-size",str(batch),"--max-workers","1","--seed",str(seed)]
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,check=False,
                   cwd=str(VERIFY.parent))
  try:data=json.loads(p.stdout)
  except json.JSONDecodeError:data={"parse_error":p.stdout[-1200:]}
  return {"exit_code":p.returncode,"output":data,"stderr_tail":p.stderr[-1500:],
          "pass":p.returncode==0 and data.get("status")=="PASS"}
 except subprocess.TimeoutExpired:
  return {"pass":False,"timeout":True}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--shots-per-x",type=int,default=2)
 p.add_argument("--max-x",type=int,default=8)
 p.add_argument("--batch-size",type=int,default=16)
 p.add_argument("--seed",type=int,default=12345)
 p.add_argument("--timeout",type=int,default=180)
 p.add_argument("--report",default=str(REPORT))
 a=p.parse_args()
 if min(a.shots_per_x,a.max_x,a.batch_size,a.timeout)<1 or (a.shots_per_x*a.max_x)%a.batch_size:
  p.error("invalid shots or batch size")
 if not KMX.is_file() or not REF.is_file() or not VERIFY.is_file():
  p.error("K001/K005 official assets are missing")
 RUN.mkdir(parents=True,exist_ok=True)
 import kickmix as km
 d={"experiment":"K013_EXACT_TOFFOLI_SANDWICH_REWRITE",
   "status":"STARTED","submitted":False,"official_full_benchmark":False,
   "rewrites_cross_feedback":False,"rules_exhaustively_proved":False}
 report=Path(a.report);report.parent.mkdir(parents=True,exist_ok=True)
 def save():report.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  d["unitary_proof_instances"]=prove_rules()
  d["rules_exhaustively_proved"]=True
  before=digest(REF)
  original=km.Circuit.from_file(str(REF))
  d["baseline_stats"]=stats(original)
  lines=KMX.read_text(encoding="utf-8").splitlines(keepends=True)
  rewritten=[];i=0;hits=collections.Counter();recognized=0
  while i<len(lines):
   cur=parse(lines[i])
   if cur is not None:recognized+=1
   if i+2<len(lines):
    trip=[parse(lines[i+j]) for j in range(3)]
    if all(x is not None for x in trip):
     repl=replacement(trip)
     if repl:
      if not same_unitary(trip,repl):raise AssertionError("Unproven source rewrite")
      rewritten.extend([g+" "+" ".join(q)+"\n" for g,q in repl])
      hits[trip[1][0]]+=1
      i+=3;continue
   rewritten.append(lines[i]);i+=1
  d["recognized_gates"]=recognized
  d["matches"]=dict(hits);d["total_rewrites"]=sum(hits.values())
  print("K013 EXHAUSTIVE IDENTITIES",d["unitary_proof_instances"],flush=True)
  print("K013 MATCHES",d["matches"],"TOTAL",d["total_rewrites"],flush=True)
  if d["total_rewrites"]==0:
   d["status"]="PASS_NO_EXACT_TEMPLATE_MATCHES"
   save();print("K013 STATUS",d["status"],flush=True);return
  kmx=RUN/"candidate.kmx";kmx.write_text("".join(rewritten),encoding="utf-8")
  c=km.Circuit.from_file(str(kmx),format="kmx")
  kmb=RUN/"candidate.kmb";c.to_file(str(kmb),format="kmb")
  d["candidate_stats"]=stats(c)
  d["candidate_path"]=str(kmb);d["candidate_sha256"]=digest(kmb)
  if d["candidate_stats"]["qubits"]!=d["baseline_stats"]["qubits"]:
   raise AssertionError("Qubits changed")
  if d["candidate_stats"]["toffoli_like"]!=d["baseline_stats"]["toffoli_like"]-2*d["total_rewrites"]:
   raise AssertionError("Toffoli reduction mismatch")
  if digest(REF)!=before:raise AssertionError("Official sample modified")
  print("K013 REFERENCE",d["baseline_stats"],flush=True)
  print("K013 CANDIDATE",d["candidate_stats"],flush=True)
  print("K013 RUNNING OFFICIAL MATCHED VERIFIER...",flush=True)
  d["baseline_verification"]=run_verifier(REF,a.shots_per_x,a.max_x,a.batch_size,a.seed,a.timeout)
  save()
  if not d["baseline_verification"]["pass"]:
   d["status"]="FAIL_BASELINE";save();print("K013 STATUS",d["status"]);return
  d["candidate_verification"]=run_verifier(kmb,a.shots_per_x,a.max_x,a.batch_size,a.seed,a.timeout)
  bb=d["baseline_verification"]["output"];cc=d["candidate_verification"]["output"]
  d["score_delta"]=cc.get("score",float("nan"))-bb.get("score",float("nan"))
  if not d["candidate_verification"]["pass"]:d["status"]="FAIL_CANDIDATE"
  elif d["score_delta"]<0:d["status"]="PASS_OFFICIAL_SMOKE_SCORE_WIN"
  else:d["status"]="PASS_OFFICIAL_SMOKE_NO_SCORE_WIN"
  save();print("K013 SCORE",bb.get("score"),cc.get("score"),"DELTA",d["score_delta"])
  print("K013 STATUS",d["status"],"REPORT",report)
 except Exception:
  d["status"]="ERROR";d["trace"]=traceback.format_exc()[-5000:]
  save();raise
if __name__=="__main__":main()
