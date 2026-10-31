#!/usr/bin/env python3
"""A11: public QPE frequency-register bit-flip sensitivity, CPU-only.
Synthetic corruption, not calibrated device noise; no QPU submissions.
"""
import argparse,gzip,json,math,random,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from integrations.darkstar_hybrid import quaspy_public_postprocess as post

PROFILES=("clean","lsb","msb","single_random","ber_0p001","ber_0p01","ber_0p05")
ARMS=("cf_full","ekera_short")

def masks(profile,case,shot,bits_by_arm):
    rng=random.Random(f"A11-v1:{profile}:{case}:{shot}")
    u=rng.random()
    if profile.startswith("ber_"):
        p={"ber_0p001":0.001,"ber_0p01":0.01,"ber_0p05":0.05}[profile]
        # Coupled quantiles across different readout widths; does not create equivalent physical noise.
        maxbits=max(bits_by_arm.values())
        draws=[rng.random() for _ in range(maxbits)]
        return {arm:sum(1<<i for i in range(bits) if draws[i]<p) for arm,bits in bits_by_arm.items()}
    return {arm:(0 if profile=="clean" else 1 if profile=="lsb" else
                 (1<<(bits-1)) if profile=="msb" else (1<<min(bits-1,int(u*bits))))
            for arm,bits in bits_by_arm.items()}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",required=True)
    p.add_argument("--audit",default="results/indie_diamond_20261030/audit.json.gz")
    p.add_argument("--output",default="results/quaspy_a11_bitflip.json")
    p.add_argument("--max-pairs",type=int,default=0)
    p.add_argument("--timeout",type=int,default=2)
    a=p.parse_args()
    if a.max_pairs<0 or a.timeout<1:raise ValueError("invalid budget")
    post.load_upstream(a.upstream)
    with gzip.open(a.audit,"rt") as f:old=json.load(f)
    cases={x["case"]:x for x in old["public_cases"]}
    pairs={}
    for r in old["rows"]:
        if r["cohort"]=="holdout" and r["arm"] in ARMS:
            pairs.setdefault((r["case"],r["shot"]),{})[r["arm"]]=r
    selected=[(key,pair) for key,pair in sorted(pairs.items()) if set(pair)==set(ARMS)]
    if a.max_pairs:selected=selected[:a.max_pairs]
    assert selected
    report={"status":"STARTED","qpu_jobs":0,"selected_pairs":len(selected),
      "model":"deterministic synthetic bit-flip channel over public QPE frequency",
      "disclaimer":"Not calibrated physical IBM readout noise. Different register sizes produce different total bit-flip probabilities.",
      "profiles":{},"rows":[]}
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    for profile in PROFILES:
        counts={arm:{"success":0,"pow":0,"timeouts":0,"bit_flips":0} for arm in ARMS}
        for (case,shot),pair in selected:
            n=int(cases[case]["N"]);base=int(cases[case]["base"])
            masks_by_arm=masks(profile,case,shot,{arm:pair[arm]["phase_bits"] for arm in ARMS})
            for arm in ARMS:
                record=pair[arm];frequency=record["frequency"]
                flips=masks_by_arm[arm].bit_count() if frequency is not None else 0
                if frequency is None:
                    ans={"factors":None,"status":"TAIL_CENSORED","ledger":{"pow_calls":0}}
                else:
                    y=int(frequency)^masks_by_arm[arm]
                    ans=post.recover(n,base,int(record["phase_bits"]),y,
                        "cf" if arm=="cf_full" else "ekera",timeout=a.timeout)
                good=bool(ans["factors"] and math.prod(ans["factors"])==n)
                counts[arm]["success"]+=good
                counts[arm]["pow"]+=ans["ledger"]["pow_calls"]
                counts[arm]["timeouts"]+=ans["status"]=="WORK_LIMIT"
                counts[arm]["bit_flips"]+=flips
                report["rows"].append({"profile":profile,"case":case,"shot":shot,"arm":arm,
                    "verified":good,"flips":flips,"pow_calls":ans["ledger"]["pow_calls"],
                    "status":ans["status"]})
        cf=counts["cf_full"];qu=counts["ekera_short"];size=len(selected)
        report["profiles"][profile]={
            "trials_per_arm":size,"cf_verified":cf["success"],"quaspy_verified":qu["success"],
            "uplift_pp":100*(qu["success"]-cf["success"])/size,
            "cf_pow_per_verified":cf["pow"]/cf["success"] if cf["success"] else None,
            "quaspy_pow_per_verified":qu["pow"]/qu["success"] if qu["success"] else None,
            "cf_work_limit":cf["timeouts"],"quaspy_work_limit":qu["timeouts"],
            "cf_bit_flips":cf["bit_flips"],"quaspy_bit_flips":qu["bit_flips"]}
        print(profile,json.dumps(report["profiles"][profile]),flush=True)
        out.write_text(json.dumps(report,indent=2)+"\n")
    for arm,key in (("cf_full","cf_verified"),("ekera_short","quaspy_verified")):
        expected=sum(bool(pair[arm]["result"]["factors"]) for _,pair in selected)
        assert report["profiles"]["clean"][key]==expected,f"clean {arm} replay mismatch"
    report["status"]="PASS";out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":"PASS","selected_pairs":len(selected),"profiles":report["profiles"]},indent=2))
if __name__=="__main__":main()
