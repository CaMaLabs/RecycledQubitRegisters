#!/usr/bin/env python3
"""A61: actual binary controlled modular constant adder, clean flags.

For 0 <= y < N, control=1 maps y -> (y+k) mod N; states y>=N
remain fixed. Implements threshold comparators by O(w) prefix controls,
controlled binary increments, reversible wrap correction. This is a real
Qiskit gate circuit, NOT a full controlled modular multiplier; MCX
decomposition cost remains to be benchmarked.
"""
import argparse,json,random,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
from qiskit.circuit.library import MCXGate
from qiskit_aer import AerSimulator

def flip_pattern(qc, controls, target, pattern):
 if not controls:
  qc.x(target);return
 if len(controls)==1:
  if pattern==0:qc.x(controls[0])
  qc.cx(controls[0],target)
  if pattern==0:qc.x(controls[0])
 else:
  qc.append(MCXGate(len(controls),ctrl_state=pattern),controls+[target])

def ge(qc,work,target,threshold):
 """XOR [work >= threshold] onto target with disjoint lexicographic prefixes."""
 w=len(work);limit=1<<w
 if threshold<=0:qc.x(target);return
 if threshold>=limit:return
 # Strictly greater prefixes at first differing bit, plus equality.
 for j in range(w-1,-1,-1):
  if (threshold>>j)&1:continue
  positions=[j]+list(range(j+1,w))
  pattern=1
  for t,bit in enumerate(positions[1:],1):
   pattern|=((threshold>>bit)&1)<<t
  flip_pattern(qc,[work[b] for b in positions],target,pattern)
 flip_pattern(qc,work,target,threshold)

def add_constant(qc,work,k,enable):
 """In-place add k mod 2^w using controlled high-to-low carry propagation."""
 w=len(work);k%=1<<w
 for j in range(w):
  if not ((k>>j)&1):continue
  for i in range(w-1,j,-1):
   controls=[enable]+work[j:i]
   flip_pattern(qc,controls,work[i],(1<<len(controls))-1)
  qc.cx(enable,work[j])

def build(n,k):
 if n<3 or n%2!=1:raise ValueError("odd N >= 3 required")
 w=n.bit_length();k%=n
 qc=QuantumCircuit(w+4)
 control=qc.qubits[0]
 work=list(qc.qubits[1:w+1])
 valid=qc.qubits[w+1];wrap=qc.qubits[w+2];predicate_scratch=qc.qubits[w+3]
 if k==0:return qc
 # valid = [y<N]; wrap = [N-k<=y<N].
 qc.x(valid);ge(qc,work,valid,n)
 ge(qc,work,wrap,n-k);ge(qc,work,wrap,n)
 # The two flags must only act with the external control enabled.
 # Control on external phase qubit is incorporated in each addition.
 # For wrap correction, external control is additionally required.
 # Use clean, reversible AND into an extra qubit for each enabled operation:
 # use multi-control via a dedicated controlled increment function.
 def add_two_controls(value,flag1,flag2):
  # Controlled addition of constant using MCX with both control flags.
  value%=(1<<w)
  for j in range(w):
   if not ((value>>j)&1):continue
   for i in range(w-1,j,-1):
    ctrls=[flag1,flag2]+work[j:i]
    flip_pattern(qc,ctrls,work[i],(1<<len(ctrls))-1)
   qc.ccx(flag1,flag2,work[j])
 add_two_controls(k,control,valid)
 add_two_controls(-n,control,wrap)
 # Uncompute wrap using the output: for c=1, wrap = [out<k].
 # For c=0 the input has not changed. Thus use conditional cleanup
 # dependent on control and reverse input predicate when control=0.
 # First clean the raw wrap predicate from ORIGINAL y (c=0) or OUTPUT y (c=1)
 # using a controlled target-XOR comparator (one extra control).
 def controlled_ge(target,threshold,condition):
  # Compute into a clean predicate qubit, conditionally XOR the result,
  # and uncompute. This composes the independently verified ge primitive
  # instead of duplicating its prefix-control implementation.
  ge(qc,work,predicate_scratch,threshold)
  qc.ccx(condition,predicate_scratch,target)
  ge(qc,work,predicate_scratch,threshold)
 # Control-off: reverse original comparators; control-on: use output <k.
 qc.x(control)
 controlled_ge(wrap,n-k,control);controlled_ge(wrap,n,control)
 qc.x(control)
 # Control-on: out < k, using XOR of c and [out >= k & c].
 qc.cx(control,wrap);controlled_ge(wrap,k,control)
 # valid is unchanged by modular map, so original comparator uncomputes
 # whether c=0 or 1.
 qc.x(valid);ge(qc,work,valid,n)
 return qc

def verify(n,k,probes,threads,exhaustive):
 w=n.bit_length();circ=build(n,k)
 sim=AerSimulator(method="matrix_product_state",max_parallel_threads=threads)
 compiled=transpile(circ,sim,optimization_level=0,seed_transpiler=61)
 ys=list(range(1<<w)) if exhaustive else list(dict.fromkeys(
    [0,1,n-1,n,(1<<w)-1]+random.Random(61+n+k).sample(range(1<<w),min(probes,1<<w))))
 count=0
 for ctrl in (0,1):
  for y in ys:
   test=QuantumCircuit(circ.num_qubits,circ.num_qubits)
   if ctrl:test.x(0)
   for j in range(w):
    if y>>j&1:test.x(j+1)
   test.compose(compiled,inplace=True)
   test.measure(range(circ.num_qubits),range(circ.num_qubits))
   counts=sim.run(test,shots=1,seed_simulator=61).result().get_counts()
   if len(counts)!=1:raise AssertionError("non-deterministic output")
   got=int(next(iter(counts)),2)
   z=(y+k)%n if ctrl and y<n else y
   want=ctrl|(z<<1)
   if got!=want:raise AssertionError(f"N={n} k={k} ctrl={ctrl} y={y} got={got} want={want}")
   count+=1
 return {"gate_cases":count,"verified":True,"ancillas_clean":True,
    "native_counts":dict(compiled.count_ops()),"native_depth":compiled.depth()}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=35)
 p.add_argument("--constants",type=int,nargs="+",default=[8])
 p.add_argument("--probes",type=int,default=4)
 p.add_argument("--exhaustive",action="store_true")
 p.add_argument("--no-aer",action="store_true")
 p.add_argument("--threads",type=int,default=2)
 p.add_argument("--output",default="results/a61_binary_modular_adder.json")
 a=p.parse_args();o=Path(a.output);o.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A61_BINARY_MODULAR_CONSTANT_ADDITION","status":"IN_PROGRESS",
    "full_multiplier_built":False,"rows":[]}
 def save():o.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  for k in a.constants:
   t=time.perf_counter()
   circ=build(a.n,k)
   row={"n":a.n,"constant":k,"qubits":circ.num_qubits,
       "counts":dict(circ.count_ops()),"depth":circ.depth()}
   if not a.no_aer:row["audit"]=verify(a.n,k,a.probes,a.threads,a.exhaustive)
   row["seconds"]=round(time.perf_counter()-t,3)
   d["rows"].append(row);save()
   print("A61 N",a.n,"k",k,"qubits",circ.num_qubits,
         "counts",row["counts"],"depth",row["depth"],
         "verified",not a.no_aer,flush=True)
  d["status"]="PASS_SAMPLED_OR_EXHAUSTIVE_GATE_AUDIT" if not a.no_aer else "PASS_SOURCE_ONLY"
  save()
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-4000:];save();raise
 print("A61 STATUS",d["status"],"SAVED",o,flush=True)
if __name__=="__main__":main()
