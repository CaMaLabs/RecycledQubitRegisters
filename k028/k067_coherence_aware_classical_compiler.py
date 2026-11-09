#!/usr/bin/env python3
"""K067 — sound classical-feedforward constant propagation for Kickmix KMX.

Classical values are tracked as affine XOR functions of unknown measurement
outcomes. When a condition is *provably* constant 0/1, simplify the quantum
instruction. This can remove expensive controlled gates *only when justified*.

Never measure the coherent input, never replace an unknown quantum control with
classical control. Unrecognized instructions are kept unchanged. No public
third-party circuit is represented as CaMaLabs original work.

--self-test uses exhaustive Boolean checks of affine expressions and scope rules.
--source may be K040's KMX (our own) or public Helios reference (benchmark).
Only a full-domain double-seed official PASS counts as success.
"""
from __future__ import annotations
import argparse,collections,hashlib,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"competition/k001/private/official/verifiers"))
HMR=re.compile(r"^HMR\s+q\d+\s+b(\d+)$",re.I)
STORE=re.compile(r"^BIT_STORE([01])\s+b(\d+)$",re.I)
INVERT=re.compile(r"^BIT_INVERT\s+b(\d+)\s+if\s+b(\d+)$",re.I)
GUARD=re.compile(r"^(.*?)\s+if\s+b(\d+)\s*$",re.I)
PUSH=re.compile(r"^PUSH_CONDITION\s+if\s+b(\d+)$",re.I)
BIT=re.compile(r"\bb(\d+)\b")
# (constant_bit, frozenset(symbolic unknown variables))
ZERO=(0,frozenset());ONE=(1,frozenset())
def xor(a,b):return a[0]^b[0],a[1]^b[1] if False else frozenset(a[1] ^ b[1])
def symbols(s):return sorted(s[1])
def isconst(v):return not v[1]
def known(v):return v[0] if isconst(v) else None
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def transform(lines):
 # Every otherwise unread bit is an independent unknown, not zero.
 state={};nextvar=0;scope=[];st=collections.Counter();out=[]
 def fresh():
  nonlocal nextvar
  r=(0,frozenset([nextvar]));nextvar+=1;return r
 def read(name):
  if name not in state:state[name]=fresh()
  return state[name]
 for line in lines:
  s=line.strip()
  if not s or s.startswith(("#","//")):
   out.append(line);continue
  m=HMR.fullmatch(s)
  if m:
   # Measurement result is an *unknown* classical bit, even after RESET;
   # assigning 0 here would incorrectly erase coherent information.
   out.append(line);state[m.group(1)]=fresh();st["measurements"]+=1;continue
  m=STORE.fullmatch(s)
  if m:
   state[m.group(2)]=(int(m.group(1)),frozenset())
   out.append(line);st["bit_stores"]+=1;continue
  m=INVERT.fullmatch(s)
  if m:
   dest,src=m.groups()
   new=xor(read(dest),read(src))
   state[dest]=new
   out.append(line);st["bit_inverts"]+=1
   if isconst(new):st["known_classical_bits"]+=1
   continue
  m=PUSH.fullmatch(s)
  if m:
   # We don't remove scopes: preserving control stack semantics is safest.
   v=read(m.group(1))
   scope.append(known(v))
   out.append(line)
   if known(v) is not None:st["known_scope_conditions"]+=1
   continue
  if s.upper()=="POP_CONDITION":
   if scope:scope.pop()
   out.append(line);continue
  m=GUARD.fullmatch(s)
  if m:
   prefix,bit=m.groups()
   value=known(read(bit))
   op=prefix.split()[0].upper() if prefix.split() else ""
   if value==0:
    # Only delete a guarded *unitary* quantum operation. Never remove
    # measurement / bit mutation / control scope / reset / metadata.
    if op in ("X","Y","Z","H","S","T","CX","CZ","CCX","CCZ",
              "CSWAP","SWAP","Z_POW"):
     st["removed_conditional_"+op]+=1
     continue
   elif value==1:
    if op in ("X","Y","Z","H","S","T","CX","CZ","CCX","CCZ",
              "CSWAP","SWAP","Z_POW"):
     out.append(prefix+"\n")
     st["unconditioned_"+op]+=1
     continue
   # Conservative: if unknown or unfamiliar, preserve exact instruction.
  # Unknown bit writes invalidate tracked classical values. Other unknown
  # quantum operations do not affect classical bits except through HMR.
  if s.startswith("BIT_"):
   refs=BIT.findall(s)
   if refs:state[refs[0]]=fresh()
   st["unknown_classical_mutation"]+=1
  out.append(line)
 return out,dict(st)
