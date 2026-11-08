#!/usr/bin/env python3
"""K006: conservative phase-exact A110 cancellation in the official kickmix KMx.

Only X, CX and CCX on explicit qN operands can participate. Every other
instruction, including feedback, measurement, conditional scoping, metadata,
register append, phase, and unknown syntax, is an impenetrable fence.
The XOR write/read-set commutation test makes removed matching involutions
exactly equivalent on all quantum inputs, including entangled states.

No claim of reduced score until independent official verifier passes.
Does not use the enormous DQI sample or submit anything.
"""
import argparse,collections,hashlib,json,re,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PRIVATE=(ROOT/"../k001/private").resolve()
SOURCE=PRIVATE/"official/sample_submission/invsqrt.kmb"
KM_X=PRIVATE/"runs/k005/reference_roundtrip.kmx"
OUT_DIR=PRIVATE/"runs/k006"
REPORT=ROOT/"k006_first_optimizer.json"
GATE=re.compile(r"^(X|CX|CCX)\\s+(q[0-9]+)(?:\\s+(q[0-9]+))?(?:\\s+(q[0-9]+))?\\s*$")
ARITY={"X":1,"CX":2,"CCX":3}

def parse(line):
 if line.strip()!=line.rstrip("\r\n"):
  # Allow ordinary left-aligned instructions only. Any formatting ambiguity
  # is a fence, not a rewriting opportunity.
  return None
 m=GATE.fullmatch(line.strip())
 if m is None:return None
 name=m.group(1)
 qs=tuple(x for x in m.groups()[1:] if x is not None)
 if len(qs)!=ARITY[name] or len(set(qs))!=len(qs):return None
 return {"name":name,"qs":qs,"controls":frozenset(qs[:-1]),
  "target":qs[-1],"key":(name,qs)}
def commute(a,b):
 # XOR-target gates commute if neither modifies any control of the other.
 return a["target"] not in b["controls"] and b["target"] not in a["controls"]
def optimize_segment(segment,window):
 # Preserve exact text of all surviving instructions.
 stack=[];removed=collections.Counter()
 for line,desc in segment:
  match=None
  for i in range(len(stack)-1,max(-1,len(stack)-window-1),-1):
   prior=stack[i][1]
   if prior["key"]==desc["key"]:
    match=i;break
   if not commute(prior,desc):break
  if match is None:stack.append((line,desc))
  else:
   stack.pop(match)
   removed[desc["name"]]+=1
 return [line for line,desc in stack],removed

def optimize(text,window):
 lines=text.splitlines(keepends=True)
 output=[];segment=[];removed=collections.Counter()
 syntax_counts=collections.Counter()
 segments=0
 def flush():
  nonlocal segments
  if not segment:return
  result,count=optimize_segment(segment,window)
  output.extend(result);removed.update(count);segment.clear();segments+=1
 for line in lines:
  first=line.strip().split(maxsplit=1)
  if first:syntax_counts[first[0]]+=1
  desc=parse(line)
  if desc is None:
   flush()
   output.append(line)
  else:segment.append((line,desc))
 flush()
 return "".join(output),{"source_lines":len(lines),
   "cancelled_pairs":sum(removed.values()),
   "removed_instructions":2*sum(removed.values()),
   "removed_by_gate":dict(sorted(removed.items())),
   "safe_segments":segments,
   "instruction_token_histogram":dict(syntax_counts.most_common(45)),
   "strictly_rewritable_gate_count":sum(v for k,v in syntax_counts.items() if k in ARITY)}

def sha(path):
 with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def stats(c):
 s=c.operation_statistics()
 return {"instructions":int(s.num_instructions),
   "toffoli_like":int(s.num_toffoli_like),
   "t_like":int(s.num_t_like),
   "qubits":int(c.num_qubits),"bits":int(c.num_bits),
   "reaction_depth":int(c.reaction_depth())}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--window",type=int,default=200)
 p.add_argument("--output",default=str(REPORT))
 a=p.parse_args()
 if a.window<1:p.error("window must be positive")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 OUT_DIR.mkdir(parents=True,exist_ok=True)
 d={"experiment":"K006_SAFE_KMX_COMMUTING_INVOLUTION_CANCEL",
   "status":"IN_PROGRESS","candidate_submitted":False,
   "optimizer_scope":"Strict X/CX/CCX only; all non-whitelisted instruction syntax creates hard boundaries",
   "limitations":["Unknown instructions treated as noncommuting hard barriers",
     "Circuit statistics and parse success are not substitutes for official functional verification",
     "A cancellation may reduce instructions without improving competition score",
     "Official reference and private files are not committed to GitHub"]}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  import kickmix as km
  if not SOURCE.is_file():raise FileNotFoundError(SOURCE)
  d["reference_sha256_before"]=sha(SOURCE)
  ref=km.Circuit.from_file(str(SOURCE))
  d["reference_stats"]=stats(ref)
  # Independently export official reference if K005 copy is missing.
  if not KM_X.is_file():
   KM_X.parent.mkdir(parents=True,exist_ok=True)
   ref.to_file(str(KM_X),format="kmx")
  source_text=KM_X.read_text(encoding="utf-8")
  optimized,report=optimize(source_text,a.window)
  d["rewrite"]=report
  kmx=OUT_DIR/"candidate.kmx"
  kmx.write_text(optimized,encoding="utf-8")
  print("K006 REWRITE",report["cancelled_pairs"],"pairs",
    "tokens",report["instruction_token_histogram"],flush=True)
  candidate=km.Circuit.from_file(str(kmx),format="kmx")
  d["candidate_stats"]=stats(candidate)
  kmb=OUT_DIR/"candidate.kmb"
  candidate.to_file(str(kmb),format="kmb")
  d["candidate_kmb_sha256"]=sha(kmb)
  d["candidate_kmb_bytes"]=kmb.stat().st_size
  d["candidate_paths"]={"kmx":str(kmx),"kmb":str(kmb)}
  if sha(SOURCE)!=d["reference_sha256_before"]:
   raise AssertionError("Official reference was modified")
  if report["cancelled_pairs"]==0:
   d["status"]="PASS_ZERO_SAFE_CANCELLATIONS"
  elif d["candidate_stats"]["qubits"]!=d["reference_stats"]["qubits"] or d["candidate_stats"]["bits"]!=d["reference_stats"]["bits"]:
   d["status"]="FAIL_REGISTER_LAYOUT_CHANGED"
  else:d["status"]="PENDING_OFFICIAL_VERIFIER"
  save()
  print("K006 REFERENCE",d["reference_stats"],flush=True)
  print("K006 CANDIDATE",d["candidate_stats"],flush=True)
  print("K006 OUTPUT",kmb,flush=True)
  print("K006 STATUS",d["status"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-6000:]
  save();raise
if __name__=="__main__":main()
