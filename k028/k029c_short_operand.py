#!/usr/bin/env python3
"""K029-C: QRR support-bound operand shortening for Kickmix partial product rows.

Reuses QRR's known prefix/operand-width shortening idea. Here, only the
quantum *source operand* is truncated to its proven nonzero support;
the entire target suffix remains full width so carries propagate exactly.
The original init_and/del_and measurement-uncompute remains unchanged.
"""
from __future__ import annotations
import argparse,importlib,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
VERIFIERS=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VERIFIERS))
import kickmix as km
P=dict(coef_bits=17,delta_bits=12,product_bits=27,result_bits=28,square_bits=27)

def test(path,level,seed,timeout):
    cmd=[sys.executable,str(VERIFIERS/"invsqrt/verify_submission_invsqrt.py"),
         str(path),"--format","kmb","--max-x",str(level),"--shots-per-x","1",
         "--batch-size",str(min(level,256)),"--max-workers","1","--seed",str(seed)]
    began=time.monotonic()
    try:p=subprocess.run(cmd,cwd=VERIFIERS,capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired:return dict(status="TIMEOUT",elapsed=round(time.monotonic()-began,3))
    try:d=json.loads(p.stdout)
    except json.JSONDecodeError:d=dict(status="NON_JSON",error=p.stdout[-800:])
    return dict(status=d.get("status"),exit=p.returncode,score=d.get("score"),
        error_ratio=d.get("worst_error_over_tolerance"),error=d.get("error"),
        stderr=p.stderr[-400:],elapsed=round(time.monotonic()-began,3))

def make_patch(mode,counters,reference):
    def add(builder,inverse,control,terms,target,scratch,subtract=False):
        n=len(target)
        indices=[i for _,i in terms]
        lo=min(indices);hi=max(indices)
        if lo<0 or hi>=n:
            raise ValueError("invalid term support: "+repr((lo,hi,n)))
        counters["rows"]+=1
        counters["source_bits_reference"]+=n-lo
        counters["source_bits_candidate"]+=hi-lo+1
        counters["shortened_rows"]+=int(hi<n-1)
        if mode=="reference":
            return reference(builder,inverse,control,terms,target,scratch,subtract=subtract)
        sources=km.array([q for q,_ in terms])
        products=km.array([scratch[i] for _,i in terms])
        builder.init_and(control,sources,products)
        source=scratch[lo:hi+1]
        dest=target[lo:]
        if subtract != inverse:
            builder.isub(source,target=dest)
        else:
            builder.iadd(source,target=dest)
        builder.del_and(control,sources,products)
    return add

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default=str(ROOT/"competition/k029c/results"))
    ap.add_argument("--levels",default="64,512,4096,65536")
    ap.add_argument("--seeds",default="12345,23456")
    ap.add_argument("--timeout",type=int,default=300)
    a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    prec=ref.Precision(**P)
    orig=ref._add_row
    data=[]
    levels=[int(x) for x in a.levels.split(",")]
    seeds=[int(x) for x in a.seeds.split(",")]
    try:
        for mode in ("reference","short_source"):
            counts=dict(rows=0,shortened_rows=0,source_bits_reference=0,source_bits_candidate=0)
            ref._add_row=make_patch(mode,counts,orig)
            try:
                c=ref.build_nr_circuit(10,prec=prec)
                path=out/f"{mode}.kmb"
                c.to_file(str(path),format="kmb")
                print(json.dumps(dict(mode=mode,counters=counts,bytes=path.stat().st_size)),flush=True)
            except Exception as e:
                print(json.dumps(dict(mode=mode,status="BUILD_FAIL",error=repr(e))),flush=True)
                raise
            for level in levels:
                for seed in seeds:
                    rec=dict(mode=mode,level=level,seed=seed,**test(path,level,seed,a.timeout))
                    data.append(rec);print(json.dumps(rec,sort_keys=True),flush=True)
                    if rec["status"]!="PASS" or rec.get("exit")!=0:
                        print("STOP_ON_FAIL",mode,level,seed,flush=True)
                        return
    finally:
        ref._add_row=orig
        (out/"official_ab.json").write_text(json.dumps(data,indent=2))
    print("COMPLETED",out/"official_ab.json",flush=True)

if __name__=="__main__":main()
