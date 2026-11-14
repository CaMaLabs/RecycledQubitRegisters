#!/usr/bin/env python3
"""K146: export exact bounded Helios unitary islands as Polytof .qc files.
Extraction only; upstream compiler's ancilla gadgets are NOT verified Helios rewrites.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
from collections import Counter
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
OPS={"X":1,"CX":2,"CCX":3,"CCZ":3,"H":1,"Z":1,"S":1,"T":1}
QC={"X":"X","CX":"cnot","CCX":"tof","CCZ":"Z","H":"H","Z":"Z","S":"S","T":"T"}
WIRE=re.compile(r"q([0-9]+)\Z")
def parse(line):
 t=line.strip().split()
 if not t or t[0] not in OPS or len(t)!=OPS[t[0]]+1:return None
 if not all(WIRE.fullmatch(v) for v in t[1:]):return None
 q=tuple(int(v[1:]) for v in t[1:])
 return (t[0],q) if len(set(q))==len(q) else None
def islands(lines):
 start=None;seq=[]
 for i,s in enumerate(lines+["__END__"]):
  item=parse(s)
  if item is None:
   if seq:yield start,i,seq
   start=None;seq=[]
  else:
   if start is None:start=i
   seq.append(item)
def make_case(seq,start,end,maxw):
 wires=sorted({q for _,qs in seq for q in qs})
 n=sum(op in ("CCX","CCZ") for op,_ in seq)
 if n<2 or len(wires)>maxw:return None
 return {"first_line":start+1,"end_line":end,"wires":wires,"qubits":len(wires),
         "toffoli_like":n,"ccx":sum(op=="CCX" for op,_ in seq),
         "ccz":sum(op=="CCZ" for op,_ in seq),
         "hadamards":sum(op=="H" for op,_ in seq),"gates":seq}
def render(c):
 names=["q"+str(x) for x in c["wires"]]
 body=[".v "+" ".join(names),".i "+" ".join(names),"BEGIN"]
 body.extend(QC[op]+" "+" ".join("q"+str(x) for x in qs) for op,qs in c["gates"])
 return "\n".join(body+["END",""])
def extract(lines,maxlines,maxw):
 found=[];reasons=Counter()
 for start,end,seq in islands(lines):
  for offset in range(0,len(seq),maxlines):
   sub=seq[offset:offset+maxlines]
   c=make_case(sub,start+offset,start+offset+len(sub),maxw)
   if c:found.append(c)
   else:reasons["ineligible_chunk"]+=1
 found.sort(key=lambda c:(-c["toffoli_like"],c["qubits"],c["hadamards"],c["first_line"]))
 return found,dict(reasons)
def selftest():
 example=["HMR q1 b1","CX q21 q45","CX q21 q46","CX q21 q30","CX q21 q51",
 "CCX q40 q45 q28","CCX q28 q46 q41","CCX q41 q30 q51","HMR q41 b2"]
 cs,_=extract(example,128,62)
 assert len(cs)==1 and cs[0]["toffoli_like"]==3
 assert "tof q40 q45 q28" in render(cs[0])
 assert parse("CZ q1 q2") is None
 assert parse("CCX q1 q2 q3 if b1") is None
 assert parse("Z_POW q28 0.02") is None
 print("K146_SELFTEST PASS three-CCX export and strict barriers",flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--out",type=Path,default=Path("competition/k146/results"))
 p.add_argument("--max-lines",type=int,default=128)
 p.add_argument("--max-wires",type=int,default=62)
 p.add_argument("--top",type=int,default=8)
 p.add_argument("--selftest",action="store_true")
 a=p.parse_args();selftest()
 if a.selftest:return
 if not(3<=a.max_wires<=62 and 1<=a.max_lines<=4096 and 1<=a.top<=100):p.error("invalid bounds")
 raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
 cases,reason=extract(raw.decode().splitlines(),a.max_lines,a.max_wires)
 a.out.mkdir(parents=True,exist_ok=True);selected=[]
 for i,c in enumerate(cases[:a.top]):
  file=a.out/f"rank{i:02d}_L{c['first_line']}_{c['end_line']}.qc"
  file.write_text(render(c))
  selected.append({"qc":str(file),"qc_sha256":hashlib.sha256(file.read_bytes()).hexdigest(),
     **{k:v for k,v in c.items() if k!="gates"}})
 report={"status":"EXPORTED_ONLY_NO_UPSTREAM_EXECUTION","pinned_sha256":sha,
 "eligible_islands":len(cases),"top":selected,"rejections":reason,
 "caveats":["Exact original order retained within each maximal supported gate island",
 "HMR, CZ, conditional gates, arbitrary rotation and resets are strict boundaries",
 "Upstream compile may introduce ancillas and assume selected gadget measurement outcomes",
 "QC extraction and tensor rank alone cannot certify quantum-channel or Kaggle equivalence"]}
 (a.out/"extraction.json").write_text(json.dumps(report,indent=2)+"\n")
 print("K146_RESULT",json.dumps({"eligible_islands":len(cases),
 "top":selected[:3],"report":str(a.out/"extraction.json")}),flush=True)
if __name__=="__main__":main()
