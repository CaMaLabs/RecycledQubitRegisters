#!/usr/bin/env python3
"""A43: full u/cx cost audit plus synthetic READOUT-noise recovery replay.

Reads actual A42 Aer frequencies, never generates ideal/model samples. Readout
bit flips are applied AFTER measurement to examine classical-bit corruption;
this is NOT physical gate noise. Quaspy/CF receive the same corrupted samples.
Records paired baseline and noisy rates, modular power counts, and limitations.
"""
import argparse,json,math,random,sys,time,traceback
from pathlib import Path
from qiskit import transpile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"hardware")]
import qrr_a41_n143_dynamic_recycled_quaspy as a41
from integrations.darkstar_hybrid import quaspy_public_postprocess as post

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--input",default="results/a42_n143_reproducibility.json")
 p.add_argument("--output",default="results/a43_full_cost_readout_noise.json")
 p.add_argument("--upstream",default="/tmp/qrr-indie-quaspy")
 p.add_argument("--readout-error",type=float,nargs="+",default=[0,.001,.005,.01,.02,.05])
 p.add_argument("--replicates",type=int,default=4)
 p.add_argument("--seed",type=int,default=20261031)
 p.add_argument("--skip-native-cost",action="store_true")
 a=p.parse_args()
 if not 1<=a.replicates<=100:p.error("replicates must be 1..100")
 if any(not 0<=e<=1 for e in a.readout_error):p.error("invalid error rate")
 src=json.loads(Path(a.input).read_text())
 if src.get("status")!="PASS_REPEATED_ACTUAL_AER_MEASUREMENT_LEDGER" or src.get("n")!=143 or not src.get("rows"):
  p.error("input must contain completed real A42 N143 gate-level measurements")
 base,bits=src["base"],src["bits"]
 rows=src["rows"]
 for row in rows:
  assert 0<=int(row["frequency"])<(1<<bits) and row["bitstring"]
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 report={"experiment":"A43_REAL_AER_READOUT_REPLAY_NATIVE_GATE_COST",
 "status":"IN_PROGRESS","qpu_jobs":0,"sample_provenance":"unchanged A42 real Aer gate-level bitstrings",
 "noise_kind":"independent synthetic postmeasurement classical-bit-flip channel ONLY",
 "physical_gate_noise_tested":False,"n":143,"base":base,"bits":bits,
 "original_samples":len(rows),"replicates_per_error":a.replicates,"results":[]}
 def save():out.write_text(json.dumps(report,indent=2)+"\n")
 save()
 try:
  if not a.skip_native_cost:
   print("A43 decomposing entire circuit to {u,cx}; may take some time",flush=True)
   t=time.perf_counter()
   qc,schedule=a41.build(base,bits)
   native=transpile(qc,basis_gates=["u","cx","measure","reset","if_else"],
     optimization_level=0,seed_transpiler=a.seed)
   counts={str(k):int(v) for k,v in native.count_ops().items()}
   if set(counts)-{"u","cx","measure","reset","if_else"}:
    raise AssertionError("undecomposed source gates remain "+repr(counts))
   report["fully_decomposed"]={"counts":counts,"depth":native.depth(),
       "logical_qubits":native.num_qubits,"seconds":round(time.perf_counter()-t,3),
       "note":"Dynamic if_else may contain internal phase rotations not included in top-level counts; no physical layout."}
   save()
   print("A43 NATIVE COST",report["fully_decomposed"],flush=True)
  post.load_upstream(a.upstream)
  rng=random.Random(a.seed)
  for rate in a.readout_error:
   sample_results=[]
   for repetition in range(a.replicates):
    for row in rows:
     observed=int(row["frequency"])
     corrupted=observed
     for b in range(bits):
      if rng.random()<rate:corrupted^=1<<b
     value={"source_frequency":observed,"corrupted_frequency":corrupted,
            "bit_flips":(observed^corrupted).bit_count()}
     for method in ("cf","ekera"):
      recovered=post.recover(143,base,bits,corrupted,method=method,budget=100000,timeout=3)
      factor=recovered["factors"]
      if factor is not None:assert math.prod(factor)==143
      value[method]={"success":factor is not None,
                      "pow_calls":recovered["ledger"]["pow_calls"],
                      "status":recovered["status"]}
     sample_results.append(value)
   n=len(sample_results)
   stat={"readout_error_probability":rate,"samples":n,
    "actual_bit_flips":sum(v["bit_flips"] for v in sample_results),
    "cf_successes":sum(v["cf"]["success"] for v in sample_results),
    "quaspy_successes":sum(v["ekera"]["success"] for v in sample_results),
    "cf_pow_calls":sum(v["cf"]["pow_calls"] for v in sample_results),
    "quaspy_pow_calls":sum(v["ekera"]["pow_calls"] for v in sample_results),
    "per_sample":sample_results}
   report["results"].append(stat);save()
   print("A43 RATE",rate,"n",n,"flip",stat["actual_bit_flips"],
     "CF",stat["cf_successes"],"QUASPY",stat["quaspy_successes"],flush=True)
  report["status"]="PASS_NATIVE_COST_AND_SYNTHETIC_READOUT_NOISE" if not a.skip_native_cost else "PASS_SYNTHETIC_READOUT_NOISE_ONLY"
 except Exception as e:
  report["status"]="FAIL_NOT_VALIDATED";report["error"]=repr(e)
  report["traceback"]=traceback.format_exc()[-4000:];save();raise
 save()
 print("A43 STATUS",report["status"],"SAVED",out,flush=True)
if __name__=="__main__":main()
