#!/usr/bin/env python3
"""A108: A97 multiplier source-region ledger plus A107 uniform-null audit.

Independently reconstructs A97's source circuit with explicit stage
boundaries using its original public adders and exact per-constant decision
rule. Asserts the instrumented source instruction stream EXACTLY equals the
frozen A97 builder before profiling. Native full-circuit cost is measured
separately; regional costs are stand-alone diagnostic proxies, NEVER
mistaken for additive full-circuit transpiler attribution.

Also loads A107 full-QPE result JSON and audits the exact uniform frequency
null and empirical distributions against the existing postprocessor.
No QPU jobs; no paid runtime; no claimed factoring advantage.
"""
import argparse,collections,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a61_binary_modular_adder import ge
from qrr_a87b_direct_prefix_multiplier import add as a87b_add,verify_multiplier
from qrr_a96_interval_prefix_multiplier import add as a96_add
from qrr_a97_adaptive_modadd_multiplier import build as frozen_build,candidate_cost
from qrr_a89_aer_phase_holdout import recover,lattice_hit,order

def source_signature(q):
 # Semantic and gate controls; use qasm-ish structural descriptions.
 # Equality requires gate name, qubit indices, operation parameters and
 # conditional control-state for MCX gates.
 out=[]
 for inst in q.data:
  op=inst.operation
  out.append((op.name,
    tuple(q.find_bit(bit).index for bit in inst.qubits),
    str(getattr(op,"ctrl_state",None)),
    tuple(str(p) for p in op.params)))
 return out

def instrument(n,a,level,seed):
 w=n.bit_length();a%=n;inverse=pow(a,-1,n)
 q=QuantumCircuit(2*w+6)
 c=q.qubits[0];x=list(q.qubits[1:1+w]);y=list(q.qubits[1+w:1+2*w])
 active,enable,lv,lw,lp=q.qubits[1+2*w:]
 sections=[];decisions={};cache={}
 def section(label,work):
  start=len(q.data);work()
  sections.append({"label":label,"start_op":start,
    "end_op":len(q.data),"source_ops":len(q.data)-start})
 def toggle():
  q.cx(c,active);ge(q,x+[c],active,(1<<w)+n)
 section("activation_compute",toggle)
 def accumulate(source,target,coef,phase):
  for j,s in enumerate(source):
   k=(coef*(1<<j))%n
   if not k:continue
   if k not in cache:
    p=a87b_add(n,k);v=a96_add(n,k)
    pc=candidate_cost(p,level,seed)
    vc=candidate_cost(v,level,seed)
    selected="a96" if (vc["cx"],vc["depth"])<(pc["cx"],pc["depth"]) else "a87b"
    decisions[k]={"selected":selected,"a87b":pc,"a96":vc}
    cache[k]=v if selected=="a96" else p
   def apply():
    q.ccx(active,s,enable)
    q.compose(cache[k],qubits=[enable]+target+[lv,lw,lp],inplace=True)
    q.ccx(active,s,enable)
   section(f"{phase}:bit{j}:add{k}:{decisions[k]['selected']}",apply)
 accumulate(x,y,a,"forward")
 section("conditional_swap",lambda: [q.cswap(active,u,v) for u,v in zip(x,y)])
 accumulate(x,y,-inverse,"inverse_cleanup")
 section("activation_uncompute",toggle)
 return q,sections,decisions

def section_profile(q,sections,level,seed):
 records=[]
 for index,row in enumerate(sections):
  sub=QuantumCircuit(q.num_qubits)
  for inst in q.data[row["start_op"]:row["end_op"]]:
   sub.append(inst.operation,
      [sub.qubits[q.find_bit(bit).index] for bit in inst.qubits],
      [])
  native=transpile(sub,basis_gates=["u","cx"],optimization_level=level,seed_transpiler=seed)
  records.append({**row,
    "isolated_cx":int(native.count_ops().get("cx",0)),
    "isolated_depth":int(native.depth())})
 return records

