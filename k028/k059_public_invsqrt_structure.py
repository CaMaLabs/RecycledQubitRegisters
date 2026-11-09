#!/usr/bin/env python3
"""K059: real gate-level comparison of a public verified invsqrt and our K040/K056.

Uses the official Kickmix Python API to decode KMB into human-readable KMX.
The audit does not attribute third-party circuits to CaMaLabs, nor infer
algorithmic structure solely from file size. No modifications are performed.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"competition/k001/private/official/verifiers"))

def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()

def parse(path, blocks=20):
 raw=path.read_text(errors="replace").splitlines()
 ops=[]
 for i,line in enumerate(raw):
  t=line.strip()
  if not t or t.startswith(("#","//")):continue
  # Preserve both spelling and a sample of operand/parameter syntax.
  op=t.split()[0]
  if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*",op):
   ops.append((i,op.upper(),t))
 count=collections.Counter(o for _,o,_ in ops)
 examples={}
 for _,op,t in ops:
  if len(examples.get(op,[]))<3:examples.setdefault(op,[]).append(t[:240])
 windows=[]
 n=len(ops)
 for b in range(blocks):
  a=n*b//blocks;z=n*(b+1)//blocks
  chunk=ops[a:z]
  c=collections.Counter(o for _,o,_ in chunk)
  windows.append({"block":b,"fraction":[round(a/max(n,1),3),round(z/max(n,1),3)],
   "lines":[chunk[0][0]+1,chunk[-1][0]+1] if chunk else [],
   "ops":len(chunk),"top":c.most_common(12)})
 runs=collections.Counter()
 for a,b in zip(ops,ops[1:]):
  runs[(a[1],b[1])]+=1
 return {"lines":len(raw),"instruction_lines":n,"counts":dict(count.most_common()),
  "examples":examples,"windows":windows,
  "top_adjacent_op_pairs":[{"ops":list(k),"count":v} for k,v in runs.most_common(25)],
  "first_instructions":[t for _,_,t in ops[:40]],
  "last_instructions":[t for _,_,t in ops[-40:]]}

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--public",type=Path,default=ROOT/"competition/k058/results/dataset/invsqrt.kmb")
 ap.add_argument("--k040",type=Path,default=ROOT/"competition/k040/results/recycle.kmb")
 ap.add_argument("--k056",type=Path,default=ROOT/"competition/k056/results/fixed_point_horner_bounded.kmb")
 ap.add_argument("--include-k056",action="store_true")
 ap.add_argument("--out",type=Path,default=ROOT/"competition/k059/results")
 a=ap.parse_args()
 a.out.mkdir(parents=True,exist_ok=True)
 import kickmix as km
 candidates={"helios_public":a.public,"k040_ours":a.k040}
 if a.include_k056:candidates["k056_bounded_ours"]=a.k056
 reports={}
 for name,path in candidates.items():
  if not path.exists():
   reports[name]={"status":"MISSING","path":str(path)}
   print("K059_MISSING",name,path,flush=True);continue
  try:
   circ=km.Circuit.from_file(str(path),format="kmb")
   txt=a.out/(name+".kmx")
   circ.to_file(str(txt),format="kmx")
   s=parse(txt)
   s.update({"status":"OK","num_qubits":circ.num_qubits,
    "binary_sha256":digest(path),"decoded_sha256":digest(txt),
    "binary_bytes":path.stat().st_size,"decoded_bytes":txt.stat().st_size,
    "decoded_path":str(txt)})
   reports[name]=s
   print("K059_CIRCUIT",json.dumps({"name":name,"qubits":s["num_qubits"],
      "instructions":s["instruction_lines"],"top":dict(list(s["counts"].items())[:25]),
      "binary_sha256":s["binary_sha256"]},sort_keys=True),flush=True)
  except Exception as e:
   reports[name]={"status":"ERROR","error":repr(e)}
   print("K059_ERROR",name,repr(e),flush=True)
 report={"source":"heliosli/qcc-circuits-live public third-party circuit",
         "comparison":"K040 and optionally K056, our independently developed prototypes",
         "caveat":"Opcode histograms are not sufficient to establish polynomial/NR/lookup algorithms",
         "circuits":reports}
 target=a.out/"structure.json"
 target.write_text(json.dumps(report,indent=2))
 print("K059_RESULT",json.dumps({k:{"status":v["status"],
   "qubits":v.get("num_qubits"),"instructions":v.get("instruction_lines"),
   "top":dict(list(v.get("counts",{}).items())[:12])}
   for k,v in reports.items()},sort_keys=True),flush=True)
 print("SAVED",target,flush=True)
if __name__=="__main__":main()
