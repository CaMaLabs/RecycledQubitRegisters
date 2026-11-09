#!/usr/bin/env python3
"""K047: selective Kickmix arithmetic-qubit budgeting atop K040 winner.

A/B test caps on only selected K034 row-local iadd/isub operations. Full
K040 construction, phase-cut, c3 recycling, and official verifier are
preserved. Promotes strictly better prefix-scoring circuits only after
two full-domain official seed passes. No inferred improvement from width.
"""
from __future__ import annotations
import argparse,hashlib,importlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"competition/k001/private/official/verifiers"))
import kickmix as km

def mod(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m);return m

k031=mod("k031_k047",ROOT/"competition/k031/k031_full_domain_repair.py")
k034=mod("k034_k047",ROOT/"competition/k034/k034_row_local_scratch.py")
k040=mod("k040_k047",ROOT/"competition/k040/k040_c3_lifetime_ab.py")
PREC=dict(coef_bits=17,delta_bits=12,product_bits=27,result_bits=28,square_bits=28)
FROZEN_SCORE=1803994.6591350352
CONTROL_WIDTH=238
EXPECTED_ROWS=178

def selected(mode,i,width,low):
    if mode=="all":return True
    if mode=="first_half":return i<89
    if mode=="second_half":return i>=89
    if mode.startswith("quarter"):
        q=int(mode[-1]);return (EXPECTED_ROWS*q//4)<=i<(EXPECTED_ROWS*(q+1)//4)
    if mode=="wide22":return width>=22
    if mode=="wide26":return width>=26
    if mode=="narrow22":return width<22
    if mode=="every4":return i%4==0
    if mode=="every8":return i%8==0
    if mode=="low_ge8":return low>=8
    raise ValueError(mode)

def budgeted_row(mode,cap,counts):
    def row(builder,inverse,control,terms,target,scratch,subtract=False):
        if not terms:raise AssertionError("Empty Horner/partial-product row")
        indices=[i for _,i in terms]
        low=min(indices)
        high=max(indices)
        if low<0 or high>=len(target):
            raise ValueError("Invalid partial product support "+repr((low,high,len(target))))
        width=len(target)-low
        n=width
        index=counts["rows"]
        counts["rows"]+=1
        counts["max_width"]=max(width,counts["max_width"])
        use_cap=cap is not None and selected(mode,index,width,low)
        tmp=builder.alloc_qubits(n)
        src=km.array([q for q,_ in terms])
        prod=km.array([tmp[i-low] for _,i in terms])
        builder.init_and(control,src,prod)
        operand=tmp[:width]
        dest=target[low:len(target)]
        if use_cap:
            # Cap only the arithmetic workspace, not the register allocator
            # at construction time or the partial-product AND network.
            builder.set_max_qubits(cap)
            counts["budgeted"]+=1
        try:
            if subtract!=inverse:
                builder.isub(operand,target=dest)
            else:
                builder.iadd(operand,target=dest)
        finally:
            if use_cap:builder.set_max_qubits(CONTROL_WIDTH)
        builder.del_and(control,src,prod)
        builder.free(tmp)
    return row

def build(ref,mode,cap,path):
    originals=(ref.build_nr_circuit,ref._add_row,ref._load_coefficients,
               ref._horner,ref._phase_by_bits)
    stats={"rows":0,"budgeted":0,"max_width":0}
    life={"open":0,"close":0,"loader":0,"horner":0}
    try:
        ref._add_row=budgeted_row(mode,cap,stats)
        ref._load_coefficients,ref._horner=k040.hooks(ref,"recycle",life)
        ref.build_nr_circuit=k040.patch_build(originals[0])
        ref._phase_by_bits=k031.make_phase(ref,1)
        circuit=ref.build_nr_circuit(10,prec=ref.Precision(**PREC))
        circuit.to_file(str(path),format="kmb")
        info={"num_qubits":circuit.num_qubits,
              "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
              "bytes":path.stat().st_size,"row_stats":stats,"lifecycle":life}
        if stats["rows"]!=EXPECTED_ROWS:
            raise RuntimeError("Unexpected row count; K040 source changed: "+str(info))
        if (life["open"],life["close"],life["loader"],life["horner"])!=(2,2,2,2):
            raise RuntimeError("Unexpected coefficient lifecycle: "+str(info))
        return info
    finally:
        (ref.build_nr_circuit,ref._add_row,ref._load_coefficients,
         ref._horner,ref._phase_by_bits)=originals

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default=str(ROOT/"competition/k047/results"))
    p.add_argument("--timeout",type=int,default=300)
    p.add_argument("--max-full",type=int,default=3,
                   help="maximum prefix-winning candidates to full-verify")
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    frozen=ROOT/"competition/k040/results/recycle.kmb"
    if not frozen.is_file():raise SystemExit("Frozen verified K040 circuit missing")
    control_hash=hashlib.sha256(frozen.read_bytes()).hexdigest()
    base=k031.verify(frozen,64,12345,a.timeout)
    if base.get("status")!="PASS" or base.get("exit_code")!=0:
        raise SystemExit("Frozen K040 control prefix did not pass")
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    runs=[]
    # First ensure a construction with no caps is bit-for-bit K040.
    unbounded=out/"unbounded_control.kmb"
    control_build=build(ref,"all",None,unbounded)
    if control_build["sha256"]!=control_hash:
        raise SystemExit("Control rebuild differs from frozen K040; aborting sweep: "+str(control_build))
    print("K047_CONTROL",json.dumps({"sha_match":True,"qubits":control_build["num_qubits"],
        "sha256":control_hash,"prefix_score":base["score"]}),flush=True)
    modes=("all","first_half","second_half","quarter0","quarter1",
           "quarter2","quarter3","wide22","wide26","narrow22",
           "every4","every8","low_ge8")
    # A broad cap of 237 costs 78 Toffolis globally; a smaller cap tests
    # whether a *restricted set* of operations can trade better.
    for cap in (237,236,232,228):
        for mode in modes:
            path=out/f"{mode}_cap{cap}.kmb"
            row={"mode":mode,"cap":cap,"path":str(path)}
            try:
                info=build(ref,mode,cap,path)
                row["build"]=info
                screen=k031.verify(path,64,12345,a.timeout)
                row["screen"]=screen
                row["status"]="PASS_PREFIX" if (
                    screen.get("status")=="PASS" and screen.get("exit_code")==0
                    ) else "FAIL_PREFIX"
                row["delta_prefix"]=screen["score"]-base["score"] if row["status"]=="PASS_PREFIX" else None
            except Exception as exc:
                row["status"]="ERROR"
                row["error"]=repr(exc)
            runs.append(row)
            print("K047_SCREEN",json.dumps({
                "cap":cap,"mode":mode,"status":row["status"],
                "qubits":row.get("build",{}).get("num_qubits"),
                "budgeted_rows":row.get("build",{}).get("row_stats",{}).get("budgeted"),
                "score":row.get("screen",{}).get("score"),
                "delta_prefix":row.get("delta_prefix"),
                "error":row.get("error")},sort_keys=True),flush=True)
    eligible=sorted((r for r in runs
                     if r["status"]=="PASS_PREFIX" and r["delta_prefix"]< -1e-7),
                    key=lambda r:r["screen"]["score"])
    for row in eligible[:a.max_full]:
        first=k031.verify(row["path"],k031.FULL_X,12345,a.timeout)
        row["full_seed_12345"]=first
        if first.get("status")=="PASS" and first.get("exit_code")==0:
            second=k031.verify(row["path"],k031.FULL_X,23456,a.timeout)
            row["full_seed_23456"]=second
            if second.get("status")=="PASS" and second.get("exit_code")==0:
                row["status"]="PASS_FULL"
                row["full_score"]=first["score"]
                row["delta_vs_K040"]=first["score"]-FROZEN_SCORE
        print("K047_FULL",json.dumps({
            "mode":row["mode"],"cap":row["cap"],"status":row["status"],
            "first":first.get("status"),
            "second":row.get("full_seed_23456",{}).get("status"),
            "full_score":row.get("full_score")},sort_keys=True),flush=True)
    winners=sorted((r for r in runs if r["status"]=="PASS_FULL"
                    and r["delta_vs_K040"]<0),
                   key=lambda r:r["full_score"])
    report={"control_hash":control_hash,"frozen_score":FROZEN_SCORE,
            "prefix_control":base["score"],
            "num_candidates":len(runs),"eligible_prefix":len(eligible),
            "verified_winners":[{"mode":r["mode"],"cap":r["cap"],
              "score":r["full_score"],"qubits":r["build"]["num_qubits"],
              "path":r["path"],"sha256":r["build"]["sha256"]}
              for r in winners],
            "runs":runs}
    (out/"results.json").write_text(json.dumps(report,indent=2,default=str))
    print("K047_RESULT",json.dumps({"num_screened":len(runs),
        "prefix_winners":len(eligible),
        "full_verified_winners":report["verified_winners"],
        "best_screened":[{"mode":r["mode"],"cap":r["cap"],
                          "score":r["screen"]["score"],
                          "qubits":r["build"]["num_qubits"]}
                         for r in eligible[:5]]},sort_keys=True),flush=True)
    print("SAVED",out/"results.json",flush=True)
if __name__=="__main__":main()
