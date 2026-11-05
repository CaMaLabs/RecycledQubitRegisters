#!/usr/bin/env python3
"""A95: IBM Fez read-only execution-feasibility and arithmetic-hotspot audit.

NO QPU jobs. Reads backend.target calibration metadata and completed A94 JSON
files, and compiles small arithmetic kernels locally. Outputs:
 - Two-qubit native error budget proxy (not predicted circuit fidelity)
 - Gate duration / T1/T2 scale comparison (not scheduled wall clock)
 - Isolated comparator, modular-adder and multiplier compilation hotspots
 - Required error reduction factors for illustrative aggregate-error budgets

Never interpret naive independent-gate estimates as an actual success
probability: coherent errors, idles, crosstalk, leakage, gate distributions,
dynamic control and routing schedules are not modeled. All A94 stage costs
are single independently compiled controlled-multiplication stages.
"""
import argparse,collections,datetime,json,math,statistics,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a84_fused_carry_multiplier import fused_add as a84_add
from qrr_a87b_direct_prefix_multiplier import add as a87_add,conditioned_ge
from qrr_a61_binary_modular_adder import ge

def stats(vals):
 vals=[float(v) for v in vals if v is not None and math.isfinite(float(v)) and float(v)>=0]
 return {"count":len(vals),"min":min(vals),"median":statistics.median(vals),
   "max":max(vals),"mean":statistics.mean(vals)} if vals else {"count":0}

def metadata(backend):
 target=backend.target
 gates={}
 for name in sorted(target.operation_names):
  try:entries=list(target[name].items())
  except Exception:continue
  qargs_rows=[(qargs,prop) for qargs,prop in entries if qargs is not None]
  if not qargs_rows:continue
  width=len(qargs_rows[0][0])
  if width not in (1,2):continue
  gates[name]={"arity":width,"qargs":len(qargs_rows),
    "duration_seconds":stats([getattr(p,"duration",None) for _,p in qargs_rows if p is not None]),
    "error":stats([getattr(p,"error",None) for _,p in qargs_rows if p is not None])}
 try:properties=backend.qubit_properties()
 except Exception:properties=[]
 if not isinstance(properties,(list,tuple)):properties=[properties] if properties else []
 return {"backend":backend.name,"backend_qubits":backend.num_qubits,
   "snapshot_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
   "target_dt_seconds":getattr(target,"dt",None),
   "qubit_t1_seconds":stats([getattr(x,"t1",None) for x in properties if x is not None]),
   "qubit_t2_seconds":stats([getattr(x,"t2",None) for x in properties if x is not None]),
   "native_gates":gates}

def best_2q(meta):
 choices=[(name,x) for name,x in meta["native_gates"].items()
     if x["arity"]==2 and x["error"].get("count",0)]
 if not choices:return None
 # This is ONLY a descriptive calibration proxy; operation kinds vary.
 name,row=min(choices,key=lambda item:item[1]["error"]["median"])
 return {"gate":name,"median_error":row["error"]["median"],
         "median_duration_seconds":row["duration_seconds"].get("median")}

def load_stages(paths,backend_name):
 rows={}
 for path in paths:
  p=Path(path)
  if not p.is_file():continue
  d=json.loads(p.read_text())
  if d.get("status") not in ("PASS_IBM_TARGET_LOCAL_ROUTED_HOLDOUT","PARTIAL_CHECKPOINT"):continue
  if d.get("settings",{}).get("backend")!=backend_name:
   raise ValueError(f"{path}: checkpoint backend does not match {backend_name}")
  for key,stage in d.get("stages",{}).items():
   if all(n in stage.get("architectures",{}) for n in ("a84","a87b")):
    if key in rows:
     prev=rows[key]
     if prev["architectures"]!=stage["architectures"]:
      raise ValueError(f"Conflicting A94 checkpoint values for power {key}")
    rows[key]=stage
 return rows

def per_stage_budget(stages,meta,target_errors):
 # Use A94 reported total 2Q operations and a representative TARGET
 # error only. Gate-type-specific qubit-edge placement is unavailable in
 # the saved A94 summary and this is not a fitted physical noise model.
 two=best_2q(meta)
 if two is None:return {"status":"CALIBRATED_2Q_ERRORS_UNAVAILABLE"}
 p=two["median_error"];dur=two["median_duration_seconds"]
 out={}
 for k,row in stages.items():
  res={}
  for name in ("a84","a87b"):
   stage=row["architectures"][name]
   count=stage.get("two_qubit_gates")
   if count is None:continue
   expected=count*p
   # exp(-N*p) is a heuristic proxy for independent rare events,
   # NOT probability of correct computational output.
   nominal=math.exp(-expected) if expected<745 else 0.0
   depth=stage.get("depth")
   res[name]={"two_qubit_count":count,"depth":depth,
       "expected_two_qubit_fault_events_proxy":expected,
       "zero_two_qubit_fault_proxy":nominal,
       "depth_times_median_2q_duration_seconds_proxy":depth*dur if dur is not None else None,
       "required_error_rate_for_expected_faults_below":
         {str(v):v/count for v in target_errors}}
  out[k]=res
 return {"status":"ILLUSTRATIVE_METADATA_ONLY",
    "representative_calibration":two,"stages":out,
    "warning":"Not predicted success probability or actual scheduled runtime. Counts include all 2Q types; using one median error is an approximation."}

