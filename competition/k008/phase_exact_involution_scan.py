#!/usr/bin/env python3
"""K008 — phase-exact, barrier-aware kickmix involution cancellation.

All rewrite rules are exact operator equalities on every state, including
entangled inputs. The optimizer only handles X, CX, CCX, Z, CZ, CCZ and
CSWAP with bare qN operands. It does NOT cross measurements, R/HMR,
Z_POW, control scopes, INFO_TAGs, registration or unknown instructions.

Commutation proof for supported gates:
* XOR-target gates with controls C and target t commute when neither
  modifies a control of the other. Identical gates always commute.
* Diagonal Z/CZ/CCZ gates commute with all other diagonal gates and with
  XOR-target gates if the XOR target is outside the diagonal's support.
* CSWAP is passed only by identical operations or operations on entirely
  disjoint qubits. Conservative but safe.
Every supported gate squares to identity. We cancel two identical gates
if all intervening operations commute with the later gate.
"""
import argparse,collections,hashlib,json,re,sys,traceback
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIVATE=(HERE/"../k001/private").resolve()
SOURCE=PRIVATE/"official/sample_submission/invsqrt.kmb"
ORIG_KMX=PRIVATE/"runs/k005/reference_roundtrip.kmx"
OUT_DIR=PRIVATE/"runs/k008"
REPORT=HERE/"k008_optimizer_report.json"
ARITY={"X":1,"CX":2,"CCX":3,"Z":1,"CZ":2,"CCZ":3,"CSWAP":3}
REGEX=re.compile(r"^([A-Z_]+)(?:\s+(q[0-9]+))?(?:\s+(q[0-9]+))?(?:\s+(q[0-9]+))?\s*$")
DIAGONAL={"Z","CZ","CCZ"}
XOR={"X","CX","CCX"}
SWAPS={"CSWAP"}

def parse(line):
 if line!=line.lstrip():return None
 m=REGEX.fullmatch(line.strip())
 if m is None:return None
 op=m.group(1)
 if op not in ARITY:return None
 qs=tuple(q for q in m.groups()[1:] if q is not None)
 if len(qs)!=ARITY[op] or len(set(qs))!=len(qs):return None
 # Reordering controls for CX/CCX and CZ is equivalent mathematically,
 # but keep the exact written order for the initial conservative pass.
 return (op,qs)

def commutes(a,b):
 if a==b:return True
 op1,q1=a;op2,q2=b
 s1=set(q1);s2=set(q2)
 if op1 in SWAPS or op2 in SWAPS:
  return s1.isdisjoint(s2)
 if op1 in DIAGONAL and op2 in DIAGONAL:return True
 if op1 in XOR and op2 in XOR:
  return q1[-1] not in q2[:-1] and q2[-1] not in q1[:-1]
 if op1 in XOR and op2 in DIAGONAL:return q1[-1] not in s2
 if op1 in DIAGONAL and op2 in XOR:return q2[-1] not in s1
 raise AssertionError((a,b))

def optimize_segment(segment,window):
 stack=[];counts=collections.Counter()
 for line,gate in segment:
  found=None
  for i in range(len(stack)-1,max(-1,len(stack)-window-1),-1):
   earlier=stack[i][1]
   if earlier==gate:
    found=i
    break
   if not commutes(earlier,gate):break
  if found is None:stack.append((line,gate))
  else:
   counts[gate[0]]+=1
   stack.pop(found)
 return [line for line,_ in stack],counts

def optimize(text,window):
 lines=text.splitlines(keepends=True)
 output=[];segment=[];removed=collections.Counter()
 syntax=collections.Counter();recognized=collections.Counter()
 segments=0
 def flush():
  nonlocal segments
  if not segment:return
  remaining,c=optimize_segment(segment,window)
  output.extend(remaining);removed.update(c);segment.clear();segments+=1
 for line in lines:
  token=line.strip().split(maxsplit=1)
  if token:syntax[token[0]]+=1
  g=parse(line)
  if g is None:
   flush();output.append(line)
  else:
   recognized[g[0]]+=1
   segment.append((line,g))
 flush()
 return "".join(output),{"recognized":dict(sorted(recognized.items())),
  "cancelled_pairs":dict(sorted(removed.items())),
  "cancelled_pairs_total":sum(removed.values()),
  "removed_instructions":2*sum(removed.values()),
  "recognized_gates_total":sum(recognized.values()),
  "segments":segments,
  "source_instruction_tokens":dict(syntax.most_common(30)),
  "original_lines":len(lines),
  "optimized_lines":len(lines)-2*sum(removed.values())}