def null_audit(path):
 d=json.loads(Path(path).read_text());cfg=d["settings"]
 n=int(cfg["n"]);base=int(cfg["base"]);bits=int(cfg["bits"])
 if not 9<=n<=10000 or not 2<=bits<=20 or math.gcd(base,n)!=1:
  raise ValueError("A107 result parameters out of supported bounds")
 max_multiple=int(cfg.get("max_multiple",4));r=order(base,n)
 hit_count=factor_count=0
 for f in range(1<<bits):
  factor_count+=int(recover(n,base,bits,f,max_multiple) is not None)
  hit_count+=int(lattice_hit(f,bits,r))
 denom=1<<bits
 existing=d.get("exact_uniform_null",{})
 if existing and (existing.get("verified_factor_count")!=factor_count
   or existing.get("phase_lattice_hits")!=hit_count):
  raise AssertionError("A107 stored exact uniform null does not match recomputation")
 archs={}
 for label,row in d["architectures"].items():
  aggregate=row.get("aggregate")
  if not aggregate:continue
  shots=int(aggregate["shots"])
  factors=int(aggregate["verified_factor_count"])
  archs[label]={"shots":shots,"factor_recoveries":factors,
    "empirical_factor_rate":factors/shots,
    "uniform_expected_factor_recoveries":shots*factor_count/denom,
    "uniform_factor_rate":factor_count/denom,
    "enrichment_over_uniform_rate":(factors/shots)/(factor_count/denom) if factor_count else None,
    "probability_all_successes_if_independent_uniform_draws":
     (factor_count/denom)**shots if factors==shots else None}
 return {"source_file":str(path),"n":n,"base":base,"bits":bits,
   "exact_uniform":{"factor_count":factor_count,"lattice_count":hit_count,
     "total_frequencies":denom,"factor_rate":factor_count/denom,
     "lattice_rate":hit_count/denom},"measured":archs,
   "warning":"Exact uniform null is a postprocessor sanity check, NOT a matched circuit/noise control or evidence of quantum advantage."}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=35)
 p.add_argument("--a",type=int,default=8)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--seed",type=int,default=10801)
 p.add_argument("--skip-basis",action="store_true")
 p.add_argument("--skip-section-costs",action="store_true")
 p.add_argument("--qpe-results",nargs="*",default=["results/a107_n15_qpe.json","results/a107_n35_qpe.json"])
 p.add_argument("--output",default="results/a108_a97_multiplier_hotspots.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.a)!=1:p.error("odd N >=9 and coprime a required")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A108_FROZEN_A97_FULL_MULTIPLIER_REGIONAL_AUDIT",
   "status":"IN_PROGRESS","settings":{"n":a.n,"a":a.a,"level":a.level,"seed":a.seed},
   "qpu_jobs_submitted":0,
   "limitations":["Isolated section compilation is not additive or full native critical-path attribution",
     "This is exact source-circuit reconstruction checked against frozen A97",
     "Uniform frequency null is not a matched quantum or noise control",
     "No novelty, ML-KEM, secure RSA, or quantum hardware claim"]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  q,sections,decisions=instrument(a.n,a.a,a.level,a.seed)
  frozen,ledger=frozen_build(a.n,a.a,level=a.level,seed=a.seed,objective="cx")
  if source_signature(q)!=source_signature(frozen):
   raise AssertionError("Instrumented circuit diverged from frozen A97 source operations")
  if {k:v["selected"] for k,v in decisions.items()} != {k:v["selected"] for k,v in ledger.items()}:
   raise AssertionError("Selected modular-add architectures differ from A97")
  d["source_exact_match"]=True
  d["width"]=q.num_qubits
  d["source_ops"]=len(q.data)
  d["selected_adders"]={str(k):v for k,v in sorted(decisions.items())}
  if not a.skip_basis:
   d["exhaustive_basis_cases"]=verify_multiplier(a.n,a.a,lambda n,k:q)
  full=transpile(q,basis_gates=["u","cx"],optimization_level=a.level,seed_transpiler=a.seed)
  d["full_native"]={"cx":int(full.count_ops().get("cx",0)),
    "depth":int(full.depth()),"qubits":full.num_qubits}
  print("A108 EXACT_A97_MATCH",len(q.data),"ops","native",d["full_native"],flush=True)
  save()
  if not a.skip_section_costs:
   details=section_profile(q,sections,a.level,a.seed)
   d["sections"]=details
   groups={}
   for rec in details:
    label=rec["label"].split(":")[0]
    group=groups.setdefault(label,{"sections":0,"source_ops":0,
      "sum_isolated_cx":0,"sum_isolated_depth_not_critical_path":0})
    group["sections"]+=1
    group["source_ops"]+=rec["source_ops"]
    group["sum_isolated_cx"]+=rec["isolated_cx"]
    group["sum_isolated_depth_not_critical_path"]+=rec["isolated_depth"]
   d["regions_isolated_cost_proxy"]=groups
   print("A108 REGIONAL_PROXIES",groups,flush=True)
   save()
  nulls=[]
  for filename in a.qpe_results:
   if not Path(filename).is_file():
    print("A108 NULL SKIP missing",filename,flush=True);continue
   item=null_audit(filename)
   nulls.append(item)
   print("A108 EXACT_UNIFORM_NULL",item["n"],item["exact_uniform"],flush=True)
  d["a107_uniform_null_audits"]=nulls
  d["status"]="PASS_EXACT_FROZEN_A97_SOURCE_AND_COST_AUDIT"
  save();print("A108 STATUS",d["status"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-6000:]
  save();raise

if __name__=="__main__":main()