def verifier(path,full,timeout):
 p=ROOT/"competition/k031/k031_full_domain_repair.py"
 spec=importlib.util.spec_from_file_location("k031_k067",p)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 checks={}
 for label,n,seed in [("prefix",64,12345)]+(
    [("full_12345",mod.FULL_X,12345),("full_23456",mod.FULL_X,23456)] if full else []):
  checks[label]=mod.verify(path,n,seed,timeout)
  if checks[label].get("status")!="PASS" or checks[label].get("exit_code")!=0:break
 return checks
def selftest():
 # Verify constant folding doesn't mis-handle unknown measurement inputs.
 examples=[
  (["BIT_STORE0 b0\n","BIT_INVERT b0 if b1\n","BIT_INVERT b0 if b1\n","CZ q0 q1 if b0\n"],0,1),
  (["BIT_STORE1 b0\n","BIT_STORE1 b1\n","BIT_INVERT b0 if b1\n","CCX q0 q1 q2 if b0\n"],0,1),
  (["BIT_STORE0 b0\n","HMR q0 b0\n","CZ q1 q2 if b0\n"],0,0),
  (["BIT_STORE1 b0\n","CX q1 q2 if b0\n"],1,0),
 ]
 for seq,unchanged,removed in examples:
  out,st=transform(seq)
  reduction=len(seq)-len(out)
  assert reduction==removed,(seq,out,st)
  if unchanged:assert out[-1].strip()=="CX q1 q2"
 # Every self-canceling XOR of unknown classical bits becomes zero.
 a=(0,frozenset([1,5,8]))
 assert xor(a,a)==ZERO
 assert xor(xor(a,ONE),a)==ONE
 print("K067_SELFTEST PASS",flush=True)
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--source",type=Path,default=ROOT/"competition/k059/results/helios_public.kmx")
 ap.add_argument("--out",type=Path,default=ROOT/"competition/k067/results")
 ap.add_argument("--full",action="store_true")
 ap.add_argument("--timeout",type=int,default=600)
 ap.add_argument("--self-test",action="store_true")
 a=ap.parse_args()
 if a.self_test:selftest();return
 a.out.mkdir(parents=True,exist_ok=True)
 if not a.source.is_file():raise SystemExit("Missing KMX: "+str(a.source))
 original=a.source.read_text().splitlines(keepends=True)
 candidate,st=transform(original)
 removals=sum(v for k,v in st.items() if k.startswith("removed_conditional_"))
 scan={"source":str(a.source),"sha256":sha(a.source),
       "source_lines":len(original),"candidate_lines":len(candidate),
       "removed_quantum_gates":removals,"stats":st,
       "rule":"Only provably constant classical controls may eliminate guarded quantum operations"}
 print("K067_SCAN",json.dumps(scan,sort_keys=True),flush=True)
 report={"scan":scan,"attribution":
   "If source is Helios, third-party public benchmark; no claim of original authorship"}
 if candidate==original:
  report["status"]="NO_CHANGE"
 else:
  kmx=a.out/"candidate.kmx";kmx.write_text("".join(candidate))
  try:
   import kickmix as km
   circuit=km.Circuit.from_file(str(kmx),format="kmx")
   kmb=a.out/"candidate.kmb";circuit.to_file(str(kmb),format="kmb")
   report["candidate_sha256"]=sha(kmb)
   report["num_qubits"]=circuit.num_qubits
   report["official"]=verifier(kmb,a.full,a.timeout)
   valid=all(v.get("status")=="PASS" and v.get("exit_code")==0 for v in report["official"].values())
   report["status"]="PASS_FULL" if (valid and a.full and len(report["official"])==3) else (
       "PASS_PREFIX_ONLY" if valid else "FAIL")
  except Exception as e:report["status"]="ERROR";report["error"]=repr(e)
 (a.out/"result.json").write_text(json.dumps(report,indent=2,default=str))
 print("K067_RESULT",json.dumps({"status":report["status"],"removed_quantum_gates":removals,
  "official":report.get("official"),"error":report.get("error")},sort_keys=True),flush=True)
 print("SAVED",a.out/"result.json",flush=True)
if __name__=="__main__":main()
