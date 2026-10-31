#!/usr/bin/env python3
"""A22 matched N35 end-to-end *synthetic* bridge.
Same modulus/base/precision for ideal recycled-QPE sampling and public CF/Quaspy
verification, including a separate, counted public repeated-squaring audit.
NOT hardware, NOT a Dark Star population claim, NOT a physical-noise model.
"""
import argparse,collections,gzip,json,math,random,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from integrations.darkstar_hybrid import quaspy_public_postprocess as post
from hardware.qrr_indie_diamond_audit import draw_head

N=35
def oracle_order(a):
    assert math.gcd(a,N)==1
    x=1
    for r in range(1,N+1):
        x=(x*a)%N
        if x==1:return r
    raise AssertionError("No order")

def public_squaring(a,bits):
    # Only public base and modulus. Explicitly count modular squarings.
    v=a; vals=[];work=0
    for j in range(bits):
        vals.append(v)
        v=v*v%N;work+=1
    return vals,work

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",required=True)
    p.add_argument("--shots",type=int,default=128)
    p.add_argument("--output",default="results/qrr_a22_n35_matched_synthetic.json")
    args=p.parse_args()
    assert 1<=args.shots<=4096
    post.load_upstream(args.upstream)
    output={"status":"STARTED","qpu_jobs":0,"modulus":N,"shots_per_configuration":args.shots,
      "warning":"Oracle order enters ONLY the synthetic sampler. Solver receives public (N,base,bits,frequency); this is not real hardware or a full Dark Star optimization.",
      "rows":[]}
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    def save():path.write_text(json.dumps(output,indent=2)+"\n")
    try:
        for base in (2,8):
            r=oracle_order(base)
            for bits in (4,6,8):
                powers,sq=public_squaring(base,bits)
                # Verify actual circuit's powers in construction order.
                assert powers==[pow(base,1<<j,N) for j in range(bits)]
                row={"base":base,"bits":bits,"oracle_order_not_given_to_solver":True,
                  "public_squarings":sq,"quaspy_eligible":bits>N.bit_length(),"active_powers":sorted(set(x for x in powers if x!=1)),
                  "public_powers":powers,"counts":{"head_censored":0,"cf_verified":0,
                    "quaspy_verified":0,"cf_pow_calls":0,"quaspy_pow_calls":0,
                    "cf_work_limited":0,"quaspy_work_limited":0,"quaspy_ineligible":0},
                  "frequency_shots":[]}
                rng=random.Random(f"A22-matched-v1:{base}:{bits}")
                for shot in range(args.shots):
                    # Only synthetic sampler sees the secret validation order.
                    z=rng.randrange(r);u=rng.random()
                    freq,mass=draw_head(r,z,bits,u)
                    if freq is None:
                        row["counts"]["head_censored"]+=1
                        continue
                    record={"shot":shot,"frequency":freq,"head_mass":mass}
                    for label,method in (("cf","cf"),("quaspy","ekera")):
                        if label=="quaspy" and bits<=N.bit_length():
                            record[label]={"verified":None,"status":"INELIGIBLE_PRECISION","pow_calls":0}
                            row["counts"]["quaspy_ineligible"]+=1
                            continue
                        answer=post.recover(N,base,bits,int(freq),method,timeout=2)
                        verified=bool(answer["factors"] and math.prod(answer["factors"])==N)
                        record[label]={"verified":verified,"status":answer["status"],
                            "pow_calls":answer["ledger"]["pow_calls"]}
                        row["counts"][label+"_verified"]+=verified
                        row["counts"][label+"_pow_calls"]+=answer["ledger"]["pow_calls"]
                        row["counts"][label+"_work_limited"]+=answer["status"]=="WORK_LIMIT"
                    row["frequency_shots"].append(record)
                output["rows"].append(row);save()
                print("A22",base,bits,"censored",row["counts"]["head_censored"],
                      "CF",row["counts"]["cf_verified"],"Quaspy",row["counts"]["quaspy_verified"],flush=True)
        output["status"]="PASS_MATCHED_SYNTHETIC_ONLY";save()
        print(json.dumps({"status":output["status"],"qpu_jobs":0,
            "rows":[{"base":r["base"],"bits":r["bits"],"counts":r["counts"]} for r in output["rows"]]},indent=2))
    except Exception:
        output["status"]="ERROR";output["error"]=traceback.format_exc();save();raise
if __name__=="__main__":main()
