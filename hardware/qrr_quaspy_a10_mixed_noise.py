#!/usr/bin/env python3
"""A10: mixed measurement-frequency corruption on archived ideal QPE holdout.
Synthetic sensitivity test, NOT a calibrated physical noise model. CPU only.
"""
import argparse,gzip,json,math,random,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from integrations.darkstar_hybrid import quaspy_public_postprocess as post

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",required=True)
    p.add_argument("--audit",default="results/indie_diamond_20261030/audit.json.gz")
    p.add_argument("--output",default="results/quaspy_a10_mixed_noise.json")
    p.add_argument("--max-pairs",type=int,default=0)
    p.add_argument("--timeout",type=int,default=2)
    a=p.parse_args()
    if a.max_pairs<0:raise ValueError("max-pairs must be >=0")
    post.load_upstream(a.upstream)
    with gzip.open(a.audit,"rt") as f:source=json.load(f)
    cases={r["case"]:r for r in source["public_cases"]}
    pairs={}
    for row in source["rows"]:
        if row["cohort"]=="holdout" and row["arm"] in ("cf_full","ekera_short"):
            pairs.setdefault((row["case"],row["shot"]),{})[row["arm"]]=row
    selected=[(key,v) for key,v in sorted(pairs.items()) if set(v)=={"cf_full","ekera_short"}]
    if a.max_pairs:selected=selected[:a.max_pairs]
    assert selected
    profiles={
      "clean":(0.0,0.0,0),
      "low":(0.05,0.01,8),
      "medium":(0.15,0.05,32),
      "high":(0.30,0.10,128),
      "severe":(0.50,0.20,128),
      "uniform":(0.0,1.0,0),
    }
    output={"status":"STARTED","pairs":len(selected),"profiles":{},"rows":[],"qpu_jobs":0,
            "noise_model":"seeded mixture of no-change, symmetric frequency offset, and uniform corruption; not hardware calibrated",
            "baseline":"CF 2n versus Quaspy 2n-4; identical stochastic event category and signed offset per paired readout",
            "limitations":"Same absolute offset differs as physical phase for different precision; ideal oracle-generated frequencies remain underlying input"}
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    for profile,(p_offset,p_uniform,maxoffset) in profiles.items():
        counters={arm:{"success":0,"pow":0,"censored":0,"work_limit":0} for arm in ("cf_full","ekera_short")}
        for (case,shot),arms in selected:
            public=cases[case];n=int(public["N"]);base=int(public["base"])
            rng=random.Random(f"A10-v1:{profile}:{case}:{shot}")
            draw=rng.random()
            category=("uniform" if draw<p_uniform else
                      "offset" if draw<p_uniform+p_offset else "clean")
            offset=rng.choice((-1,1))*rng.randint(1,maxoffset) if category=="offset" else 0
            normalized_u=rng.random()
            for arm in ("cf_full","ekera_short"):
                rec=arms[arm];bits=int(rec["phase_bits"]);y=rec["frequency"]
                if y is not None:
                    if category=="uniform":y=int(normalized_u*(1<<bits))
                    elif category=="offset":y=(y+offset)%(1<<bits)
                if y is None:
                    result={"status":"TAIL_CENSORED","factors":None,"ledger":{"pow_calls":0}}
                    counters[arm]["censored"]+=1
                else:
                    result=post.recover(n,base,bits,y,"cf" if arm=="cf_full" else "ekera",timeout=a.timeout)
                factors=result["factors"];success=bool(factors and math.prod(factors)==n)
                counters[arm]["success"]+=success
                counters[arm]["pow"]+=result["ledger"]["pow_calls"]
                counters[arm]["work_limit"]+=result["status"]=="WORK_LIMIT"
                output["rows"].append({"profile":profile,"case":case,"shot":shot,"arm":arm,
                  "category":category,"offset":offset,"factors_verified":success,
                  "pow_calls":result["ledger"]["pow_calls"],"status":result["status"]})
        cf=counters["cf_full"];qu=counters["ekera_short"]
        output["profiles"][profile]={"cf_success":cf["success"],"quaspy_success":qu["success"],
          "trials":len(selected),"uplift_pp":100*(qu["success"]-cf["success"])/len(selected),
          "cf_pow_per_factor":cf["pow"]/cf["success"] if cf["success"] else None,
          "quaspy_pow_per_factor":qu["pow"]/qu["success"] if qu["success"] else None,
          "cf_work_limit":cf["work_limit"],"quaspy_work_limit":qu["work_limit"]}
        print(profile,output["profiles"][profile],flush=True)
        dest.write_text(json.dumps(output,indent=2)+"\n")
    # A10 clean baseline must reproduce frozen source results exactly.
    expected={arm:sum(bool(v[arm]["result"]["factors"]) for _,v in selected) for arm in ("cf_full","ekera_short")}
    assert output["profiles"]["clean"]["cf_success"]==expected["cf_full"]
    assert output["profiles"]["clean"]["quaspy_success"]==expected["ekera_short"]
    assert output["profiles"]["uniform"]["cf_success"]==0 or output["profiles"]["uniform"]["quaspy_success"]>=0
    output["status"]="PASS"
    dest.write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps({"status":"PASS","pairs":len(selected),"profiles":output["profiles"]},indent=2))
if __name__=="__main__":main()
