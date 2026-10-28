#!/usr/bin/env python3
"""FROZEN fresh 4-row N25 public B31+B47/rho64 survivor selector.

RESEARCH LEAD: Chase Lunsford / CaMaLabs. ZERO IBM QPU. Does NOT inspect
factor identities, multiplicative order or any QPE measurement when selecting.
Reuses original public frame, B31 and exact original metered B47/rho64/trial
fixed classical budgets. Freeze SHA public N/base list BEFORE separate scoring.
"""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,math,time

import dark_star_n25_online_public_manifest as prior_public
import dark_star_n25_online_qpe_arithmetic as previous
import dark_star_public_multichoice_survivor_holdout as classical

ROOT=Path("results/dark_star_ptp")
DEST=ROOT/"dark_star_n25_fresh_cf50_manifest.json"
OLD=ROOT/"dark_star_n25_online_public_manifest.json"
PROTOCOL="docs/DARK_STAR_N25_FRESH_PUBLIC_SURVIVOR_CF50_PROTOCOL.md"
SALT="QRR-N25-CF50-FRESH-POP-20261028"
BASE_SALT="QRR-N25-CF50-FRESH-BASE-20261028"
GROUPS=(("G1_mod3_1",1),("G2_mod3_2",2))
POOL=(2,3,5,7,11,13,17,19,23,29,31)
TARGET=2
MAX_RANK=200
REV="dark-star-n25-fresh-public-b47-rho64-survivors-v1-20261028"


def sha(*parts):
    return hashlib.sha256("|".join(map(str,parts)).encode()).hexdigest()

def canonical(rows):
    return json.dumps(rows,sort_keys=True,separators=(",",":"))

def fresh_public_base(n,group):
    start=int(sha(BASE_SALT,group,n),16)%len(POOL)
    for offset in range(len(POOL)):
        b=POOL[(start+offset)%len(POOL)]
        if math.gcd(n,b)==1:
            return b
    raise AssertionError("No coprime public base")


def manifest():
    frozen=json.loads(OLD.read_text())
    prev=frozen["selected_public_rows"]
    assert len(prev)==8
    assert frozen["selected_sha256"]=="66b3cdb1ac58c1dffac3838c4113ffddb6fa9e6a1cc863890d55d997dc97fae7"
    prior_ids={int(z["N"]) for z in prev}
    assert len(prior_ids)==8
    frame=prior_public.public_frame()
    selected=[]
    screenings={}
    root_start=time.process_time()
    for group,remainder in GROUPS:
        eligible=(n for n in frame if n not in prior_ids and n%3==remainder)
        ordered=sorted(eligible,key=lambda n:(sha(SALT,group,n),n))
        tested=[]
        count=0
        for n in ordered[:MAX_RANK]:
            base=fresh_public_base(n,group)
            start=time.process_time()
            # EXACT old public B31 budget and its own operation ledger.
            b31=classical.classical_cascade(n,base)
            rec=dict(N=n,public_base=base,public_rank=len(tested)+1,
                     group=group,B31_factored=bool(b31["found"]),
                     B31_factor=b31["factor"],B31_source=b31["source"],
                     B31_operation_counts=b31["counts"])
            if not b31["found"]:
                # GENUINELY RUN the same old public fixed B47+rho64+small-prime
                # budget; do not look at p/q and do not use order as classifier.
                extra=previous.classical_budget(n)
                rec["additional_B47_rho64_trial97"]=extra
                rec["survived_both_fixed_public_classical_budgets"]=not extra["classically_solved"]
            else:
                rec["additional_B47_rho64_trial97"]=None
                rec["survived_both_fixed_public_classical_budgets"]=False
            rec["public_screen_CPU_ms"]=round(1000*(time.process_time()-start),5)
            tested.append(rec)
            if rec["survived_both_fixed_public_classical_budgets"]:
                selected.append(dict(N=n,base=base,cube=pow(base,3,n),
                       group=group,public_rank=rec["public_rank"],
                       unsolved_by_fixed_public_B31_B47_rho64_trial97=True))
                count+=1
                if count==TARGET:
                    break
        screenings[group]=tested
        assert count==TARGET,(
            "Frozen cap failed: no adaptive cohort reselection",
            group,count,len(tested))
    assert len(selected)==2*TARGET==4
    assert len({s["N"] for s in selected})==4
    assert not prior_ids.intersection(s["N"] for s in selected)
    for s in selected:
        assert s["cube"]==pow(s["base"],3,s["N"])
        assert math.gcd(s["N"],s["base"])==1
        assert s["unsolved_by_fixed_public_B31_B47_rho64_trial97"]
    selected_sha=hashlib.sha256(canonical(selected).encode()).hexdigest()
    return dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
        experiment="public_only_fresh_N25_fixed_classical_survivors_BEFORE_model",
        preregistration=PROTOCOL,
        original_eight_selected_sha256=frozen["selected_sha256"],
        original_eight_N_excluded=sorted(prior_ids),
        population_range=[1<<24,1<<25],
        prime_construction_range=[3500,11000],
        original_public_frame_size=len(frame),
        public_ranking_salt=SALT,public_base_salt=BASE_SALT,
        public_base_pool=list(POOL),
        group_rules={g:mod for g,mod in GROUPS},
        selected_per_group=TARGET,
        candidate_cap_per_group=MAX_RANK,
        public_screenings=screenings,
        selected_public_rows=selected,selected_sha256=selected_sha,
        public_only_B31_and_B47_rho64_trial97_screening=True,
        **{"secret_factor_or_validation_order_not_used_in_public_selection":True,
           "no_QPE_or_factor_witness_scored_during_selection":True},
        manifest_elapsed_CPU_seconds=round(time.process_time()-root_start,5),
        zero_QPU=True,qpu_jobs_submitted=0,paid_runtime_used=False,
        completed_utc=datetime.now(timezone.utc).isoformat())

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    o=manifest()
    DEST.write_text(json.dumps(o,indent=2)+"\n")
    print("FRESH N25 PUBLIC CASES SHA",o["selected_sha256"],
          "GROUP LEDGER SIZES",
          {g:len(v) for g,v in o["public_screenings"].items()},flush=True)
    for row in o["selected_public_rows"]:
        print("FROZEN PUBLIC-ONLY UNSOLVED FIXED BUDGET",row,flush=True)
    print("MANIFEST_ONLY; NO multiplicative orders, NO QPE, NO IBM QPU",flush=True)

if __name__=="__main__":
    main()
