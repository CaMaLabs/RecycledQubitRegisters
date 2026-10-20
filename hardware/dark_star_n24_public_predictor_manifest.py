#!/usr/bin/env python3
"""Freeze a new PUBLIC-ONLY 24-bit synthetic semiprime selector holdout.

Only N, public base, classical B31 screen, residues/Jacobi and a simple
public bit-count proxy can enter selection. Prime factors construct the
synthetic frame but are NEVER stored or used in public rankings/features.
No hidden orders, factor witnesses, QPE models, Qiskit, IBM or QPU jobs.
Research lead: Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
import dark_star_ptp_shor_audit as ds
import dark_star_public_multichoice_survivor_holdout as mc

LO,HI=1<<23,1<<24
PRIME_LO,PRIME_HI=2000,6000
GROUPS=(("G1_mod3_1",1),("G2_mod3_2",2))
POOL=(2,3,5,7,11,13,17,19,23,29,31)
SALT="QRR-N24-PUBLIC-PREDICTOR-V1-POP-20261020"
BASE_SALT="QRR-N24-PUBLIC-PREDICTOR-V1-BASE-20261020"
DEST=Path("results/dark_star_ptp/dark_star_n24_public_predictor_manifest.json")
TARGET=8
CAP=300
PROXY_J=range(8)

def hash_int(*x):
    return int.from_bytes(hashlib.sha256("|".join(map(str,x)).encode()).digest(),"big")

def canonical(rows):
    return json.dumps(rows,sort_keys=True,separators=(",",":"))

def jacobi(a,n):
    """Public Jacobi symbol; no factorization or CRT."""
    if n<=0 or not (n&1):raise ValueError("odd positive N required")
    a%=n
    out=1
    while a:
        while a%2==0:
            a//=2
            if n%8 in (3,5):out=-out
        a,n=n,a
        if a%4==3 and n%4==3:out=-out
        a%=n
    return out if n==1 else 0

def public_base(n,group):
    first=hash_int(BASE_SALT,group,n)%len(POOL)
    for i in range(len(POOL)):
        a=POOL[(first+i)%len(POOL)]
        if math.gcd(a,n)==1:return a
    raise AssertionError("No coprime public base")

def synthetic_frame():
    """Construct integer N public candidates; DISCARD p/q prior to ranking."""
    pnums=[p for p in ds.sieve_primes(PRIME_HI) if PRIME_LO<=p<=PRIME_HI]
    ns=set()
    for i,p in enumerate(pnums):
        for q in pnums[i+1:]:
            n=p*q
            if n>=HI:break
            if n>=LO and n%3 in (1,2):
                ns.add(n)
    assert len(ns)>=1000,len(ns)
    return ns

def public_costs(n,a):
    b=pow(a,3,n)
    powers=[]
    for base in (a,b):
        powers.append([pow(base,1<<i,n).bit_count() for i in PROXY_J])
    plain=sum(powers[0]); cube=sum(powers[1])
    return dict(
       plain_bitcounts=powers[0],cube_bitcounts=powers[1],
       plain_sum=plain,cube_sum=cube,
       cube_minus_plain=cube-plain,
       P2_source_proxy_predict_positive=(cube<plain))

def build():
    frame=synthetic_frame()
    selected=[]
    screens={}
    for group,mod in GROUPS:
        ranked=sorted((n for n in frame if n%3==mod),
          key=lambda n:(hash_int(SALT,group,n),n))
        tested=[]; chosen=[]
        for n in ranked[:CAP]:
            a=public_base(n,group)
            result=mc.classical_cascade(n,a)
            screen=dict(N=n,base=a,rank=len(tested)+1,
                public_B31_factored=bool(result['found']),
                classical_factor=result['factor'],
                first_source=result['source'],
                operation_counts=result['counts'])
            tested.append(screen)
            if result['found']:continue
            costs=public_costs(n,a)
            chosen.append(dict(N=n,base=a,
              public_cube=pow(a,3,n),
              group=group,rank=screen['rank'],
              P1_mod3_1_predict_positive=(n%3==1),
              P2_public_bitweight_proxy=costs,
              jacobi_symbol=jacobi(a,n),
              public_B31_unfactored=True))
            if len(chosen)==TARGET:break
        if len(chosen)!=TARGET:
            raise RuntimeError(f"Only {len(chosen)} of {TARGET} B31 survivors in {group} scan{len(tested)}")
        selected.extend(chosen)
        screens[group]=tested
    assert len(selected)==16 and len({x['N'] for x in selected})==16
    assert all(LO<=x['N']<HI and math.gcd(x['base'],x['N'])==1
               and x['public_cube']==pow(x['base'],3,x['N']) for x in selected)
    return dict(experiment='n24_public_predictor_prevalidation_manifest',
        preregistered_document='docs/DARK_STAR_N24_PUBLIC_PREDICTOR_PREREG.md',
        research_lead='Chase Lunsford / CaMaLabs',
        interval=[LO,HI],prime_construction_range=[PRIME_LO,PRIME_HI],
        selection_salt=SALT,base_salt=BASE_SALT,
        public_base_pool=list(POOL), public_bitweight_j=list(PROXY_J),
        n_in_public_candidate_frame=len(frame),
        selected_public_rows=selected,public_screenings=screens,
        selected_sha256=hashlib.sha256(canonical(selected).encode()).hexdigest(),
        labels_not_evaluated_or_used_for_selection=True,
        no_validation_factors_or_orders=True,
        no_QPU=True,qpu_jobs_submitted=0,
        note='Frozen PUBLIC-only 24bit N/a, B31 ledger and fully public features. NO p/q, validation order, factor witness, QPE or quantum backend.')

if __name__=='__main__':
    j=build()
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(j,indent=2)+'\n')
    print('PUBLIC N24 MANIFEST SHA',j['selected_sha256'],'frameNs',j['n_in_public_candidate_frame'],flush=True)
    for g,s in j['public_screenings'].items():
        print('GROUP',g,'screened',len(s),'B31 factored',sum(x['public_B31_factored'] for x in s),
              'selected',[(x['N'],x['base']) for x in j['selected_public_rows'] if x['group']==g],flush=True)
    print('NO VALIDATION ORDERS OR FACTOR LABELS OR QPU',flush=True)
