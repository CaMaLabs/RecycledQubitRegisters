#!/usr/bin/env python3
"""Public N35 mathematical IDEAL QFT phase precision 4/6/8, no QPU.

Research lead Chase Lunsford / CaMaLabs. Reverify existing implemented four
WIDE phase-control source before extrapolating ideal six/eight-bit precision.
New six/eight-bit models are mathematical ideal projections, NOT implemented
gate-source checks, IBM Fez native compilation, iterative recycling, or shots.
Independent complex FFT vs literal Qiskit Statevector QFT. Strict and bounded
public-only fraction/GCD policy unchanged with maximum public r=64.
"""
from __future__ import annotations

import argparse
import json
import math
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from qiskit.quantum_info import Statevector
from qiskit.circuit.library import QFTGate

import qrr_n35_four_bit_ideal_outcome_scoring as original

N=35
BASES=(2,8)
BITS=(4,6,8)
MAX_PUBLIC_R=64
REV="qrr-n35-ideal-phase-precision-4-6-8-v1-20261020"
ROOT=Path("results/n35_ideal_phase_precision")
EPS=1e-9


def public_cf_denominators(k,M):
    """Unmodified regular CF-convergent algorithm, generalized 16->M."""
    if not (0<=k<M):
        raise ValueError("Out of range public readout fraction")
    if k==0:
        return []
    n,d=k,M
    coefficients=[]
    while d:
        digit,remainder=divmod(n,d)
        coefficients.append(digit)
        n,d=d,remainder
    pn2,pn1=0,1
    qn2,qn1=1,0
    qs=[]
    for a in coefficients:
        p=a*pn1+pn2
        q=a*qn1+qn2
        if 2<=q<=M and q not in qs:
            qs.append(q)
        pn2,pn1=pn1,p
        qn2,qn1=qn1,q
    rational_final=M//math.gcd(k,M)
    if rational_final not in qs:
        raise AssertionError(f"Missing exact final CF denominator {k}/{M}")
    return qs


