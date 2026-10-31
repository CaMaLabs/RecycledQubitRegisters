#!/usr/bin/env python3
"""Quaspy A8: controlled readout perturbations of frozen ideal holdout frequencies.
No oracle access by recovery; no quantum jobs. Not a calibrated hardware noise model.
"""
import argparse, gzip, json, math, random, statistics, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from integrations.darkstar_hybrid import quaspy_public_postprocess as post

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",required=True)
    p.add_argument("--audit",default="results/indie_diamond_20261030/audit.json.gz")
    p.add_argument("--output",default="results/quaspy_a8_noise_sweep.json")
    p.add_argument("--max-pairs",type=int,default=128,help="0 for all held-out paired readouts")
    p.add_argument("--timeout",type=float,default=2.)
    a=p.parse_args()
    if a.max_pairs<0:raise ValueError("max-pairs must be nonnegative")
    post.load_upstream(a.upstream)
    with gzip.open(a.audit,"rt") as f: data=json.load(f)
    cases={x["case"]:x for x in data["public_cases"]}
    pairs={}
    for r in data["rows"]:
        if r["cohort"]!="holdout" or r["arm"] not in ("cf_full","ekera_short"):continue
        pairs.setdefault((r["case"],r["shot"]),{})[r["arm"]]=r
    selected=[(key,v) for key,v in sorted(pairs.items()) if set(v)=={"cf_full","ekera_short"}]
    if a.max_pairs:selected=selected[:a.max_pairs]
    assert selected
    regimes=("unchanged","plus_one","minus_one","low_bit_flip","uniform")
    summary={}
    rows=[]
    for regime in regimes:
        buckets={"cf_full":[],"ekera_short":[]}
        for (case,shot),pair in selected:
            public=cases[case];n=int(public["N"]);base=int(public["base"])
            for arm in ("cf_full","ekera_short"):
                record=pair[arm];m=int(record["phase_bits"]);y=record["frequency"]
                rng=random.Random(f"A8-v1:{case}:{shot}:{arm}:{regime}")
                if y is not None:
                    if regime=="plus_one":y=(y+1)%(1<<m)
                    elif regime=="minus_one":y=(y-1)%(1<<m)
                    elif regime=="low_bit_flip":y=y^1
                    elif regime=="uniform":y=rng.randrange(1<<m)
                    else:assert regime=="unchanged"
                if y is None:
                    result={"status":"TAIL_CENSORED","factors":None,"candidate_exponent":None,"ledger":{"pow_calls":0,"seconds":0.}}
                else:
                    result=post.recover(n,base,m,y,"cf" if arm=="cf_full" else "ekera",timeout=a.timeout)
                factors=result["factors"];verified=bool(factors and math.prod(factors)==n)
                row={"case":case,"shot":shot,"bits":public["bits"],"arm":arm,"regime":regime,
                     "frequency":str(y) if y is not None else None,
                     "verified_factors":verified,"status":result["status"],
                     "pow_calls":result["ledger"]["pow_calls"],"seconds":result["ledger"]["seconds"]}
                rows.append(row);buckets[arm].append(row)
        cf=buckets["cf_full"];eq=buckets["ekera_short"]
        cfs=sum(x["verified_factors"] for x in cf);eqs=sum(x["verified_factors"] for x in eq)
        summary[regime]={"trials_per_arm":len(cf),"cf_verified":cfs,"quaspy_verified":eqs,
            "cf_rate":cfs/len(cf),"quaspy_rate":eqs/len(eq),
            "uplift":(eqs-cfs)/len(cf),
            "cf_pow_calls":sum(x["pow_calls"] for x in cf),
            "quaspy_pow_calls":sum(x["pow_calls"] for x in eq)}
        print(f"{regime}: CF {cfs}/{len(cf)}, Quaspy {eqs}/{len(eq)}; uplift {summary[regime]['uplift']:+.3f}",flush=True)
    # Frozen identical no-noise arm must match previously archived factor outcomes for selected pairs.
    archive={(r["case"],r["shot"],r["arm"]):bool(r["result"]["factors"]) for _,pair in selected for r in pair.values()}
    for r in rows:
        if r["regime"]=="unchanged":
            assert r["verified_factors"]==archive[(r["case"],r["shot"],r["arm"])],"Unchanged replay mismatch"
    output={"status":"PASS","model":"deterministic frequency perturbation; NOT calibrated Fez error",
      "selected_pairs":len(selected),"zero_qpu_jobs":True,
      "baseline_policy":"CF full 2n bits vs Quaspy short 2n-4; equal perturbations in native frequency units",
      "limitations":"Different bit widths make +/-1 non-equivalent physical phase errors. Uniform is a destructive null control.",
      "summary":summary,"rows":rows}
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps({"status":"PASS","selected_pairs":len(selected),"summary":summary},indent=2))
if __name__=="__main__":main()
