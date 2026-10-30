#!/usr/bin/env python3
"""Frequency-weighted N35 arithmetic hotspot audit. CPU only; no IBM access.
Uses actual public power schedule, not hidden multiplicative order or factors.
Research lead Chase Lunsford / CaMaLabs.
"""
from collections import Counter
import argparse,json
from pathlib import Path

N=35; BASES=(2,8); PRECISIONS=(4,6,8)
def public_constants(power):
    inv=pow(power,-1,N)
    return [power*(1<<i)%N for i in range(6)]+[(-inv*(1<<i))%N for i in range(6)]
def audit():
    summary={}
    for base in BASES:
        counts=Counter(); detail={}
        for bits in PRECISIONS:
            c=Counter(); stages=[]
            for j in range(bits-1,-1,-1):
                power=pow(base,1<<j,N)
                if power==1:
                    stages.append(dict(stage_j=j,power=power,modadd_calls=0))
                    continue
                ks=public_constants(power)
                assert len(ks)==12 and all(1<=k<N for k in ks)
                c.update(ks)
                stages.append(dict(stage_j=j,power=power,modadd_calls=12,constants=ks))
            counts.update(c)
            detail[str(bits)]={"stages":stages,"total_add_calls":sum(c.values()),
                "selected_k_frequencies":dict(sorted(c.items()))}
        summary[str(base)]={"precision":detail,"frequency_across_b4_b6_b8":dict(sorted(counts.items())),
          "ranked_constants":[{"k":k,"occurrences":freq} for k,freq in counts.most_common()]}
    return {"research_lead":"Chase Lunsford / CaMaLabs","scope":"actual public weighted modular-add stage frequencies, not optimization result",
      "bases":summary,"no_order_or_factor_injected":True,"qpu_jobs":0,
      "native_compiles":0,"phase_exact_proofs_new":0}
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",default="results/qrr_n35_weighted_hotspots/hotspots.json");a=p.parse_args()
    r=audit();f=Path(a.output);f.parent.mkdir(parents=True,exist_ok=True)
    f.write_text(json.dumps(r,indent=2)+"\n")
    for base in BASES:
        b=r["bases"][str(base)]
        print("BASE",base,"calls", {k:v["total_add_calls"] for k,v in b["precision"].items()})
        print("top",b["ranked_constants"][:12])
    print("NO QPU; next requires exact new candidate and paired native proof")
if __name__=="__main__":main()
