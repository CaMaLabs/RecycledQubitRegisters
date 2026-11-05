#!/usr/bin/env python3
"""A92: A87b boxed recycled QPE + stage semantics + topology-aware routing.

SOURCE mode builds complete boxed dynamic 24-bit QPE (no full transpilation)
and tests every distinct modular-power source gate on selected deterministic
basis states. Include invalid work states and clean ancillas.

ROUTE mode profiles one selected controlled-modular-multiplication power
per invocation for A84 and A87b on a synthetic nearest-neighbor line.
The width matches both circuits, but this is NOT an actual IBM device:
no calibrated errors, scheduling, or QPU jobs. Checkpoint is resumable.
Do not call routed-stage sums full QPE costs.
"""
import argparse,collections,json,math,random,sys,time,traceback
from pathlib import Path
from qiskit import transpile
from qiskit.transpiler import CouplingMap
sys.path.insert(0,str(Path(__file__).resolve().parent))
from qrr_a88_integrated_qpe_ab import qpe
from qrr_a84_fused_carry_multiplier import build as a84
from qrr_a87b_direct_prefix_multiplier import build as a87b
from qrr_a65_reversible_basis_exhaustive import evaluate,instruction_stream

def cases(n,k,w,count,seed):
 rng=random.Random(seed^k)
 xs=[0,1,n-1,n,(1<<w)-1,n//2]
 xs.extend(rng.randrange(1<<w) for _ in range(count))
 return [(ctrl,x) for ctrl in (0,1) for x in dict.fromkeys(xs)]

def audit(n,k,builder,count,seed):
 q=builder(n,k);s=instruction_stream(q);w=n.bit_length()
 for ctrl,x in cases(n,k,w,count,seed):
  got=evaluate(s,ctrl|(x<<1))
  target=ctrl|((((k*x)%n) if ctrl and x<n else x)<<1)
  if got!=target:
   raise AssertionError(f"N={n} power={k} control={ctrl} x={x} got={got} expected={target}")
 return len(cases(n,k,w,count,seed))

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=2491)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=24)
 p.add_argument("--mode",choices=("source","route"),default="source")
 p.add_argument("--probes",type=int,default=16,
   help="Additional seeded random work states per control per power")
 p.add_argument("--seed",type=int,default=9201)
 p.add_argument("--level",type=int,choices=(0,1,2,3),default=1)
 p.add_argument("--max-new-powers",type=int,default=1)
 p.add_argument("--route-powers",nargs="*",type=int,default=None,
   help="Explicit modular powers to route, defaults to all in phase schedule")
 p.add_argument("--output",default="results/a92_n2491_source.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("odd n>=9, coprime base")
 if not 2<=a.bits<=2*a.n.bit_length():p.error("bits outside 2..2w")
 if a.probes<0 or a.max_new_powers<1:p.error("probes >=0; max-new-powers >=1")
 powers=[pow(a.base,1<<j,a.n) for j in range(a.bits)]
 unique=list(dict.fromkeys(k for k in powers if k!=1))
 if a.route_powers is not None:
  unknown=set(a.route_powers)-set(unique)
  if unknown:p.error("route powers not in schedule: "+str(sorted(unknown)))
  selected=list(dict.fromkeys(a.route_powers))
 else:selected=unique
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 settings={"n":a.n,"base":a.base,"bits":a.bits,"mode":a.mode,
           "seed":a.seed,"level":a.level,"probes":a.probes,
           "route_powers":selected if a.mode=="route" else None}
 if out.exists():
  d=json.loads(out.read_text())
  if d.get("settings")!=settings:raise ValueError("Existing checkpoint has different settings; choose new --output")
 else:
  d={"experiment":"A92_A87B_BOXED_QPE_TOPOLOGY_AUDIT","settings":settings,
     "status":"IN_PROGRESS","rows":{},
     "limitations":["Boxed source QPE is not full native compilation",
       "Line topology is synthetic, not a specific processor or its calibrated error model",
       "Routed single-stage gate counts are not full 24-bit QPE costs",
       "Basis semantic checks are computational-basis tests, not coherent phase proofs"]}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  if a.mode=="source":
   start=time.perf_counter()
   q,cache=qpe(a.n,a.base,a.bits,a87b,"a87b_boxed")
   counts=q.count_ops()
   d["source"]={"qubits":q.num_qubits,"classical_bits":q.num_clbits,
      "top_level_instructions":len(q.data),
      "boxed_unique_powers":len(cache),
      "boxed_definition_operations":sum(len(g.definition.data) for g in cache.values()),
      "measurements":int(counts.get("measure",0)),
      "resets":int(counts.get("reset",0)),
      "if_else":int(counts.get("if_else",0)),
      "full_native_compilation":False}
   save()
   for k in unique:
    if str(k) in d["rows"]:continue
    t=time.perf_counter()
    verified=audit(a.n,k,a87b,a.probes,a.seed)
    d["rows"][str(k)]={"power":k,"basis_cases":verified,
                         "seconds":round(time.perf_counter()-t,3)}
    save()
    print("A92 BASIS",k,verified,"PASS",flush=True)
   d["build_seconds"]=round(time.perf_counter()-start,3)
   d["status"]="PASS_BOXED_QPE_AND_SAMPLED_STAGE_BASIS"
   print("A92 SOURCE qubits",q.num_qubits,
      "boxed_unique_powers",len(cache),"top_level_ops",len(q.data),flush=True)
  else:
   for k in selected:
    key=str(k)
    row=d["rows"].setdefault(key,{"power":k,"architectures":{}})
    if all(n in row["architectures"] for n in ("a84","a87b")):continue
    for name,builder in (("a84",a84),("a87b",a87b)):
     if name in row["architectures"]:continue
     t=time.perf_counter()
     qc=builder(a.n,k)
     row.setdefault("basis_cases",{})[name]=audit(a.n,k,builder,a.probes,a.seed)
     save()
     # Explicit symmetric nearest-neighbor line with native cx/rz/sx/x.
     # A common initial layout is fixed to avoid a hidden layout advantage.
     edges=[(i,i+1) for i in range(qc.num_qubits-1)]
     cmap=CouplingMap(edges);cmap.make_symmetric()
     routed=transpile(qc,coupling_map=cmap,basis_gates=["rz","sx","x","cx"],
        initial_layout=list(range(qc.num_qubits)),layout_method="trivial",
        routing_method="sabre",optimization_level=a.level,seed_transpiler=a.seed)
     row["architectures"][name]={"qubits":routed.num_qubits,
       "cx":int(routed.count_ops().get("cx",0)),"depth":routed.depth(),
       "seconds":round(time.perf_counter()-t,3),
       "route":"synthetic_bidirectional_line",
       "initial_layout":"identity",
       "basis_gates":["rz","sx","x","cx"]}
     save()
     print("A92 ROUTED",k,name,"CX",row["architectures"][name]["cx"],
        "depth",row["architectures"][name]["depth"],flush=True)
    baseline=row["architectures"]["a84"];candidate=row["architectures"]["a87b"]
    row["comparison"]={"cx_reduction_pct":round(100*(baseline["cx"]-candidate["cx"])/baseline["cx"],4),
       "depth_reduction_pct":round(100*(baseline["depth"]-candidate["depth"])/baseline["depth"],4)}
    save()
    completed=sum(all(n in d["rows"].get(str(k),{}).get("architectures",{})
                  for n in ("a84","a87b")) for k in selected)
    if completed>=a.max_new_powers:break
   completed=sum(all(n in d["rows"].get(str(k),{}).get("architectures",{})
                 for n in ("a84","a87b")) for k in selected)
   d["complete_routed_powers"]=completed
   d["total_requested_routed_powers"]=len(selected)
   d["status"]="PASS_ROUTED_STAGE_COMPARISON" if completed==len(selected) else "PARTIAL_ROUTED_CHECKPOINT"
  save()
  print("A92 STATUS",d["status"],"SAVED",out,flush=True)
 except Exception:
  d["status"]="FAIL_OR_INTERRUPTED";d["error"]=traceback.format_exc()[-5000:]
  save();raise

if __name__=="__main__":main()
