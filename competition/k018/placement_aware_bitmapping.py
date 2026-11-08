#!/usr/bin/env python3
"""K018: QRR placement-aware bitmapping / safe active-wire compaction.

Applies QRR's active-only wire mapping idea to the best K016 precision
candidate, with mathematically honest safety gates:
  * identify used qubit slots and qubits in named register declarations;
  * compute a dense bijection over every *used* q-index, maintaining all
    operations and register declarations;
  * ONLY create a candidate if total kickmix qubits actually decrease;
  * verify any candidate against the official Kaggle invsqrt verifier.

General reuse after last reference is NOT automatically safe: untouched
qubits may remain entangled or have to remain allocated until clean;
HMR/R events are NOT generic RESET. This module never attempts to alias
two used qubits merely because their text reference intervals don't overlap.
For documented reset-based reuse, a later semantic allocator should prove
clean-state and no-future-reference constraints before attempting aliasing.

Physical IBM Fez placement is not scored by the kickmix competition.
No QPU jobs, purchases, remote actions or Kaggle submissions.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, re, subprocess, sys, traceback
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIVATE=(HERE/"../k001/private").resolve()
K016=HERE.parent/"k016/k016_precision_search.json"
BASE=PRIVATE/"official/sample_submission/invsqrt.kmb"
VERIFIER=PRIVATE/"official/verifiers/invsqrt/verify_submission_invsqrt.py"
OUTDIR=PRIVATE/"runs/k018"
REPORT=HERE/"k018_bitmapping_audit.json"
QREF=re.compile(r"(?<![A-Za-z0-9_])q(\d+)(?![A-Za-z0-9_])")
OP=re.compile(r"^\s*([A-Z_]+)")
PHASE_SENSITIVE={"HMR","R","CZ","CCZ","Z","Z_POW","PUSH_CONDITION","POP_CONDITION"}
REUSE_EVENTS={"RESET","FREE"}
def sha(path):
 with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def stats(c):
 x=c.operation_statistics()
 return {"qubits":int(c.num_qubits),"bits":int(c.num_bits),
 "instructions":int(x.num_instructions),"toffoli_like":int(x.num_toffoli_like),
 "t_like":int(x.num_t_like),"reaction_depth":int(c.reaction_depth())}
def inspect_text(source):
 first={};last={};counts=collections.Counter();ops=collections.Counter()
 register_owners=collections.defaultdict(set)
 for line_no,line in enumerate(source.splitlines(),1):
  m=OP.match(line)
  name=m.group(1) if m else ""
  ops[name]+=1
  qrefs=[int(s) for s in QREF.findall(line)]
  for q in set(qrefs):
   first.setdefault(q,line_no);last[q]=line_no
   counts[q]+=1
   if name in ("REGISTER","APPEND_TO_REGISTER"):
    register_owners[q].add(name)
 if not first:raise RuntimeError("No used quantum wires found")
 indices=sorted(first)
 # All qubits are included, even qubits only referenced in declaration
 # metadata, so the mapping is a true wire permutation, not a deletion.
 mapping={old:new for new,old in enumerate(indices)}
 # Interval overlap is descriptive only, not a register reuse proof.
 event=collections.Counter()
 for q in indices:
  event[first[q]]+=1
  event[last[q]+1]-=1
 running=peak=peak_at=0
 for line,delta in sorted(event.items()):
  running+=delta
  if running>peak:peak=running;peak_at=line
 gaps=sorted(set(range(max(indices)+1))-set(indices))
 return {"qubit_indices_used":len(indices),"max_original_qubit_index":max(indices),
 "unreferenced_index_holes":len(gaps),"unreferenced_index_holes_preview":gaps[:50],
 "dense_remap_possible":any(k!=v for k,v in mapping.items()),
 "reference_span_overlap_peak":peak,"reference_span_overlap_peak_line":peak_at,
 "operations":dict(ops.most_common()),
 "registered_qubit_count":len(register_owners),
 "phase_sensitive_markers":{x:ops[x] for x in sorted(PHASE_SENSITIVE) if ops[x]},
 "explicit_clean_reset_or_release_markers":{x:ops[x] for x in sorted(REUSE_EVENTS) if ops[x]},
 "frequent_qubit_references":counts.most_common(15),
 "mapping":mapping}
def rewrite(source,mapping):
 # Only exact qN wire tokens are rewritten. Classical bN remain unchanged.
 # Kickmix parser is the arbiter of resulting syntactic validity.
 return QREF.sub(lambda m:"q"+str(mapping[int(m.group(1))]),source)
def verify(path,shots,max_x,seed,timeout):
 total=shots*max_x
 batch=min(total,256)
 while total%batch:batch-=1
 cmd=[sys.executable,str(VERIFIER),str(path),"--format","kmb",
      "--shots-per-x",str(shots),"--max-x",str(max_x),
      "--batch-size",str(batch),"--max-workers","1","--seed",str(seed)]
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,check=False,
      cwd=str(VERIFIER.parent))
  try:res=json.loads(p.stdout)
  except json.JSONDecodeError:res={"parse_error":p.stdout[-1500:]}
  return {"passed":p.returncode==0 and res.get("status")=="PASS",
   "returncode":p.returncode,"result":res,"stderr_tail":p.stderr[-1500:]}
 except subprocess.TimeoutExpired:
  return {"passed":False,"timeout":True}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--case",type=int,default=5)
 p.add_argument("--shots-per-x",type=int,default=2)
 p.add_argument("--max-x",type=int,default=8)
 p.add_argument("--seed",type=int,default=12345)
 p.add_argument("--timeout",type=int,default=180)
 p.add_argument("--report",type=Path,default=REPORT)
 a=p.parse_args()
 if a.case<1 or min(a.shots_per_x,a.max_x,a.timeout)<1:p.error("invalid arguments")
 if not K016.exists() or not BASE.exists() or not VERIFIER.exists():
  p.error("K001/K016 input files missing")
 prior=json.loads(K016.read_text())
 options=[x for x in prior["trials"] if x["case"]==a.case]
 if len(options)!=1 or not options[0].get("path"):
  p.error(f"K016 case {a.case} has no recorded candidate")
 prior_row=options[0]
 candidate=Path(prior_row["path"])
 if not candidate.is_file():p.error(f"Candidate absent: {candidate}")
 if sha(candidate)!=prior_row["sha256"]:p.error("Candidate SHA mismatch")
 import kickmix as km
 OUTDIR.mkdir(parents=True,exist_ok=True)
 report={"experiment":"K018_QRR_PLACEMENT_AWARE_ACTIVE_BITMAPPING",
  "status":"STARTED","case":a.case,
  "source_candidate_sha256":sha(candidate),
  "official_reference_sha256":sha(BASE),
  "kaggle_submitted":False,"full_domain_verified":False,
  "safety_policy":{
   "preserve_all_explicitly_referenced_quantum_wires":True,
   "allow_wire_aliasing_from_first_last_text_reference":False,
   "allow_measured_qubit_reuse_without_reset_proof":False,
   "only_promote_on_lower_actual_qubit_count_and_official_verifier_pass":True},
  "limitations":["A bijective renumbering alone cannot reduce required quantum resources unless there are unused indexed slots",
    "First-last textual reference spans do not prove ancillas are clean, released, or reusable",
    "Native IBM physical routing optimizations have no direct kickmix Q-times-C benefit",
    "A 16-shot verifier pass is only preliminary and not full-domain validation"]}
 def save():
  a.report.parent.mkdir(parents=True,exist_ok=True)
  a.report.write_text(json.dumps(report,indent=2)+"\n")
 save()
 try:
  original=km.Circuit.from_file(str(candidate))
  report["original_stats"]=stats(original)
  kmx=OUTDIR/"original.kmx"
  original.to_file(str(kmx),format="kmx")
  text=kmx.read_text(encoding="utf-8")
  metadata=inspect_text(text)
  mapping=metadata.pop("mapping")
  report["bitmapping"]=metadata
  if len(mapping)!=report["original_stats"]["qubits"]:
   report["status"]="NO_SAFE_COMPACTION_REFERENCED_QUANTUM_WIRE_COUNT_DIFFERS"
   report["reason"]="Not all allocated qubits are explicitly traceable from qN tokens; no destructive rewrite attempted"
   save();print("K018 STATUS",report["status"],flush=True)
  elif not metadata["dense_remap_possible"]:
   report["status"]="NO_SAFE_COMPACTION_ALL_WIRES_ALREADY_DENSE"
   save();print("K018 STATUS",report["status"],flush=True)
  else:
   out=OUTDIR/"bitmapped_candidate.kmx"
   out.write_text(rewrite(text,mapping),encoding="utf-8")
   circuit=km.Circuit.from_file(str(out),format="kmx")
   report["remapped_stats"]=stats(circuit)
   if report["remapped_stats"]["qubits"]>=report["original_stats"]["qubits"]:
    report["status"]="NO_QUANTUM_RESOURCE_REDUCTION_FROM_DENSE_BITMAPPING"
   elif report["remapped_stats"]["toffoli_like"]!=report["original_stats"]["toffoli_like"]:
    report["status"]="REJECT_RESOURCE_INVARIANT_CHANGED"
   else:
    kmb=OUTDIR/"bitmapped_candidate.kmb"
    circuit.to_file(str(kmb),format="kmb")
    report["candidate_path"]=str(kmb)
    report["candidate_sha256"]=sha(kmb)
    print("K018 VERIFY ORIGINAL...",flush=True)
    report["baseline_verifier"]=verify(candidate,a.shots_per_x,a.max_x,a.seed,a.timeout)
    if report["baseline_verifier"]["passed"]:
     print("K018 VERIFY COMPACTED...",flush=True)
     report["bitmapped_verifier"]=verify(kmb,a.shots_per_x,a.max_x,a.seed,a.timeout)
     report["status"]="PASS_PRELIMINARY_ACTIVE_BITMAPPING" if report["bitmapped_verifier"]["passed"] else "REJECT_VERIFIER_FAILURE"
    else:report["status"]="REJECT_BASELINE_VERIFIER_FAILURE"
  if sha(candidate)!=report["source_candidate_sha256"]:
   raise AssertionError("Source K016 candidate mutated")
  save()
  print("K018 CASE",a.case,"REFERENCE_STATS",report["original_stats"])
  print("K018 MAPPING","used_wires",metadata["qubit_indices_used"],
   "index_holes",metadata["unreferenced_index_holes"],
   "span_peak",metadata["reference_span_overlap_peak"],
   "explicit_resets",metadata["explicit_clean_reset_or_release_markers"])
  print("K018 STATUS",report["status"])
  print("K018 REPORT",a.report)
 except Exception:
  report["status"]="ERROR";report["traceback"]=traceback.format_exc()[-6000:]
  save();raise
if __name__=="__main__":main()
