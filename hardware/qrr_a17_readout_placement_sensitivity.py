#!/usr/bin/env python3
"""A17: sensitivity-only transfer of A15 mean readout assignment errors to
the frozen Quaspy holdout. NOT a physical prediction: A15 is N35 b8, whereas
this holdout is synthetic 32..96-bit semiprimes with much longer phase registers.
No QPU calls. Do not substitute for mapped circuit or reset/noise simulation.
"""
import argparse,gzip,json,math,random,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from integrations.darkstar_hybrid import quaspy_public_postprocess as post

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",required=True)
    p.add_argument("--a15",default="results/qrr_a15_fez_measure_reset_calibration.json")
    p.add_argument("--audit",default="results/indie_diamond_20261030/audit.json.gz")
    p.add_argument("--output",default="results/qrr_a17_readout_sensitivity.json")
    p.add_argument("--pairs",type=int,default=128)
    p.add_argument("--timeout",type=int,default=2)
    a=p.parse_args()
    post.load_upstream(a.upstream)
    cal=json.loads(Path(a.a15).read_text())
    row=next(r for r in cal["rows"] if r["base"]==8 and r["bits"]==8)
    probs={s["seed"]:s["measure"]["mean_calibrated_error"] for s in row["seeds"] if s["seed"] in (509,1223)}
    assert set(probs)=={509,1223} and all(0<=x<1 for x in probs.values())
    assert all(s["reset"]["mean_calibrated_error"] is None for s in row["seeds"])
    with gzip.open(a.audit,"rt") as f:old=json.load(f)
    cases={r["case"]:r for r in old["public_cases"]}
    grouped={}
    for r in old["rows"]:
        if r["cohort"]=="holdout" and r["arm"] in ("cf_full","ekera_short"):
            grouped.setdefault((r["case"],r["shot"]),{})[r["arm"]]=r
    chosen=[(key,v) for key,v in sorted(grouped.items()) if set(v)=={"cf_full","ekera_short"}]
    if a.pairs:chosen=chosen[:a.pairs]
    assert chosen
    output={"status":"STARTED","qpu_jobs":0,"pairs":len(chosen),
      "source":"A15 Fez base8 b8 mean readout calibration; seeds509 and1223",
      "caveat":"Counterfactual independent phase-register bit-flips on longer synthetic ideal QPE registers. NOT a mapped quantum hardware error model; no reset, gate, feedback, correlation or readout confusion matrix.",
      "scenarios":{},"rows":[]}
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    for seed in ("clean",509,1223):
        rate=0 if seed=="clean" else probs[seed]
        stat={k:{"verified":0,"pow":0,"work_limit":0} for k in ("cf_full","ekera_short")}
        for (case,shot),pair in chosen:
            n=int(cases[case]["N"]);base=int(cases[case]["base"])
            for arm in ("cf_full","ekera_short"):
                record=pair[arm];bits=int(record["phase_bits"]);freq=record["frequency"]
                rng=random.Random(f"A17-coupled-v1:{case}:{shot}:{arm}")
                # Same random uniforms between seeds: monotonic bit-error coupling.
                mask=sum(1<<i for i in range(bits) if rng.random()<rate)
                if freq is None:
                    result={"factors":None,"status":"TAIL_CENSORED","ledger":{"pow_calls":0}}
                else:
                    result=post.recover(n,base,bits,int(freq)^mask,
                                        "cf" if arm=="cf_full" else "ekera",timeout=a.timeout)
                good=bool(result["factors"] and math.prod(result["factors"])==n)
                stat[arm]["verified"]+=good
                stat[arm]["pow"]+=result["ledger"]["pow_calls"]
                stat[arm]["work_limit"]+=result["status"]=="WORK_LIMIT"
                output["rows"].append({"scenario":str(seed),"case":case,"shot":shot,
                    "arm":arm,"bit_flips":mask.bit_count() if freq is not None else 0,
                    "verified":good,"pow_calls":result["ledger"]["pow_calls"]})
        cf=stat["cf_full"];q=stat["ekera_short"]
        output["scenarios"][str(seed)]={"bit_error_assumption":rate,
          "cf_verified":cf["verified"],"quaspy_verified":q["verified"],
          "cf_pow_per_factor":cf["pow"]/cf["verified"] if cf["verified"] else None,
          "quaspy_pow_per_factor":q["pow"]/q["verified"] if q["verified"] else None,
          "cf_work_limit":cf["work_limit"],"quaspy_work_limit":q["work_limit"]}
        print("A17",seed,json.dumps(output["scenarios"][str(seed)]),flush=True)
        dest.write_text(json.dumps(output,indent=2)+"\n")
    assert output["scenarios"]["clean"]["cf_verified"]==sum(bool(v["cf_full"]["result"]["factors"]) for _,v in chosen)
    assert output["scenarios"]["clean"]["quaspy_verified"]==sum(bool(v["ekera_short"]["result"]["factors"]) for _,v in chosen)
    output["status"]="PASS_SENSITIVITY_ONLY"
    dest.write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps({"status":output["status"],"pairs":len(chosen),"scenarios":output["scenarios"],"qpu_jobs":0},indent=2))
if __name__=="__main__":main()
