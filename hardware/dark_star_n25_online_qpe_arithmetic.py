#!/usr/bin/env python3
"""Fresh N25 public survivor, ON-DEMAND CF/GCD QPE sampler + source-gate costs.

No O(N) precomputation of factor-winning denominators; tests are made only
for a sampled QPE measurement. Fixed SHA manifest before scoring. CPU only.
Research lead Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations
import argparse,hashlib,json,math,random,time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

import numpy as np
from numba import njit
import dark_star_n22_numerical_precision_audit as prec
import dark_star_n22_full_tail_qpe_holdout as tail
import dark_star_public_multichoice_survivor_holdout as mc
import dark_star_n25_online_public_manifest as pub
import dark_star_ptp_shor_audit as ds
import dark_star_recycled_scalable_arithmetic_audit as gates

ROOT=Path("results/dark_star_ptp")
MANIFEST=ROOT/"dark_star_n25_online_public_manifest.json"
PREREG="docs/DARK_STAR_N25_ONLINE_VERIFIER_ARITHMETIC_PREREG.md"
SHA="66b3cdb1ac58c1dffac3838c4113ffddb6fa9e6a1cc863890d55d997dc97fae7"
STAGES=tuple(range(4,51,2))
SAMPLES=4096
W=32
SHOTS=4
ALPHA=.01
FAMILY=8*2*len(STAGES)*2*2
LOG=math.log(2/(ALPHA/FAMILY))
SEED="QRR-N25-ONLINE-ARITH-PHASE-20261025"
assert len(STAGES)==24 and FAMILY==1536
prec.LOG=LOG

@njit
def gcd_n(a,b):
    if a<0:a=-a
    if b<0:b=-b
    while b:
        a,b=b,a%b
    return a

@njit
def modpow_n(a,e,n):
    value=1
    x=a%n
    while e:
        if e&1:value=(value*x)%n
        x=(x*x)%n
        e//=2
    return value

@njit
def online_factor_cf(y,Q,a,n):
    """Public y,N,a ONLY. Return accepted, denominators checked, powers, GCDs."""
    if y==0:return False,0,0,0
    x=y
    d0=Q
    prevprev=1
    prev=0
    ncheck=0
    powers=0
    gcds=0
    while d0:
        q=x//d0
        rem=x%d0
        den=q*prev+prevprev
        if den>n:break
        if 1<den and den%2==0:
            ncheck+=1
            powers+=1
            if modpow_n(a,den,n)==1:
                half=modpow_n(a,den//2,n)
                powers+=1
                gcds+=2
                low=gcd_n(half-1,n)
                high=gcd_n(half+1,n)
                if (1<low<n) or (1<high<n):
                    return True,ncheck,powers,gcds
        prevprev,prev=prev,den
        x,d0=d0,rem
    return False,ncheck,powers,gcds

@njit
def sample_head(centers,residuals,ubins,r,Q,base,n):
    k=len(centers)
    heads=0
    tail_total=0.
    tail_second=0.
    den_checks=0
    modular_powers=0
    gcds=0
    tail_events=0
    max_oversum=0.
    for i in range(k):
        mass=0.
        picked=False
        good=False
        for j in range(-W,W+1):
            t=residuals[i]-r*j
            if t==0:
                p=1.
            else:
                numerator=math.sin(math.pi*(float(t)/float(r)))
                denominator=float(Q)*math.sin(math.pi*float(t)/(float(r)*float(Q)))
                p=(numerator/denominator)**2
            if not math.isfinite(p) or p<0.:
                raise ValueError("Invalid QPE bin probability")
            mass+=p
            if not picked and ubins[i]<mass:
                picked=True
                y=(centers[i]+j)%Q
                good,d,pw,g=online_factor_cf(y,Q,base,n)
                den_checks+=d
                modular_powers+=pw
                gcds+=g
        if mass>1.+1e-8:raise ValueError("QPE head mass > 1")
        if mass-1.>max_oversum:max_oversum=mass-1.
        omission=max(0.,1.-mass)
        if omission>1./63.+1e-6:
            raise ValueError("Analytic tail bound violated")
        if not picked:tail_events+=1
        if good:heads+=1
        tail_total+=omission
        tail_second+=omission*omission
    return (heads,tail_total,tail_second,den_checks,modular_powers,
            gcds,tail_events,max_oversum)

def read_public():
    data=json.loads(MANIFEST.read_text())
    rows=data["selected_public_rows"]
    assert data["selected_sha256"]==SHA
    assert hashlib.sha256(pub.canonical(rows).encode()).hexdigest()==SHA
    assert data["factor_order_and_qpe_not_inspected_for_selection"]
    assert data["zero_QPU"] and data["qpu_jobs_submitted"]==0
    assert len(rows)==8 and len({x["N"] for x in rows})==8
    for x in rows:
        n=x["N"]
        assert pub.LO<=n<pub.HI
        assert pub.base_for(n,x["group"])==x["base"]
        assert x["cube"]==pow(x["base"],3,n)
        assert x["B31_unfactored"]
        original=next(z for z in data["public_screenings"][x["group"]] if z["N"]==n)
        assert original["rank"]==x["rank"] and not original["B31_factored"]
    return data

def classical_budget(n):
    """PUBLIC B47/rho64/prime<=97; NOT full trial. All physical CPU counted separately."""
    start=time.process_time()
    p47=mc.pminusone(n,47)
    rho=dict(attempts=0,iterations=0,gcd_calls=0,modular_squares=0,factor=None)
    trial=dict(checks=0,factor=None)
    factor=p47["factor"] if p47["found"] else None
    source="Pollard_p_minus_1_B47" if factor else None
    if not factor:
        for seed in (2,3):
            rho["attempts"]+=1
            x=y=seed%n
            for _ in range(64):
                x=(x*x+1)%n
                y=(y*y+1)%n
                y=(y*y+1)%n
                rho["modular_squares"]+=3
                rho["gcd_calls"]+=1
                rho["iterations"]+=1
                g=math.gcd(abs(x-y),n)
                if 1<g<n:
                    factor=g
                    rho["factor"]=g
                    source="Floyd_rho_64"
                    break
                if g==n:break
            if factor:break
    if not factor:
        for p in ds.sieve_primes(97):
            trial["checks"]+=1
            if n%p==0:
                factor=p
                trial["factor"]=p
                source="small_prime_trial_97"
                break
    if factor:
        assert 1<int(factor)<n and n%int(factor)==0
    return dict(classically_solved=bool(factor),factor=int(factor) if factor else None,
        source=source,B47=p47,rho=rho,trial97=trial,
        elapsed_CPU_ms=round(1000*(time.process_time()-start),5),
        quantum_needed_after_fixed_public_filter=not bool(factor))

def validation_factors(n):
    for p in ds.sieve_primes(math.isqrt(n)):
        if n%p==0:
            q=n//p
            assert p<q
            assert all(q%d!=0 for d in range(2,math.isqrt(q)+1))
            return p,q
    raise AssertionError("Semiprime frame invalid")

def common_uniforms(n,m):
    seed=int.from_bytes(hashlib.sha256(f"{SEED}|{n}|{m}".encode()).digest(),"big")
    rng=random.Random(seed)
    u=np.array([rng.random() for _ in range(SAMPLES)],dtype=np.float64)
    v=np.array([rng.random() for _ in range(SAMPLES)],dtype=np.float64)
    return u,v

def stage(n,base,r,m,uniforms):
    u,v=uniforms
    Q=1<<m
    c=np.empty(SAMPLES,dtype=np.int64)
    t=np.empty(SAMPLES,dtype=np.int64)
    for i,ui in enumerate(u):
        s=min(r-1,int(float(ui)*r))
        # Python arbitrary precision s*Q. Int64 would overflow at N25 x Q50.
        q,rem=divmod(s*Q,r)
        if rem*2>=r:
            c[i]=q+1;t[i]=rem-r
        else:
            c[i]=q;t[i]=rem
    val=sample_head(c,t,v,r,Q,base,n)
    head,om,om2,ds_checked,pows,gcds,tail_events,oversum=val
    h=head/SAMPLES
    tmean=om/SAMPLES
    eps_h,var_h=prec.bernstein_eps(h,h,SAMPLES)
    eps_t,var_t=prec.bernstein_eps(tmean,om2/SAMPLES,SAMPLES)
    omission_up=min(1./63.,tmean+eps_t)
    lower=max(0.,h-eps_h)
    upper=min(1.,h+eps_h+omission_up)
    assert 0<=lower<=upper<=1
    assert oversum<=1e-8
    return dict(m=m,lower=lower,upper=upper,
        sample_count=SAMPLES,head_accepted_count=int(head),
        head_accepted_fraction=h,head_variance=var_h,head_error=eps_h,
        tail_mass_mean=tmean,tail_variance=var_t,tail_error=eps_t,
        tail_upper_bound=omission_up,tail_events=int(tail_events),
        online_CF_denominators_checked=int(ds_checked),
        online_modpow_calls=int(pows),online_gcd_calls=int(gcds),
        random_phase_and_outcome_iid_assumed=True)

def score_arm(n,base,order,common,gate_cache):
    rows=[]
    verifier=Counter()
    structural=[]
    for m in STAGES:
        z=stage(n,base,order,m,common[m])
        rows.append(z)
        verifier["denominators_checked"]+=z["online_CF_denominators_checked"]
        verifier["modpow_calls"]+=z["online_modpow_calls"]
        verifier["gcd_calls"]+=z["online_gcd_calls"]
        g=gates.stage_arithmetic_count(n,base,m,gate_cache)
        structural.append(dict(m=m,ccx=int(g["ccx"]),cx=int(g["cx"]),
                          cswap=int(g["cswap"])))
    assert len(rows)==len(STAGES)
    success_low=1-math.prod((1-r["lower"])**SHOTS for r in rows)
    success_high=1-math.prod((1-r["upper"])**SHOTS for r in rows)
    c_low,round_low=tail.cost_for_bound(n,base,rows,gate_cache,"lower")
    c_high,round_high=tail.cost_for_bound(n,base,rows,gate_cache,"upper")
    assert 0<=success_low<=success_high<=1.+1e-10
    assert c_low<=c_high+1e-5
    return dict(base=base,validation_only_order=order,
        factor_probability_by_cap_interval=[success_low,success_high],
        modeled_CCX_attempt_interval=[c_low,c_high],
        modeled_round_interval=[round_low,round_high],
        modeled_CCX_per_factor_success_interval=[
            c_low/success_high if success_high>0 else None,
            c_high/success_low if success_low>0 else None],
        online_CF_evaluation_only_operations=dict(verifier),
        structural_modular_arithmetic_per_stage=structural,
        stages=rows,precomputed_factor_producing_denominators=0)

def selftest():
    # Verify on-demand CF matches independent original public factor verifier
    # for every short measurement, including non-producing denominators.
    checked=0
    for n,a in ((15,2),(21,2),(35,2),(77,2),(143,2)):
        for m in (4,6,8):
            Q=1<<m
            for y in range(Q):
                actual=bool(online_factor_cf(y,Q,a,n)[0])
                expected=bool(tail.old.explicit_cf_proper_factor(n,a,y,m,{}))
                assert actual==expected,(n,a,m,y,actual,expected)
                checked+=1
    # No upfront O(N) factor certificate scan is called anywhere in this file.
    return dict(online_CF_matches_legacy_direct_public_factor_extractor=checked,
                bigint_phase_center=True,native_runtime_disabled=True)

def score(index):
    manifest=read_public()
    spec=manifest["selected_public_rows"][index]
    n,a,b=spec["N"],spec["base"],spec["cube"]
    start=time.process_time()
    tests=selftest()
    classical=classical_budget(n)
    # Only after public manifest frozen and public classical cost recorded:
    p,q=validation_factors(n)
    if classical["factor"]:
        assert n%classical["factor"]==0
    lam=math.lcm(p-1,q-1)
    ra=gates.multiplicative_order_from_lambda(a,n,lam)
    rb=gates.multiplicative_order_from_lambda(b,n,lam)
    assert rb==ra//math.gcd(ra,3)
    wa=gates.factor_witness(a,ra,n)
    wb=gates.factor_witness(b,rb,n)
    assert wa["factor_success"]==wb["factor_success"] and wa["factors"]==wb["factors"]
    common={m:common_uniforms(n,m) for m in STAGES}
    cache={}
    plain=score_arm(n,a,ra,common,cache)
    cube=score_arm(n,b,rb,common,cache)
    compare=tail.classify(plain,cube)
    assert all(len(z["stages"])==24 and z["precomputed_factor_producing_denominators"]==0 for z in (plain,cube))
    row=dict(**spec,public_classical_after_B31=classical,
        validation_only=dict(prime_factors=[p,q],order_plain=ra,
            order_cube=rb,odd_cube_identity=True,half_witness_invariant=True,
            factor_capable=wa["factor_success"]),
        plain=plain,cube=cube,cube_vs_plain=compare,
        model_eval_CPU_seconds=round(time.process_time()-start,5),
        zero_QPU=True)
    out=dict(experiment="dark_star_n25_online_verifier_real_arithmetic_source_model",
        preregistration=PREREG,manifest_sha256=SHA,selected_index=index,
        previously_unknown_sample_before_scoring=True,
        result_complete=True,rows=[row],selftests=tests,
        sampling=dict(samples_per_stage=SAMPLES,stages=list(STAGES),alpha=ALPHA,
            union_family=FAMILY,head_bins=2*W+1,phase_salt=SEED,
            caveat="nominal empirical Bernstein IID pseudorandom phases; not directed-rounded machine proof"),
        claims="source-gate structural logical CCX model, ON-DEMAND public verifier; NOT native transpilation or QPU",
        zero_QPU=True,qpu_jobs_submitted=0,paid_runtime_used=False,
        completed_utc=datetime.now(timezone.utc).isoformat())
    pth=Path(f"n25_{index:02d}.json")
    pth.write_text(json.dumps(out,indent=2)+"\n")
    print("DONE",index,"N",n,"base",a,"orders",ra,"->",rb,
        "classical",classical["source"],"quantum_needed",classical["quantum_needed_after_fixed_public_filter"],
        "ratio",compare["ratio"],compare["status"],
        "seconds",row["model_eval_CPU_seconds"],"file",str(pth),flush=True)

def merge(folder):
    mf=read_public()
    specs=mf["selected_public_rows"]
    rows=[]
    for index,spec in enumerate(specs):
        file=folder/f"n25-row-{index}"/f"n25_{index:02d}.json"
        data=json.loads(file.read_text())
        assert data["manifest_sha256"]==SHA and data["result_complete"]
        assert data["selected_index"]==index and data["zero_QPU"]
        assert data["sampling"]["union_family"]==FAMILY
        assert data["sampling"]["stages"]==list(STAGES)
        assert data["selftests"]["online_CF_matches_legacy_direct_public_factor_extractor"]==((1<<4)+(1<<6)+(1<<8))*5
        assert len(data["rows"])==1
        row=data["rows"][0]
        assert all(row[k]==v for k,v in spec.items())
        assert row["validation_only"]["odd_cube_identity"]
        assert row["validation_only"]["half_witness_invariant"]
        assert row["cube_vs_plain"]==tail.classify(row["plain"],row["cube"])
        assert all(z["precomputed_factor_producing_denominators"]==0 for z in (row["plain"],row["cube"]))
        assert all(len(z["stages"])==24 for z in (row["plain"],row["cube"]))
        rows.append(row)
        print("AUDITED",index,row["N"],row["cube_vs_plain"]["status"],flush=True)
    classes=Counter(r["cube_vs_plain"]["status"] for r in rows)
    usable_plain=sum(r["plain"]["factor_probability_by_cap_interval"][0]>0 for r in rows)
    usable_cube=sum(r["cube"]["factor_probability_by_cap_interval"][0]>0 for r in rows)
    classical_solved=sum(r["public_classical_after_B31"]["classically_solved"] for r in rows)
    pass_model=(classes["cube_model_win"]>=3 and classes["cube_model_loss"]<=1 and usable_cube>=usable_plain)
    summary=dict(total=8,model_statuses=dict(classes),
        bounded_win=classes["cube_model_win"],bounded_loss=classes["cube_model_loss"],
        model_success_lower_positive_plain=usable_plain,
        model_success_lower_positive_cube=usable_cube,
        primary_model_gate_pass=pass_model,
        solved_by_B47_rho64_small_trial=classical_solved,
        quantum_work_remaining_after_public_fixed_filter=8-classical_solved,
        end_to_end_quantum_demand_gate_pass=(8-classical_solved)>0,
        source_arithmetic_only_no_native_hardware=True)
    out=dict(experiment="dark_star_n25_online_8_original_shards_verified",
        preregistration=PREREG,source_manifest_sha256=SHA,complete=True,
        zero_QPU=True,qpu_jobs_submitted=0,paid_runtime_used=False,
        summary=summary,rows=rows,
        note="No full precomputed CF factor table, but ideal sampling validation uses synthetic hidden orders; source CCX counter is NOT a compiled native hardware cost.")
    ROOT.mkdir(parents=True,exist_ok=True)
    merged=ROOT/"dark_star_n25_online_model_all_8.json"
    merged.write_text(json.dumps(out,indent=2)+"\n")
    for i in range(8):
        source=folder/f"n25-row-{i}"/f"n25_{i:02d}.json"
        (ROOT/f"dark_star_n25_online_model_index{i:02d}.json").write_bytes(source.read_bytes())
    print("ALL EIGHT VERIFIED",json.dumps(summary),"NO QPU",flush=True)

def main():
    args=argparse.ArgumentParser()
    mode=args.add_mutually_exclusive_group(required=True)
    mode.add_argument("--index",type=int,choices=range(8))
    mode.add_argument("--merge",action="store_true")
    args.add_argument("--shards",type=Path,default=Path("n25-shards"))
    a=args.parse_args()
    if a.merge:merge(a.shards)
    else:score(a.index)

if __name__=="__main__":
    main()
