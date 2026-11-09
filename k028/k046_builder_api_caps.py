#!/usr/bin/env python3
"""K046: use Kickmix set_max_qubits() method for bounded allocator sweeps.
Tests whether tighter max_qubits affects internal wire allocation. Promotion
requires 64-input screen and official full-domain verification on two seeds.
"""
from __future__ import annotations
import argparse,hashlib,importlib,importlib.util,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"competition/k001/private/official/verifiers"))
import kickmix as km

def mod(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
k031=mod("k031_k045",ROOT/"competition/k031/k031_full_domain_repair.py")
k034=mod("k034_k045",ROOT/"competition/k034/k034_row_local_scratch.py")
k040=mod("k040_k045",ROOT/"competition/k040/k040_c3_lifetime_ab.py")
PREC=dict(coef_bits=17,delta_bits=12,product_bits=27,result_bits=28,square_bits=28)
SCORE=1803994.6591350352

def construct(ref,cap,path):
    ctor=km.CircuitBuilder
    old=(ref.build_nr_circuit,ref._add_row,ref._load_coefficients,
         ref._horner,ref._phase_by_bits)
    def capped(*a,**k):
        obj=ctor(*a,**k)
        if cap is not None:
            obj.set_max_qubits(cap)
            actual=getattr(obj,"max_qubits",None)
            if actual!=cap:
                raise RuntimeError("Builder cap not retained: "+repr(actual))
        return obj
    try:
        ref._add_row=k034.local_row("compact",{"rows":0,"allocated_sum":0,"max_row_width":0})
        life={"open":0,"close":0,"loader":0,"horner":0}
        ref._load_coefficients,ref._horner=k040.hooks(ref,"recycle",life)
        ref.build_nr_circuit=k040.patch_build(old[0])
        ref._phase_by_bits=k031.make_phase(ref,1)
        km.CircuitBuilder=capped
        circuit=ref.build_nr_circuit(10,prec=ref.Precision(**PREC))
        circuit.to_file(str(path),format="kmb")
        return {"qubits":circuit.num_qubits,
                "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                "life":life}
    finally:
        km.CircuitBuilder=ctor
        (ref.build_nr_circuit,ref._add_row,ref._load_coefficients,
         ref._horner,ref._phase_by_bits)=old

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default=str(ROOT/"competition/k046/results"))
    ap.add_argument("--timeout",type=int,default=300)
    a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    frozen=ROOT/"competition/k040/results/recycle.kmb"
    if not frozen.is_file():raise SystemExit("Frozen K040 candidate missing")
    expect=hashlib.sha256(frozen.read_bytes()).hexdigest()
    baseline=k031.verify(frozen,64,12345,a.timeout)
    if baseline.get("status")!="PASS":raise SystemExit("K040 control prefix failed")
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    obj=km.CircuitBuilder()
    diagnostics={"builder_type":str(type(obj)),
        "builder_doc":str(km.CircuitBuilder.__doc__)[:1200],
        "max_qubits_before":repr(getattr(obj,"max_qubits","NOT_EXPOSED")),
        "capacity_members":[n for n in dir(obj) if any(k in n.lower() for k in ("max","qubit","alloc","free","limit","cap"))]}
    try:
        obj.set_max_qubits(255)
        diagnostics["setter_result"]="SET_OK"
        diagnostics["max_qubits_after"]=repr(getattr(obj,"max_qubits",None))
    except Exception as exc:
        diagnostics["setter_result"]="NOT_WRITABLE"
        diagnostics["setter_error"]=repr(exc)
    print("K046_API",json.dumps(diagnostics,sort_keys=True),flush=True)
    (out/"api.json").write_text(json.dumps(diagnostics,indent=2))
    if diagnostics["setter_result"]!="SET_OK":
        print("K046_STOP: set_max_qubits not available; cap sweep skipped.",flush=True)
        return
    rows=[]
    for cap in (None,216,220,224,228,232,236,237,238,240,255):
        row={"cap":cap}
        path=out/("unbounded.kmb" if cap is None else f"cap_{cap}.kmb")
        try:
            info=construct(ref,cap,path)
            row["build"]=info
            if cap is None and info["sha256"]!=expect:
                raise AssertionError("Unbounded build SHA differs from K040")
            if info["qubits"]<238:
                screen=k031.verify(path,64,12345,a.timeout)
                row["screen"]=screen
                if (screen.get("status")=="PASS" and screen.get("exit_code")==0
                    and screen.get("score",1e100)<baseline["score"]):
                    first=k031.verify(path,k031.FULL_X,12345,a.timeout)
                    row["full_seed_12345"]=first
                    if first.get("status")=="PASS" and first.get("exit_code")==0:
                        second=k031.verify(path,k031.FULL_X,23456,a.timeout)
                        row["full_seed_23456"]=second
                        if second.get("status")=="PASS" and second.get("exit_code")==0:
                            row["verified_improvement"]=True
                            row["score"]=first["score"]
                            row["delta_vs_K040"]=first["score"]-SCORE
            row["status"]="BUILT"
        except Exception as e:
            row["status"]="ERROR"
            row["error"]=repr(e)
        rows.append(row)
        print("K046",json.dumps(row,sort_keys=True),flush=True)
    (out/"results.json").write_text(json.dumps(rows,indent=2))
    winners=[r for r in rows if r.get("verified_improvement")]
    print("K046_RESULT",json.dumps({"winners":[r["cap"] for r in winners],
        "best_score":min((r["score"] for r in winners),default=None)}),flush=True)
    print("SAVED",out/"results.json",flush=True)
if __name__=="__main__":main()