def kernel_hotspots(n,constants,level):
 w=n.bit_length()
 out=[]
 def compile_one(label,circuit):
  tic=time.perf_counter()
  native=transpile(circuit,basis_gates=["u","cx"],
      optimization_level=level,seed_transpiler=95)
  record={"kernel":label,"qubits":native.num_qubits,
     "cx":int(native.count_ops().get("cx",0)),"depth":int(native.depth()),
     "source_ops":len(circuit.data),
     "compile_seconds":round(time.perf_counter()-tic,3)}
  out.append(record)
  print("A95 KERNEL",label,"CX",record["cx"],"depth",record["depth"],flush=True)
 for k in constants:
  compile_one("a84_modadd_"+str(k),a84_add(n,k))
  compile_one("a87b_modadd_"+str(k),a87_add(n,k))
 # Threshold cleanup is repeated up to three times per modular add.
 for threshold in (n//2,n-1):
  baseline=QuantumCircuit(w+3)
  work=list(baseline.qubits[1:w+1]);condition=baseline.qubits[0]
  target=baseline.qubits[w+1];scratch=baseline.qubits[w+2]
  ge(baseline,work,scratch,threshold)
  baseline.ccx(condition,scratch,target)
  ge(baseline,work,scratch,threshold)
  compile_one("a84_cond_ge_"+str(threshold),baseline)
  direct=QuantumCircuit(w+3)
  conditioned_ge(direct,list(direct.qubits[1:w+1]),
       direct.qubits[w+1],threshold,direct.qubits[0])
  compile_one("a87b_cond_ge_"+str(threshold),direct)
 return out

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--backend-name",default="ibm_fez")
 p.add_argument("--instance",default="open-instance")
 p.add_argument("--n",type=int,default=2491)
 p.add_argument("--constants",nargs="+",type=int,default=[8,64,2448])
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--a94-results",nargs="+",default=[
   "results/a94_ibm_power8.json","results/a94_ibm_remaining_four.json"])
 p.add_argument("--target-faults",nargs="+",type=float,default=[1.0,0.1])
 p.add_argument("--output",default="results/a95_ibm_fez_feasibility.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1:p.error("n must be odd and >=9")
 if not a.constants or any(not 0<k<a.n for k in a.constants):p.error("constants 1..N-1")
 if any(not x>0 for x in a.target_faults):p.error("target-faults must be positive")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A95_IBM_TARGET_READ_ONLY_FEASIBILITY_AND_KERNEL_HOTSPOTS",
    "status":"IN_PROGRESS","n":a.n,"constants":a.constants,
    "target":a.backend_name,"metadata_only":True,"qpu_jobs_submitted":0,
    "calibration_warning":"Metadata snapshot may change; heuristic fault/depth proxies are not a noise simulation.",
    "limitations":["No QPU jobs or paid runtime",
      "No complete QPE compilation or physical schedule",
      "No leakage/crosstalk/idle/readout/feedback or correlated error model",
      "Independent 2Q-error estimates are descriptive, not factoring probabilities",
      "Individual kernel counts cannot be summed to equal optimized full-stage gates"]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  from qiskit_ibm_runtime import QiskitRuntimeService
  tic=time.perf_counter()
  service=QiskitRuntimeService(instance=a.instance) if a.instance else QiskitRuntimeService()
  backend=service.backend(a.backend_name)
  d["backend_target"]=metadata(backend)
  d["target_fetch_seconds"]=round(time.perf_counter()-tic,3)
  save()
  print("A95 TARGET",backend.name,"qubits",backend.num_qubits,
    "native_2q",[k for k,v in d["backend_target"]["native_gates"].items() if v["arity"]==2],flush=True)
  stages=load_stages(a.a94_results,backend.name)
  d["a94_stage_powers_found"]=sorted(int(k) for k in stages)
  if not stages:d["checkpoint_warning"]="No completed A94 stage checkpoints found at supplied paths"
  d["execution_proxies"]=per_stage_budget(stages,d["backend_target"],a.target_faults)
  save()
  for k in sorted(stages,key=int):
   x=d["execution_proxies"].get("stages",{}).get(k,{})
   if x:
    print("A95 PROXY",k,"A84 faults",round(x["a84"]["expected_two_qubit_fault_events_proxy"],2),
       "A87b faults",round(x["a87b"]["expected_two_qubit_fault_events_proxy"],2),flush=True)
  d["kernel_compilation"]=kernel_hotspots(a.n,a.constants,a.level)
  grouped={}
  for k in a.constants:
   a0=next(row for row in d["kernel_compilation"] if row["kernel"]=="a84_modadd_"+str(k))
   a1=next(row for row in d["kernel_compilation"] if row["kernel"]=="a87b_modadd_"+str(k))
   grouped[str(k)]={"cx_reduction_pct":round(100*(a0["cx"]-a1["cx"])/a0["cx"],4),
     "depth_reduction_pct":round(100*(a0["depth"]-a1["depth"])/a0["depth"],4)}
  d["kernel_comparison"]=grouped
  d["status"]="PASS_METADATA_AND_LOCAL_KERNEL_COST_AUDIT"
  save();print("A95 STATUS",d["status"],"kernels",len(d["kernel_compilation"]),
     "A94 stages",len(stages),flush=True)
 except Exception:
  d["status"]="ERROR_OR_PARTIAL";d["error"]=traceback.format_exc()[-6000:]
  save();raise

if __name__=="__main__":main()