def file_sha(path):
 with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def stats(c):
 o=c.operation_statistics()
 return {"instructions":int(o.num_instructions),
    "toffoli_like":int(o.num_toffoli_like),"t_like":int(o.num_t_like),
    "qubits":int(c.num_qubits),"bits":int(c.num_bits),
    "reaction_depth":int(c.reaction_depth())}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--window",type=int,default=512)
 p.add_argument("--report",default=str(REPORT))
 a=p.parse_args()
 if a.window<1:p.error("--window must be positive")
 import kickmix as km
 OUT_DIR.mkdir(parents=True,exist_ok=True)
 report=Path(a.report);report.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"K008_PHASE_EXACT_INVOLUTION_SCAN",
    "status":"IN_PROGRESS","submitted":False,"verifier_passed":False,
    "proof_scope":"X,CX,CCX,Z,CZ,CCZ,CSWAP involutions; hard boundaries for everything else",
    "limitations":["No equivalence claim across any measurement or conditional boundary",
                   "Local reduction in operations alone does not imply lower Q times C score",
                   "Official verifier must independently confirm candidate correctness"]}
 def save():report.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  if not SOURCE.is_file():raise FileNotFoundError(SOURCE)
  d["reference_sha256"]=file_sha(SOURCE)
  ref=km.Circuit.from_file(str(SOURCE))
  d["reference_stats"]=stats(ref)
  if not ORIG_KMX.is_file():
   ORIG_KMX.parent.mkdir(parents=True,exist_ok=True)
   ref.to_file(str(ORIG_KMX),format="kmx")
  source=ORIG_KMX.read_text(encoding="utf-8")
  rewritten,audit=optimize(source,a.window)
  d["audit"]=audit
  if audit["recognized_gates_total"]<10000:raise AssertionError("Unexpectedly few parsed gates")
  kmx=OUT_DIR/"candidate.kmx"
  kmx.write_text(rewritten,encoding="utf-8")
  candidate=km.Circuit.from_file(str(kmx),format="kmx")
  d["candidate_stats"]=stats(candidate)
  kmb=OUT_DIR/"candidate.kmb"
  candidate.to_file(str(kmb),format="kmb")
  d["candidate_kmb_sha256"]=file_sha(kmb)
  d["candidate_path"]=str(kmb)
  if file_sha(SOURCE)!=d["reference_sha256"]:raise AssertionError("Official reference changed")
  if d["reference_stats"]["qubits"]!=d["candidate_stats"]["qubits"] or d["reference_stats"]["bits"]!=d["candidate_stats"]["bits"]:
   raise AssertionError("Register dimensions changed")
  if audit["removed_instructions"]!=d["reference_stats"]["instructions"]-d["candidate_stats"]["instructions"]:
   raise AssertionError("Instruction delta disagrees with removal audit")
  d["status"]="PENDING_OFFICIAL_VERIFIER" if audit["cancelled_pairs_total"] else "PASS_NO_CANCELLATIONS"
  save()
  print("K008 RECOGNIZED",audit["recognized"],flush=True)
  print("K008 CANCELLED",audit["cancelled_pairs"],"TOTAL",audit["cancelled_pairs_total"],flush=True)
  print("K008 REFERENCE",d["reference_stats"],flush=True)
  print("K008 CANDIDATE",d["candidate_stats"],flush=True)
  print("K008 PATH",kmb,flush=True)
  print("K008 STATUS",d["status"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-6000:]
  save();raise
if __name__=="__main__":main()
