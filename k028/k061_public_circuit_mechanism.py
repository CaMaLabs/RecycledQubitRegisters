#!/usr/bin/env python3
"""K061: quantitative explanation of low-cost full-domain public invsqrt circuit.

Analyze K059 KMX streams. Report classically-conditioned gate share, gate
cluster boundaries, measurement-local phase corrections, costly gate hotspots,
operand qubits, and explicit classical logic. This is structural evidence,
not a claim that the exact inverse-square-root numerical algorithm is known.
"""
from __future__ import annotations
import argparse, collections, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
GATES={"CCX","CCZ","CSWAP","CX","CZ","HMR","R","Z_POW",
       "PUSH_CONDITION","POP_CONDITION","BIT_INVERT","BIT_STORE0","BIT_STORE1"}
Q=re.compile(r"\bq(\d+)\b")
B=re.compile(r"\bb(\d+)\b")
def analyze(path,blocks):
 lines=path.read_text(errors="replace").splitlines()
 entries=[]
 for line_no,line in enumerate(lines,1):
  s=line.strip()
  if not s or s.startswith("#"):continue
  opcode=s.split()[0].upper()
  if opcode in ("REGISTER","APPEND_TO_REGISTER","INFO_TAG"):continue
  entries.append({"line":line_no,"op":opcode,"code":s,
                  "qubits":[int(n) for n in Q.findall(s)],
                  "bits":[int(n) for n in B.findall(s)],
                  "explicit_if":" if b" in s})
 n=len(entries)
 counts=collections.Counter(e["op"] for e in entries)
 controlled=collections.Counter(e["op"] for e in entries if e["explicit_if"])
 qubits=collections.Counter(q for e in entries for q in e["qubits"])
 bit_usage=collections.Counter(b for e in entries for b in e["bits"])
 measurements=[(i,e) for i,e in enumerate(entries) if e["op"]=="HMR"]
 corrections=[]
 for i,e in measurements:
  m=re.search(r"\bHMR\s+q\d+\s+b(\d+)",e["code"])
  if not m:continue
  bit=m.group(1)
  subsequent=entries[i+1:i+8]
  phases=[a for a in subsequent if a["op"] in ("CZ","Z","CCZ","Z_POW") and
          re.search(r"\bif b"+re.escape(bit)+r"\b",a["code"])]
  if phases:corrections.append({"line":e["line"],"bit":bit,
     "correction_count":len(phases),"corrections":[x["code"] for x in phases[:3]]})
 windows=[]
 for i in range(blocks):
  part=entries[n*i//blocks:n*(i+1)//blocks]
  h=collections.Counter(e["op"] for e in part)
  conditional=collections.Counter(e["op"] for e in part if e["explicit_if"])
  windows.append({"index":i,"lines":[part[0]["line"],part[-1]["line"]] if part else [],
    "instructions":len(part),"ccx":h["CCX"],"ccz":h["CCZ"],"cswap":h["CSWAP"],
    "hmr":h["HMR"],"r":h["R"],"cx":h["CX"],"cz":h["CZ"],
    "conditional_cx":conditional["CX"],"conditional_cz":conditional["CZ"],
    "classical_bit_ops":h["BIT_INVERT"]+h["BIT_STORE0"]+h["BIT_STORE1"],
    "conditions":h["PUSH_CONDITION"]})
 zero=[w for w in windows if w["ccx"]==w["hmr"]==0]
 # Detailed neighborhood around largest Toffoli-free region
 spans=[];start=0
 for i,e in enumerate(entries):
  if e["op"] in ("CCX","CCZ","CSWAP","HMR","R"):
   if i-start>=20:spans.append((start,i))
   start=i+1
 if n-start>=20:spans.append((start,n))
 spans=sorted(spans,key=lambda pair:pair[1]-pair[0],reverse=True)[:8]
 free_spans=[]
 for a,b in spans:
  part=entries[a:b]
  cnt=collections.Counter(e["op"] for e in part)
  free_spans.append({"length":b-a,"lines":[part[0]["line"],part[-1]["line"]],
    "counts":dict(cnt),"first":[e["code"] for e in part[:5]],
    "last":[e["code"] for e in part[-5:]]})
 return {"file":str(path),"total_instructions":n,"opcodes":dict(counts),
  "conditional_gate_counts":dict(controlled),
  "conditional_gate_fractions":{op:round(controlled[op]/counts[op],5)
    for op in ("CX","CZ","Z","CCX","CCZ") if counts[op]},
  "measurement_count":len(measurements),
  "measurements_with_nearby_phase_corrections":len(corrections),
  "measurement_phase_correction_examples":corrections[:12],
  "distinct_classical_bits_seen":len(bit_usage),
  "distinct_quantum_operand_indices":len(qubits),
  "most_used_quantum_operands":qubits.most_common(20),
  "blocks":windows,"zero_toffoli_and_measurement_blocks":zero,
  "longest_nonclifford_measurement_free_spans":free_spans}
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--input",type=Path,default=ROOT/"competition/k059/results")
 ap.add_argument("--out",type=Path,default=ROOT/"competition/k061/results")
 ap.add_argument("--blocks",type=int,default=32)
 a=ap.parse_args()
 a.out.mkdir(parents=True,exist_ok=True)
 report={}
 for key in ("helios_public","k040_ours","k056_bounded_ours"):
  p=a.input/(key+".kmx")
  if not p.exists():
   print("K061_MISSING",key,p,flush=True);continue
  report[key]=analyze(p,a.blocks)
  d=report[key]
  print("K061_SUMMARY",json.dumps({"name":key,
   "opcodes":{k:d["opcodes"].get(k,0) for k in
    ("CCX","CCZ","CSWAP","HMR","R","CX","CZ","Z","Z_POW")},
   "conditional_gate_counts":d["conditional_gate_counts"],
   "conditional_gate_fractions":d["conditional_gate_fractions"],
   "distinct_classical_bits_seen":d["distinct_classical_bits_seen"],
   "measurement_phase_corrections":d["measurements_with_nearby_phase_corrections"],
   "longest_free_spans":d["longest_nonclifford_measurement_free_spans"][:3]},
   sort_keys=True),flush=True)
  for block in d["zero_toffoli_and_measurement_blocks"]:
   print("K061_ZERO_COST_BLOCK",json.dumps({"name":key,**block},sort_keys=True),flush=True)
 (a.out/"report.json").write_text(json.dumps(report,indent=2))
 print("K061_SAVED",a.out/"report.json",flush=True)
if __name__=="__main__":main()
