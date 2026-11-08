#!/usr/bin/env python3
"""K030-B: resource-aware truncation of smallest inverse-sqrt phase rotations.

No verifier modifications. Retains the full Newton-Raphson arithmetic and
deletes only leading low-significance controlled Z_POW gates.
The maximum deleted absolute turn angle (in turns) is bounded by
sum_{j=0}^{cut-1} 2**(j-f+1). This is a sufficient worst-case bound
for any bitstring, not an empirical error estimate.

Uses one-shot matched A/B verifier comparisons. Caution: official verifier
prefix passing does not prove full-domain correctness.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import importlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VERIFIERS=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VERIFIERS))
import kickmix as km

P=dict(coef_bits=17,delta_bits=12,product_bits=27,
       result_bits=28,square_bits=27)

def verification(path,level,seed,timeout):
    cmd=[sys.executable,str(VERIFIERS/"invsqrt/verify_submission_invsqrt.py"),
         str(path),"--format","kmb","--max-x",str(level),
         "--shots-per-x","1","--batch-size",str(min(level,256)),
         "--max-workers","1","--seed",str(seed)]
    began=time.monotonic()
    try:p=subprocess.run(cmd,cwd=VERIFIERS,capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired:return {"status":"TIMEOUT","elapsed":round(time.monotonic()-began,3)}
    try:d=json.loads(p.stdout)
    except json.JSONDecodeError:d={"status":"NON_JSON","error":p.stdout[-500:]}
    keys=("status","score","toffoli_equivalent","toffoli_count","t_count",
          "rotation_count","rotation_eps","num_qubits","reaction_depth",
          "worst_error_over_tolerance","error")
    o={k:d.get(k) for k in keys}
    o["exit"]=p.returncode
    o["elapsed"]=round(time.monotonic()-began,3)
    o["stderr"]=p.stderr[-500:]
    return o

def make_phase(cut):
    def phase(builder,y):
        f=len(y)
        if not 0 <= cut <= f:
            raise ValueError((cut,f))
        with builder.mark("phase_by_bits"):
            for j in range(cut,f):
                builder.z_pow(y[j],Fraction(2)**(j-f+1))
    return phase

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",default=str(ROOT/"competition/k030b/results"))
    p.add_argument("--max-cut",type=int,default=6)
    p.add_argument("--levels",default="64,512,4096,65536")
    p.add_argument("--seeds",default="12345,23456")
    p.add_argument("--timeout",type=int,default=300)
    a=p.parse_args()
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    prec=ref.Precision(**P)
    orig=ref._phase_by_bits
    levels=[int(x) for x in a.levels.split(",")]
    seeds=[int(x) for x in a.seeds.split(",")]
    output_bits=prec.output_bits(10)
    records=[]
    try:
        for cut in range(0,min(a.max_cut,output_bits)+1):
            ref._phase_by_bits=orig if cut==0 else make_phase(cut)
            file=out/f"phase_cut_{cut}.kmb"
            try:
                circuit=ref.build_nr_circuit(10,prec=prec)
                circuit.to_file(str(file),format="kmb")
                # all omitted rotations: each bit may be set; sum is an
                # absolute maximum error in turns, not phase amplitude.
                bound=sum(Fraction(2)**(j-output_bits+1) for j in range(cut))
                build={"cut":cut,"output_bits":output_bits,
                       "max_omitted_turns":float(bound),
                       "max_omitted_radians":float(2*math.pi*bound),
                       "circuit_bytes":file.stat().st_size}
                print("BUILD",json.dumps(build),flush=True)
            except Exception as e:
                record={"cut":cut,"status":"BUILD_FAIL","error":repr(e)}
                records.append(record);print(json.dumps(record),flush=True)
                continue
            passed=True
            for level in levels:
                for seed in seeds:
                    row={**build,"level":level,"seed":seed,
                         **verification(file,level,seed,a.timeout)}
                    records.append(row)
                    print(json.dumps(row,sort_keys=True,default=str),flush=True)
                    if row.get("status")!="PASS" or row.get("exit")!=0:
                        passed=False
                        break
                if not passed:break
            (out/"phase_sweep.json").write_text(json.dumps(records,indent=2))
    finally:
        ref._phase_by_bits=orig

    top=max(levels)
    ranks=[]
    for cut in range(min(a.max_cut,output_bits)+1):
        rows=[r for r in records if r.get("cut")==cut and r.get("level")==top]
        if len(rows)==len(seeds) and all(r.get("status")=="PASS" and r.get("exit")==0 for r in rows):
            ranks.append({"cut":cut,"average_score":sum(r["score"] for r in rows)/len(rows),
                          "max_omitted_radians":rows[0]["max_omitted_radians"]})
    print("VERIFIED_PREFIX_FRONTIER",json.dumps(sorted(ranks,key=lambda r:r["average_score"])),flush=True)
    print("SAVED",out/"phase_sweep.json",flush=True)

if __name__=="__main__":main()
