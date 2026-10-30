#!/usr/bin/env python3
"""Standalone comparator A/B, optional Qiskit exact-state check, no QPU."""
import argparse,itertools,json

def gates(kind):
 g=[]
 def op(name,*indices):g.append((name,indices))
 if kind=="factored":
  op("ccx",0,1,6)
  for x,a,t in [(2,6,7),(3,7,8),(4,8,9)]:
   op("cx",x,t);op("cx",a,t);op("ccx",x,a,t)
  op("ccx",5,9,10)
  for x,a,t in [(4,8,9),(3,7,8),(2,6,7)]:
   op("ccx",x,a,t);op("cx",a,t);op("cx",x,t)
  op("ccx",0,1,6)
 elif kind=="ripple":
  constant=29
  for i in range(6):
   b=(constant>>i)&1;p=6+i-1 if i else None;t=6+i
   if p is None:
    if b:op("cx",i,t)
   elif b==0:op("ccx",i,p,t)
   else:op("cx",i,t);op("cx",p,t);op("ccx",i,p,t)
  op("cx",11,12)
  for i in reversed(range(6)):
   b=(constant>>i)&1;p=6+i-1 if i else None;t=6+i
   if p is None:
    if b:op("cx",i,t)
   elif b==0:op("ccx",i,p,t)
   else:op("ccx",i,p,t);op("cx",p,t);op("cx",i,t)
 else:raise ValueError(kind)
 return g

def state(g,y,flag,width):
 s=[(y>>i)&1 for i in range(6)]+[0]*(width-7)+[flag]
 for name,indices in g:
  if name=="cx":a,t=indices;s[t]^=s[a]
  else:a,b,t=indices;s[t]^=s[a]&s[b]
 return s

def main():
 p=argparse.ArgumentParser();p.add_argument("--qiskit",action="store_true");p.add_argument("--output",default="qrr_n35_comparator_ab_results.json");a=p.parse_args()
 result={"research_lead":"Chase Lunsford / CaMaLabs","test":"N35 standalone geq35 comparator A/B","basis":{},"qiskit_executed":False,"native_fez_compiled":False,"qpu_jobs":0,"integration_into_N35_modadd":False,"limitations":"Reference is original standalone primitive ripple clone, not later optimized OR-carry or whole-circuit Fez baseline"}
 for kind,width in [("factored",11),("ripple",13)]:
  g=gates(kind)
  for y,f in itertools.product(range(64),range(2)):
   expected=[(y>>i)&1 for i in range(6)]+[0]*(width-7)+[f^int(y>=35)]
   assert state(g,y,f,width)==expected,(kind,y,f)
  result["basis"][kind]={"pass":True,"basis_cases":128,"qubits":width,"clean_scratch":width-7,"cx":sum(n=="cx" for n,_ in g),"ccx":sum(n=="ccx" for n,_ in g),"exact_phase_plus_one":True}
  if a.qiskit:
   from qiskit import QuantumCircuit
   from qiskit.quantum_info import Statevector
   qc=QuantumCircuit(width)
   for name,idx in g:getattr(qc,name)(*idx)
   for y,f in itertools.product(range(64),range(2)):
    start=y|(f<<(width-1))
    target=sum(b<<i for i,b in enumerate(state(g,y,f,width)))
    v=Statevector.from_int(start,2**width).evolve(qc).data
    assert abs(v[target]-1)<1e-12 and abs(sum(abs(z)**2 for z in v)-1)<1e-12
   result["basis"][kind]["actual_qiskit_statevectors"]=128
 if a.qiskit:result["qiskit_executed"]=True
 with open(a.output,"w") as f:json.dump(result,f,indent=2)
 print(json.dumps(result,indent=2))
if __name__=="__main__":main()
