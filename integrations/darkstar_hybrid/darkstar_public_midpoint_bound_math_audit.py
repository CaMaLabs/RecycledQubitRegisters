#!/usr/bin/env python3
"""Exact proof audit: PTP residue masks cannot certify factor distance.

This is NOT a prospective performance holdout. Illustrative two 30-bit
constructed composites, exact general algebra, public lower-bound lemma.
Research lead Chase Lunsford / CaMaLabs. CPU ONLY, NO QPU.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime,timezone
from pathlib import Path

from integrations.darkstar_hybrid import darkstar_v2 as ds
from integrations.darkstar_hybrid import midpoint_qr_pruner as qr

OUT=Path("results/dark_star_unified/darkstar_public_midpoint_bounds_mathematical_audit.json")
PRIMES=(3,5,7,11,13,17)
WHEEL=math.prod(PRIMES)
# Construction-only examples: these private factors never enter a
# factoring algorithm or proposed public predictor.
CONSTRUCTED=(
    (922551607,29989,30763),
    (537116557,8719,61603),
)
ASSERT_RESIDUE=60037
ASSERT_OFFSETS=(2,11985)

def x_limit_from_certified_factor_lower_bound(n,lower):
    """If 1<=lower<=p<=sqrt(n), upper bound x=(p+n/p)/2.

    Derived by monotonic decrease of t+n/t on (0,sqrt n].
    The input lower is an EXTERNAL promise or certified exclusion bound;
    NEVER infer from secret p during an attack.
    """
    if lower<1 or lower*lower>n:
        raise ValueError("L needs to be within the possible smaller-factor range")
    return (lower*lower+n)//(2*lower)

def verify_proof_for_odd_n(n):
    assert n>=9 and n%2==1
    x=(n+1)//2
    y=(n-1)//2
    assert x*x-n==y*y
    # Infinite CRT-compatible progression; explicitly check finite prefix
    # as a regression test of the symbolic polynomial identity.
    evidence=[]
    for k in (-2,-1,0,1,2,3,17,101):
        shifted=x+k*WHEEL
        residue=(shifted*shifted-n)%WHEEL
        assert residue==(y*y)%WHEEL
        passes={}
        for ell in PRIMES:
            mask=qr.allowed_mask(ell,n%ell)
            assert mask[shifted%ell]
            passes[str(ell)]=True
        evidence.append(dict(k=k,midpoint_x=shifted,
            residue_difference_square_mod_W=residue,all_QR_masks_pass=True))
    return dict(N=n,x_trivial=x,y_trivial=y,wheel=WHEEL,
        symbolic_identity="(x_trivial+k*M)^2-N=(N-1)^2/4 +2*k*M*x_trivial+k^2*M^2",
        universal_residue_class_x_mod_M=x%WHEEL,
        check_k=evidence)

def deterministic_pair_audit():
    rows=[]
    for n,p,q in CONSTRUCTED:
        assert n==p*q and p<q and p>1 and n.bit_length()==30
        assert ds.is_probable_prime(p) and ds.is_probable_prime(q)
        assert math.gcd(n,WHEEL)==1
        true_x=(p+q)//2
        x0=qr.ceil_sqrt(n)
        d=true_x-x0
        assert d>=0
        y=(q-p)//2
        assert true_x*true_x-n==y*y
        passed=[qr.allowed_mask(ell,n%ell)[true_x%ell] for ell in PRIMES]
        assert all(passed)
        # Generic public lower bound L=19 follows from N coprime to 3..17
        # and 2; do not use p in the bound formula.
        L=19
        bound=x_limit_from_certified_factor_lower_bound(n,L)
        assert true_x<=bound
        rows.append(dict(N=n,synthetic_construction_only_p=p,
            synthetic_construction_only_q=q,
            public_bitlength=n.bit_length(),
            public_N_mod_full_W=n%WHEEL,
            true_Fermat_x_posthoc=true_x,
            true_midpoint_offset_D_posthoc=d,
            true_y_posthoc=y,
            all_actual_midpoint_sieve_masks_pass=all(passed),
            lower_factor_bound_L=19,
            certified_generic_midpoint_upper_bound=bound,
            generic_upper_bound_offset=bound-x0,
            useful_upper_bound_at_2048_bit_RSA=False))
    assert [z["true_midpoint_offset_D_posthoc"] for z in rows]==list(ASSERT_OFFSETS)
    assert rows[0]["public_N_mod_full_W"]==rows[1]["public_N_mod_full_W"]==ASSERT_RESIDUE
    assert rows[0]["public_bitlength"]==rows[1]["public_bitlength"]==30
    return rows

def run():
    rows=deterministic_pair_audit()
    witness=[verify_proof_for_odd_n(n) for n,_,_ in CONSTRUCTED]
    for n in (15,21,35,209,713,4703*10477,8377*14323,2**35-1):
        if n%2:
            witness.append(verify_proof_for_odd_n(n))
    # Exact monotone lemma validated on toy semiprime sample, as a
    # regression check; main mathematical proof in the accompanying doc.
    for n,p,q in CONSTRUCTED:
        actual=(p+q)//2
        for certified_lower in (1,3,5,7,11,17,19,p):
            assert certified_lower<=p
            assert actual<=x_limit_from_certified_factor_lower_bound(n,certified_lower)
    out=dict(experiment="DarkStar_PTP_public_QR_no_proximity_bound_exact_math",
        preregistration="docs/DARK_STAR_PUBLIC_MIDPOINT_BOUND_MATH_PROTOCOL.md",
        scope="deterministic mathematical counterexample and proof; not prospective factoring speed holdout",
        M=WHEEL,sieve_primes=list(PRIMES),
        proof_public_trivial_midpoint_infinite_congruence_progression=True,
        proof_global_factor_lower_bound_formula="x <= floor((L*L+N)/(2*L)) given certified L<=p<=sqrt(N)",
        constructed_same_residue_counterexample=rows,
        actual_synthetic_distance_comparison=dict(
            first_D=rows[0]["true_midpoint_offset_D_posthoc"],
            second_D=rows[1]["true_midpoint_offset_D_posthoc"],
            same_public_bitlength=True,
            same_public_wheel_residue=True,
            first_N_mod_W=rows[0]["public_N_mod_full_W"],
            second_N_mod_W=rows[1]["public_N_mod_full_W"]),
        finite_instances_of_universal_algebra=witness,
        RSA2048_balanced_factor_ratio_at_most_2=True,
        RSA2048_conditional_midpoint_bound="D/sqrt(N) <= 3/(2*sqrt(2))-1 ~= 0.0606601718, order 2^1020 midpoints for 2048-bit moduli",
        no_reliable_public_proximity_prediction_from_QR_masks_alone=True,
        no_claim_no_public_predictor_of_any_kind_exists=True,
        no_new_factoring_speed_or_asymptotic_attack_claim=True,
        quantum_simulator_used=False,zero_QPU=True,IBM_runtime_jobs=0,
        generated_utc=datetime.now(timezone.utc).isoformat())
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2)+"\n")
    print("EXACT MATHEMATICAL CERTIFICATE",json.dumps(out["actual_synthetic_distance_comparison"]),flush=True)
    print("PROOF QR trivial midpoint repeating with M",WHEEL,"and exact factor-size x bound; NO QPU",flush=True)

if __name__=="__main__":
    run()