def public_factor_witness(base,r):
    """Identical frozen original factor-from-r conditions, public a,N only."""
    if r<2 or r%2:
        return None
    if pow(base,r,N)!=1:
        return None
    z=pow(base,r//2,N)
    gm=math.gcd(z-1,N)
    gp=math.gcd(z+1,N)
    found=sorted(g for g in (gm,gp) if 1<g<N and N%g==0)
    if not found:
        return None
    return dict(r=r,proper_factor=found[0],complementary_factor=N//found[0],
                public_half_power=z,gcd_minus=gm,gcd_plus=gp)


def public_cf_policy(base,k,M,max_multiple):
    """Frozen strict m=1 or generous bounded m<=4, r<=64; no order data."""
    assert max_multiple in (1,4)
    qs=public_cf_denominators(k,M)
    tried=[]
    seen=set()
    even_tests=0
    witness=None
    for q in qs:
        for m in range(1,max_multiple+1):
            r=q*m
            if r>MAX_PUBLIC_R or r in seen:
                continue
            seen.add(r)
            even=(r%2==0)
            tried.append(dict(q=q,multiplier=m,r=r,even=even))
            if not even:
                continue
            even_tests+=1
            found=public_factor_witness(base,r)
            if found is not None and witness is None:
                witness=dict(continued_fraction_q=q,public_multiple=m,**found)
    return dict(success=witness is not None,first_success=witness,
                continued_fraction_denominators=qs,
                all_public_r_candidates=tried,
                public_even_exponent_tests=even_tests,
                input_measurement_zero_policy=(k==0 and len(tried)==0))


def classic_controls(base):
    gm=math.gcd(base-1,N)
    gp=math.gcd(base+1,N)
    immediate=sorted(z for z in (gm,gp) if 1<z<N and N%z==0)
    even=[dict(candidate_even_r=r,result=public_factor_witness(base,r))
          for r in (2,4,6,8)]
    return dict(gcd_base_minus_one=gm,gcd_base_plus_one=gp,
        pre_qft_immediate_factor=immediate[0] if immediate else None,
        pre_qft_classical_gcd_preempts_quantum_claim=bool(immediate),
        four_public_even_exponent_scan=even,
        classical_even_exponent_scan_finds_factor=any(
              x['result'] is not None for x in even),
        no_true_order_or_factors_to_select_exponents=True)


def original_historic_anchor(base):
    """Check exact OLD original source and all 16 original scoring rows."""
    d=json.loads(Path(
       f"results/n35_ideal_iqft_outcome/qrr_n35_ideal_iqft_outcomes_base{base}.json"
    ).read_text())
    assert d["N"]==N and d["public_base"]==base and d["success"]
    assert d["status"]=="ALL_IDEAL_OUTCOME_AND_CLASSICAL_SCORE_PROOFS_PASS"
    assert d["source_phase_qubits"]==4 and d["original_source_ancillas"]==25
    p=d["previous_source_exact_gate_verification"]
    assert p["pass_all"] and p["all_25_ancillas_returned_zero"]
    assert p["quantum_complex_output_phase_plus_one"]
    assert d["independent_analytic_statevector_check"][
       "all_1024_complex_amplitudes_checked"]
    return d


def phase_probabilities(base,bits):
    """Actual literal QFTGate(b).inverse() on (b+6) reduced ideal state.

    Independent analytic FFT across phase axis. Known clean-aux 4bit source
    guarantees only prior 4-bit implemented unitary; 6/8 are CONDITIONAL ideal.
    """
    M=1<<bits
    values=[pow(base,c,N) for c in range(M)]
    if any(not (0<=y<N) for y in values):
        raise AssertionError("Public modular work output outside six-bit valid domain")
    vector=np.zeros(M*64,dtype=np.complex128)
    for c,y in enumerate(values):
        vector[c+M*y] += 1/math.sqrt(M)
    if abs(float(np.vdot(vector,vector).real)-1)>1e-10:
        raise AssertionError("Input ideal QFT state not normalized")
    tick=time.perf_counter()
    qiskit=np.asarray(
        Statevector(vector).evolve(QFTGate(bits).inverse(),
                                  qargs=list(range(bits))).data,dtype=complex)
    elapsed=time.perf_counter()-tick
    # The first axis is a six-bit WORK basis y, the second is phase c.
    # FFT sign - matches the verified four-qubit QFTGate.inverse convention.
    analytic=np.fft.fft(vector.reshape((64,M)),axis=1)/math.sqrt(M)
    analytic=analytic.reshape(M*64)
    max_amp=float(np.max(np.abs(qiskit-analytic)))
    if max_amp>EPS:
        raise AssertionError(
            f"Analytic Fourier versus independent Qiskit inverse QFT mismatch bits={bits} base={base} max={max_amp}")
    p_q=np.sum(np.abs(qiskit.reshape((64,M)))**2,axis=0)
    p_analytic=np.sum(np.abs(analytic.reshape((64,M)))**2,axis=0)
    if float(np.max(np.abs(p_q-p_analytic)))>EPS:
        raise AssertionError("QFT full 64-work trace does not agree with independent FFT")
    p=np.asarray(p_analytic,dtype=float)
    if (not np.all(np.isfinite(p))) or np.min(p)<-1e-11:
        raise AssertionError("Invalid ideal QFT outcome probability")
    if abs(float(np.sum(p))-1)>1e-10:
        raise AssertionError(f"Probability not normalized for bits={bits}")
    predicted_schedule=[pow(base,1<<i,N) for i in range(bits)]
    return p,dict(pass_all=True,phase_bits=bits,precision_M=M,
       independent_literal_Qiskit_QFTGate_Statevector=True,
       independent_Numpy_complex_FFT=True,
       actual_complex_amplitude_comparison_count=M*64,
       max_complex_amplitude_difference=max_amp,
       phase_probability_sum=float(np.sum(p)),
       vector_norm_1=True,all_64_work_residues_traced_out=True,
       original_powers_from_public_pow_only=True,
       reachable_reduced_state_qubits=bits+6,
       literal_QFT_statevector_cpu_seconds=elapsed,
       physical_backend_read=False,real_device_shots=0,
       public_work_values_for_every_control=values,
       public_controlled_power_schedule=predicted_schedule,
       public_nonidentity_controlled_power_count=sum(x!=1 for x in predicted_schedule),
       hypothetical_WIDE_logical_qubits=bits+6+25,
       hypothetical_WIDE_device_CZ_unknown=True,
       hypothetical_WIDE_device_depth_unknown=True,
       not_an_implemented_six_or_eight_bit_source=(bits!=4),
       no_adaptive_or_recycled_control_circuit_constructed=True)


def score_width(base,bits,history):
    M=1<<bits
    p,proof=phase_probabilities(base,bits)
    if bits==4:
        old_rows=history["ideal_phase_outcome_rows"]
        assert len(old_rows)==16
        for k,previous_row in enumerate(old_rows):
            if abs(float(p[k])-float(previous_row["ideal_probability"]))>EPS:
                raise AssertionError(f"Four-bit historical probability anchor drift base={base} k={k}")
    rows=[]
    strict_hit=[]
    bounded_hit=[]
    for k in range(M):
        strict=public_cf_policy(base,k,M,1)
        bounded=public_cf_policy(base,k,M,4)
        if strict["success"] and not bounded["success"]:
            raise AssertionError("Strict public policy cannot beat identical bounded policy")
        if k==0 and (strict["success"] or bounded["success"]):
            raise AssertionError("Public phase zero cannot succeed")
        if bits==4:
            old=history["ideal_phase_outcome_rows"][k]
            for key,policy in (("strict_CF_convergents",strict),
                               ("bounded_public_multiples_upto_four",bounded)):
                old_policy=old[key]
                for f in ("success","first_success","continued_fraction_denominators",
                          "public_even_exponent_tests","all_public_r_candidates",
                          "input_measurement_zero_policy"):
                    if policy[f]!=old_policy[f]:
                        raise AssertionError(
                          f"Fourbit CLASSICAL policy drift base={base} k={k} {key}.{f}")
        rows.append(dict(phase_outcome_k=k,phase_fraction=f"{k}/{M}",
                ideal_probability=float(p[k]),strict_CF_convergents=strict,
                bounded_public_multiples_upto_four=bounded))
        strict_hit.append(int(strict["success"]))
        bounded_hit.append(int(bounded["success"]))
    strict_p=float(np.dot(p,np.array(strict_hit)))
    bounded_p=float(np.dot(p,np.array(bounded_hit)))
    result=dict(
       exact_ideal_probabilities_all_outcomes=[float(x) for x in p],
       outcome_case_count=M,
       outcomes=rows,
       quantum_probability_verification=proof,
       public_postprocessing=dict(
         strict_CF_ideal_success_probability=strict_p,
         bounded_4_public_multiples_ideal_success_probability=bounded_p,
         strict_cf_uniform_k_baseline=float(np.mean(strict_hit)),
         bounded_cf_uniform_k_baseline=float(np.mean(bounded_hit)),
         strict_successful_k=[i for i,x in enumerate(strict_hit) if x],
         bounded_successful_k=[i for i,x in enumerate(bounded_hit) if x],
         zero_phase_outcome_probability=float(p[0]),
         strictly_public_candidate_max_r=MAX_PUBLIC_R,
         bounded_policy_multipliers=[1,2,3,4],
         no_true_order_input=True,
         every_k_including_zero_scored=True
       ))
    if bits==4:
        past=history["postprocessing_score"]
        assert abs(strict_p-past["strict_cf_ideal_success_probability"])<EPS
        assert abs(bounded_p-past["bounded_4_public_multiples_ideal_success_probability"])<EPS
        assert abs(result["public_postprocessing"]["strict_cf_uniform_k_baseline"]-
                   past["strict_cf_uniform_fourbit_k_baseline"])<EPS
        assert abs(result["public_postprocessing"]["bounded_cf_uniform_k_baseline"]-
                   past["bounded_cf_uniform_fourbit_k_baseline"])<EPS
    return result


def run_base(base):
    if base not in BASES:raise ValueError("Public base missing")
    ROOT.mkdir(parents=True,exist_ok=True)
    dest=ROOT/f"qrr_n35_ideal_phase_precision_base{base}.json"
    result=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
        date_utc=datetime.now(timezone.utc).isoformat(),
        preregistration="docs/QRR_N35_IDEAL_PHASE_PRECISION_4_6_8_PREREG.md",
        N=N,public_base=base,frozen_phase_bits=list(BITS),
        scope="IDEAL analytic and Qiskit reduced-state phase precision 4/6/8; only previous 4 wide qubits implemented",
        source_work_bits=6,source_clean_ancillas=25,
        identical_fixed_public_r_ceiling=MAX_PUBLIC_R,
        actual_qpu_jobs=0,actual_device_shots=0,
        no_backend_token_or_device_access=True,no_free_or_paid_quantum_runtime=True,
        new_six_eight_bit_circuit_built=False,
        recycled_phase_control_implemented=False,
        outcomes_by_phase_bits={},
        success=False,status="STARTED")
    def save():dest.write_text(json.dumps(result,indent=2,default=str)+"\n")
    save()
    try:
        source=original.source_proof(base)
        assert source["pass_all"] and source["quantum_complex_output_phase_plus_one"]
        assert source["all_25_ancillas_returned_zero"]
        for z in ("original","selected"):
            p=source["full_power_source_proofs"][z]
            assert p["exact_source_operator_basis_cases"]==1024
            assert p["all_25_helpers_clean"] and p["exact_complex_phase_plus_one"]
        history=original_historic_anchor(base)
        result["verified_existing_4bit_full_source"]=source
        result["historical_original_fourbit_receipt"]=(
           f"results/n35_ideal_iqft_outcome/qrr_n35_ideal_iqft_outcomes_base{base}.json")
        result["status"]="ORIGINAL_FOUR_BIT_SOURCE_GATE_PROOF_PASSED"
        save()
        print("ORIGINAL ACTUAL 35Q FOUR-BIT SOURCE 1024+1024 PASS base",base,
              "ALL 25 CLEAN, quantum phase exactly +1",flush=True)
        baseline=classic_controls(base)
        result["public_classical_prechecks"]=baseline
        for bits in BITS:
            result["outcomes_by_phase_bits"][str(bits)]=score_width(base,bits,history)
            result["status"]=f"IDEAL_{bits}BIT_PROVED"
            save()
            s=result["outcomes_by_phase_bits"][str(bits)]["public_postprocessing"]
            q=result["outcomes_by_phase_bits"][str(bits)]["quantum_probability_verification"]
            print("N35 PHASE PRECISION",base,"BITS",bits,"M",1<<bits,
               "IDEAL_STRICT",s["strict_CF_ideal_success_probability"],
               "IDEAL_BOUNDED",s["bounded_4_public_multiples_ideal_success_probability"],
               "UNIFORM_STRICT",s["strict_cf_uniform_k_baseline"],
               "UNIFORM_BOUNDED",s["bounded_cf_uniform_k_baseline"],
               "ZERO_OUTCOME",s["zero_phase_outcome_probability"],
               "FFT_VS_QISKIT_MAX_AMP",q["max_complex_amplitude_difference"],
               "PUBLIC_STAGES",q["public_nonidentity_controlled_power_count"],
               "WIDE_LOGICAL_QUANTUM_QUBITS_FORECAST",q["hypothetical_WIDE_logical_qubits"],
               "NO QPU",flush=True)
        # Only AFTER all candidate generation and scores, descriptive order.
        hits=[r for r in range(1,71) if pow(base,r,N)==1]
        if not hits:raise AssertionError("Post-scoring public order check empty")
        true_order=min(hits)
        assert true_order==(12 if base==2 else 4)
        result["descriptive_order_after_all_scores"]={
           "public_power_bruteforce_first_r":true_order,
           "order_not_used_in_model_or_postprocessing":True}
        result["status"]="ALL_4_6_8_IDEAL_QFT_AND_PUBLIC_SCORING_PROOFS_PASS"
        result["success"]=True
        save()
        print("N35 COMPLETE 4/6/8 IDEAL PROJECTION",base,
              "B4 ORIGINAL ANCHOR VERIFIED, ALL AMPLITUDES QFT/FFT EQUAL",
              "PUBLIC GCD IMMEDIATE",baseline["pre_qft_immediate_factor"],
              "6/8 ARE NOT COMPILED, NO QPU",flush=True)
        return 0
    except Exception as exc:
        result.update(success=False,status="FAIL",
           failure_class=type(exc).__name__,
           failure_message=str(exc)[:1600],
           failure_traceback=traceback.format_exc()[-2700:],
           actual_qpu_jobs=0,actual_device_shots=0)
        save()
        print("N35 4/6/8 IDEAL PROJECTION FAILURE",base,type(exc).__name__,
              str(exc)[:650],traceback.format_exc()[-1100:],"ZERO QPU",flush=True)
        return 1


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--base",required=True,type=int,choices=BASES)
    raise SystemExit(run_base(p.parse_args().base))
