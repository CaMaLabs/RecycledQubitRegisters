#!/usr/bin/env python3
"""K175: read-only structural inventory of pinned Helios KMX.

Reports instruction vocabulary, wire usage, gate distribution, rolling repeated
windows, and plausible replacement boundaries. Does not claim compatibility.
"""
import argparse, collections, hashlib, json, pathlib, re
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
WIRE=re.compile(r"(?<![A-Za-z0-9_])q(\d+)\b")
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=pathlib.Path,default=pathlib.Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("competition/k175/results/structural_audit.json"))
 p.add_argument("--window",type=int,default=16)
 a=p.parse_args()
 raw=a.baseline.read_bytes()
 sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
 lines=raw.decode("utf-8").splitlines()
 ops=collections.Counter(); samples={}; wires=collections.Counter()
 lineinfo=[]
 for i,line in enumerate(lines,1):
  s=line.strip()
  if not s or s.startswith("#"):continue
  op=s.split()[0];ops[op]+=1
  samples.setdefault(op,{"line":i,"text":s[:250]})
  ws=tuple(int(x) for x in WIRE.findall(s))
  for w in ws:wires[w]+=1
  lineinfo.append((i,op,ws,s))
 # Fingerprint repeated opcode windows without storing giant strings.
 w=max(2,a.window); windows=collections.defaultdict(list)
 for i in range(len(lineinfo)-w+1):
  seq=tuple(x[1] for x in lineinfo[i:i+w])
  h=hashlib.blake2b("\0".join(seq).encode(),digest_size=8).hexdigest()
  if len(windows[h])<8:windows[h].append(lineinfo[i][0])
 repeats=sorted(({"start_lines":v,"instances_sampled":len(v),"opcode_fingerprint":k}
                 for k,v in windows.items() if len(v)>1),
                key=lambda x:(-x["instances_sampled"],x["start_lines"][0]))[:20]
 gate_like={k:v for k,v in ops.items() if any(t in k.upper() for t in ("TOFF","CCX","CNOT","CX","GATE","HAD","PHASE","ROT","MEASURE","RESET"))}
 report={"baseline_sha256":sha,"size_bytes":len(raw),"line_count":len(lines),
         "instruction_count":len(lineinfo),"opcode_counts":dict(ops.most_common()),
         "opcode_examples":samples,"gate_like_opcode_counts":gate_like,
         "distinct_wire_tokens":len(wires),"max_wire_index":max(wires,default=None),
         "wire_reference_counts":dict(sorted(wires.items())),
         "first_25_instructions":[{"line":i,"text":s} for i,_,_,s in lineinfo[:25]],
         "last_25_instructions":[{"line":i,"text":s} for i,_,_,s in lineinfo[-25:]],
         "repeated_opcode_windows":repeats,
         "k171_substitution_identified":False,"score_verified":False,
         "limitations":["Opcode-window repetition does not establish semantic equivalence.",
                        "qN tokens may not represent all KMX wire naming conventions.",
                        "No circuit modifications or official scoring performed."]}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2)+"\n")
 summary={k:report[k] for k in ("line_count","instruction_count","opcode_counts","gate_like_opcode_counts","distinct_wire_tokens","max_wire_index","k171_substitution_identified","score_verified")}
 print("K175_STRUCTURE",json.dumps(summary,sort_keys=True),flush=True)
 print("K175_OPCODE_EXAMPLES",json.dumps(samples,sort_keys=True),flush=True)
 print("K175_WRITTEN",a.out,flush=True)
if __name__=="__main__":main()
