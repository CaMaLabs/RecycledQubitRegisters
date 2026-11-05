#!/usr/bin/env python3
"""A23: common N35 exact recycled-branch distribution -> public recovery.
No QPU. Compare with independent exact eigenphase mixture, not A22's
radius-limited sampled frequencies. Uses the existing verified quantum-branch
model; NOT gate-level noisy dynamic hardware emulation.
"""
import argparse,json,math,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import qrr_n35_true_recycled_phase_feedforward as circuit
from integrations.darkstar_hybrid import quaspy_public_postprocess as post

def independent_qpe_mixture(base,bits):
    N=35
    x=1;order=0
    while True:
        order+=1;x=x*base%N
        if x==1:break
        assert order<=N
    Q=1<<bits
    result=[]
    for k in range(Q):
        total=0.
        for z in range(order):
            # Direct geometric sum, independent of dynamic branch implementation.
            amp=sum(complex(math.cos(2*math.pi*t*(z/order-k/Q)),
                            math.sin(2*math.pi*t*(z/order-k/Q))) for t in range(Q))/Q
            total+=abs(amp)**2/order
        result.append(total)
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--upstream",required=True)
    ap.add_argument("--output",default="results/qrr_a23_recycled_exact_distribution_postprocess.json")
    ap.add_argument("--tol",type=float,default=1e-9)
    a=ap.parse_args()
    post.load_upstream(a.upstream)
    report={"status":"STARTED","qpu_jobs":0,
        "source":"existing exact coherent-work N35 recycled-phase branch model, not native noise, not hardware shots",
        "rows":[]}
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    def save():dest.write_text(json.dumps(report,indent=2)+"\n")
    try:
        for base in (2,8):
            for bits in (4,6,8):
                recycled,meta=circuit.emit_branch_model_probabilities(base,bits)
                spectral=independent_qpe_mixture(base,bits)
                delta=max(abs(x-y) for x,y in zip(recycled,spectral))
                if delta>a.tol:raise AssertionError(f"independent phase mismatch base={base} bits={bits} max={delta}")
                row={"base":base,"bits":bits,"max_recycled_vs_independent_spectral":delta,
                    "source_branch_proof":meta["pass_all"],"total_probability":sum(recycled),
                    "methods":{}}
                for label,method in (("cf","cf"),("quaspy","ekera")):
                    if label=="quaspy" and bits<=35 .bit_length():
                        row["methods"][label]={"eligible":False,"success_probability":None}
                        continue
                    rate=0.;calls=0;weighted_calls=0.;limited=[]
                    for freq,p in enumerate(recycled):
                        r=post.recover(35,base,bits,freq,method,timeout=2)
                        success=bool(r["factors"] and math.prod(r["factors"])==35)
                        rate+=p*success
                        calls+=r["ledger"]["pow_calls"]
                        weighted_calls+=p*r["ledger"]["pow_calls"]
                        if r["status"]=="WORK_LIMIT":limited.append(freq)
                    row["methods"][label]={"eligible":True,"success_probability":rate,
                        "uniform_outcome_pow_calls":calls,"probability_weighted_pow_calls":weighted_calls,
                        "work_limited_bins":limited}
                report["rows"].append(row);save()
                print("A23",base,bits,"max_delta",delta,"CF",row["methods"]["cf"]["success_probability"],
                      "Quaspy",row["methods"]["quaspy"]["success_probability"],flush=True)
        report["status"]="PASS_EXACT_IDEAL_BRIDGE";save()
        print(json.dumps({"status":report["status"],"qpu_jobs":0,"rows":report["rows"]},indent=2))
    except Exception:
        report["status"]="FAIL";report["traceback"]=traceback.format_exc();save();raise
if __name__=="__main__":main()
